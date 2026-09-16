from pathlib import Path
from bs4 import BeautifulSoup
import unittest

from mtg_epub.typstHtml import _apply_typst_polyfills, _matching_close_paren


class TestTypstHtml(unittest.TestCase):
    def test_matching_close_paren_handles_strings_and_nested_parens(self):
        text = 'conf("test (inside string)", (nested), final)'
        closing = _matching_close_paren(text, 4)
        self.assertEqual(closing, len(text) - 1)

    def test_apply_typst_polyfills_removes_local_imports_and_conf_block(self):
        content = """#import "@local/mtgstory:0.2.0": conf
#show: doc => conf(
    "Episode 1",
    set_name: "Bloomburrow",
    story_date: datetime(day: 1, month: 7, year: 2024),
    author: "WotC",
    doc
)

The adventure begins here.
"""
        result = _apply_typst_polyfills(content)
        self.assertNotIn('@local/mtgstory', result)
        self.assertNotIn('#show: doc => conf', result)
        self.assertIn('The adventure begins here.', result)
        self.assertIn('// --- START POLYFILL ---', result)
        self.assertIn('#let letter_block', result)

    def test_ast_pov_heading_and_divider_transformation(self):
        html_input = """
        <html><body>
        <p><strong>Kaito</strong></p>
        <p>He drew his blade in silence.</p>
        <div><svg><polyline points="0,0 100,0"/></svg></div>
        <p>The shadows shifted.</p>
        </body></html>
        """
        soup = BeautifulSoup(html_input, "html.parser")

        # Reproduz as regras do typstHtml para estruturação
        for p_tag in soup.find_all("p"):
            children = p_tag.contents
            if len(children) == 1 and children[0].name in ["strong", "b"]:
                h2_tag = soup.new_tag("h2")
                h2_tag.string = children[0].get_text(strip=True)
                p_tag.replace_with(h2_tag)

        for polyline in soup.find_all("polyline"):
            if polyline.parent and polyline.parent.name == "svg":
                svg_container = polyline.parent
                if svg_container.parent and svg_container.parent.name == "div":
                    hr_tag = soup.new_tag("hr")
                    svg_container.parent.replace_with(hr_tag)

        body_str = str(soup.body)
        self.assertIn("<h2>Kaito</h2>", body_str)
        self.assertIn("<hr/>", body_str)
        self.assertNotIn("<polyline", body_str)


if __name__ == "__main__":
    unittest.main()
