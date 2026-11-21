"""Tests for scripts/optimize_images.py. Run: python3 -m unittest tests/test_optimize_images.py -v"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("optimize_images", ROOT / "scripts" / "optimize_images.py")
opt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opt)


class OptimizeImagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        opt.SRC, opt.OUT = base / "src", base / "img"
        opt.SRC.mkdir()
        self.argv = sys.argv
        sys.argv = ["optimize_images.py", "--placeholder"]

    def tearDown(self):
        sys.argv = self.argv
        self.tmp.cleanup()

    def center(self, name):
        img = Image.open(opt.OUT / name).convert("RGB")
        return img.getpixel((img.width // 2, img.height // 2))

    def test_og_falls_back_to_real_hero_even_with_placeholder_flag(self):
        Image.new("RGB", (1600, 1000), (220, 20, 20)).save(opt.SRC / "hero.jpg")
        opt.main()
        r, g, b = self.center("og.jpg")
        self.assertGreater(r, 180)
        self.assertLess(g, 80)

    def test_transparent_png_lands_on_white_background(self):
        Image.new("RGBA", (1600, 1000), (0, 0, 0, 0)).save(opt.SRC / "vf-2.png")
        opt.main()
        self.assertGreater(min(self.center("vf-2-800.webp")), 245)

    def test_transparent_cutout_is_fitted_not_cropped(self):
        # wide 2:1 cutout with red "bumpers" at both ends: both must survive (no side crop)
        img = Image.new("RGBA", (2000, 1000), (0, 0, 0, 0))
        img.paste((220, 20, 20, 255), (0, 400, 60, 600))
        img.paste((220, 20, 20, 255), (1940, 400, 2000, 600))
        img.save(opt.SRC / "vf-5.png")
        opt.main()
        out = Image.open(opt.OUT / "vf-5-800.webp").convert("RGB")
        reds = [x for x in range(out.width) if out.getpixel((x, out.height // 2))[1] < 100]
        self.assertTrue(reds and reds[0] < 80 and reds[-1] > out.width - 80, reds[:3] + reds[-3:])


if __name__ == "__main__":
    unittest.main()
