from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .manifest import load_manifest, manifest_item_for
from .metadata import extract_metadata
from .pipeline import EpubPipeline, collect_typst_files, copy_report, run_epubcheck, validate_epub


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Converte fontes Typst de MTG Stories para EPUB3")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path, help="Arquivo Typst específico")
    source.add_argument("--set", dest="set_name", help="Nome exato ou parcial da coleção")
    source.add_argument("--all", action="store_true", help="Converte todas as coleções")
    parser.add_argument("--combine", action="store_true", help="Gera também um EPUB omnibus")
    parser.add_argument("--output-dir", type=Path, default=Path("epubs"))
    parser.add_argument("--stories-dir", type=Path, default=Path("stories"))
    parser.add_argument("--manifest", type=Path, default=Path("scraped_manifest.json"))
    parser.add_argument("--fonts-dir", type=Path, default=Path("fonts"), help="Diretório opcional com arquivos ZIP/ fontes temáticas")
    parser.add_argument("--report", type=Path, help="Arquivo JSON com o resultado da execução")
    parser.add_argument("--jobs", type=int, default=1, help="Conversões simultâneas")
    parser.add_argument("--force", action="store_true", help="Ignora o cache")
    parser.add_argument("--no-validate", action="store_true", help="Desativa a validação estrutural")
    parser.add_argument("--epubcheck", type=Path, nargs="?", const=Path("tools/epubcheck-5.4.0/epubcheck.jar"), help="Executa EpubCheck; sem valor usa a instalação local")
    parser.add_argument("--validate", type=Path, help="Valida um EPUB existente")
    return parser


def _check_pandoc() -> None:
    if shutil.which("pandoc") is None:
        raise RuntimeError("Pandoc não encontrado no PATH")
    subprocess.run(["pandoc", "-v"], check=True, capture_output=True, text=True)


def _target_sets(args: argparse.Namespace) -> list[Path]:
    if args.set_name:
        candidates = [path for path in args.stories_dir.iterdir() if path.is_dir() and args.set_name.lower() in path.name.lower()]
        if len(candidates) != 1:
            raise ValueError(f"Coleção ambígua ou inexistente: {args.set_name}")
        return candidates
    return sorted(path for path in args.stories_dir.iterdir() if path.is_dir())


def _metadata(path: Path, manifest: dict) -> object:
    return extract_metadata(path, manifest_item_for(path, manifest))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.validate:
        problems = validate_epub(args.validate)
        if args.epubcheck:
            checker = args.epubcheck if args.epubcheck.is_absolute() else (Path.cwd() / args.epubcheck).resolve()
            problems.extend(run_epubcheck(args.validate, checker))
        if problems:
            for problem in problems:
                print(f"[ERRO] {problem}", file=sys.stderr)
            return 1
        print(f"[OK] EPUB válido: {args.validate}")
        return 0
    if not (args.file or args.set_name or args.all):
        build_parser().error("forneça --file, --set ou --all")

    try:
        _check_pandoc()
        manifest = load_manifest(args.manifest)
        epubcheck = args.epubcheck
        if epubcheck and not epubcheck.is_absolute():
            epubcheck = (Path.cwd() / epubcheck).resolve()
        pipeline = EpubPipeline(args.output_dir, epubcheck=epubcheck if not args.no_validate else None, fonts_dir=args.fonts_dir)
        jobs = max(1, args.jobs)
        tasks: list[tuple[Path, Path, object, bool]] = []
        if args.file:
            source = args.file.resolve()
            tasks.append((source, args.output_dir / source.with_suffix(".epub").name, _metadata(source, manifest), False))
        else:
            for set_folder in _target_sets(args):
                for source in collect_typst_files(set_folder):
                    metadata = _metadata(source, manifest)
                    output = args.output_dir / set_folder.name / source.with_suffix(".epub").name
                    tasks.append((source, output, metadata, False))
                if args.combine:
                    sources = collect_typst_files(set_folder)
                    if sources:
                        metadata = _metadata(sources[0], manifest)
                        metadata = metadata.__class__(
                            title=f"{metadata.set_name} (Complete Stories)",
                            set_name=metadata.set_name,
                            author="Wizards of the Coast",
                            date=metadata.date,
                            series=metadata.series,
                            series_index=1,
                            source_file=sources[0],
                            cover_image=metadata.cover_image,
                        )
                        tasks.append((set_folder, args.output_dir / set_folder.name / f"{set_folder.name} - Omnibus.epub", (sources, metadata), True))

        def execute(task: tuple[Path, Path, object, bool]):
            source, output, metadata, combine = task
            if combine:
                sources, omnibus_metadata = metadata
                return pipeline.convert(sources, output, omnibus_metadata, combine=True, force=args.force)
            return pipeline.convert([source], output, metadata, force=args.force)

        with ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(execute, tasks)) if jobs > 1 else [execute(task) for task in tasks]
        if not args.no_validate:
            for result in results:
                if result.success and validate_epub(result.output):
                    result.success = False
                    result.status = "failed"
                    result.error = "falha na validação EPUB"
        report = args.report or args.output_dir / "conversion-report.json"
        copy_report(report, results)
        for result in results:
            prefix = "OK" if result.success else "ERRO"
            print(f"[{prefix}] {result.status}: {result.output}")
        failures = sum(not result.success for result in results)
        print(f"Resumo: {len(results) - failures} sucesso(s), {failures} falha(s), relatório: {report}")
        return 1 if failures else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[ERRO] {error}", file=sys.stderr)
        return 1
