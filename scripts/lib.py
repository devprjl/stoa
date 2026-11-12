import datetime
import hashlib
import json
import re
import time
import tomllib
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ART = DATA / "art"
CACHE = ROOT / "scripts" / ".cache"
USER_AGENT = "stoa-pack-builder/1.0"
CATEGORIES = ("philosophy", "literature", "game", "movie", "tv")


def fetch(url, binary=False, attempts=6, headers=None):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            return body if binary else body.decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or attempt == attempts - 1:
                raise
            time.sleep(min(120, int(error.headers.get("Retry-After") or 20) + 2))


def api(host, **params):
    params.update(format="json", formatversion="2")
    return json.loads(fetch(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params)))


def sources():
    with open(ROOT / "scripts" / "sources.toml", "rb") as handle:
        return tomllib.load(handle)["source"]


def normalize(text):
    text = unicodedata.normalize("NFKD", text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def quote_id(text):
    return hashlib.sha1(normalize(text).encode()).hexdigest()[:8]


def file_hash(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:8]


def load_quotes():
    path = DATA / "quotes.json"
    return json.loads(path.read_text()) if path.exists() else []


def save_quotes(quotes):
    rows = [json.dumps(quote, ensure_ascii=False) for quote in quotes]
    (DATA / "quotes.json").write_text("[\n" + ",\n".join(rows) + "\n]\n")


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
