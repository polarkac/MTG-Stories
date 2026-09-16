import tempfile
import unittest
from pathlib import Path
from PIL import Image

from mtg_epub.image_compressor import compress_image, batch_compress_directories


class TestImageCompressor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compress_large_image_resizes_and_reduces_size(self):
        large_path = self.dir_path / "large.jpg"
        # Cria imagem 2000x1000
        img = Image.new("RGB", (2000, 1000), color=(180, 50, 50))
        img.save(large_path, "JPEG", quality=95)

        orig_size = large_path.stat().st_size
        changed = compress_image(large_path, max_dim=1400, quality=80)
        self.assertTrue(changed)

        with Image.open(large_path) as result:
            w, h = result.size
            self.assertEqual(w, 1400)
            self.assertEqual(h, 700)
            self.assertEqual(result.format, "JPEG")

        new_size = large_path.stat().st_size
        self.assertLess(new_size, orig_size)

    def test_batch_compress_directories(self):
        sub = self.dir_path / "stories" / "sample"
        sub.mkdir(parents=True)
        img1 = sub / "01.jpg"
        Image.new("RGB", (1800, 1200), color="blue").save(img1, "JPEG")

        stats = batch_compress_directories([self.dir_path], max_dim=1000, quality=75, verbose=False)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["compressed"], 1)
        self.assertGreater(stats["saved_bytes"], 0)

        with Image.open(img1) as res:
            self.assertLessEqual(max(res.size), 1000)


if __name__ == "__main__":
    unittest.main()
