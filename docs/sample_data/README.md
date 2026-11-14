# Sample files for testing the import

Both files are **simulated** and made up for testing. They are not real astronaut or NASA data.

- `simulated_crew_14_days.csv`: 154 readings (11 indicators over 14 days, ending 14 Nov 2026). Heart rate rises and sleep and mood fall in the last five days, and one radiation day is high (2.45 mSv), so the trend, forecast and model flags have something to show.
- `test_with_errors_and_alerts.csv`: 7 rows. Four are valid and trigger alerts (radiation 6.2 critical, glucose 260 critical, mood 3 critical). Three are bad on purpose, and the import should skip them with a reason for each.

How to use: sign in, open Add reading, choose the file under "Import readings from a file".
