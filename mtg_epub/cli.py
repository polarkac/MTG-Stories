from __future__ import annotations

import argparse
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from .manifest import load_manifest, manifest_item_for
from .metadata import extract_metadata, _readable_set_name
from .models import StoryMetadata
from .pipeline import EpubPipeline, collect_typst_files, copy_report, run_epubcheck, validate_epub
from .sluggyfy import slugify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_name_from_slug(slug: str) -> str:
    return _readable_set_name(slug)


def _set_slug(path: Path) -> str:
    """Slug do set a partir do nome da pasta (ex.: '058-duskmourn-...' -> 'duskmourn-...')."""
    return re.sub(r"^\d+[-_\s]*", "", path.name)


def _set_name(path: Path) -> str:
    """Nome legível do set (usa set-names.json)."""
    from .metadata import readable_set_name_from_folder
    return readable_set_name_from_folder(path.name)


def _collection_key(value: str) -> str:
    """Normaliza um slug/nome para comparação: minúsculas, sem números iniciais, sem pontuação."""
    value = re.sub(r"^\d+[-_\s]*", "", value)   # remove "058-", "058 ", "058_"
    value = value.casefold().replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _appendix_target(folder_name: str, story_slugs: list[str]) -> str | None:
    """
    Recebe o nome da pasta do guide/card_lore e a lista de slugs de sets.
    Devolve o slug do set alvo, ou None (caso de Ulgrotha e livros autônomos).
    """
    # 1. Remove número inicial (ex.: "057 - ", "001 - ")
    no_num = re.sub(r"^\d+[-_\s]*", "", folder_name).strip()
    # 2. Remove prefixo de guias de planeswalker (com ou sem 's, hífen ou espaço)
    cleaned = re.sub(
        r"^planeswalkers?(?:['’]s)?[\s\-_]*(?:guides?[\s\-_]*(?:to)?[\s\-_]*)?",
        "",
        no_num,
        flags=re.IGNORECASE,
    ).strip()
    key = _collection_key(cleaned)

    # Ulgrotha vira livro autônomo (não anexado a nenhum set existente)
    if "ulgrotha" in key:
        return None

    direct = {_collection_key(s): s for s in story_slugs}
    if key in direct:
        return direct[key]

    if "zendikar" in key:
        return next((s for s in story_slugs if _collection_key(s) == "battle for zendikar"), None)
    if "new phyrexia" in key or "phyrexia" in key:
        return next((s for s in story_slugs if "phyrexia" in _collection_key(s)), None)
    return None


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Converte fontes Typst de MTG Stories para EPUB3")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path, help="Arquivo Typst específico")
    source.add_argument("--set", dest="set_name", help="Nome exato ou parcial da coleção")
    source.add_argument("--all", action="store_true", help="Converte todas as coleções")
    source.add_argument("--collection", action="store_true", help="Gera a coleção Magic Stories, um EPUB por set")
    parser.add_argument("--compress-images", action="store_true", help="Comprime imagens do acervo com Pillow para otimizar tamanho em e-readers")
    parser.add_argument("--combine", action="store_true", help="Gera também um EPUB omnibus")
    parser.add_argument("--output-dir", type=Path, default=Path("epubs"))
    parser.add_argument("--stories-dir", type=Path, default=Path("stories"))
    parser.add_argument("--manifest", type=Path, default=Path("scraped_manifest.json"))
    parser.add_argument("--fonts-dir", type=Path, default=Path("fonts"))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--jobs", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--epubcheck", type=Path, nargs="?", const=Path("tools/epubcheck-5.4.0/epubcheck.jar"))
    parser.add_argument("--validate", type=Path)
    return parser


# ---------------------------------------------------------------------------
# Seleção de sets
# ---------------------------------------------------------------------------

def _target_sets(args: argparse.Namespace) -> list[Path]:
    if args.set_name:
        needle = slugify(args.set_name)
        candidates = [
            path for path in args.stories_dir.iterdir()
            if path.is_dir() and needle in slugify(path.name)
        ]
        if len(candidates) != 1:
            raise ValueError(f"Coleção ambígua ou inexistente: {args.set_name}")
        return candidates
    return sorted(path for path in args.stories_dir.iterdir() if path.is_dir())


def _metadata(path: Path, manifest: dict) -> StoryMetadata:
    return extract_metadata(path, manifest_item_for(path, manifest))


# ---------------------------------------------------------------------------
# Tarefas de coleção
# ---------------------------------------------------------------------------

