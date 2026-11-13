import argparse
import html
import json
import random
import re
import sys
import time

from lib import CACHE, ENABLED, api, load_quotes, normalize, quote_id, save_quotes, sources, today

SKIP_SECTIONS = re.compile(
    r"misattribut|disputed|attributed|quotes? about|^about|external links|see also|cast|taglines?|dialogue|references|notes|"
    r"criticism|reception|sources|bibliography|voice cast|related|reviews|commentary|production|spurious|incorrect|unsourced|quotations|songs?|ballad|lyrics|soundtrack",
    re.I,
)
CITATION = re.compile(
    r"^(as quoted|quoted in|p\.|pp\.|page|book|chapter|ch\.|line|lines|act|letter|section|§|variant|alternate|translation|source|"
    r"cf\.|ibid|vol\.|part|verse|canto|stanza|fragment|\d)",
    re.I,
)
TERMINAL = (".", "!", "?", ".”", "!”", "?”", '."', '!"', '?"', ".'", "…")


def cache_path(page):
    return CACHE / (re.sub(r"[^\w]+", "_", page) + ".json")


def prefetch(pages):
    CACHE.mkdir(parents=True, exist_ok=True)
    wanted = [page for page in pages if not cache_path(page).exists()]
    for start in range(0, len(wanted), 40):
        batch = wanted[start : start + 40]
        texts, alias, extra = {}, {}, {}
        while True:
            reply = api("en.wikiquote.org", action="query", prop="revisions", rvprop="content", rvslots="main", redirects="1", titles="|".join(batch), **extra)
            query = reply.get("query", {})
            for step in query.get("normalized", []) + query.get("redirects", []):
                alias[step["from"]] = step["to"]
            for page in query.get("pages", []):
                revisions = page.get("revisions")
                if revisions:
                    texts[page["title"]] = revisions[0]["slots"]["main"]["content"]
            if "continue" not in reply:
                break
            extra = reply["continue"]
            time.sleep(1)
        for page in batch:
            title = page
            for _ in range(4):
                title = alias.get(title, title)
            cache_path(page).write_text(json.dumps({"text": texts.get(title)}))
        time.sleep(2)


def wikitext(page):
    if not cache_path(page).exists():
        prefetch([page])
    return json.loads(cache_path(page).read_text())["text"]


