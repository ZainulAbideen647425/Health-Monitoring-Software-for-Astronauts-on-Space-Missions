# Radiation, camera pulse check and file import

## Radiation dose (dosimeter reading)
A laptop cannot sense radiation, so the app does not pretend to. The **radiation dose** indicator holds the daily dose, in mSv for the last 24 hours, that the crew member reads from a personal dosimeter and types in.

Thresholds (prototype values built from NASA figures, not medical limits for one day):
- Normal: 0 to 1.3 mSv/day. NASA's technical brief requires galactic cosmic ray dose rates below 1.3 mSv/day in free space and 0.9 mSv/day on planetary surfaces.
- Caution: above 1.3 up to 5 mSv/day. Curiosity's RAD instrument measured about 1.84 mSv/day on the way to Mars, so a Mars transit shows as caution.
- Critical: above 5 mSv/day, which suggests a solar particle event (NASA's limit for one event is 250 mSv).
- Career limit: less than 600 mSv. The app does not yet keep a running career total; guidance tells the crew to ask the flight surgeon.

Sources: NASA radiation protection technical brief (OCHMO) and the Curiosity RAD results reported by Space.com. The simulated sample values (about 0.5 mSv/day on a station, 1.8 in transit) are illustrative.

## Camera pulse check
Add reading has a 15-second pulse check. The crew member covers the camera lens with a fingertip, and the page measures the red-channel brightness change with each heartbeat (photoplethysmography), finds the beats and estimates beats per minute. It runs entirely in the browser, and no video is stored or sent.
- It refuses to give a number if the lens does not look covered, the signal is too weak, or the beats are too uneven.
- A saved camera result is stored with the source `camera_analysis`.
- It is a rough estimate, not a medical device. The algorithm is tested on synthetic pulse signals; it has not been validated against a clinical pulse sensor.
- The camera needs `localhost` or a secure (HTTPS) page, and the person must allow camera access.

## File import and real NASA data
Add reading can import a CSV file with the columns `indicator, value, measured_at` (a template can be downloaded, and a Mission reports export also works). Readings already saved are skipped, bad rows are listed and skipped, and imported readings are marked "Imported from file".

**No real NASA dataset is bundled.** All sample data is simulated and labelled. To use real public data, such as data from the NASA Open Science Data Repository, convert it to this CSV format and import it. The indicator names are listed at `/health-indicators`.
