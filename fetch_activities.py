import requests, json, os

print("imports OK")
print("CLIENT_ID set:", "STRAVA_CLIENT_ID" in os.environ)
print("CLIENT_SECRET set:", "STRAVA_CLIENT_SECRET" in os.environ)
print("REFRESH_TOKEN set:", "STRAVA_REFRESH_TOKEN" in os.environ)

# Get a fresh access token
auth = requests.post("https://www.strava.com/oauth/token", data={
    "client_id":     os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
    "grant_type":    "refresh_token"
})

print("Auth response:", auth.status_code, auth.json())
access_token = auth.json()["access_token"]

# Fetch latest 10 activities
resp = requests.get("https://www.strava.com/api/v3/athlete/activities",
    headers={"Authorization": f"Bearer {access_token}"},
    params={"per_page": 10}
)

# Save to JSON
with open("activities.json", "w") as f:
    json.dump(resp.json(), f)