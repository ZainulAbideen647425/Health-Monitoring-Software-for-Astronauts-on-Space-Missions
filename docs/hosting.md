# Hosting the server online (so the phone app needs no Wi-Fi or address typing)

The phone app is a shell that opens the dashboard from a server. Host the server once and the app can open it from anywhere.

1. Make a free account at render.com and connect your GitHub account.
2. New > Blueprint, choose this repository. `render.yaml` and the `Dockerfile` do the rest.
3. When the deploy finishes, Render shows an address like `https://astro-health-xxxx.onrender.com`.
4. Put that address in `android/app/src/main/res/values/strings.xml` (`default_server`) and push. The APK is rebuilt and published on the Releases page, and opens the site directly.

Limits of the free plan: the site sleeps after inactivity and takes about a minute to wake, and its database is wiped on every restart or redeploy. It is fine for a demo, not for real data. Demo mode is off, so register an account and import `docs/sample_data/simulated_crew_14_days.csv`.

## Keeping accounts and readings (Postgres)
`render.yaml` also creates a free Postgres database and gives the site its address, plus a generated secret used to encrypt stored data. Accounts and readings then survive restarts and redeploys.
- Render's free Postgres database is deleted after about 30 days unless you upgrade it. For longer, use a free Postgres from another host (for example Neon or Supabase) and put its address in the `ASTRONAUT_HEALTH_MONITOR_DATABASE_URL` setting of the web service.
- Keep the `ASTRONAUT_HEALTH_MONITOR_ENCRYPTION_KEY` value. If it is changed or lost, stored names and readings can no longer be read.
- The free web service still sleeps when unused, but waking it no longer loses data.
