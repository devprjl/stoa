# Adding portraits

Quotes are added by script. Portraits are the one part that needs a person (or an AI session) to choose an image. Until someone has a portrait, their quotes show the category art, so nothing breaks while this waits.

## See who is waiting

```
python scripts/build.py --backfill
```

This prints the people who have quotes but no portrait, most-quoted first.

## Add a portrait

1. Find an image of the person on Wikimedia Commons. It must be **public domain** (or CC0). A photo of a statue is only public domain if the photo itself is; check the license shown on the file page, not just the age of the statue.
2. Prefer a head-and-shoulders image with a plain background. Busts, old photographs and engravings convert well.
3. Add an entry to `scripts/portraits.toml`:

   ```toml
   [[portrait]]
   id = "epicurus"            # the author's name in lower case, spaces as dashes
   name = "Epicurus"
   image = "https://upload.wikimedia.org/..."   # a version about 500 px wide
   mode = "outline"           # "tone" for dark backgrounds, "outline" for light or busy ones
   credit = "File name (Public domain), Wikimedia Commons"
   ```

   The `id` must match the author name as the pack writes it, or the quotes will not find it. `python scripts/build.py --backfill` shows the names.
4. Build it and look at it:

   ```
   pip install pillow
   python scripts/art.py --only epicurus
   python scripts/art.py --show epicurus
   ```

   If it is hard to read, try the other `mode`, or a different image, then rerun with `--force`. An optional `crop = [left, top, right, bottom]` (fractions from 0 to 1) cuts the image down to the face.
5. Rebuild the pack so the quotes pick up the new portrait, and check it:

   ```
   python scripts/build.py
   python scripts/build.py --check
   nvim -l tests/run.lua
   ```
6. Commit `scripts/portraits.toml` and `data/`.

## Rules

- Only public-domain or CC0 images.
- One portrait per person. To replace one, change its entry and rebuild with `--force`.
- Do not edit quote text by hand. Quotes come from `scripts/harvest.py`.
