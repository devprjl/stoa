import argparse
import json
import sys

from lib import ART, CATEGORIES, DATA, ENABLED, file_hash, load_quotes, normalize, quote_id, save_quotes, slug, today

FIELDS = ("id", "text", "author", "work", "category", "art", "ref", "added")


def art_for(quote):
    person = slug(quote.get("author") or "")
    if person and (ART / f"{person}.json").exists():
        return person
    return quote["category"]


def clean(quotes):
    seen, kept, problems = set(), [], []
    for quote in quotes:
        text = " ".join(str(quote.get("text", "")).split())
        key = normalize(text)
        if len(text) < 20 or not key:
            problems.append(f"too short: {text!r}")
            continue
        if key in seen:
            continue
        if quote.get("category") not in CATEGORIES:
            problems.append(f"unknown category {quote.get('category')!r}: {text[:50]!r}")
            continue
        if not quote.get("author") and not quote.get("work"):
            problems.append(f"no author or work: {text[:50]!r}")
            continue
        seen.add(key)
        entry = {**quote, "text": text, "id": quote_id(text)}
        entry["art"] = art_for(entry)
        entry.setdefault("added", today())
        kept.append({field: entry[field] for field in FIELDS if entry.get(field)})
    return kept, problems


def art_index():
    index, problems = {}, []
    for path in sorted(ART.glob("*.json")):
        record = json.loads(path.read_text())
        for size in ("large", "small"):
            lines = record.get(size)
            if not isinstance(lines, list) or not lines or len({len(line) for line in lines}) != 1:
                problems.append(f"art {path.name}: bad {size} block")
        if record.get("id") != path.stem:
            problems.append(f"art {path.name}: id does not match file name")
        index[path.stem] = file_hash(path)
    for required in (*ENABLED, "default"):
        if required not in index:
            problems.append(f"missing art: {required}")
    return index, problems


def backfill(quotes):
    waiting = {}
    for quote in quotes:
        if quote.get("author") and quote["art"] == quote["category"]:
            waiting[quote["author"]] = waiting.get(quote["author"], 0) + 1
    return sorted(waiting.items(), key=lambda item: (-item[1], item[0]))


def build(check, show_backfill):
    stored = load_quotes()
    quotes, problems = clean(stored)
    art, art_problems = art_index()
    problems += art_problems

    counts = {category: 0 for category in CATEGORIES}
    for quote in quotes:
        counts[quote["category"]] += 1

    index_path = DATA / "index.json"
    previous = json.loads(index_path.read_text()) if index_path.exists() else {}
    body = {"schema": 1, "quotes": len(quotes), "categories": counts, "art": art}
    changed = any(previous.get(key) != value for key, value in body.items()) or stored != quotes
    index = {"version": previous.get("version", 0) + (1 if changed else 0), "updated": today() if changed else previous.get("updated", today()), **body}

    waiting = backfill(quotes)
    if show_backfill:
        print(json.dumps([{"author": author, "quotes": count} for author, count in waiting], ensure_ascii=False, indent=1))
    for problem in problems:
        print("problem: " + problem, file=sys.stderr)
    print(f"pack {index['version']}: {len(quotes)} quotes, {len(art)} art pieces, {len(waiting)} people waiting for a portrait, {'changed' if changed else 'unchanged'}", file=sys.stderr)

    if check:
        return 1 if problems or changed else 0
    save_quotes(quotes)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate the pack, drop duplicates, assign art and rebuild data/index.json")
    parser.add_argument("--check", action="store_true", help="fail if the pack has problems or the index is stale")
    parser.add_argument("--backfill", action="store_true", help="print the people who have quotes but no portrait yet")
    arguments = parser.parse_args()
    sys.exit(build(arguments.check, arguments.backfill))
