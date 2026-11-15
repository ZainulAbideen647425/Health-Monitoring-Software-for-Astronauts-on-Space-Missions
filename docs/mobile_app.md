# Using the dashboard as a phone app

The dashboard is an installable web app (a PWA). On a phone it opens full screen from the home screen with its own icon, and the page itself loads offline.

## What it does
- `manifest.webmanifest` gives the app its name, icons and colours.
- `sw.js` (a service worker) keeps the page shell, icons and body map available offline. It never stores health data or any API response, and the test suite checks that.
- The menu drawer, compact header and pulse input already work on phone screens.

## What it needs
Phones only allow installing, service workers and camera access on a **secure page**: `https://...` or `localhost`.
- On the computer running the server, `http://localhost:8000` is enough.
- To use it on a phone, the server must be reachable over HTTPS. Options: deploy it to a host that provides HTTPS, or use a tunnel (for example a Cloudflare or ngrok tunnel) to your laptop. Plain `http://192.168.x.x` over Wi-Fi will show the page, but the phone will not offer to install it and the camera will be blocked.
- Switch on `ASTRONAUT_HEALTH_MONITOR_SECURE_COOKIES=true` when serving over HTTPS.
- Never use demo mode on a public address: its password is public.

## Installing
- Android (Chrome): open the page, then use **Install as app** in Profile & settings, or the browser menu > Install app.
- iPhone (Safari): Share > Add to Home Screen.

## Not included
This is not a native Android or iOS app and is not in an app store. Readings made while offline are not saved on the phone for later upload.
