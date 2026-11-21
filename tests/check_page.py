"""Static checks for the landing page. Run: python3 -m unittest tests/check_page.py -v"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHONE = "0376793468"
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

    def test_no_prices(self):
        self.assertIsNone(re.search(r"\d[\d.,]*\s*(triệu|tỷ|vnđ|đ\b)", self.body_text, re.I))


if __name__ == "__main__":
    unittest.main()
