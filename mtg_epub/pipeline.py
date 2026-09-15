from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from zipfile import ZIP_STORED, ZipFile

from .metadata import extract_metadata
from .models import ConversionResult, StoryMetadata
from .text import sanitize_typst_for_pandoc
from .themes import DEFAULT_FONTS_DIR, load_theme_css, prepare_theme_fonts, theme_for_set

try:
    from PIL import Image
except ImportError:
    Image = None


EPUB_CSS = """
@charset "utf-8";
body { font-family: "Palatino Linotype", Palatino, Georgia, serif; font-size: 1.05em; line-height: 1.5; margin: 4% 5%; color: #1a1a1a; background-color: #fafafa; text-align: justify; -webkit-hyphens: auto; hyphens: auto; }
p { margin-top: 0; margin-bottom: 0; text-indent: 1.5em; widows: 2; orphans: 2; }
h1 { page-break-before: always; page-break-after: avoid; font-size: 1.9em; line-height: 1.25; margin: 1.5em 0 .8em; text-align: center; font-weight: bold; }
h2, h3 { page-break-after: avoid; }
h1 + p::first-letter { font-size: 3.2em; font-weight: bold; float: left; margin: .05em .1em 0 0; line-height: .8; }
p.first-p, h1 + p, h2 + p, h3 + p, hr + p, blockquote + p { text-indent: 0; margin-top: 1em; }
blockquote { margin: 1.2em 1em; padding: .5em 1em; border-left: 4px solid #555; background-color: #f7f7f7; font-style: italic; }
blockquote p { text-indent: 0; margin-bottom: .5em; }
hr { border: none; text-align: center; margin: 2em 0; height: 1.5em; }
hr:before { content: "*  *  *"; color: #555; font-size: 1.2em; letter-spacing: .5em; }
figure { margin: 1.5em 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; height: auto; border-radius: 4px; }
figcaption { font-size: .85em; color: #555; margin-top: .5em; font-style: italic; }
"""


class EpubPipeline:
    def __init__(self, output_dir: Path, cache_path: Path | None = None, timeout: int = 300, epubcheck: Path | None = None, fonts_dir: Path | None = DEFAULT_FONTS_DIR):
        self.output_dir = output_dir
        self.cache_path = cache_path or output_dir / ".epub-cache.json"
        self.timeout = timeout
        self.epubcheck = epubcheck
        self.fonts_dir = fonts_dir
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")

    @staticmethod
    def _fingerprint(files: list[Path], options: str) -> str:
        digest = hashlib.sha256(options.encode("utf-8"))
        for path in files:
            digest.update(str(path.resolve()).encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def convert(self, input_files: list[Path], output: Path, metadata: StoryMetadata, combine: bool = False, force: bool = False) -> ConversionResult:
        started = time.perf_counter()
        source = input_files[0]
        theme = theme_for_set(metadata.set_name)
        fingerprint = self._fingerprint(input_files, f"{EPUB_CSS}|{load_theme_css(theme)}|{combine}|1.1.0")
        cache_key = str(output.resolve())
        if not force and output.exists() and self.cache.get(cache_key) == fingerprint:
            return ConversionResult(source, output, True, "skipped", time.perf_counter() - started, skipped=True)

        try:
            self._run_pandoc(input_files, output, metadata, combine, theme)
            problems = validate_epub(output)
            if problems:
                raise ValueError("; ".join(problems))
            if self.epubcheck:
                problems = run_epubcheck(output, self.epubcheck, self.timeout)
                if problems:
                    raise ValueError("; ".join(problems))
            self.cache[cache_key] = fingerprint
            self._save_cache()
            return ConversionResult(source, output, True, "generated", time.perf_counter() - started)
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() if error.stderr else str(error)
            return ConversionResult(source, output, False, "failed", time.perf_counter() - started, detail)
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            return ConversionResult(source, output, False, "failed", time.perf_counter() - started, str(error))

    def _run_pandoc(self, input_files: list[Path], output: Path, metadata: StoryMetadata, combine: bool, theme) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mtg-epub-") as temp_name:
            temp_dir = Path(temp_name)
            css_path = temp_dir / "styles.css"
            css_path.write_text(EPUB_CSS + "\n" + load_theme_css(theme), encoding="utf-8")
            embedded_fonts = prepare_theme_fonts(theme, self.fonts_dir, temp_dir)
            metadata_path = temp_dir / "metadata.xml"
            metadata_path.write_text(_metadata_xml(metadata), encoding="utf-8")
            clean_inputs: list[Path] = []
            for index, source in enumerate(input_files):
                clean = sanitize_typst_for_pandoc(source.read_text(encoding="utf-8", errors="replace"), source.parent)
                if combine:
                    chapter = extract_metadata(source).title
                    clean = f"= {chapter}\n\n{clean.lstrip()}"
                clean_path = temp_dir / f"chapter-{index:04d}.typ"
                clean_path.write_text(clean, encoding="utf-8")
                clean_inputs.append(clean_path)

            command = [
                "pandoc", "-f", "typst", "-t", "epub3", "-o", str(output),
                "--css", str(css_path), "--epub-metadata", str(metadata_path),
                "--toc", "--toc-depth=2", "--split-level=1",
                "--metadata", f"title={metadata.title}",
                "--metadata", f"creator={metadata.author}",
                "--metadata", f"date={metadata.date}",
                "--metadata", "publisher=Wizards of the Coast",
                "--metadata", "lang=en-US",
            ]
            if metadata.cover_image and metadata.cover_image.exists():
                cover = _prepare_cover(metadata.cover_image, temp_dir)
                command.extend(["--epub-cover-image", str(cover)])
            for font in embedded_fonts:
                command.extend(["--epub-embed-font", str(font)])
            command.extend(str(path) for path in clean_inputs)
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=self.timeout)


