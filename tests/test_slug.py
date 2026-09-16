import unittest
from pathlib import Path

from mtg_epub.sluggyfy import slugify
from extract_windows import sanitize_path_string, update_typst_includes_and_images


class TestSlugNormalization(unittest.TestCase):
    def test_slugify_removes_quotes_and_spaces(self):
        self.assertEqual(slugify("004 - Dragon's Maze.typ"), "004-dragons-maze.typ")
        self.assertEqual(slugify("001_Episode 1- Calamity Comes to Valley.typ"), "001-episode-1-calamity-comes-to-valley.typ")
        self.assertEqual(slugify('003_Barrin"s Tall Tale.pdf'), "003-barrins-tall-tale.pdf")
        self.assertEqual(slugify("Planeswalker's Guide to Ulgrotha"), "planeswalkers-guide-to-ulgrotha")

    def test_sanitize_path_string(self):
        raw = "stories/004 - Dragon's Maze/003_Barrin's Tall Tale.typ"
        expected = "stories/004-dragons-maze/003-barrins-tall-tale.typ"
        self.assertEqual(sanitize_path_string(raw), expected)

    def test_update_typst_includes_and_images(self):
        typst_content = (
            '#figure(image("001_Episode 1- Calamity Comes to Valley/01.jpg", width: 100%))\n'
            '#include "./stories/004_Dragon"s Maze.typ"'
        )
        updated = update_typst_includes_and_images(typst_content)
        self.assertIn('image("001-episode-1-calamity-comes-to-valley/01.jpg"', updated)
        self.assertIn('#include "./stories/004-dragons-maze.typ"', updated)
        self.assertNotIn("Dragon", updated)


if __name__ == "__main__":
    unittest.main()
