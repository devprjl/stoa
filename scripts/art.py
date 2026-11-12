import argparse
import io
import json
import re
import sys
import time
import urllib.parse

from PIL import Image, ImageChops, ImageFilter, ImageOps

from lib import ART, CACHE, USER_AGENT, fetch, load_quotes
from themes import terms_for

SIZES = {"large": (60, 30), "small": (40, 20)}
DOTS = ((0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80))
BLANK = chr(0x2800)
SKIP_TITLES = re.compile(r"\b(nude|naked|torso|bathers?|odalisque|erotic)\b", re.I)
SKIP_KINDS = re.compile(r"textile|weaving|lace|embroider|carpet|manuscript|calligraph|document|book|album|fragment|sampler|tapestry|coin|seal|wallpaper", re.I)
HEADERS = {"AIC-User-Agent": USER_AGENT}


def get_json(url, headers=None):
    return json.loads(fetch(url, headers=headers))


def cached(name, producer):
    path = CACHE / "museum" / (re.sub(r"[^\w.-]+", "_", name) + ".json")
    if path.exists():
        return json.loads(path.read_text())
    value = producer()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    time.sleep(0.4)
    return value


def search_aic(term, page):
    def run():
        query = urllib.parse.urlencode(
            {"q": term, "query[term][is_public_domain]": "true", "fields": "id,title,artist_title,date_display,image_id,classification_title", "limit": 40, "page": page + 1}
        )
        rows = get_json("https://api.artic.edu/api/v1/artworks/search?" + query, HEADERS).get("data", [])
        return [
            {
                "source": f"aic:{row['id']}",
                "title": row.get("title"),
                "artist": row.get("artist_title"),
                "date": row.get("date_display"),
                "kind": row.get("classification_title") or "",
                "museum": "Art Institute of Chicago",
                "link": f"https://www.artic.edu/artworks/{row['id']}",
                "image": f"https://www.artic.edu/iiif/2/{row['image_id']}/full/400,/0/default.jpg",
            }
            for row in rows
            if row.get("image_id")
        ]

    return cached(f"aic_{term}_{page}", run)


def search_cma(term, page):
    def run():
        query = urllib.parse.urlencode({"q": term, "cc0": 1, "has_image": 1, "limit": 40, "skip": page * 40, "fields": "id,title,creators,creation_date,images,type,url"})
        rows = get_json("https://openaccess-api.clevelandart.org/api/artworks/?" + query).get("data", [])
        found = []
        for row in rows:
            image = ((row.get("images") or {}).get("web") or {}).get("url")
            if not image:
                continue
            creators = row.get("creators") or []
            artist = re.sub(r"\s*\(.*$", "", creators[0].get("description", "")) if creators else None
            found.append(
                {
                    "source": f"cma:{row['id']}",
                    "title": row.get("title"),
                    "artist": artist or None,
                    "date": row.get("creation_date"),
                    "kind": row.get("type") or "",
                    "museum": "Cleveland Museum of Art",
                    "link": row.get("url"),
                    "image": image,
                }
            )
        return found

    return cached(f"cma_{term}_{page}", run)


def search_met(term, page):
    def run():
        query = urllib.parse.urlencode({"q": term, "hasImages": "true", "isPublicDomain": "true"})
        ids = get_json("https://collectionapi.metmuseum.org/public/collection/v1.1/search?" + query).get("objectIDs") or []
        found = []
        for object_id in ids[page * 12 : page * 12 + 12]:
            try:
                row = get_json(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}")
            except Exception:
                continue
            time.sleep(0.1)
            if not row.get("isPublicDomain") or not row.get("primaryImageSmall"):
                continue
            found.append(
                {
                    "source": f"met:{object_id}",
                    "title": row.get("title"),
                    "artist": row.get("artistDisplayName") or None,
                    "date": row.get("objectDate"),
                    "kind": (row.get("classification") or "") + " " + (row.get("objectName") or ""),
                    "museum": "The Metropolitan Museum of Art",
                    "link": row.get("objectURL"),
                    "image": row["primaryImageSmall"],
                }
            )
        return found

    return cached(f"met_{term}_{page}", run)


MUSEUMS = (search_aic, search_cma, search_met)


def braille(bitmap, columns, rows):
    pixels = bitmap.load()
    lines = []
    for row in range(rows):
        line = ""
        for column in range(columns):
            bits = 0
            for dx, dy, bit in DOTS:
                if pixels[column * 2 + dx, row * 4 + dy]:
                    bits |= bit
            line += chr(0x2800 + bits)
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


