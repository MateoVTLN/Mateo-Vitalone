"""Build activities.json from a Strava *bulk export* (no API needed).

Strava reserved its API to paid subscribers, so the daily API workflow can no
longer run. This script is the free alternative: it turns the ZIP you get from
    Strava → Settings → My Account → "Download or Delete Your Account"
             → "Download Request (optional)"
into the same activities.json the website already consumes.

It keeps EVERYTHING the site uses — distance, time, pace, elevation, heart rate,
route maps — for your WHOLE history, and it preserves the photos and kudos that
were already fetched via the API (merged in by activity id, so they are not lost).

Usage
-----
    # one-time, for Garmin .fit routes:
    pip install fitdecode

    python import_strava_export.py  path/to/unzipped_export_folder

Then review activities.json, commit it and push — GitHub Pages redeploys itself.

What the free export CANNOT give (Strava limitation, not this script):
  * new photos for activities that were never fetched via the API
  * kudos counts for those same activities
Both are preserved for activities we HAD already fetched.
"""

import csv
import glob
import gzip
import json
import math
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    import fitdecode
    HAVE_FIT = True
except ImportError:
    HAVE_FIT = False

OUTPUT = "activities.json"
MAX_POLYLINE_POINTS = 250   # decimate summary routes to keep the JSON light

# CSV headers are localised to the account language — accept EN and FR.
ALIASES = {
    "id":        ["Activity ID", "ID de l'activité"],
    "date":      ["Activity Date", "Date de l'activité"],
    "name":      ["Activity Name", "Nom de l'activité"],
    "type":      ["Activity Type", "Type d'activité"],
    "elapsed":   ["Elapsed Time", "Temps écoulé"],
    "moving":    ["Moving Time", "Temps de déplacement", "Temps de mouvement"],
    "distance":  ["Distance"],
    "elevation": ["Elevation Gain", "Dénivelé positif", "Gain d'altitude"],
    "avg_hr":    ["Average Heart Rate", "Fréquence cardiaque moyenne"],
    "max_hr":    ["Max Heart Rate", "Fréquence cardiaque maximale"],
    "max_speed": ["Max Speed", "Vitesse maximale"],
    "filename":  ["Filename", "Nom de fichier"],
}

