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

## Reading a report from a photo
Add reading has a **Read a report from a photo** panel. Choose or take a photo of a printed report or device screen. The text is read in the browser with Tesseract.js (files in `web/ocr/`, Apache 2.0 licence), so the photo is not uploaded and no outside service is used. The first use downloads about 10 MB from the app's own server.
- The app looks for heart rate, blood pressure, glucose (mg/dL or mmol/L), temperature (C or F), sleep hours and radiation dose in mSv. Numbers outside believable ranges are ignored.
- **Nothing is saved automatically.** The found values are listed with checkboxes and editable numbers. The person confirms them, and they are saved with the source `camera_analysis`.
- Accuracy depends on the photo. Printed text in good light works best; handwriting and seven-segment device displays are often misread. This is a convenience, not a medical measurement.
- `docs/sample_data/simulated_report.png` is a made-up report for testing.

## Alternatives when there is no camera or dosimeter
- **Tap counter (pulse).** The person taps a button with each heartbeat for 15 to 20 seconds. The app needs at least 8 taps over 6 seconds, rejects uneven tapping and implausible rates, and fills in the heart rate for the person to save. It is saved as a manual entry noted "Pulse counted by tapping".
- **Radiation estimate.** A person with no dosimeter reading can save an *estimated* daily dose for the chosen environment: about 1.84 mSv/day in transit and 0.64 mSv/day on the Mars surface (Curiosity RAD, reported by Space.com), about 0.5 mSv/day on the Moon or a rover (the NASA technical brief's surface figure, before shielding), and about 0.5 mSv/day on a station (an approximate figure that does not come from the NASA brief). It is saved with the note "Estimated from mission environment, not measured" and shown as "Estimated, not measured". It is a rough orientation figure, not a measurement.
- **Running career total.** The dose for each day (the highest value that day) is added up and compared with NASA's 600 mSv career limit, with a progress bar and an estimate of the days left at the chosen environment's rate. Only the latest 1,000 readings are used.
