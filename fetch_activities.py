import requests, json, os

print("FILE LOADED")

auth = requests.post("https://www.strava.com/oauth/token", data={
    "client_id":     os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
    "grant_type":    "refresh_token"
})
access_token = auth.json()["access_token"]

resp = requests.get("https://www.strava.com/api/v3/athlete/activities",
    headers={"Authorization": f"Bearer {access_token}"},
    params={"per_page": 10}
)

with open("activities.json", "w") as f:
    json.dump(resp.json(), f)