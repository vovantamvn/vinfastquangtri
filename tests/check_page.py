"""Static checks for the landing page. Run: python3 -m unittest tests/check_page.py -v"""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHONE = "0376793468"
SITE = "https://vinfastquangtri.net/"
TEL = f"tel:{PHONE}"
ZALO = f"https://zalo.me/{PHONE}"
DISCLAIMER = (
    "Trang cá nhân của tư vấn bán hàng, không phải website chính thức của VinFast. "
    "Thông tin chi tiết tại vinfastauto.com."
)
MODELS = [
    ("vf-2", "VF 2"), ("vf-3", "VF 3"), ("vf-5", "VF 5"), ("vf-6", "VF 6"), ("vf-7", "VF 7"),
    ("vf-8", "VF 8"), ("vf-9", "VF 9"), ("vf-mpv-7", "VF MPV 7"), ("limo-green", "Limo Green"),
]
COMMONS_IMAGES = []
GROUPS = ["Xe gia đình & cá nhân", "Xe kinh doanh dịch vụ"]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children, self.text_parts = [], []

    def text(self):
        parts = list(self.text_parts)
        for c in self.children:
            parts.append(c.text())
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def iter(self):
        yield self
        for c in self.children:
            yield from c.iter()

    def find_all(self, tag, **attrs):
        return [n for n in self.iter() if n.tag == tag and all(n.attrs.get(k) == v for k, v in attrs.items())]

    def has_class(self, cls):
        return cls in (self.attrs.get("class") or "").split()

    def ancestors(self):
        p = self.parent
        while p:
            yield p
            p = p.parent


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = Node("#root", [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.text_parts.append(data)


def load(name="index.html"):
    b = TreeBuilder()
    b.feed((ROOT / name).read_text(encoding="utf-8"))
    return b.root


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load()
        cls.body_text = cls.doc.find_all("body")[0].text()

    def test_lang_vi(self):
        self.assertEqual(self.doc.find_all("html")[0].attrs.get("lang"), "vi")

    def test_single_h1(self):
        h1 = self.doc.find_all("h1")
        self.assertEqual(len(h1), 1)
        self.assertIn("VinFast Quảng Trị", h1[0].text())

    def test_contact_links_are_plain_anchors(self):
        tel = self.doc.find_all("a", href=TEL)
        zalo = self.doc.find_all("a", href=ZALO)
        self.assertGreaterEqual(len(tel), 2)
        self.assertGreaterEqual(len(zalo), 2)
        for a in tel + zalo:
            self.assertNotIn("onclick", a.attrs)

    def test_phone_visible_as_text(self):
        self.assertTrue("0376 793 468" in self.body_text or PHONE in self.body_text)

    def test_seller_name(self):
        self.assertIn("Võ Đức Thành", self.body_text)

    def test_footer_disclaimer(self):
        footer = self.doc.find_all("footer")
        self.assertEqual(len(footer), 1)
        self.assertIn(DISCLAIMER, footer[0].text())

    def test_body_has_bottom_padding_for_sticky_bar(self):
        css = (ROOT / "assets/css/style.css").read_text(encoding="utf-8")
        bar = re.search(r"\.contact-bar\s*\{([^}]*)\}", css)
        self.assertIsNotNone(bar)
        self.assertRegex(bar.group(1), r"position:\s*fixed")
        body = re.search(r"(?m)^body\s*\{([^}]*)\}", css)
        self.assertIsNotNone(body)
        self.assertIn("padding-bottom", body.group(1))


    def models(self):
        return [n for n in self.doc.find_all("article") if n.has_class("model")]

    def test_model_ids_in_order(self):
        self.assertEqual([m.attrs.get("id") for m in self.models()], [i for i, _ in MODELS])

    def test_model_headings(self):
        for m, (_, name) in zip(self.models(), MODELS):
            h3 = m.find_all("h3")
            self.assertEqual(len(h3), 1)
            self.assertEqual(h3[0].text(), f"VinFast {name}")

    def test_two_groups(self):
        groups = [n for n in self.doc.iter() if n.has_class("model-group")]
        self.assertEqual(len(groups), 2)
        self.assertEqual([g.find_all("h2")[0].text() for g in groups], GROUPS)
        service_ids = [m.attrs["id"] for m in groups[1].find_all("article")]
        self.assertEqual(service_ids, ["limo-green"])

    def test_each_card_has_specs_and_zalo(self):
        for m in self.models():
            specs = [u for u in m.find_all("ul") if u.has_class("specs")]
            self.assertEqual(len(specs), 1, m.attrs["id"])
            self.assertTrue(3 <= len(specs[0].find_all("li")) <= 4, m.attrs["id"])
            self.assertEqual(len(m.find_all("a", href=ZALO)), 1, m.attrs["id"])

    def img_urls(self):
        for img in self.doc.find_all("img"):
            yield img, img.attrs.get("src")
            for part in (img.attrs.get("srcset") or "").split(","):
                if part.strip():
                    yield img, part.split()[0]

    def test_images_exist_and_within_budget(self):
        imgs = self.doc.find_all("img")
        self.assertTrue(any(i.attrs.get("fetchpriority") == "high" for i in imgs), "no hero image")
        for img, url in self.img_urls():
            path = ROOT / url
            self.assertTrue(path.is_file(), url)
            budget = 150_000 if Path(url).name.startswith("hero") else 80_000
            self.assertLessEqual(path.stat().st_size, budget, url)
        for img in imgs:
            if img.attrs.get("src", "").endswith(".svg"):
                continue  # vector logo: one file serves every size
            self.assertIn("srcset", img.attrs, img.attrs.get("src"))
            self.assertIn("sizes", img.attrs, img.attrs.get("src"))

    def test_img_attrs(self):
        imgs = self.doc.find_all("img")
        hero = [i for i in imgs if i.attrs.get("fetchpriority") == "high"]
        self.assertEqual(len(hero), 1)
        self.assertNotIn("loading", hero[0].attrs)
        for img in imgs:
            for a in ("alt", "width", "height"):
                self.assertTrue(img.attrs.get(a), f"{img.attrs.get('src')} missing {a}")
            if img is not hero[0] and not img.attrs.get("src", "").endswith(".svg"):  # header logo loads eagerly
                self.assertEqual(img.attrs.get("loading"), "lazy", img.attrs.get("src"))

    def meta(self, **attrs):
        found = self.doc.find_all("meta", **attrs)
        self.assertEqual(len(found), 1, attrs)
        return found[0].attrs.get("content", "")

    def test_meta(self):
        self.assertIn("VinFast Quảng Trị", self.doc.find_all("title")[0].text())
        self.assertTrue(120 <= len(self.meta(name="description")) <= 160)
        canon = self.doc.find_all("link", rel="canonical")
        self.assertEqual([c.attrs["href"] for c in canon], [SITE])
        self.assertTrue(self.meta(name="viewport"))
        self.assertEqual(len(self.doc.find_all("link", rel="icon")), 1)

    def test_og_tags(self):
        title = self.meta(property="og:title")
        self.assertTrue(title.startswith("Võ Đức Thành"), title)  # share preview must not read as official
        self.assertIn("VinFast Quảng Trị", title)
        self.assertTrue(self.meta(property="og:description"))
        self.assertEqual(self.meta(property="og:url"), SITE)
        self.assertEqual(self.meta(property="og:image"), SITE + "assets/img/og.jpg")
        self.assertTrue((ROOT / "assets/img/og.jpg").is_file())
        self.assertEqual(self.meta(property="og:locale"), "vi_VN")

    def test_jsonld(self):
        blocks = [json.loads(s.text()) for s in self.doc.find_all("script", type="application/ld+json")]
        by_type = {b["@type"]: b for b in blocks}
        person = by_type["Person"]
        self.assertEqual(person["name"], "Võ Đức Thành")
        self.assertEqual(person["telephone"], "+84376793468")
        self.assertTrue(person["areaServed"])
        items = by_type["ItemList"]["itemListElement"]
        self.assertEqual([i["name"] for i in items], [f"VinFast {n}" for _, n in MODELS])
        self.assertEqual([i["url"] for i in items], [f"{SITE}#{i}" for i, _ in MODELS])

    def test_seo_files(self):
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(f"Sitemap: {SITE}sitemap.xml", robots)
        locs = re.findall(r"<loc>(.*?)</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertEqual(locs, [SITE])
        nf = load("404.html")
        self.assertTrue(nf.find_all("a", href=TEL) and nf.find_all("a", href=ZALO))
        self.assertEqual(nf.find_all("html")[0].attrs.get("lang"), "vi")
        self.assertTrue((ROOT / "assets/img/favicon.svg").is_file())

    def test_tracking_attrs(self):
        for href, kind in ((TEL, "call"), (ZALO, "zalo")):
            for a in self.doc.find_all("a", href=href):
                self.assertEqual(a.attrs.get("data-track"), kind)
        scripts = [s.attrs.get("src") for s in self.doc.find_all("script") if s.attrs.get("src")]
        self.assertIn("assets/js/main.js", scripts)

    def test_photo_credits(self):
        """Commons photos are CC BY / CC BY-SA: each needs author, license and source link."""
        footer = self.doc.find_all("footer")[0]
        credits = [li for li in footer.find_all("li") if li.find_all("a")]
        # only images still sourced from Commons need credits; official VinFast renders don't
        self.assertEqual(len(credits), len(COMMONS_IMAGES))
        for label in COMMONS_IMAGES:
            self.assertTrue(any(li.text().startswith(label + ":") for li in credits), label)
        for li in credits:
            links = [a.attrs.get("href", "") for a in li.find_all("a")]
            self.assertTrue(any(h.startswith("https://commons.wikimedia.org/wiki/File:") for h in links), li.text())
            self.assertTrue(any("creativecommons.org/licenses/" in h for h in links), li.text())
            self.assertRegex(li.text(), r"CC BY(-SA)? 4\.0")

    def test_no_prices(self):
        self.assertIsNone(re.search(r"\d[\d.,]*\s*(triệu|tỷ|vnđ|đ\b)", self.body_text, re.I))

    def test_favicon_is_vinfast_emblem(self):
        icons = self.doc.find_all("link", rel="icon")
        self.assertEqual(icons[0].attrs["href"], "assets/img/favicon.svg")
        fav = (ROOT / "assets/img/favicon.svg").read_text(encoding="utf-8")
        self.assertNotIn("#1464f4", fav)  # not a blue tile: the stacked logo on white
        self.assertIn('fill="#ffffff"', fav)  # white backdrop so it shows on dark tab bars
        self.assertGreaterEqual(fav.count("<path"), 9)  # V emblem + VINFAST wordmark
        apple = self.doc.find_all("link", rel="apple-touch-icon")
        self.assertEqual(len(apple), 1)
        self.assertTrue((ROOT / apple[0].attrs["href"]).is_file())

    def test_header_shows_vinfast_logo(self):
        header = self.doc.find_all("header")[0]
        logos = [i for i in header.find_all("img") if i.attrs.get("src") == "assets/img/vinfast-logo.svg"]
        self.assertEqual(len(logos), 1)
        self.assertIn("VinFast", logos[0].attrs.get("alt", ""))
        self.assertTrue((ROOT / "assets/img/vinfast-logo.svg").is_file())

    def test_floating_contact_buttons(self):
        floats = [n for n in self.doc.iter() if n.has_class("float-contact")]
        self.assertEqual(len(floats), 1)
        self.assertEqual(len(floats[0].find_all("a", href=TEL)), 1)
        self.assertEqual(len(floats[0].find_all("a", href=ZALO)), 1)
        for a in floats[0].find_all("a"):
            self.assertTrue(a.attrs.get("aria-label"))  # icon-only buttons need a label

    def test_each_model_has_slogan(self):
        for m in self.models():
            slogans = [p for p in m.find_all("p") if p.has_class("model-slogan")]
            self.assertEqual(len(slogans), 1, m.attrs["id"])
            self.assertTrue(slogans[0].text(), m.attrs["id"])

    def test_why_items_have_icons(self):
        items = [li for ul in self.doc.find_all("ul") if ul.has_class("why-list") for li in ul.find_all("li")]
        self.assertEqual(len(items), 4)
        for li in items:
            self.assertEqual(len(li.find_all("svg")), 1)


if __name__ == "__main__":
    unittest.main()
