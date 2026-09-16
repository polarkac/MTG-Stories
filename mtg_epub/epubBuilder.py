"""Monta um EPUB3 a partir de capítulos HTML já compilados pelo Typst real.

Substitui o antigo fluxo Typst -> pandoc: aqui o Typst já fez a conversão
para HTML de verdade, então esta camada só precisa saber empacotar HTML em
EPUB — o que o ebooklib já faz de forma madura e sem regex nenhum.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from ebooklib import epub

from .typstHtml import CompiledChapter, compile_chapter_html


@dataclass
class BookMetadata:
    identifier: str
    title: str
    author: str = "Wizards of the Coast"
    language: str = "en"
    cover_image_path: Path | None = None
    series: str | None = None
    series_index: int | float | None = None
    date: str | None = None


@dataclass
class ChapterSource:
    typ_path: Path
    chapter_title: str  # título mostrado no sumário/TOC


def _font_mime_type(path: Path) -> str:
    """Retorna o mime-type correto para o EpubCheck não reclamar."""
    ext = path.suffix.lower()
    if ext == ".otf": return "font/otf"
    if ext == ".ttf": return "font/ttf"
    if ext in {".woff", ".woff2"}: return f"font/{ext[1:]}"
    return "application/octet-stream"


def build_epub(
    metadata: BookMetadata,
    chapters: list[ChapterSource],
    root: Path,
    output_path: Path,
    css_content: str,
    fonts: list[Path] | None = None
) -> None:
    book = epub.EpubBook()
    book.set_identifier(metadata.identifier)
    book.set_title(metadata.title)
    book.set_language(metadata.language)
    book.add_author(metadata.author)

    if metadata.date:
        book.add_metadata("DC", "date", metadata.date)

    if metadata.series:
        # Metadados Calibre (e-readers populares)
        book.add_metadata(None, "meta", metadata.series, {"name": "calibre:series"})
        if metadata.series_index is not None:
            book.add_metadata(None, "meta", str(metadata.series_index), {"name": "calibre:series_index"})
        # Metadados EPUB3 padrão W3C
        book.add_metadata(None, "meta", metadata.series, {"property": "belongs-to-collection", "id": "c01"})
        book.add_metadata(None, "meta", "series", {"refines": "#c01", "property": "collection-type"})
        if metadata.series_index is not None:
            book.add_metadata(None, "meta", str(metadata.series_index), {"refines": "#c01", "property": "group-position"})

    if metadata.cover_image_path is not None:
        book.set_cover(
            metadata.cover_image_path.name,
            metadata.cover_image_path.read_bytes(),
        )
    
    # 1. Adiciona o CSS (agora dinâmico com o tema do set)
    style = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=css_content)
    book.add_item(style)

    # 2. Embutir as Fontes Temáticas no EPUB
    if fonts:
        for font_path in fonts:
            font_item = epub.EpubItem(
                uid=font_path.stem,
                file_name=f"fonts/{font_path.name}",
                media_type=_font_mime_type(font_path),
                content=font_path.read_bytes()
            )
            book.add_item(font_item)

    # 3. Processar e adicionar os Capítulos
    epub_chapters = []
    for index, chapter in enumerate(chapters, start=1):
        compiled: CompiledChapter = compile_chapter_html(chapter.typ_path, root)

        item = epub.EpubHtml(
            title=chapter.chapter_title,
            file_name=f"chap_{index:04d}.xhtml",
            lang=metadata.language,
        )
        
        item.content = (
            f"<html><body>"
            f"<h1>{xml_escape(chapter.chapter_title)}</h1>\n"
            f"{compiled.body_html}"
            f"</body></html>"
        )
        
        item.add_item(style)
        book.add_item(item)
        epub_chapters.append(item)
        
    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *epub_chapters]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)