from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from mtg_epub.pipeline import validate_epub


def test_validate_epub_accepts_required_structure(tmp_path):
    epub = tmp_path / "valid.epub"
    with ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        archive.writestr("META-INF/container.xml", "<container/>", compress_type=ZIP_DEFLATED)
        archive.writestr("EPUB/content.opf", "<package/>", compress_type=ZIP_DEFLATED)
        archive.writestr("EPUB/nav.xhtml", "<html/>", compress_type=ZIP_DEFLATED)

    assert validate_epub(epub) == []


def test_validate_epub_reports_missing_structure(tmp_path):
    epub = tmp_path / "invalid.epub"
    with ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_DEFLATED)

    problems = validate_epub(epub)

    assert "mimetype precisa estar sem compressão" in problems
    assert "container.xml ausente" in problems
    assert "package OPF ausente" in problems
