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


    def test_cutout_with_faint_haze_is_trimmed_to_the_car(self):
        # wide canvas, faint near-transparent haze everywhere, small opaque car in the middle
        img = Image.new("RGBA", (2560, 1066), (0, 0, 0, 8))
        img.paste((220, 20, 20, 255), (1000, 400, 1560, 700))
        img.save(opt.SRC / "vf-8.png")
        opt.main()
        out = Image.open(opt.OUT / "vf-8-800.webp").convert("RGB")
        reds = [x for x in range(out.width) if out.getpixel((x, out.height // 2))[1] < 100]
        self.assertGreater(len(reds), out.width * 0.8)  # car fills the frame width

    def test_hero_cutout_keeps_transparency(self):
        # hero sits on a blue gradient, so a cut-out hero must stay transparent
        img = Image.new("RGBA", (2000, 1000), (0, 0, 0, 0))
        img.paste((250, 250, 250, 255), (500, 300, 1500, 700))
        img.save(opt.SRC / "hero.webp")
        opt.main()
        out = Image.open(opt.OUT / "hero-800.webp")
        self.assertEqual(out.mode, "RGBA")
        self.assertEqual(out.getpixel((2, 2))[3], 0)
        self.assertEqual(out.getpixel((out.width // 2, out.height // 2))[3], 255)
        og = Image.open(opt.OUT / "og.jpg").convert("RGB")  # og is JPEG: flattened, not black
        self.assertGreater(sum(og.getpixel((2, 2))), 150)

    def test_white_background_render_is_fitted_not_cropped(self):
        # 16:9 studio render on plain white with the car touching both side edges
        img = Image.new("RGB", (1920, 1080), (255, 255, 255))
        img.paste((220, 20, 20), (0, 500, 60, 700))
        img.paste((220, 20, 20), (1860, 500, 1920, 700))
        img.save(opt.SRC / "vf-6.jpg", quality=95)
        opt.main()
        out = Image.open(opt.OUT / "vf-6-800.webp").convert("RGB")
        reds = [x for x in range(out.width) if out.getpixel((x, out.height // 2))[1] < 100]
        self.assertTrue(reds and reds[0] < 80 and reds[-1] > out.width - 80, reds[:3] + reds[-3:])

    def test_photo_with_scene_background_is_still_cropped_to_fill(self):
        # a normal photo (non-white corners) keeps cover-crop: no white bars added
        Image.new("RGB", (1920, 1080), (40, 60, 90)).save(opt.SRC / "vf-8.jpg", quality=95)
        opt.main()
        out = Image.open(opt.OUT / "vf-8-800.webp").convert("RGB")
        self.assertLess(max(out.getpixel((2, 2))), 120)


if __name__ == "__main__":
    unittest.main()