def _prepare_cover(path: Path, temp_dir: Path) -> Path:
    if path.suffix.lower() != ".webp" or Image is None:
        return path
    target = temp_dir / "cover.jpg"
    with Image.open(path) as image:
        image.convert("RGB").save(target, "JPEG", quality=92)
    return target


def _metadata_xml(metadata: StoryMetadata) -> str:
    series = xml_escape(metadata.series)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<package-metadata>
<meta name="calibre:series" content="{series}"/>
<meta name="calibre:series_index" content="{metadata.series_index}"/>
<meta property="belongs-to-collection" id="c01">{series}</meta>
<meta refines="#c01" property="collection-type">series</meta>
<meta refines="#c01" property="group-position">{metadata.series_index}</meta>
</package-metadata>
'''


def validate_epub(path: Path) -> list[str]:
    problems: list[str] = []
    if not path.exists():
        return ["arquivo EPUB não foi criado"]
    try:
        with ZipFile(path) as archive:
            names = set(archive.namelist())
            if "mimetype" not in names:
                problems.append("mimetype ausente")
            elif archive.getinfo("mimetype").compress_type != ZIP_STORED:
                problems.append("mimetype precisa estar sem compressão")
            if "META-INF/container.xml" not in names:
                problems.append("container.xml ausente")
            if not any(name.endswith(".opf") for name in names):
                problems.append("package OPF ausente")
            if not any(name.endswith("nav.xhtml") for name in names):
                problems.append("navegação EPUB ausente")
            for name in names:
                if name.endswith((".xhtml", ".html", ".css")):
                    content = archive.read(name).decode("utf-8", errors="replace")
                    if "\\Users\\" in content or ":\\" in content:
                        problems.append(f"caminho absoluto encontrado em {name}")
                        break
    except (OSError, ValueError, KeyError) as error:
        problems.append(f"EPUB inválido: {error}")
    return problems


def run_epubcheck(path: Path, epubcheck_jar: Path, timeout: int = 300) -> list[str]:
    if not epubcheck_jar.exists():
        return [f"EpubCheck não encontrado: {epubcheck_jar}"]
    try:
        result = subprocess.run(
            ["java", "-jar", str(epubcheck_jar), str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ["Java não encontrado no PATH para executar o EpubCheck"]
    except subprocess.TimeoutExpired:
        return [f"EpubCheck excedeu o timeout de {timeout}s"]
    if result.returncode:
        detail = (result.stdout + "\n" + result.stderr).strip()
        return [detail or f"EpubCheck retornou código {result.returncode}"]
    return []


def collect_typst_files(set_folder: Path) -> list[Path]:
    return sorted(path for path in set_folder.glob("*.typ") if path.name[:3].isdigit() and path.name[3:4] == "_")


def copy_report(path: Path, results: list[ConversionResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([result.as_json() for result in results], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
