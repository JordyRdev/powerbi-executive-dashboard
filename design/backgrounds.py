"""Draws the three page backgrounds (1600 x 900) with Pillow.

The backgrounds hold everything that never changes: panels, the navigation rail,
panel titles, legends and the glow behind the hero tile. Visuals sit on top with
transparent backgrounds. Called from generate.py; can also run on its own:

    python design/backgrounds.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 900
S = 2  # draw at 2x and scale down for smooth edges

PAGE = (10, 13, 18)
PANEL = (16, 21, 28)
HAIRLINE = (31, 36, 43)
TEXT = (233, 237, 242)
MUTED = (140, 150, 165)
ICON = (107, 116, 128)
MINT = (61, 219, 180)
AMBER = (242, 180, 90)

FONT_CANDIDATES = {
    "regular": ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "semibold": ["C:/Windows/Fonts/seguisb.ttf", "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "bold": ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}


def font(size: float, weight: str = "regular") -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, int(round(size * S)))
    return ImageFont.load_default()


def mix(c, bg, a):
    return tuple(int(round(a * x + (1 - a) * y)) for x, y in zip(c, bg))


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W * S, H * S), PAGE)
        self.d = ImageDraw.Draw(self.img)

    def rrect(self, x, y, w, h, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S - 1, (y + h) * S - 1], radius=r * S,
                                 fill=fill, outline=outline, width=max(1, int(round(width * S))))

    def panel(self, x, y, w, h):
        self.rrect(x, y, w, h, 16, fill=PANEL, outline=HAIRLINE)

    def line(self, pts, fill, width=1):
        self.d.line([(px * S, py * S) for px, py in pts], fill=fill, width=int(width * S), joint="curve")

    def text(self, x, y, s, size=12, weight="regular", fill=MUTED, spacing=0.0, anchor="la"):
        f = font(size, weight)
        if not spacing:
            self.d.text((x * S, y * S), s, font=f, fill=fill, anchor=anchor)
            return
        cx = x * S
        for ch in s:
            self.d.text((cx, y * S), ch, font=f, fill=fill, anchor="la")
            cx += f.getlength(ch) + spacing * S

    def caps(self, x, y, s):
        """Panel title: small caps, letter-spaced, muted."""
        self.text(x, y, s.upper(), size=11, weight="semibold", fill=MUTED, spacing=1.6)

    def glow(self, cx, cy, r, colour, alpha, clip):
        layer = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(layer).ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                                      fill=int(255 * alpha))
        layer = layer.filter(ImageFilter.GaussianBlur(r * S * 0.45))
        mask = Image.new("L", self.img.size, 0)
        x, y, w, h = clip
        ImageDraw.Draw(mask).rounded_rectangle([x * S + 2, y * S + 2, (x + w) * S - 3, (y + h) * S - 3],
                                               radius=15 * S, fill=255)
        from PIL import ImageChops
        layer = ImageChops.multiply(layer, mask)
        self.img.paste(Image.new("RGB", self.img.size, colour), (0, 0), layer)

    def save(self, path: Path):
        self.img.resize((W, H), Image.LANCZOS).save(path, optimize=True)


# ------------------------------------------------------------------ shared parts

NAV = [("overview", 108), ("segments", 162), ("trust", 216)]


def rail(c: Canvas, active: str):
    c.line([(76, 0), (76, H)], HAIRLINE)
    c.rrect(20, 22, 36, 36, 9, fill=MINT)
    c.text(38, 40.5, "H", size=17, weight="bold", fill=PAGE, anchor="mm")
    for key, cy in NAV:
        on = key == active
        col = MINT if on else ICON
        if on:
            c.rrect(16, cy - 22, 44, 44, 10, fill=mix(MINT, PAGE, 0.10))
        if key == "overview":
            for dx in (-5, 4):
                for dy in (-5, 4):
                    c.rrect(38 + dx - 3.5 + 0.5, cy + dy - 3.5 + 0.5, 7, 7, 1.5, outline=col, width=1.4)
        elif key == "segments":
            c.line([(29, cy + 5), (35, cy - 1), (39, cy + 3), (47, cy - 5)], col, 1.6)
            c.line([(42, cy - 5), (47, cy - 5), (47, cy)], col, 1.6)
        else:
            pts = [(38, cy - 9), (46, cy - 6), (46, cy + 1), (38, cy + 9), (30, cy + 1), (30, cy - 6), (38, cy - 9)]
            c.line(pts, col, 1.6)


def header(c: Canvas, kicker: str):
    c.text(107, 28, kicker.upper(), size=11, weight="semibold", fill=MUTED, spacing=1.6)


def legend_box(c, x, y, colour, label):
    c.rrect(x, y + 3, 10, 10, 2, fill=colour)
    c.text(x + 16, y, label, size=12, fill=MUTED)


def legend_line(c, x, y, colour, label, dashed=False):
    if dashed:
        c.line([(x, y + 8), (x + 5, y + 8)], colour, 2)
        c.line([(x + 9, y + 8), (x + 14, y + 8)], colour, 2)
    else:
        c.line([(x, y + 8), (x + 14, y + 8)], colour, 2)
    c.text(x + 20, y, label, size=12, fill=MUTED)


# ------------------------------------------------------------------ pages

def overview() -> Canvas:
    c = Canvas()
    rail(c, "overview")
    header(c, "Halcyon Pay · Executive overview")
    # header pill (text comes from a measure on a button)
    c.line([(1389, 40), (1389, 64)], HAIRLINE)
    c.rrect(1404, 35, 166, 32, 16, fill=mix(MINT, PAGE, 0.08), outline=mix(MINT, PAGE, 0.45))

    hero = (107, 93, 391, 238)
    c.panel(*hero)
    c.glow(330, 330, 230, MINT, 0.08, hero)
    c.caps(130, 116, "Net revenue")
    c.rrect(362, 110, 114, 26, 13, outline=HAIRLINE)
    c.text(419, 123.5, "Daily, this month", size=10.5, fill=MUTED, anchor="mm")

    for i, label in enumerate(["Payment volume", "Take rate", "Active merchants", "Fraud loss"]):
        x = 514 + i * 268
        c.panel(x, 93, 252, 238)
        c.caps(x + 19, 124, label)

    c.panel(107, 349, 988, 302)
    c.caps(130, 372, "Net revenue vs plan")
    legend_box(c, 959, 381, MINT, "Actual")
    legend_line(c, 1027, 381, AMBER, "Plan", dashed=True)

    c.panel(1111, 349, 459, 302)
    c.caps(1134, 372, "Volume by country")
    c.text(1134, 623, "Low", size=11, fill=MUTED)
    x0, x1 = 1164, 1514
    for k in range(x1 - x0):
        t = k / (x1 - x0)
        col = mix(MINT, (24, 64, 58), t)
        c.d.line([((x0 + k) * S, 627 * S), ((x0 + k) * S, 631 * S)], fill=col, width=S)
    c.text(1522, 623, "High", size=11, fill=MUTED)

    c.panel(107, 669, 988, 215)
    c.panel(1111, 669, 459, 215)
    c.caps(1134, 690, "Data trust")
    return c


def segments() -> Canvas:
    c = Canvas()
    rail(c, "segments")
    header(c, "Halcyon Pay · Segments")
    c.panel(107, 149, 900, 350)
    c.caps(130, 168, "Monthly net revenue, 24 months")
    legend_line(c, 735, 165, MINT, "Selected segment")
    legend_line(c, 870, 165, MUTED, "Segment average")
    c.panel(107, 515, 900, 369)
    c.panel(1023, 149, 547, 735)
    c.caps(1046, 168, "Volume by country and segment")
    return c


TILES = [
    ("Freshness", "Last file loaded before 07:00 CET", "on the day after the last business date"),
    ("Reconciliation", "Daily revenue minus finance ledger", "for the month; passes under €1"),
    ("Completeness", "Rows present ÷ 20 countries × 5 segments", "× days in the month"),
    ("Late files", "Acquirer files still pending", "a warning, not a failure"),
]


def trust() -> Canvas:
    c = Canvas()
    rail(c, "trust")
    header(c, "Halcyon Pay · Data trust")
    for i, (label, r1, r2) in enumerate(TILES):
        x = 107 + i * 369
        c.panel(x, 93, 356, 170)
        c.caps(x + 23, 116, label)
        c.text(x + 23, 212, r1, size=12, fill=MUTED)
        c.text(x + 23, 230, r2, size=12, fill=MUTED)
    c.panel(107, 279, 900, 330)
    c.caps(130, 298, "Reconciliation, daily revenue vs ledger")
    legend_box(c, 720, 295, MINT, "Daily")
    legend_box(c, 790, 295, (74, 84, 98), "Ledger")
    legend_line(c, 865, 295, AMBER, "Gap")
    c.panel(1023, 279, 547, 605)
    c.caps(1046, 298, "Completeness by month and segment")
    c.panel(107, 625, 900, 259)
    c.caps(130, 644, "Load log, files not loaded")
    return c


def draw_all(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for name, fn in [("bg_overview.png", overview), ("bg_segments.png", segments), ("bg_trust.png", trust)]:
        path = out_dir / name
        fn().save(path)
        files.append(path)
    return files


if __name__ == "__main__":
    for p in draw_all(Path(__file__).resolve().parent / "backgrounds"):
        print(p)
