# Health status rules and personal baselines (Phase 2)

> Educational prototype. Not a medical device. Verify every range against primary sources before real use.

## How a reading is judged

1. **Expected-range rule** (same logic for every indicator):
   - below the critical lower limit or above the critical upper limit: **critical**
   - between the normal minimum and maximum (inclusive): **normal**
   - anything else: **caution**
2. **Personal baseline** (the astronaut's previous readings of the same indicator, up to 14, at least 5 needed):
   - A reading is *unusual for this astronaut* when it differs from their average by more than
     `max(2 standard deviations, minimum meaningful change)`.
3. **Trend** (last 5 readings including the current one): a straight line is fitted; if the line's total change
   reaches the minimum meaningful change the trend is *rising* or *falling*.
4. **Final status**: the rule status, except a *normal* reading that is unusual for the astronaut or shows a trend
   becomes **caution**. Only a rule can make a reading **critical**.
5. **Contact the flight surgeon** is true exactly when the final status is critical.

## Ranges used

| Indicator | Normal | Critical when | Meaningful change |
|---|---|---|---|
| Heart rate (resting, bpm) | 50 to 100 | below 40 or above 120 | 10 |
| Systolic pressure (mmHg) | 90 to 129 | below 80 or above 159 | 10 |
| Diastolic pressure (mmHg) | 60 to 79 | below 50 or above 99 | 8 |
| Blood glucose (mg/dL, fasting) | 70 to 99 | below 54 or above 249 | 20 |
| Body temperature (C) | 36.1 to 37.5 | below 35.0 or above 37.9 | 0.5 |
| Sleep (hours in 24 h) | 7 to 9 | below 4 | 1.5 |
| Mood (1 to 10) | 6 to 10 | below 4 | 2 |

Values between the normal and critical limits are *caution*.

## Sources and honesty about them

- **Blood pressure:** American Heart Association categories (https://heart.org/bplevels). Confirmed directly.
  This prototype is more conservative than the AHA for a closed environment (160 or higher is critical).
- **Heart rate:** AHA guidance of 60 to 100 bpm at rest, with trained people as low as 40. The lower normal limit is 50
  because astronaut crews are fit; the personal baseline refines this.
- **Glucose:** American Diabetes Association Standards of Care categories (fasting 70 to 99 normal, 100 to 125
  prediabetes range, below 70 hypoglycemia, below 54 severe). Confirmed through summaries of the ADA standards,
  not the ADA document itself.
- **Temperature:** fever from 38.0 C and hypothermia below 35 C (CDC definitions as summarised by health references).
  Any fever is critical here because infections spread easily in a closed spacecraft.
- **Sleep:** NASA schedules 8.5 hours per night, but crew averaged about 6 hours in flight (Barger et al., Brigham and
  Women's Hospital, https://sciencedaily.com/releases/2014/08/140807215803.htm).
- **Mood:** a self-report scale designed for this prototype, not a diagnostic instrument.

Each rule's `source_notes` and `source_urls` are also published by `GET /health-status-rules`.

## Known limitations

- One set of adult ranges for everyone; no age, sex or medical history adjustment.
- Heart rate assumes a resting measurement, glucose assumes fasting or pre-meal. The app cannot yet check this.
- Blood pressure and heart rate are judged one reading at a time (no multi-indicator reasoning).
- Baselines need five earlier readings of the same indicator.
