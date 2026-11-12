import argparse
import json
import sys

from lib import ART, CATEGORIES, DATA, load_quotes, normalize, quote_id, save_quotes, today

FIELDS = ("id", "text", "author", "work", "category", "ref", "added")


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
        entry.setdefault("added", today())
        kept.append({field: entry[field] for field in FIELDS if entry.get(field)})
    return kept, problems


def check_art(quotes):
    problems, sources = [], {}
    ids = {quote["id"] for quote in quotes}
    for path in sorted(ART.glob("*.json")):
        record = json.loads(path.read_text())
        if path.stem not in ids:
            problems.append(f"art {path.name}: no quote uses it")
        for size in ("large", "small"):
            lines = record.get(size)
            if not isinstance(lines, list) or not lines or len({len(line) for line in lines}) != 1:
                problems.append(f"art {path.name}: bad {size} block")
        source = record.get("source")
        if not source:
            problems.append(f"art {path.name}: no source")
        elif source in sources:
            problems.append(f"art {path.name}: same artwork as {sources[source]} ({source})")
        else:
            sources[source] = path.name
    missing = [quote["id"] for quote in quotes if not (ART / f"{quote['id']}.json").exists()]
    return len(sources), missing, problems


def build(check, prune=False):
    quotes, problems = clean(load_quotes())
    art, missing, art_problems = check_art(quotes)
    problems += art_problems
    if missing and not prune:
        problems.append(f"{len(missing)} quotes have no art yet (run art.py, or build.py --prune to hold them back)")
    if prune:
        quotes = [quote for quote in quotes if quote["id"] not in set(missing)]

    counts = {category: 0 for category in CATEGORIES}
    for quote in quotes:
        counts[quote["category"]] += 1

    index_path = DATA / "index.json"
    previous = json.loads(index_path.read_text()) if index_path.exists() else {}
    body = {"schema": 1, "quotes": len(quotes), "categories": counts, "art": art}
    changed = any(previous.get(key) != value for key, value in body.items()) or load_quotes() != quotes
    index = {"version": previous.get("version", 0) + (1 if changed else 0), "updated": today() if changed else previous.get("updated", today()), **body}

    for problem in problems:
        print("problem: " + problem, file=sys.stderr)
    print(f"pack {index['version']}: {len(quotes)} quotes {counts}, {art} art pieces, {'changed' if changed else 'unchanged'}", file=sys.stderr)

    if check:
        return 1 if problems or changed else 0
    save_quotes(quotes)
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate the pack, drop duplicates and rebuild data/index.json")
    parser.add_argument("--check", action="store_true", help="fail if the pack has problems or the index is stale")
    parser.add_argument("--prune", action="store_true", help="drop quotes that have no art file yet")
    arguments = parser.parse_args()
    sys.exit(build(arguments.check, arguments.prune))
