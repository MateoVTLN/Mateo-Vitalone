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
