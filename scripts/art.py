import argparse
import io
import json
import sys
import time
import tomllib

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from lib import ART, CACHE, ROOT, fetch

SIZES = {"large": (60, 30), "small": (40, 20)}
DOTS = ((0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80))
BLANK = chr(0x2800)


def braille(bits, columns, rows):
    pixels = bits.load()
    lines = []
    for row in range(rows):
        line = ""
        for column in range(columns):
            value = 0
            for dx, dy, bit in DOTS:
                if pixels[column * 2 + dx, row * 4 + dy]:
                    value |= bit
            line += chr(0x2800 + value)
        lines.append(line)
    return trim(lines)


def trim(lines):
    while lines and not lines[0].strip(BLANK):
        lines.pop(0)
    while lines and not lines[-1].strip(BLANK):
        lines.pop()
    if not lines:
        return lines
    left = min(len(line) - len(line.lstrip(BLANK)) for line in lines if line.strip(BLANK))
    right = max(len(line.rstrip(BLANK)) for line in lines)
    return [line[left:right].ljust(right - left, BLANK) for line in lines]


def bitmap(gray, columns, rows, dither=True):
    width, height = columns * 2, rows * 4
    fitted = ImageOps.contain(gray, (width, height), Image.LANCZOS)
    board = Image.new("L", (width, height), 0)
    board.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    if dither:
        return board.convert("1", dither=Image.FLOYDSTEINBERG)
    return board.point(lambda value: 255 if value > 110 else 0).convert("1", dither=Image.NONE)


def edge_level(gray):
    small = gray.resize((64, 64))
    pixels = small.load()
    edge = sorted([pixels[x, y] for x in range(64) for y in (0, 1, 62, 63)] + [pixels[x, y] for y in range(64) for x in (0, 1, 62, 63)])
    return edge[len(edge) // 2]


def crop(image, box):
    if not box:
        return image
    width, height = image.size
    return image.crop((int(box[0] * width), int(box[1] * height), int(box[2] * width), int(box[3] * height)))


def tone(image):
    gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=2)
    if edge_level(gray) > 135:
        gray = ImageOps.invert(gray)
    return gray.point(lambda value: 0 if value < 45 else value)


def outline(image):
    gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    width, height = gray.size
    margin = max(2, width // 16)
    pixels = gray.load()
    column = Image.new("L", (1, height))
    for y in range(height):
        edge = sorted([pixels[x, y] for x in range(margin)] + [pixels[width - 1 - x, y] for x in range(margin)])
        column.putpixel((0, y), edge[len(edge) // 2])
    backdrop = column.resize((width, height)).filter(ImageFilter.GaussianBlur(max(2, height // 40)))
    distance = ImageOps.autocontrast(ImageChops.difference(gray, backdrop), cutoff=1)
    return distance.point(lambda value: 0 if value < 70 else min(255, int(value * 1.15)))


MODES = {"tone": tone, "outline": outline}


def convert(image, mode="tone", box=None):
    gray = MODES[mode](crop(image.convert("RGB"), box))
    return {name: braille(bitmap(gray, columns, rows), columns, rows) for name, (columns, rows) in SIZES.items()}


def temple():
    size = 480
    image = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(image)
    draw.polygon([(40, 150), (240, 50), (440, 150)], fill=255)
    draw.polygon([(110, 138), (240, 76), (370, 138)], fill=0)
    draw.ellipse((222, 96, 258, 132), fill=255)
    draw.rectangle((40, 158, 440, 182), fill=255)
    for index in range(6):
        left = 62 + index * 68
        draw.rectangle((left - 6, 190, left + 42, 200), fill=255)
        draw.rectangle((left, 200, left + 36, 370), fill=255)
        for flute in range(1, 3):
            draw.rectangle((left + flute * 12 - 1, 206, left + flute * 12 + 1, 364), fill=0)
        draw.rectangle((left - 6, 370, left + 42, 380), fill=255)
    draw.rectangle((30, 388, 450, 404), fill=255)
    draw.rectangle((14, 412, 466, 428), fill=255)
    return image


DRAWN = {"philosophy": ("Temple", temple), "default": ("Temple", temple)}


def save(art_id, name, kind, credit, sizes):
    ART.mkdir(parents=True, exist_ok=True)
    record = {"id": art_id, "name": name, "kind": kind, "credit": credit, **sizes}
    (ART / f"{art_id}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")


def portraits():
    with open(ROOT / "scripts" / "portraits.toml", "rb") as handle:
        return tomllib.load(handle).get("portrait", [])


def source_image(entry):
    cached = CACHE / "portraits" / f"{entry['id']}.img"
    if not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(fetch(entry["image"], binary=True))
        time.sleep(1)
    return Image.open(io.BytesIO(cached.read_bytes()))


def build(only, force):
    for art_id, (name, draw) in DRAWN.items():
        if (only and art_id not in only) or ((ART / f"{art_id}.json").exists() and not force):
            continue
        image = draw()
        sizes = {size: braille(bitmap(image, columns, rows, dither=False), columns, rows) for size, (columns, rows) in {"large": (44, 22), "small": (30, 15)}.items()}
        save(art_id, name, "category", "Drawn for stoa.nvim", sizes)
        print(f"ok    {art_id}", file=sys.stderr)
    for entry in portraits():
        if (only and entry["id"] not in only) or ((ART / f"{entry['id']}.json").exists() and not force):
            continue
        if "image" not in entry:
            continue
        try:
            sizes = convert(source_image(entry), entry.get("mode", "tone"), entry.get("crop"))
        except Exception as error:
            print(f"fail  {entry['id']}: {error}", file=sys.stderr)
            continue
        save(entry["id"], entry["name"], "portrait", entry["credit"], sizes)
        print(f"ok    {entry['id']}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the art library: one portrait per person in portraits.toml, plus category art")
    parser.add_argument("--only", action="append", help="art id to build (repeatable)")
    parser.add_argument("--force", action="store_true", help="rebuild art that already exists")
    parser.add_argument("--show", help="print the art with this id")
    arguments = parser.parse_args()
    if arguments.show:
        record = json.loads((ART / f"{arguments.show}.json").read_text())
        print("\n".join(record["large"]), "\n\n" + "\n".join(record["small"]), "\n" + record["credit"])
    else:
        build(arguments.only, arguments.force)
