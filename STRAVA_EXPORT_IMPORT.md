# Updating the Sport page for free (Strava bulk export)

Strava now reserves its API to **paid subscribers**, so the automatic daily
fetch no longer works on a free account. This is the free alternative: import
your Strava **bulk export** into `activities.json` yourself.

It is **manual** by nature — Strava generates the export on request (it can take
a few hours and is e-mailed to you), so it cannot run automatically 4×/day. But
it rebuilds your **whole history** with totals, records and every route map, and
it **keeps the photos and kudos** already fetched via the API (merged by
activity id, never lost).

## One-time setup

```bash
pip install fitdecode      # lets the importer read Garmin .fit route files
```

## Each time you want to refresh the data

1. **Request your export**: Strava → **Settings → My Account** →
   *"Download or Delete Your Account"* → **"Download Request (optional)"** →
   *Request your archive*. Wait for the e-mail from Strava (often a few hours)
   and download the ZIP.

2. **Unzip it** anywhere on your computer — you get a folder containing
   `activities.csv` and an `activities/` folder of track files.
   ⚠️ Keep this folder **out of the repo** — the full archive contains private
   data (messages, e-mail…). `.gitignore` already blocks the usual names.

3. **Run the importer** from the repo root, pointing at that unzipped folder:

   ```bash
   python import_strava_export.py  "C:/path/to/export_folder"
   ```

   It prints a summary, e.g.
   `Wrote activities.json: 342 activities (318 with a route map), 6 kept their photos`.

4. **Publish**:

   ```bash
   git add activities.json
   git commit -m "Update Strava activities from export"
   git push
   ```

   GitHub Pages redeploys automatically; the Sport page shows the new data.

## What the free export can and can't do

| | Export importer (free) | API (paid subscription) |
|---|---|---|
| Whole history, totals, records, all-routes map | ✅ | ✅ |
| Distance, time, pace, elevation, heart rate | ✅ | ✅ |
| Photos & kudos already fetched | ✅ preserved | ✅ |
| **New** photos & kudos | ❌ not in the export | ✅ |
| Automatic, several times a day | ❌ manual | ✅ 4×/day |

If you later subscribe, re-enable the automatic path: see the top of
`.github/workflows/fetch_strava.yml` and `STRAVA_SETUP.md`.
