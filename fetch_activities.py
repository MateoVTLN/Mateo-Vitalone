"""Fetch the FULL Strava activity history into activities.json.

- Paginates through /athlete/activities (200 per page) until exhausted.
- Keeps activities.json lean: only the fields the site actually uses.
- Caches photo URLs from the previous activities.json so old photos are
  not re-fetched on every run; photos are (re)fetched only for activities
  that report photos but have none cached, plus the most recent ones.
- Stays well under Strava rate limits (200 req / 15 min, 2000 / day).
"""

import json
import os
import time

import requests

KEEP_FIELDS = [
    "id", "name", "distance", "moving_time", "elapsed_time",
    "total_elevation_gain", "type", "sport_type", "start_date",
    "start_date_local", "timezone", "average_speed", "max_speed",
    "average_heartrate", "max_heartrate", "achievement_count",
    "kudos_count", "total_photo_count", "location_city", "location_country",
]

MAX_PHOTO_REQUESTS = 80      # per run, keeps us far from rate limits
REFRESH_RECENT_PHOTOS = 10   # always re-check photos for the N newest activities


def get_access_token():
    auth = requests.post("https://www.strava.com/oauth/token", data={
        "client_id":     os.environ["STRAVA_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        "grant_type":    "refresh_token",
    })
    if auth.status_code != 200 or "access_token" not in auth.json():
        # Strava's error body never contains secrets, so it is safe to print.
        print(f"::error::Strava token refresh failed (HTTP {auth.status_code}): {auth.text}")
        print("Most likely the STRAVA_REFRESH_TOKEN secret is no longer valid "
              "(revoked or re-authorized app). Regenerate it and update the "
              "repository secret — see STRAVA_SETUP.md.")
        raise SystemExit(1)
    return auth.json()["access_token"]


def fetch_all_activities(headers):
    """Paginate through the whole activity history."""
    activities, page = [], 1
    while True:
        resp = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page},
        )
        if resp.status_code != 200:
            print(f"::error::Fetching activities page {page} failed "
                  f"(HTTP {resp.status_code}): {resp.text[:500]}")
            raise SystemExit(1)
        batch = resp.json()
        if not batch:
            break
        activities.extend(batch)
        print(f"Page {page}: {len(batch)} activities")
        page += 1
        time.sleep(1)
    return activities


def fetch_photos(headers, activity_id):
    resp = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/photos",
        headers=headers,
        params={"size": 1200},
    )
    if resp.status_code != 200:
        return []
    return [
        p["urls"]["1200"]
        for p in resp.json()
        if isinstance(p, dict) and "urls" in p and "1200" in p["urls"]
    ]


def load_cache():
    """Previous activities.json → {id: activity} for photo-URL reuse."""
    try:
        with open("activities.json", encoding="utf-8") as f:
            return {a["id"]: a for a in json.load(f) if isinstance(a, dict) and "id" in a}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    raw = fetch_all_activities(headers)
    print(f"Total activities fetched: {len(raw)}")

    cache = load_cache()
    photo_budget = MAX_PHOTO_REQUESTS
    slim = []

    for i, a in enumerate(raw):
        entry = {k: a.get(k) for k in KEEP_FIELDS}
        entry["map"] = {"summary_polyline": (a.get("map") or {}).get("summary_polyline", "")}

        cached = cache.get(a["id"], {})
        entry["photos_urls"] = cached.get("photos_urls", [])

        has_photos = (a.get("total_photo_count") or a.get("photo_count") or 0) > 0
        needs_fetch = has_photos and (not entry["photos_urls"] or i < REFRESH_RECENT_PHOTOS)
        if needs_fetch and photo_budget > 0:
            entry["photos_urls"] = fetch_photos(headers, a["id"])
            photo_budget -= 1
            time.sleep(0.5)

        slim.append(entry)

    slim.sort(key=lambda x: x["start_date"] or "", reverse=True)

    with open("activities.json", "w", encoding="utf-8") as f:
        json.dump(slim, f, indent=1, ensure_ascii=False)

    print(f"Wrote activities.json: {len(slim)} activities, "
          f"{os.path.getsize('activities.json') / 1024:.0f} KB")


if __name__ == "__main__":
    main()
