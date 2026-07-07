"""Incrementally import Garmin Connect activities into activities.json.

Your activities originate on your Garmin device (Garmin → Garmin Connect →
Strava), and Garmin has NOT closed access to your own data the way Strava did.
This script pulls from Garmin Connect and **only adds activities that are not
already in activities.json** — matched by start time — so existing entries
(and the Strava photos / kudos they carry) are preserved untouched.

Garmin uses different activity ids than Strava, so matching is done on the
start timestamp (within a 2-minute window): if a Garmin activity lines up with
one already in the file, it is skipped and the existing (Strava) version is kept.

Setup
-----
    pip install garminconnect

First run (interactive — handles two-factor auth):
    # optional: avoid typing them by setting env vars first
    #   Windows PowerShell:  $env:GARMIN_EMAIL="you@mail"; $env:GARMIN_PASSWORD="…"
    python fetch_garmin.py
    -> a login token is saved in .garmin_tokens/ (gitignored); later runs reuse
       it, so you never store your password anywhere.

Later runs:
    python fetch_garmin.py            # scans all, adds only what's new
    python fetch_garmin.py --recent 40   # only look at the 40 latest (faster)

Note: Garmin often blocks automated logins from cloud servers, which is why this
is meant to run locally. Automating it (4×/day) is a separate, later step.
"""

import getpass
import json
import os
import sys
import time
from datetime import datetime, timezone

OUTPUT = "activities.json"
TOKENSTORE = os.path.expanduser(os.environ.get("GARMINTOKENS", ".garmin_tokens"))
MATCH_TOLERANCE_S = 120        # two activities within 2 min = the same one
MAX_POLYLINE_POINTS = 250
PAGE = 100

# Garmin typeKey → the English tokens the website expects (icons + pace logic).
TYPE_MAP = {
    "running": "Run", "treadmill_running": "Run", "indoor_running": "Run",
    "trail_running": "TrailRun",
    "cycling": "Ride", "road_biking": "Ride", "gravel_cycling": "Ride",
    "indoor_cycling": "Ride", "virtual_ride": "Ride", "commuting": "Ride",
    "mountain_biking": "MountainBikeRide",
    "walking": "Walk", "casual_walking": "Walk", "speed_walking": "Walk",
    "hiking": "Hike",
    "lap_swimming": "Swim", "open_water_swimming": "Swim",
    "strength_training": "WeightTraining",
    "indoor_cardio": "Workout", "cardio": "Workout", "hiit": "Workout",
    "fitness_equipment": "Workout", "yoga": "Workout", "pilates": "Workout",
    "rowing": "Rowing", "indoor_rowing": "Rowing",
    "resort_skiing_snowboarding": "AlpineSki", "cross_country_skiing": "NordicSki",
}


# ── polyline encoding (inverse of the decoder in script.js) ────────────────
def encode_polyline(coords, precision=5):
    factor = 10 ** precision
    out, prev_lat, prev_lng = [], 0, 0
    for lat, lng in coords:
        lat_i, lng_i = round(lat * factor), round(lng * factor)
        for delta in (lat_i - prev_lat, lng_i - prev_lng):
            delta = ~(delta << 1) if delta < 0 else (delta << 1)
            while delta >= 0x20:
                out.append(chr((0x20 | (delta & 0x1f)) + 63))
                delta >>= 5
            out.append(chr(delta + 63))
        prev_lat, prev_lng = lat_i, lng_i
    return "".join(out)


def decimate(coords, max_points=MAX_POLYLINE_POINTS):
    if len(coords) <= max_points:
        return coords
    step = len(coords) / max_points
    picked = [coords[int(i * step)] for i in range(max_points)]
    picked[-1] = coords[-1]
    return picked


# ── time helpers ───────────────────────────────────────────────────────────
def parse_epoch(s):
    """Epoch seconds (UTC) from a Strava 'Z' or Garmin 'YYYY-MM-DD HH:MM:SS' stamp."""
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s) if "T" in s else \
            datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def gmt_to_iso(s):
    e = parse_epoch(s)
    if e is None:
        return s
    return datetime.fromtimestamp(e, timezone.utc).isoformat().replace("+00:00", "Z")


