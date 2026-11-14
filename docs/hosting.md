# Hosting the server online (so the phone app needs no Wi-Fi or address typing)

The phone app is a shell that opens the dashboard from a server. Host the server once and the app can open it from anywhere.

1. Make a free account at render.com and connect your GitHub account.
2. New > Blueprint, choose this repository. `render.yaml` and the `Dockerfile` do the rest.
3. When the deploy finishes, Render shows an address like `https://astro-health-xxxx.onrender.com`.
4. Put that address in `android/app/src/main/res/values/strings.xml` (`default_server`) and push. The APK is rebuilt and published on the Releases page, and opens the site directly.

Limits of the free plan: the site sleeps after inactivity and takes about a minute to wake, and its database is wiped on every restart or redeploy. It is fine for a demo, not for real data. Demo mode is off, so register an account and import `docs/sample_data/simulated_crew_14_days.csv`.