def strip_markup(text):
    text = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<\s*/?\s*br\s*/?\s*>", " ", text, flags=re.I)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", text, flags=re.I)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[https?://\S+\s*([^\]]*)\]", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("'''", "").replace("''", "")
    text = html.unescape(text).replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def tidy(text):
    text = re.sub(r"^\[[^\]]*\]\s*", "", text)
    text = re.sub(r"\s*\[[^\]]*\]\s*$", "", text)
    text = text.strip(" \"“”")
    text = text.replace(" -- ", " — ").replace("--", "—")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def acceptable(text, low, high):
    if not (low <= len(text) <= high):
        return False
    if len(text.split()) < 6 or not text.endswith(TERMINAL):
        return False
    if re.search(r"[\[\]{}<>|=_*#~^\\]|https?:|www\.|\bpp?\.\s*\d|\bibid\b", text, re.I):
        return False
    if not re.match(r"[A-Z“\"']", text) or text.count('"') % 2:
        return False
    letters = sum(ch.isascii() and ch.isalpha() for ch in text)
    if letters / len(text) < 0.72 or sum(ch.isdigit() for ch in text) > 4:
        return False
    if re.search(r"\b(shit\w*|fuck\w*|bitch\w*|cum|piss\w*|cunt\w*|whore\w*|nigg\w*|bastard\w*|asshole\w*|damn\w*|goddamn\w*|dick|crap)\b", text, re.I):
        return False
    if text.isupper() or re.search(r"\b(translated|translation|edition|trans\.|ed\.)\b", text, re.I):
        return False
    return True


THEMES = re.compile(
    r"\b(life|live[sd]?|living|death|die[sd]?|dying|dead|time|world|truth|fear|hope|love|war|courage|brave|choice|choose|chosen|fate|destiny|"
    r"dreams?|power|free|freedom|pain|suffer\w*|strength|strong|wisdom|wise|soul|heart|mind|hero\w*|future|past|peace|dark\w*|light|honou?r|duty|"
    r"change|history|nature|memor\w+|men|man|people|human\w*|mankind|gods?|faith|justice|virtue|evil|good|happiness|happy|sorrow|grief|victory|"
    r"defeat|fail\w*|fall|rise|learn\w*|know\w*|teach\w*|fool\w*|kings?|sword|battle|enemy|enemies|friends?|alone|lonel\w+|beauty|"
    r"beautiful|stars?|night|dawn|fire|ashes|blood|home|journey|path|road|end|begin\w*|forever|eternity|eternal|mortal\w*|silence|"
    r"anger|hate|hatred|revenge|mercy|forgive\w*|regret|purpose|meaning|believe|belief|trust|lies?|honest\w*)\b",
    re.I,
)
GENERAL = re.compile(r"\b(never|always|every|everyone|everything|no one|nothing|those who|he who|whoever|all men|we are|we must|only|must|cannot|is not|there is no)\b", re.I)
PLAIN_CAPITALS = {"I", "I'm", "I've", "I'll", "I'd", "God", "Gods", "Nature", "Heaven", "Fate", "Time", "Death", "Truth", "Man", "Fortune", "Reason", "Love", "Life"}
MINIMUM = {"game": 2, "movie": 2, "tv": 2, "philosophy": 1, "literature": 2}


def names_in(text):
    count = 0
    for sentence in re.split(r"(?<=[.!?;:—])\s+", text):
        for word in sentence.split()[1:]:
            bare = word.strip(",.;:!?\"'“”’()")
            if bare[:1].isupper() and bare not in PLAIN_CAPITALS:
                count += 1
    return count


def wisdom(text, category):
    if re.match(r"^[A-Z][\w'’. -]{1,28}:\s", text) or re.search(r"[()]|\.\.\.|…|\?!|!!|\bkupo\b|\bok(ay)?\b|\bgonna\b.*\bgonna\b", text, re.I):
        return -9
    names = names_in(text)
    if names > (1 if category in ("game", "movie", "tv") else 2):
        return -9
    score = min(4, len(set(match.lower() for match in THEMES.findall(text)))) - names
    score += 1 if GENERAL.search(text) else 0
    score -= 1 if text.count("!") else 0
    score -= 1 if re.search(r"\b(you|your|me|my)\b", text, re.I) and category in ("game", "movie", "tv") and score < 3 else 0
    return score


def clean_work(work):
    if not work or len(work) < 3 or re.search(r"bartlett|dictionary|quotations|\bed\.|\bvol\.|[\[\]{}|=]|^\W+$", work, re.I):
        return None
    return work


def candidates(page_text, source):
    low, high = source.get("min", 40), source.get("max", 190)
    lines = page_text.split("\n")
    stack, found, seen_quotes_section = [], [], False

    for number, line in enumerate(lines):
        heading = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", line)
        if heading:
            level = len(heading.group(1))
            raw = heading.group(2)
            stack = [item for item in stack if item[0] < level]
            stack.append((level, strip_markup(raw), raw.strip().startswith("''")))
            continue

        if not re.match(r"^\*[^*]", line):
            continue
        if not stack or any(SKIP_SECTIONS.search(title) for _, title, _ in stack):
            continue

        raw = line[1:].strip()
        following = lines[number + 1] if number + 1 < len(lines) else ""
        translated = re.match(r"^\*\*([^*].*)$", following)
        whole_italic = raw.startswith("''") and not raw.startswith("'''") and raw.rstrip(" .").endswith("''")
        letters = [ch for ch in strip_markup(raw) if ch.isalpha()]
        foreign = bool(letters) and sum(ch.isascii() for ch in letters) / len(letters) < 0.5
        if (whole_italic or foreign) and translated and not CITATION.match(strip_markup(translated.group(1))):
            raw = translated.group(1).strip()

        bold = raw.startswith("'''") and raw.rstrip().rstrip(".!?\"”").endswith("'''")
        partly_bold = "'''" in raw
        text = tidy(strip_markup(raw))
        if not acceptable(text, low, high):
            continue

        titles = [title for _, title, _ in stack]
        work = source.get("work")
        author = source.get("author")
        if source["category"] in ("game", "movie", "tv"):
            speaker = titles[-1]
            generic = re.search(r"quotes?|others?|misc|unknown|various|narrat|intro|opening|ending|general|trailer|loading|items?|descriptions?", speaker, re.I)
            if not author and not generic and len(speaker) <= 32 and speaker.lower() != work.lower():
                author = speaker
        elif not work:
            italic = [title for _, title, is_italic in stack if is_italic]
            if italic:
                work = re.sub(r"\s*\([^)]*\)\s*$", "", italic[0]).strip() or None

        depth = wisdom(text, source["category"])
        if depth < MINIMUM[source["category"]]:
            continue
        score = depth + (3 if bold else 1 if partly_bold else 0) + (1 if 60 <= len(text) <= 150 else 0)
        found.append({"text": text, "author": author, "work": clean_work(work), "score": score})

    return found


def harvest(count, per_source, only, dry_run, seed):
    rng = random.Random(seed)
    quotes = load_quotes()
    known = {normalize(quote["text"]) for quote in quotes}
    totals = {}
    for quote in quotes:
        totals[quote.get("ref")] = totals.get(quote.get("ref"), 0) + 1

    pool = [source for source in sources() if source["category"] in ENABLED and (not only or source["page"] in only)]
    names = [source["page"] for source in pool]
    prefetch(names if count is None else names[: max(40, count * 4)])
    pool.sort(key=lambda source: (totals.get("wikiquote:" + source["page"], 0), rng.random()))

    added, scores, report = [], [], []
    for source in pool:
        if count is not None and len(added) >= count:
            break
        ref = "wikiquote:" + source["page"]
        try:
            page_text = wikitext(source["page"])
        except Exception as error:
            report.append(f"skip  {source['page']}: {error}")
            continue
        if page_text is None:
            report.append(f"miss  {source['page']}")
            continue

        fresh = []
        for item in candidates(page_text, source):
            key = normalize(item["text"])
            if key in known:
                continue
            known.add(key)
            fresh.append(item)
        rng.shuffle(fresh)
        fresh.sort(key=lambda item: -item["score"])

        room = per_source if count is None else min(per_source, count - len(added))
        taken = fresh[:room]
        for item in taken:
            entry = {"id": quote_id(item["text"]), "text": item["text"]}
            if item["author"]:
                entry["author"] = item["author"]
            if item["work"]:
                entry["work"] = item["work"]
            entry.update(category=source["category"], ref=ref, added=today())
            added.append(entry)
            scores.append(item["score"])
        report.append(f"{len(taken):>4}  of {len(fresh):>4} new  {source['page']}")

    print("\n".join(report), file=sys.stderr)
    print(f"added {len(added)} quotes, pack now {len(quotes) + len(added)}", file=sys.stderr)
    if dry_run:
        print(json.dumps([{**entry, "score": score} for entry, score in zip(added, scores)], ensure_ascii=False, indent=1))
    elif added:
        save_quotes(quotes + added)
    return added


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull new quotes from Wikiquote into data/quotes.json")
    parser.add_argument("--count", type=int, default=None, help="stop after this many new quotes in total")
    parser.add_argument("--per-source", type=int, default=1, help="most new quotes to take from one source")
    parser.add_argument("--only", action="append", help="limit to this Wikiquote page (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print the new quotes without saving them")
    parser.add_argument("--seed", type=int, default=None)
    arguments = parser.parse_args()
    harvest(arguments.count, arguments.per_source, arguments.only, arguments.dry_run, arguments.seed)