# ── existing file ──────────────────────────────────────────────────────────
def load_existing():
    try:
        with open(OUTPUT, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []
    starts = [e for e in (parse_epoch(a.get("start_date")) for a in data) if e]
    return data, starts


def is_present(epoch, starts):
    return epoch is not None and any(abs(epoch - s) <= MATCH_TOLERANCE_S for s in starts)


# ── Garmin login (lazy import so the file loads without the package) ───────
def _save_token(g):
    """Persist the login token. garminconnect exposes garth differently across
    versions, so try the known variants and don't crash if none work."""
    import garth
    for save in (lambda: g.garth.dump(TOKENSTORE),      # per-instance client
                 lambda: garth.save(TOKENSTORE),        # module-level client
                 lambda: garth.client.dump(TOKENSTORE)):
        try:
            save()
            print(f"Login token saved to {TOKENSTORE}/ — next runs won't log in again.")
            return True
        except Exception:                  # noqa: BLE001 — try the next variant
            continue
    return False


def login():
    try:
        from garminconnect import Garmin
    except ImportError:
        sys.exit("The 'garminconnect' package is required:  pip install garminconnect")

    # 1) reuse a saved token if we have one — no network login, so no rate limit
    try:
        g = Garmin()
        g.login(TOKENSTORE)
        print("Logged in to Garmin (reused saved token).")
        return g
    except Exception:                      # noqa: BLE001 — fall back to fresh login
        pass

    # 2) fresh interactive login (handles 2FA)
    email = os.environ.get("GARMIN_EMAIL") or input("Garmin email: ")
    password = os.environ.get("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")
    g = Garmin(email=email, password=password,
               prompt_mfa=lambda: input("Garmin 2FA code: "))
    try:
        g.login()
    except Exception as exc:               # noqa: BLE001
        msg = str(exc)
        if "429" in msg or "rate" in msg.lower():
            sys.exit("\nGarmin is rate-limiting your IP (HTTP 429) after too many "
                     "login attempts.\nWait ~30-60 minutes, then run this ONCE more. "
                     "After the first success the token is saved and no further "
                     "logins are needed.")
        raise

    # 3) persist the token so we never have to log in (and risk a 429) again.
    #    Even if saving fails, keep going — this run still fetches your data.
    if not _save_token(g):
        print("! Could not save the login token (harmless): this run works, but you "
              "may be prompted to log in again next time.")
    return g


# ── build one activities.json entry from a Garmin activity ─────────────────
def to_entry(g, act):
    aid = act.get("activityId")
    dist = float(act.get("distance") or 0)
    moving = int(act.get("movingDuration") or act.get("duration") or 0)
    elapsed = int(act.get("elapsedDuration") or act.get("duration") or moving)
    avg_speed = act.get("averageSpeed") or (dist / moving if moving else None)
    tkey = (act.get("activityType") or {}).get("typeKey", "") or ""
    sport = TYPE_MAP.get(tkey, tkey.replace("_", " ").title().replace(" ", "") or "Workout")

    poly = ""
    try:
        det = g.get_activity_details(aid, maxchart=0, maxpoly=MAX_POLYLINE_POINTS)
        pts = (det.get("geoPolylineDTO") or {}).get("polyline") or []
        coords = [(p["lat"], p["lon"]) for p in pts
                  if p.get("lat") is not None and p.get("lon") is not None]
        if coords:
            poly = encode_polyline(decimate(coords))
    except Exception:                      # noqa: BLE001 — a missing route must not stop the run
        pass

    return {
        "id": aid,
        "name": act.get("activityName") or "Activity",
        "distance": round(dist, 1),
        "moving_time": moving,
        "elapsed_time": elapsed,
        "total_elevation_gain": round(float(act.get("elevationGain") or 0), 1),
        "type": sport,
        "sport_type": sport,
        "start_date": gmt_to_iso(act.get("startTimeGMT")),
        "average_speed": round(avg_speed, 3) if avg_speed else None,
        "max_speed": act.get("maxSpeed"),
        "average_heartrate": act.get("averageHR"),
        "max_heartrate": act.get("maxHR"),
        "kudos_count": 0,
        "total_photo_count": 0,
        "map": {"summary_polyline": poly},
        "photos_urls": [],
        "source": "garmin",
    }


def fetch_summaries(g, cap):
    acts, start = [], 0
    while True:
        batch = g.get_activities(start, PAGE)
        if not batch:
            break
        acts.extend(batch)
        start += PAGE
        if cap and len(acts) >= cap:
            return acts[:cap]
        time.sleep(0.5)
    return acts


def main(cap=None):
    g = login()
    existing, starts = load_existing()
    print(f"{len(existing)} activities already in {OUTPUT}.")

    summaries = fetch_summaries(g, cap)
    print(f"Garmin returned {len(summaries)} activities to check.\n")

    new_entries, added = [], 0
    for act in summaries:
        epoch = parse_epoch(act.get("startTimeGMT"))
        if is_present(epoch, starts):
            continue                       # already have it (keep Strava version)
        entry = to_entry(g, act)
        new_entries.append(entry)
        if epoch:
            starts.append(epoch)           # dedup within the Garmin set too
        added += 1
        route = "🗺" if entry["map"]["summary_polyline"] else "  "
        print(f"  + {route} {(entry['start_date'] or '')[:10]}  {entry['name']}")
        time.sleep(0.4)                    # be polite to Garmin

    merged = existing + new_entries
    merged.sort(key=lambda x: x.get("start_date") or "", reverse=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=1, ensure_ascii=False)

    print(f"\nAdded {added} new activities. Total now {len(merged)} "
          f"({os.path.getsize(OUTPUT) / 1024:.0f} KB).")
    if added:
        print("Review activities.json, then:  git add activities.json && "
              'git commit -m "Add Garmin activities" && git push')


if __name__ == "__main__":
    limit = None
    if len(sys.argv) == 3 and sys.argv[1] == "--recent":
        limit = int(sys.argv[2])
    elif len(sys.argv) != 1:
        sys.exit("Usage: python fetch_garmin.py [--recent N]")
    main(limit)
