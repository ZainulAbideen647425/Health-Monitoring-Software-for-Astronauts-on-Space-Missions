# Android app

A thin Android shell (WebView) around the hosted Astronaut Health Monitor server. It adds camera access for report
photos, a file chooser and native Bluetooth heart rate sensor support.

- Build: GitHub Actions (`.github/workflows/android.yml`) builds a debug-signed APK on every change in this folder and
  publishes it as the `android-latest` release.
- Server address: set in `app/src/main/res/values/strings.xml` (`default_server`) and can be changed inside the app.
- More: [docs/mobile_app.md](../docs/mobile_app.md).