# Normalise localised sport names to the English tokens the site expects.
TYPE_MAP = {
    "course à pied": "Run", "course a pied": "Run", "run": "Run",
    "trail": "TrailRun", "trail run": "TrailRun", "course en sentier": "TrailRun",
    "vélo": "Ride", "sortie vélo": "Ride", "sortie a velo": "Ride", "ride": "Ride",
    "vtt": "MountainBikeRide", "mountain bike ride": "MountainBikeRide",
    "marche": "Walk", "walk": "Walk",
    "randonnée": "Hike", "randonnee": "Hike", "hike": "Hike",
    "natation": "Swim", "swim": "Swim",
    "musculation": "WeightTraining", "weight training": "WeightTraining",
    "entraînement": "Workout", "entrainement": "Workout", "workout": "Workout",
    "aviron": "Rowing", "rowing": "Rowing",
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
    picked[-1] = coords[-1]          # always keep the true finish point
    return picked


def haversine(coords):
    """Total path length in metres, from a list of (lat, lng)."""
    total, R = 0.0, 6371000.0
    for (a_lat, a_lng), (b_lat, b_lng) in zip(coords, coords[1:]):
        p1, p2 = math.radians(a_lat), math.radians(b_lat)
        dp, dl = math.radians(b_lat - a_lat), math.radians(b_lng - a_lng)
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        total += 2 * R * math.asin(math.sqrt(h))
    return total


# ── track-file parsing → (coords, start_iso) ──────────────────────────────
def _open_maybe_gz(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")


def _strip_ns(tag):
    return tag.split("}", 1)[-1]


def parse_gpx(fh):
    coords, start = [], None
    for _, el in ET.iterparse(fh, events=("end",)):
        tag = _strip_ns(el.tag)
        if tag == "trkpt":
            try:
                coords.append((float(el.attrib["lat"]), float(el.attrib["lon"])))
            except (KeyError, ValueError):
                pass
            if start is None:
                t = el.find("{*}time")
                if t is not None and t.text:
                    start = t.text
            el.clear()
    return coords, start


def parse_tcx(fh):
    coords, start = [], None
    for _, el in ET.iterparse(fh, events=("end",)):
        tag = _strip_ns(el.tag)
        if tag == "Trackpoint":
            lat = el.find(".//{*}LatitudeDegrees")
            lng = el.find(".//{*}LongitudeDegrees")
            if lat is not None and lng is not None:
                try:
                    coords.append((float(lat.text), float(lng.text)))
                except (TypeError, ValueError):
                    pass
            if start is None:
                t = el.find("{*}Time")
                if t is not None and t.text:
                    start = t.text
            el.clear()
    return coords, start


def parse_fit(path):
    if not HAVE_FIT:
        return [], None
    coords, start = [], None
    sc = 180.0 / 2 ** 31
    opener = gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")
    with opener as raw, fitdecode.FitReader(raw) as fit:
        for frame in fit:
            if not isinstance(frame, fitdecode.FitDataMessage) or frame.name != "record":
                continue
            if frame.has_field("position_lat") and frame.has_field("position_long"):
                lat, lng = frame.get_value("position_lat"), frame.get_value("position_long")
                if lat is not None and lng is not None:
                    coords.append((lat * sc, lng * sc))
                    if start is None and frame.has_field("timestamp"):
                        ts = frame.get_value("timestamp")
                        if isinstance(ts, datetime):
                            start = ts.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return coords, start


def read_track(path):
    """Return (coords, start_iso) for any supported track file, or ([], None)."""
    low = path.lower()
    try:
        if low.endswith((".fit", ".fit.gz")):
            return parse_fit(path)
        with _open_maybe_gz(path) as fh:
            if ".gpx" in low:
                return parse_gpx(fh)
            if ".tcx" in low:
                return parse_tcx(fh)
    except Exception as exc:       # noqa: BLE001 — a bad file must not stop the run
        print(f"   ! could not parse {os.path.basename(path)}: {exc}")
    return [], None


# ── CSV reading (duplicate + localised headers) ────────────────────────────
def read_rows(csv_path):
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        # map each logical field to ALL column indexes that match one of its aliases
        cols = {}
        for field, names in ALIASES.items():
            wanted = {n.lower() for n in names}
            cols[field] = [i for i, h in enumerate(header) if h.strip().lower() in wanted]
        for raw in reader:
            if not any(raw):
                continue
            yield {f: [raw[i] for i in idxs if i < len(raw)] for f, idxs in cols.items()}


def _first(values):
    for v in values:
        if v not in (None, ""):
            return v
    return None


def _num(values, kind=float):
    """Pick the largest sensible number among duplicate columns (SI unit)."""
    best = None
    for v in values:
        try:
            n = kind(str(v).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if best is None or n > best:
            best = n
    return best


FR_MONTHS = {"janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5,
             "juin": 6, "juil": 7, "août": 8, "aout": 8, "sept": 9, "oct": 10,
             "nov": 11, "déc": 12, "dec": 12}


def parse_date(raw):
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%b %d, %Y, %I:%M:%S %p", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S",
                "%d %b %Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)\
                           .isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    # French export format, e.g. "1 juil. 2026 09:42:16" / "1 juil. 2026, 09:42:16"
    try:
        parts = raw.replace(",", "").split()
        day = int(parts[0])
        month = FR_MONTHS[parts[1].rstrip(".").lower()]
        year = int(parts[2])
        hh, mm, ss = (int(x) for x in parts[3].split(":")) if len(parts) > 3 else (0, 0, 0)
        return datetime(year, month, day, hh, mm, ss, tzinfo=timezone.utc)\
               .isoformat().replace("+00:00", "Z")
    except (ValueError, KeyError, IndexError):
        return raw   # last resort: let the browser try


def load_existing(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {a["id"]: a for a in data if isinstance(a, dict) and a.get("id")}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# ── main ───────────────────────────────────────────────────────────────────
def main(export_dir):
    csvs = glob.glob(os.path.join(export_dir, "activities.csv"))
    if not csvs:
        csvs = glob.glob(os.path.join(export_dir, "**", "activities.csv"), recursive=True)
    if not csvs:
        sys.exit(f"activities.csv not found under {export_dir!r}. "
                 f"Point me at the UNZIPPED export folder.")
    csv_path = csvs[0]
    base = os.path.dirname(csv_path)
    print(f"Reading {csv_path}")
    if not HAVE_FIT:
        print("   (fitdecode not installed — Garmin .fit routes will be skipped. "
              "Run: pip install fitdecode)")

    existing = load_existing(OUTPUT)
    photos_kept = routes = with_route = 0
    out = []

    for row in read_rows(csv_path):
        aid = _first(row["id"])
        if not aid:
            continue
        try:
            aid = int(aid)
        except ValueError:
            continue

        distance = _num(row["distance"]) or 0.0
        if 0 < distance < 100:          # value was in km, not metres
            distance *= 1000
        moving = int(_num(row["moving"], float) or _num(row["elapsed"], float) or 0)
        elapsed = int(_num(row["elapsed"], float) or moving)

        coords, start_iso = ([], None)
        fname = _first(row["filename"])
        if fname:
            coords, start_iso = read_track(os.path.join(base, fname.strip()))

        if coords and (not distance or distance < 100):
            distance = round(haversine(coords), 1)   # fallback from GPS

        raw_type = (_first(row["type"]) or "Workout").strip()
        sport = TYPE_MAP.get(raw_type.lower(), raw_type.replace(" ", ""))

        poly = encode_polyline(decimate(coords)) if coords else ""
        if poly:
            with_route += 1
        routes += 1

        prev = existing.get(aid, {})
        photos = prev.get("photos_urls", [])
        if photos:
            photos_kept += 1

        avg_speed = (distance / moving) if moving else None

        out.append({
            "id": aid,
            "name": _first(row["name"]) or "Activity",
            "distance": round(distance, 1),
            "moving_time": moving,
            "elapsed_time": elapsed,
            "total_elevation_gain": round(_num(row["elevation"]) or 0, 1),
            "type": sport,
            "sport_type": sport,
            "start_date": start_iso or parse_date(_first(row["date"])),
            "average_speed": round(avg_speed, 3) if avg_speed else None,
            "max_speed": _num(row["max_speed"]),
            "average_heartrate": _num(row["avg_hr"]),
            "max_heartrate": _num(row["max_hr"]),
            "kudos_count": prev.get("kudos_count", 0),
            "total_photo_count": len(photos),
            "map": {"summary_polyline": poly},
            "photos_urls": photos,
        })

    out.sort(key=lambda x: x["start_date"] or "", reverse=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print(f"\nWrote {OUTPUT}: {len(out)} activities "
          f"({with_route} with a route map), "
          f"{photos_kept} kept their photos, "
          f"{os.path.getsize(OUTPUT) / 1024:.0f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python import_strava_export.py <unzipped_export_folder>")
    main(sys.argv[1])
