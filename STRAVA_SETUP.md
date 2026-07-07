# Strava API setup / fixing a broken token

The daily **Fetch Strava Activities** workflow needs three repository secrets
(GitHub → repo → Settings → Secrets and variables → Actions):

| Secret | Where it comes from |
|---|---|
| `STRAVA_CLIENT_ID` | strava.com → Settings → My API Application |
| `STRAVA_CLIENT_SECRET` | same page |
| `STRAVA_REFRESH_TOKEN` | generated once via the OAuth flow below |

If the workflow fails at the *"python fetch_activities.py"* step with a
**token refresh error**, the refresh token has been revoked or invalidated
(this happens if the app was de-authorized in Strava, or re-authorized with
different scopes). Regenerate it:

## Regenerating the refresh token

1. **Authorize the app in the browser.** Replace `YOUR_CLIENT_ID` and open
   this URL (keep `scope=activity:read_all` so private activities are included):

   ```
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
   ```

2. Click **Authorize**. The browser lands on an unreachable
   `http://localhost/?state=&code=SOMETHING&scope=…` page — that's expected.
   Copy the `code=` value from the address bar.

3. **Exchange the code for tokens** (PowerShell, replace the three values):

   ```powershell
   curl.exe -X POST https://www.strava.com/oauth/token `
     -d client_id=YOUR_CLIENT_ID `
     -d client_secret=YOUR_CLIENT_SECRET `
     -d code=CODE_FROM_STEP_2 `
     -d grant_type=authorization_code
   ```

4. The JSON answer contains `"refresh_token": "…"`. Put that value in the
   `STRAVA_REFRESH_TOKEN` repository secret (edit the existing secret).

5. Re-run the workflow: GitHub → **Actions** → *Fetch Strava Activities* →
   **Run workflow** (this runs the *current* code on `main`; re-running an old
   failed run would replay the old commit instead).

The first successful run backfills the **entire** activity history into
`activities.json`; the daily 06:00 UTC runs then keep it fresh.

## Error: "Application Status: Inactive" (HTTP 403)

If the *"python fetch_activities.py"* step prints:

```
Fetching activities page 1 failed (HTTP 403):
{"message":"Forbidden","errors":[{"resource":"Application","field":"Status","code":"Inactive"}]}
```

this is **not** a token problem — the token works, but Strava has marked the
whole API **application** as inactive, so every request is refused. Strava
usually deactivates an app by e-mail notification (check spam), sometimes after
an API-agreement or rate-limit issue.

Fix:

1. Open **https://www.strava.com/settings/api** and look for a status / message
   explaining the deactivation; check your e-mail for a Strava notice.
2. If it can be **reactivated** from that page or by replying to Strava, do so —
   nothing else needs changing, just re-run the workflow.
3. If it is stuck, **create a new API application** (new apps are active
   immediately) and update all three repository secrets: `STRAVA_CLIENT_ID`,
   `STRAVA_CLIENT_SECRET`, and a fresh `STRAVA_REFRESH_TOKEN` (redo the OAuth
   flow above with the new Client ID).
