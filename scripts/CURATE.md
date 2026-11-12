# Weekly curation run

These are the instructions for an unattended weekly run that adds a small, hand-picked batch of quotes to the pack. The daily GitHub Actions job already adds quotes by rule; this run exists to add the ones that need judgement.

## Limits

- Add at most 40 quotes per run. Stop early if anything below fails twice.
- Never edit or delete an existing quote or art file. Only add.
- Never write a quote from memory. Every quote must come out of `scripts/harvest.py`, which takes the wording from Wikiquote.
- Every new quote must end the run with its own art file. No two quotes may share an artwork.

## Steps

1. Install the one dependency: `pip install pillow`.
2. List candidates without saving them:
   `python scripts/harvest.py --per-source 4 --count 300 --dry-run > /tmp/candidates.json`
3. Read the candidates and choose up to 40. Prefer lines that stand on their own without context, say something true or striking in one or two sentences, and are not near-duplicates of each other. Keep a mix of philosophy, literature, games, film and TV. Skip anything that needs the scene around it to make sense.
4. Append the chosen entries to `data/quotes.json` (same fields as the existing entries, without the `score` field), then run `python scripts/build.py --prune` once so ids are normalized. Quotes without art are held back by `--prune`, so do the next step before the final build.
5. For each chosen quote, pick an artwork that fits what the quote means:
   - Search the Art Institute of Chicago, the Cleveland Museum of Art and the Met through the functions in `scripts/art.py` (`search_aic`, `search_cma`, `search_met`) with search terms you choose for that quote.
   - Choose a candidate whose title and subject suit the quote, that is public domain, and that no existing file in `data/art/` already uses (compare the `source` field).
   - Convert it with `convert(image_bytes(candidate))`. If it returns nothing, the image does not read well in braille; pick another.
   - Write `data/art/<quote id>.json` with the same fields as the existing art files.
   - If you cannot find a fitting piece after a few tries, run `python scripts/art.py --only <quote id>` and accept the automatic match.
6. Run the checks. All must pass:
   - `python scripts/build.py` then `python scripts/build.py --check`
   - `nvim -l tests/run.lua` (skip if Neovim is not installed)
7. Commit only the `data/` directory with the message `Add curated quotes` and push to `main`. If the push is rejected, `git pull --rebase` and push again.

## If something is wrong

If a museum or Wikiquote is unreachable, finish with whatever is complete and valid. If nothing is, make no commit. Do not change the scripts, the plugin or the workflows in this run.
