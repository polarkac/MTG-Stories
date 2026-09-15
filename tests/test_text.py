from pathlib import Path

from mtg_epub.text import remove_conf_block, sanitize_typst_for_pandoc


def test_remove_conf_block_handles_nested_datetime():
    content = '''#import "@local/mtgstory:0.2.0": conf
#show: doc => conf(
    "Episode",
    story_date: datetime(day: 01, month: 07, year: 2024),
    author: "Author",
    doc
)

The story starts here.'''

    result = remove_conf_block(content)

    assert "author:" not in result
    assert "datetime" not in result
    assert "\ndoc\n" not in result
    assert "The story starts here." in result


def test_sanitize_resolves_images_and_removes_typst_emphasis():
    result = sanitize_typst_for_pandoc(
        '#show: doc => conf("Story", doc)\n#emph[Run!] #strong[Now!]\n#figure(image("images/01.jpg"))',
        Path("C:/stories/set"),
    )

    assert "#emph" not in result
    assert "#strong" not in result
    assert "C:/stories/set/images/01.jpg" in result
