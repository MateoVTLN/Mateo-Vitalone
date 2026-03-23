import requests, json, os

auth = requests.post("https://www.strava.com/oauth/token", data={
    "client_id":     os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
    "grant_type":    "refresh_token"
})
access_token = auth.json()["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

resp = requests.get("https://www.strava.com/api/v3/athlete/activities",
    headers=headers,
    params={"per_page": 10}
)
activities = resp.json()
print(f"Nombre d'activités reçues: {len(activities)}")
for a in activities:
    print(f"  - {a['name']} | {a['start_date']}")

for activity in activities:
    photo_resp = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity['id']}/photos",
        headers=headers,
        params={"size": 600}
    )
    photos = photo_resp.json()
    activity["photos_urls"] = [
        p["urls"]["600"]
        for p in photos
        if isinstance(p, dict) and "urls" in p and "600" in p["urls"]
    ]
    
with open("activities.json", "w", encoding="utf-8") as f:
    json.dump(activities, f, indent=2, ensure_ascii=False)

print("Fichier écrit, taille:", os.path.getsize("activities.json"), "bytes")
with open("activities.json", "r", encoding="utf-8") as f:
    print("Début du fichier:", f.read(100))
