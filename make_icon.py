"""Create gxfr_utilA.ico from a simple bidirectional-transfer glyph."""
from pathlib import Path

from PIL import Image, ImageDraw

NAVY = (27, 54, 93, 255)
GOLD = (230, 179, 37, 255)
TEAL = (42, 157, 143, 255)
WHITE = (255, 255, 255, 255)
OUT = Path(__file__).with_name("gxfr_utilA.ico")
SIZES = (16, 24, 32, 48, 64, 128, 256)


def _folder(draw, x, y, w, h, fill):
    tab_h = max(1, int(h * 0.22))
    tab_w = max(2, int(w * 0.45))
    draw.rectangle([x, y, x + tab_w, y + tab_h + 1], fill=fill)
    draw.rounded_rectangle(
        [x, y + tab_h, x + w, y + h],
        radius=max(1, w // 10),
        fill=fill,
    )


def _arrow(draw, x1, x2, y, thickness, left_to_right=True):
    if x2 - x1 < 4:
        return
    head = max(2, min(thickness * 2, (x2 - x1) // 2))
    shaft_top = y - max(1, thickness // 2)
    shaft_bot = y + max(1, (thickness + 1) // 2)
    if left_to_right:
        shaft_end = max(x1, x2 - head)
        if shaft_end > x1:
            draw.rectangle([x1, shaft_top, shaft_end, shaft_bot], fill=WHITE)
        draw.polygon([(x2 - head, y - head), (x2, y), (x2 - head, y + head)], fill=WHITE)
    else:
        shaft_start = min(x2, x1 + head)
        if x2 > shaft_start:
            draw.rectangle([shaft_start, shaft_top, x2, shaft_bot], fill=WHITE)
        draw.polygon([(x1 + head, y - head), (x1, y), (x1 + head, y + head)], fill=WHITE)


def make_image(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(1, size // 18)
    draw.rounded_rectangle(
        [margin, margin, size - 1 - margin, size - 1 - margin],
        radius=max(2, size // 6),
        fill=NAVY,
    )

    folder_w = int(size * 0.30)
    folder_h = int(size * 0.26)
    folder_y = int(size * 0.36)
    left_x = int(size * 0.14)
    right_x = size - left_x - folder_w
    _folder(draw, left_x, folder_y, folder_w, folder_h, GOLD)
    _folder(draw, right_x, folder_y, folder_w, folder_h, TEAL)

    mid_left = left_x + folder_w + max(1, size // 32)
    mid_right = right_x - max(1, size // 32)
    thickness = max(1, size // 18)
    gap = max(2, size // 14)
    center = folder_y + folder_h // 2
    _arrow(draw, mid_left, mid_right, center - gap, thickness, left_to_right=True)
    _arrow(draw, mid_left, mid_right, center + gap, thickness, left_to_right=False)
    return img


def main():
    icon = make_image(256)
    icon.save(OUT, format="ICO", sizes=[(size, size) for size in SIZES])
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
