import tempfile
import unittest
from pathlib import Path

from mtg_epub.cli import _collection_tasks, _appendix_target
from mtg_epub.models import StoryMetadata


class TestCollection(unittest.TestCase):
    def test_appendix_target_affinities(self):
        story_slugs = ["020-prologue-to-battle-for-zendikar", "021-battle-for-zendikar", "050-phyrexia-all-will-be-one"]

        # Zendikar vai para Battle for Zendikar
        target_zendikar = _appendix_target("002 - Planeswalker's Guide to Zendikar", story_slugs)
        self.assertEqual(target_zendikar, "021-battle-for-zendikar")

        # New Phyrexia vai para Phyrexia
        target_phyrexia = _appendix_target("003 - Planeswalker's Guide to New Phyrexia", story_slugs)
        self.assertEqual(target_phyrexia, "050-phyrexia-all-will-be-one")

        # Ulgrotha vira livro autônomo (target None)
        target_ulgrotha = _appendix_target("001 - Planeswalker's Guide to Ulgrotha", story_slugs)
        self.assertIsNone(target_ulgrotha)

    def test_collection_task_generation_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stories_dir = root / "stories"
            guides_dir = root / "planeswalkers_guides"
            card_lore_dir = root / "card_lore"
            out_dir = root / "epubs" / "Magic Stories Collection"

            # Set 057 Bloomburrow
            bb_stories = stories_dir / "057 - Bloomburrow"
            bb_stories.mkdir(parents=True)
            ep1 = bb_stories / "001_Ep1.typ"
            ep1.write_text('#show: doc => conf("Episode 1", author: "Author A", story_date: datetime(day: 1, month: 8, year: 2024), doc)\nText', encoding="utf-8")
            ep2 = bb_stories / "002_Ep2.typ"
            ep2.write_text('#show: doc => conf("Episode 2", author: "Author B", story_date: datetime(day: 2, month: 8, year: 2024), doc)\nText', encoding="utf-8")

            # Guide Bloomburrow
            bb_guide = guides_dir / "057 - Planeswalkers Guide to Bloomburrow"
            bb_guide.mkdir(parents=True)
            g1 = bb_guide / "001_Guide.typ"
            g1.write_text('#show: doc => conf("Guide to Valley", author: "Author A", doc)\nText', encoding="utf-8")

            # Card Lore Bloomburrow
            bb_lore = card_lore_dir / "057 - Bloomburrow"
            bb_lore.mkdir(parents=True)
            cl1 = bb_lore / "001_Legends.typ"
            cl1.write_text('#show: doc => conf("Legends of Valley", author: "Author C", doc)\nText', encoding="utf-8")

            tasks = _collection_tasks(stories_dir, guides_dir, card_lore_dir, {}, out_dir)

            self.assertEqual(len(tasks), 1)
            sources, epub_path, meta, chapter_titles = tasks[0]

            # 1. Metadados do livro
            self.assertEqual(meta.series, "Magic Stories Collection")
            self.assertEqual(meta.series_index, 57)
            self.assertEqual(meta.author, "Author A, Author B, Author C")
            self.assertEqual(meta.date, "2024-08-01")

            # 2. Ordem dos capítulos: Episódios -> [Guide] -> [Card Lore]
            self.assertEqual(chapter_titles[0], "Episode 1")
            self.assertEqual(chapter_titles[1], "Episode 2")
            self.assertTrue(chapter_titles[2].startswith("[Guide]"))
            self.assertTrue(chapter_titles[3].startswith("[Card Lore]"))


if __name__ == "__main__":
    unittest.main()