def background(gray):
    width, height = gray.size
    margin = max(2, width // 16)
    pixels = gray.load()
    column = Image.new("L", (1, height))
    for y in range(height):
        edge = sorted([pixels[x, y] for x in range(margin)] + [pixels[width - 1 - x, y] for x in range(margin)])
        column.putpixel((0, y), edge[len(edge) // 2])
    return column.resize((width, height)).filter(ImageFilter.GaussianBlur(max(2, height // 40)))


def prepare(image):
    if image.height > image.width * 1.5:
        image = ImageOps.fit(image, (image.width, int(image.width * 1.35)), Image.LANCZOS, centering=(0.5, 0.25))
    elif image.width > image.height * 1.7:
        image = ImageOps.fit(image, (int(image.height * 1.6), image.height), Image.LANCZOS, centering=(0.5, 0.5))
    gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    distance = ImageOps.autocontrast(ImageChops.difference(gray, background(gray)), cutoff=1)
    return distance.point(lambda value: 0 if value < 70 else min(255, int(value * 1.15)))


def bitmap(gray, columns, rows):
    width, height = columns * 2, rows * 4
    fitted = ImageOps.contain(gray, (width, height), Image.LANCZOS)
    board = Image.new("L", (width, height), 0)
    board.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return board.convert("1", dither=Image.FLOYDSTEINBERG)


def readable(bits):
    width, height = bits.size
    box = bits.getbbox()
    if not box or (box[2] - box[0]) < width * 0.35 or (box[3] - box[1]) < height * 0.5:
        return False
    region = bits.crop(box)
    pixels = region.load()
    region_width, region_height = region.size
    total = sum(1 for x in range(region_width) for y in range(region_height) if pixels[x, y])
    density = total / (region_width * region_height)
    if not 0.12 <= density <= 0.58:
        return False
    cells = []
    for row in range(6):
        for column in range(6):
            x0, x1 = column * region_width // 6, (column + 1) * region_width // 6
            y0, y1 = row * region_height // 6, (row + 1) * region_height // 6
            lit = sum(1 for x in range(x0, x1) for y in range(y0, y1) if pixels[x, y])
            cells.append(lit / max(1, (x1 - x0) * (y1 - y0)))
    mean = sum(cells) / len(cells)
    spread = (sum((cell - mean) ** 2 for cell in cells) / len(cells)) ** 0.5
    return spread >= 0.14


def convert(raw):
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if min(image.size) < 200:
        return None
    gray = prepare(image)
    large = bitmap(gray, *SIZES["large"])
    if not readable(large):
        return None
    return {"large": braille(large, *SIZES["large"]), "small": braille(bitmap(gray, *SIZES["small"]), *SIZES["small"])}


def image_bytes(candidate):
    path = CACHE / "images" / (candidate["source"].replace(":", "_") + ".jpg")
    if path.exists():
        return path.read_bytes()
    raw = fetch(candidate["image"], binary=True, headers=HEADERS if candidate["source"].startswith("aic") else None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    time.sleep(0.25)
    return raw


def load_set(name):
    path = CACHE / name
    return set(json.loads(path.read_text())) if path.exists() else set()


def save_set(name, values):
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / name).write_text(json.dumps(sorted(values)))


def used_sources():
    return {json.loads(path.read_text()).get("source") for path in ART.glob("*.json")}


def match(quote, used, rejected, attempts):
    seed = int(quote["id"], 16)
    tries = 0
    for term in terms_for(quote, seed):
        for offset in range(len(MUSEUMS)):
            search = MUSEUMS[(seed + offset) % len(MUSEUMS)]
            for page in range(3):
                try:
                    found = search(term, page)
                except Exception as error:
                    print(f"      search failed ({search.__name__} {term!r}): {error}", file=sys.stderr)
                    break
                if not found:
                    break
                for candidate in found:
                    if candidate["source"] in used or candidate["source"] in rejected or SKIP_KINDS.search(candidate["kind"]):
                        continue
                    title = candidate["title"] or ""
                    if SKIP_TITLES.search(title) or (term == quote.get("author") and term.split()[-1].lower() not in title.lower()):
                        continue
                    if tries >= attempts:
                        return None
                    tries += 1
                    try:
                        sizes = convert(image_bytes(candidate))
                    except Exception:
                        sizes = None
                    if not sizes:
                        rejected.add(candidate["source"])
                        continue
                    return {"term": term, **candidate, **sizes}
    return None


def build(limit, only, attempts):
    ART.mkdir(parents=True, exist_ok=True)
    used, rejected = used_sources(), load_set("rejected.json")
    made = 0
    for quote in load_quotes():
        if only and quote["id"] not in only:
            continue
        target = ART / f"{quote['id']}.json"
        if target.exists():
            continue
        if limit is not None and made >= limit:
            break
        found = match(quote, used, rejected, attempts)
        if not found:
            print(f"none  {quote['id']}  {quote['text'][:50]}", file=sys.stderr)
            continue
        record = {
            "id": quote["id"],
            "title": found["title"] or "Untitled",
            "artist": found["artist"] or "Unknown artist",
            "date": found["date"] or "",
            "museum": found["museum"],
            "link": found["link"],
            "source": found["source"],
            "large": found["large"],
            "small": found["small"],
        }
        target.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
        used.add(found["source"])
        made += 1
        print(f"ok    {quote['id']}  [{found['term']}]  {record['title'][:50]} ({found['source']})", file=sys.stderr)
        if made % 20 == 0:
            save_set("rejected.json", rejected)
    save_set("rejected.json", rejected)
    print(f"made {made} art files", file=sys.stderr)
    return made


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Give every quote its own museum artwork, converted to braille")
    parser.add_argument("--limit", type=int, default=None, help="stop after this many new art files")
    parser.add_argument("--only", action="append", help="quote id to process (repeatable)")
    parser.add_argument("--attempts", type=int, default=10, help="most images to try for one quote")
    parser.add_argument("--show", help="print the art for this quote id")
    arguments = parser.parse_args()
    if arguments.show:
        record = json.loads((ART / f"{arguments.show}.json").read_text())
        print("\n".join(record["large"]), "\n\n" + "\n".join(record["small"]), f"\n{record['title']} / {record['artist']} / {record['museum']}")
    else:
        build(arguments.limit, arguments.only, arguments.attempts)
