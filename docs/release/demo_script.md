# Demo script (3 minutes)

Start: `ASTRONAUT_HEALTH_MONITOR_DEMO_MODE=true python -m uvicorn astronaut_health_monitor.api.application:create_application --factory --port 8000`, open http://127.0.0.1:8000. Fresh database.

| Time | Say | Do |
|---|---|---|
| 0:00 | "Astronauts on a Mars trip cannot wait 20 minutes for ground control. This app lets them judge their own health on board." | Show the sign-in screen. Sign in as `control.demo`, click **Add sample data**. |
| 0:25 | "One screen answers: am I okay, and what do I do now?" | **Mission overview**: ring, banner, "What to do now". Point at the symbol + word on every card (not colour alone). |
| 0:55 | "Each reading is compared with a safe range and with the astronaut's own baseline." | Open **Detail** on Sleep: range, why, what to do. |
| 1:15 | "Body map links readings to body systems and to spaceflight effects." | **Body intelligence**: click Chest, then the Cardiovascular system. |
| 1:35 | "Trends show slow changes that a single reading hides." | **Health trends**: switch 7D / 30D, show Pattern to review. |
| 1:55 | "A daily check-in covers vitals, mood, stress, activity and a private note, saved in one go and encrypted." | **Daily assessment**: fill 3 values, Save, watch the overview update. |
| 2:15 | "Rules decide the status. Machine-learning models trained on this astronaut's own history flag unusual days and forecast risk three days ahead." | **Health intelligence**: show **Model flags** (unusual days, 3-day forecast), then ask "how is my sleep". |
| 2:20 | "The tool knows where you are: station, transit, Moon or Mars." | On **Mission overview** switch the environment to Mars base, then open **Spaceflight hazards**. |
| 2:30 | "It works with no link to Earth. Readings queue locally and sync without duplicates." | Open `docs/resilience.md` table or run `pytest tests/integration/test_resilience.py -q`. |
| 2:45 | "Roles, encrypted data and a tamper-evident audit log protect crew privacy." | **Audit log** shows "The log is intact". |
| 2:55 | "Open source, 311 tests, built solo." | Show GitHub repo. |
