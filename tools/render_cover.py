"""Render the standalone sequel cover artwork as a high-resolution PNG."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT = 1600, 2560


def font(paths, size):
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


SERIF = [r"C:\Windows\Fonts\georgiab.ttf", r"C:\Windows\Fonts\Georgia.ttf"]
SERIF_REG = [r"C:\Windows\Fonts\georgia.ttf", r"C:\Windows\Fonts\Georgia.ttf"]


def render():
    image = Image.new("RGB", (WIDTH, HEIGHT))
    px = image.load()
    top = (8, 19, 39)
    middle = (17, 48, 68)
    bottom = (4, 12, 25)
    for y in range(HEIGHT):
        t = y / HEIGHT
        if t < 0.53:
            a, b, u = top, middle, t / 0.53
        else:
            a, b, u = middle, bottom, (t - 0.53) / 0.47
        u = u * u * (3 - 2 * u)
        color = tuple(round(a[i] * (1 - u) + b[i] * u) for i in range(3))
        for x in range(WIDTH):
            glow = max(0.0, 1 - (((x - 810) / 850) ** 2 + ((y - 1110) / 930) ** 2))
            px[x, y] = tuple(min(255, int(c + glow * g)) for c, g in zip(color, (8, 19, 23)))

    # A muted moon above the damaged city, the quiet aftermath rather than a battle tableau.
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((1120, 205, 1530, 615), fill=(222, 184, 111, 28))
    glow = glow.filter(ImageFilter.GaussianBlur(82))
    image = Image.alpha_composite(image.convert("RGBA"), glow)
    d = ImageDraw.Draw(image, "RGBA")
    d.ellipse((1190, 275, 1460, 545), fill=(222, 196, 145, 238), outline=(248, 225, 178, 190), width=3)
    d.ellipse((1240, 320, 1430, 510), fill=(235, 213, 171, 62))

    # Far-off Cyoria: a broken skyline and scattered reconstruction lights.
    city_y = 1115
    buildings = [(0, 140, 270), (95, 245, 390), (260, 375, 315), (390, 500, 460),
                 (520, 655, 345), (660, 760, 520), (765, 910, 380), (925, 1045, 470),
                 (1060, 1200, 330), (1195, 1325, 455), (1340, 1470, 365), (1490, 1600, 500)]
    for left, right, height in buildings:
        y = city_y - height
        d.rectangle((left, y, right, HEIGHT), fill=(5, 14, 26, 225))
        d.line((left, y, right, y), fill=(90, 129, 137, 86), width=3)
        for wx in range(left + 22, right - 12, 38):
            for wy in range(y + 34, min(city_y, y + 190), 48):
                if (wx * 13 + wy * 7) % 5 == 0:
                    d.rectangle((wx, wy, wx + 8, wy + 17), fill=(232, 177, 102, 105))
    # A few visibly broken rooflines.
    d.line([(278, 800), (308, 780), (326, 825), (359, 797)], fill=(143, 151, 145, 95), width=4)
    d.line([(1048, 715), (1082, 680), (1111, 730), (1140, 713)], fill=(143, 151, 145, 95), width=4)

    # The deep arch: layered silhouettes descend from the city into blue-black earth.
    d.polygon([(0, 1250), (220, 1160), (430, 1310), (650, 1200), (870, 1360),
               (1110, 1220), (1340, 1350), (1600, 1190), (1600, HEIGHT), (0, HEIGHT)],
              fill=(7, 24, 36, 242))
    d.polygon([(0, 1510), (250, 1390), (475, 1535), (700, 1430), (950, 1600),
               (1200, 1460), (1420, 1595), (1600, 1490), (1600, HEIGHT), (0, HEIGHT)],
              fill=(4, 16, 29, 255))
    # The lower field carries a great broken dial instead of the retired grid motif:
    # a clock face ringed once, with one span of the rim left open.
    dial = (118, 168, 178, 96)
    ccx, ccy, cr = 1150, 1655, 345
    d.ellipse((ccx - cr, ccy - cr, ccx + cr, ccy + cr), outline=dial, width=4)
    d.ellipse((ccx - cr + 44, ccy - cr + 44, ccx + cr - 44, ccy + cr - 44),
              outline=(118, 168, 178, 54), width=2)
    for minute in range(60):
        ang = math.radians(minute * 6 - 90)
        inner = cr - (34 if minute % 5 == 0 else 17)
        d.line(((ccx + int(inner * math.cos(ang)), ccy + int(inner * math.sin(ang))),
                (ccx + int((cr - 6) * math.cos(ang)), ccy + int((cr - 6) * math.sin(ang)))),
               fill=(163, 196, 196, 98 if minute % 5 == 0 else 52),
               width=4 if minute % 5 == 0 else 2)
    d.arc((ccx - cr, ccy - cr, ccx + cr, ccy + cr), 104, 152, fill=(4, 16, 29, 250), width=10)
    # The hands stand at an angle that reads as stopped rather than running.
    for angle, reach, weight in ((232, 236, 7), (48, 150, 9)):
        rad = math.radians(angle - 90)
        d.line(((ccx, ccy), (ccx + int(reach * math.cos(rad)), ccy + int(reach * math.sin(rad)))),
               fill=(206, 221, 214, 132), width=weight)
    d.ellipse((ccx - 13, ccy - 13, ccx + 13, ccy + 13), fill=(214, 226, 219, 150))
    # Two warm accents keep the lower field from going cold.
    d.ellipse((515, 1828, 579, 1892), fill=(223, 153, 81, 116))
    d.ellipse((1225, 1930, 1289, 1994), fill=(223, 153, 81, 92))

    # A small solitary mage, back turned toward the reader: scale, not a portrait likeness.
    d.ellipse((752, 1292, 849, 1390), fill=(5, 12, 23, 255))
    d.polygon([(761, 1370), (718, 1430), (690, 1680), (748, 1764), (855, 1764),
               (914, 1677), (879, 1430), (836, 1370)], fill=(6, 12, 22, 255))
    d.polygon([(763, 1393), (720, 1480), (669, 1622), (705, 1639), (787, 1505)],
              fill=(8, 17, 28, 255))
    d.polygon([(837, 1393), (881, 1470), (950, 1588), (916, 1615), (824, 1510)],
              fill=(8, 17, 28, 255))
    d.line([(770, 1420), (804, 1555), (836, 1420)], fill=(106, 148, 147, 92), width=3)
    d.line([(804, 1555), (762, 1703)], fill=(106, 148, 147, 48), width=2)

    # Delicate web motif above the title, kept clear of the dial on the right.
    cx, cy, radius = 470, 1905, 300
    web = (180, 196, 172, 95)
    d.arc((cx - radius, cy - radius, cx + radius, cy + radius), 205, 335, fill=web, width=2)
    d.arc((cx - 228, cy - 228, cx + 228, cy + 228), 205, 335, fill=web, width=2)
    d.arc((cx - 152, cy - 152, cx + 152, cy + 152), 205, 335, fill=web, width=2)
    for angle in (205, 226, 248, 270, 292, 314, 335):
        rad = math.radians(angle)
        end = (cx + int(radius * math.cos(rad)), cy + int(radius * math.sin(rad)))
        d.line((cx, cy, end[0], end[1]), fill=web, width=2)

    # Lower title field is a translucent ink wash for legibility without a hard box.
    wash = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wash)
    wd.rectangle((0, 1920, WIDTH, HEIGHT), fill=(3, 10, 22, 160))
    wash = wash.filter(ImageFilter.GaussianBlur(36))
    image = Image.alpha_composite(image, wash)
    d = ImageDraw.Draw(image, "RGBA")
    gold = (232, 205, 151, 255)
    ivory = (235, 231, 213, 255)
    title_font = font(SERIF, 122)
    subtitle_font = font(SERIF_REG, 48)
    author_font = font(SERIF_REG, 32)
    small_font = font(SERIF_REG, 27)

    def centered(text, y, f, fill, spacing=0, stroke=0):
        bbox = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
        width = bbox[2] - bbox[0]
        d.text(((WIDTH - width) / 2, y), text, font=f, fill=fill,
               stroke_width=stroke, stroke_fill=(3, 10, 18, 220))

    centered("THE SHAPE", 2048, title_font, ivory, stroke=2)
    centered("OF AFTER", 2190, title_font, ivory, stroke=2)
    d.line((475, 2364, 1125, 2364), fill=(232, 205, 151, 170), width=2)
    centered("A MOTHER OF LEARNING CONTINUATION", 2391, subtitle_font, gold)
    centered("AN UNOFFICIAL FAN-WRITTEN STORY", 2474, small_font, (190, 206, 204, 235))
    # A subtle top imprint, leaving the night and moon visually open.
    centered("THE AFTERMATH", 100, author_font, (202, 211, 204, 205))

    out = ROOT / "The Shape of After - Cover.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(out, format="PNG", optimize=True, dpi=(300, 300))
    print(f"Created {out.name}: {WIDTH}x{HEIGHT}, {out.stat().st_size} bytes")


if __name__ == "__main__":
    render()
