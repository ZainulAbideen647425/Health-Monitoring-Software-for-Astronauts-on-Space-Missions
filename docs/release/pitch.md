# Pitch text

## One line
An offline-first health monitor that lets astronauts track vitals, sleep and mood, understand what the numbers mean, and know exactly what to do next, without waiting for ground control.

## 30 seconds
On a Mars mission, a message to Earth takes up to 22 minutes each way. Astronaut Health Monitor gives the crew a private dashboard: log heart rate, blood pressure, glucose, temperature, sleep, mood, stress, fatigue and exercise. Every reading is judged against a safe range and the astronaut's own baseline, then explained in plain words with next steps and a clear "contact the flight surgeon" signal. It keeps working offline and syncs later without duplicates.

## Why it is different
1. **Autonomy**: guidance on board, no live link needed.
2. **Explainable AI**: transparent rules with cited sources decide the safety status; scikit-learn models (Isolation Forest, linear regression) trained on each astronaut's own history add unusual-day flags and a 3-day risk forecast, always labelled as flags, not diagnoses.
3. **Safe by design**: encrypted data, roles, tamper-evident audit log, honest limits.
4. **Accessible**: symbol and word beside every colour, keyboard and screen-reader friendly.
5. **Tested**: 274 automated tests, 98% coverage, type-checked, CI on every push.

## Honest limits
Educational prototype using reference ranges. Not a medical device. The models are small and trained on one person's own history, so they need about 7 to 10 days of readings before they speak. They have not been clinically validated.