def _collection_tasks(
    stories_dir: Path,
    guides_dir: Path,
    card_lore_dir: Path,
    manifest: dict,
    output_dir: Path,
) -> list[tuple[list[Path], Path, StoryMetadata, list[str]]]:
    def _sort_key(path: Path) -> int:
        m = re.match(r"^(\d+)", path.name)
        return int(m.group(1)) if m else 999

    story_folders = sorted(
        (p for p in stories_dir.iterdir() if p.is_dir()),
        key=_sort_key,
    )
    story_slugs = [_set_slug(f) for f in story_folders]

    appendices: dict[str, list[tuple[Path, str]]] = {}

    for root_dir, kind in ((guides_dir, "Guide"), (card_lore_dir, "Card Lore")):
        if not root_dir.exists():
            continue
        for folder in sorted(p for p in root_dir.iterdir() if p.is_dir()):
            typ_sources = sorted(folder.glob("*.typ"))
            if not typ_sources:
                continue

            target_slug = _appendix_target(folder.name, story_slugs)
            if target_slug is None:
                target_slug = _set_slug(folder)

            appendices.setdefault(target_slug, []).extend(
                (source, kind) for source in typ_sources
            )

    tasks: list[tuple[list[Path], Path, StoryMetadata, list[str]]] = []
    seen_targets: set[str] = set()

    # Fluxo 1: sets COM episódios
    for folder in story_folders:
        set_slug = _set_slug(folder)
        set_name = _set_name(folder)

        sources = collect_typst_files(folder)
        chapter_titles = [
            extract_metadata(source, manifest_item_for(source, manifest)).title
            for source in sources
        ]
        story_metadata = [_metadata(source, manifest) for source in sources]
        first_episode = story_metadata[0] if story_metadata else None

        for source, kind in appendices.get(set_slug, []):
            sources.append(source)
            item = manifest_item_for(source, manifest)
            chapter_titles.append(f"[{kind}] {extract_metadata(source, item).title}")
            story_metadata.append(_metadata(source, manifest))

        if not sources:
            continue

        authors: list[str] = []
        for item in story_metadata:
            if item.author not in authors:
                authors.append(item.author)

        if first_episode is not None:
            cover_image = first_episode.cover_image
        elif story_metadata:
            cover_image = next((m.cover_image for m in story_metadata if m.cover_image), None)
        else:
            cover_image = None

        metadata = StoryMetadata(
            title=set_name,
            set_name=set_name,
            author=", ".join(authors),
            date=first_episode.date if first_episode else "",
            series="Magic Stories Collection",
            series_index=_sort_key(folder),
            source_file=sources[0],
            cover_image=cover_image,
        )
        tasks.append((sources, output_dir / f"{set_name}.epub", metadata, chapter_titles))
        seen_targets.add(set_slug)

    # Fluxo 2: apêndices órfãos
    for set_slug, appendix_sources in appendices.items():
        if set_slug in seen_targets:
            continue

        sources = [source for source, _ in appendix_sources]
        if not sources:
            continue

        chapter_titles = [
            f"[{kind}] {extract_metadata(source, manifest_item_for(source, manifest)).title}"
            for source, kind in appendix_sources
        ]
        metadata_items = [_metadata(source, manifest) for source in sources]

        authors: list[str] = []
        for item in metadata_items:
            if item.author not in authors:
                authors.append(item.author)

        set_name = _set_name_from_slug(set_slug)

        metadata = StoryMetadata(
            title=set_name,
            set_name=set_name,
            author=", ".join(authors),
            date="",
            series="Magic Stories Collection",
            series_index=999,
            source_file=sources[0],
            cover_image=next((m.cover_image for m in metadata_items if m.cover_image), None),
        )
        tasks.append((sources, output_dir / f"{set_name}.epub", metadata, chapter_titles))

    return tasks


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

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

    if args.compress_images and not (args.file or args.set_name or args.all or args.collection):
        from .image_compressor import batch_compress_directories
        print("[Otimização] Iniciando compressão de imagens do acervo...")
        batch_compress_directories([args.stories_dir, Path("planeswalkers_guides"), Path("card_lore")])
        return 0

    if not (args.file or args.set_name or args.all or args.collection):
        build_parser().error("forneça --file, --set, --all, --collection ou --compress-images")

    if args.compress_images:
        from .image_compressor import batch_compress_directories
        print("[Otimização] Iniciando compressão de imagens do acervo...")
        batch_compress_directories([args.stories_dir, Path("planeswalkers_guides"), Path("card_lore")])

    try:
        manifest = load_manifest(args.manifest)
        epubcheck = args.epubcheck
        if epubcheck and not epubcheck.is_absolute():
            epubcheck = (Path.cwd() / epubcheck).resolve()
        pipeline = EpubPipeline(
            args.output_dir,
            epubcheck=epubcheck if not args.no_validate else None,
            fonts_dir=args.fonts_dir,
        )
        max_system_workers = os.cpu_count() or 1
        jobs = args.jobs if args.jobs > 0 else max_system_workers

        tasks: list[tuple[list[Path], Path, object, list[str] | None]] = []

        if args.collection:
            collection_dir = args.output_dir / "Magic Stories Collection"
            tasks_data = _collection_tasks(
                args.stories_dir,
                Path("planeswalkers_guides"),
                Path("card_lore"),
                manifest,
                collection_dir,
            )
            tasks = [(t[0], t[1], t[2], t[3]) for t in tasks_data]
            report = args.report or collection_dir / "collection-report.json"
        else:
            report = args.report or args.output_dir / "conversion-report.json"
            if args.file:
                source = args.file.resolve()
                tasks.append(([source], args.output_dir / source.with_suffix(".epub").name, _metadata(source, manifest), None))
            else:
                for set_folder in _target_sets(args):
                    for source in collect_typst_files(set_folder):
                        metadata = _metadata(source, manifest)
                        output = args.output_dir / set_folder.name / source.with_suffix(".epub").name
                        tasks.append(([source], output, metadata, None))
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
                            tasks.append((sources, args.output_dir / set_folder.name / f"{set_folder.name} - Omnibus.epub", metadata, None))

        import queue

        slots: "queue.Queue[int]" = queue.Queue()
        for i in range(jobs):
            slots.put(i)

        print(f"Iniciando compilação com {jobs} worker(s)...\n")

        main_pbar = tqdm(total=len(tasks), position=0, desc="Progresso Geral", unit="EPUB")
        worker_bars = []
        for i in range(jobs):
            b = tqdm(total=0, position=i + 1, bar_format="{desc}", leave=False)
            b.set_description_str(f"Worker {i+1}: ⏳ Aguardando...".ljust(70))
            worker_bars.append(b)

        def execute_task(task_info):
            if len(task_info) == 4:
                sources, output, metadata, chapter_titles = task_info
            else:
                sources, output, metadata, _, chapter_titles = task_info
            name = output.stem
            
            # O worker pega uma linha disponível
            slot = slots.get()
            
            # O ljust(70) preenche com espaços para apagar o nome do arquivo anterior caso fosse maior
            display_name = name[:45] + ("..." if len(name) > 45 else "")
            worker_bars[slot].set_description_str(f"Worker {slot+1}: ⚙️ {display_name}".ljust(70))
            
            # Compila
            result = pipeline.convert(sources, output, metadata, force=args.force, chapter_titles=chapter_titles)
            
            # Atualiza o total, devolve a linha e volta pro estado aguardando
            worker_bars[slot].set_description_str(f"Worker {slot+1}: ⏳ Aguardando...".ljust(70))
            main_pbar.update(1)
            slots.put(slot)
            
            return result

        with ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = [executor.submit(execute_task, t) for t in tasks]
            results = [f.result() for f in futures]

        # Finaliza e limpa as barras de interface
        main_pbar.close()
        for b in worker_bars:
            b.close()
            
        # Pula as linhas que os workers usaram para evitar sobrepor texto no terminal
        print("\n" * jobs)

        # Validação estrutural de EPUBs isolados (opcional, como estava no seu código)
        if not args.no_validate and not args.collection:
            for result in results:
                if result.success and validate_epub(result.output):
                    result.success = False
                    result.status = "failed"
                    result.error = "falha na validação EPUB"

        copy_report(report, results)
        for result in results:
            if not result.success:
                print(f"[ERRO] {result.status}: {result.output} - {result.error}")
                
        failures = sum(not result.success for result in results)
        print(f"\nResumo: {len(results) - failures} sucesso(s), {failures} falha(s)")
        print(f"Relatório detalhado: {report}")
        return 1 if failures else 0

    except (OSError, RuntimeError, ValueError) as error:
        print(f"[ERRO] {error}", file=sys.stderr)
        return 1