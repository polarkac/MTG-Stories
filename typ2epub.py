#!/usr/bin/env python3
"""Compatibilidade para o conversor EPUB de MTG Stories."""

from pathlib import Path

from mtg_epub.cli import main
from mtg_epub.metadata import extract_metadata as extract_metadata_from_typ
from mtg_epub.pipeline import EpubPipeline

ROOT_DIR = Path(__file__).resolve().parent
STORIES_DIR = ROOT_DIR / "stories"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "epubs"


def build_epub_for_story(typ_path: Path, output_epub_path: Path) -> bool:
    metadata = extract_metadata_from_typ(typ_path)
    result = EpubPipeline(output_epub_path.parent).convert([typ_path], output_epub_path, metadata)
    return result.success


def combine_set_to_single_epub(set_folder: Path, output_epub_path: Path) -> bool:
    from mtg_epub.pipeline import collect_typst_files

    sources = collect_typst_files(set_folder)
    if not sources:
        return False
    first = extract_metadata_from_typ(sources[0])
    metadata = first.__class__(
        title=f"{first.set_name} (Complete Stories)",
        set_name=first.set_name,
        author="Wizards of the Coast",
        date=first.date,
        series=first.series,
        series_index=1,
        source_file=sources[0],
        cover_image=first.cover_image,
    )
    result = EpubPipeline(output_epub_path.parent).convert(sources, output_epub_path, metadata)
    return result.success


if __name__ == "__main__":
    raise SystemExit(main())
