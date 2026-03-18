import requests, json, os

# Get a fresh access token
auth = requests.post("https://www.strava.com/oauth/token", data={
    "client_id":     os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
    "grant_type":    "refresh_token"
})
access_token = auth.json()["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

# Fetch latest 10 activities
resp = requests.get("https://www.strava.com/api/v3/athlete/activities",
    headers=headers,
    params={"per_page": 10}
)
activities = resp.json()

# For each activity, fetch its photos
for activity in activities:
    photo_resp = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity['id']}/photos",
        headers=headers,
        params={"size": 600}   # px width — 600 is a good balance
    )
    photos = photo_resp.json()
    # Keep only the URLs of available photos
    activity["photos_urls"] = [
        p["urls"]["600"]
        for p in photos
        if isinstance(p, dict) and "urls" in p and "600" in p["urls"]
    ]

# Save to JSON
with open("activities.json", "w") as f:
    json.dump(activities, f)