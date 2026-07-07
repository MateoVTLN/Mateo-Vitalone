# Updating the Sport page from Garmin Connect (free)

Since Strava closed its API to non-subscribers, this is the recommended free way
to keep the Sport page up to date. Your activities come from your Garmin device
anyway (Garmin → Garmin Connect → Strava), and Garmin has **not** locked your own
data. [`fetch_garmin.py`](fetch_garmin.py) pulls from Garmin Connect and **only
adds activities that aren't already in `activities.json`**, so the Strava
**photos and kudos** already stored are preserved untouched.

Matching is by **start time** (Garmin and Strava use different activity ids): if
a Garmin activity lines up with one already in the file, it's skipped and the
existing Strava version — with its photos — is kept.

## One-time setup

```bash
pip install garminconnect
```

## First run (interactive)

```bash
python fetch_garmin.py
```

- It asks for your Garmin **email** and **password** (or read them from the
  `GARMIN_EMAIL` / `GARMIN_PASSWORD` environment variables), and for your **2FA
  code** if two-factor is enabled.
- On success it saves a **login token** in `.garmin_tokens/` (git-ignored). Your
  password is **never stored** — later runs reuse the token.
- The first run backfills your whole history, so it downloads a route for every
  new activity — expect a few minutes and a line printed per activity.

## Later runs

```bash
python fetch_garmin.py            # scan everything, add only what's new
python fetch_garmin.py --recent 40   # only check the 40 latest (faster)
```

## Publish

```bash
git add activities.json
git commit -m "Add Garmin activities"
git push
```

GitHub Pages redeploys automatically.

## Good to know

- **What you get:** distance, time, pace, elevation, heart rate and the **route
  map** for every activity — your full history.
- **What Garmin can't give:** Strava **kudos** and **photos** (they're Strava
  social features). Those stay only on the activities already fetched via the
  Strava API, which this script preserves.
- **Why local, not automated:** Garmin frequently blocks automated logins from
  cloud servers (GitHub Actions), so this is built to run on your machine.
  Automating it 4×/day is a possible later step, with that reliability caveat.
- This uses the community `garminconnect` library (Garmin's unofficial app API).
  If a Garmin-side change ever breaks it, updating the package usually fixes it:
  `pip install -U garminconnect`.
