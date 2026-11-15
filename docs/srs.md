# Software Requirements Specification (SRS)

**Product:** Astronaut Health Monitor
**Version:** 0.1.0 (prototype)
**Context:** 2026 NASA Space Apps Challenge, "Create Health Monitoring Software for Astronauts on Space Missions"

This document states what the software must do. Every requirement below describes behaviour that exists in the code.
The last column names the automated tests that check it (in `tests/`). Design is in [system_design.md](system_design.md).

## 1. Introduction

### 1.1 Purpose
On long missions a message to Earth can take minutes each way, so a crew member may have to judge their own health
without a doctor on the line. The software records health indicators, judges them against documented ranges and the
person's own history, explains what to do, and shows the result on a simple dashboard.

### 1.2 Scope
In scope: recording and importing readings, status rules, personal baselines and trends, machine-learning analytics,
guidance, a web and Android dashboard, offline queueing, sign-in with roles, audit log and encryption at rest.
Out of scope: diagnosis, treatment decisions, real NASA crew data, sensing radiation by the app itself, and any claim of
being a medical device.

### 1.3 Users
| Role | Description | May do |
|---|---|---|
| Astronaut | A crew member | See and add their own readings only |
| Clinician | A flight surgeon or medical officer | See and add readings for every crew member |
| Mission control | An administrator | Everything above, plus manage missions, crew and users, and read the audit log |

The software implements all three roles and tests them. In practice:
- **Self-registration always creates an astronaut account**, and an astronaut sees only their own data. This is what the public web and Android demo offers.
- **Clinician and mission control accounts are not self-service.** Mission control creates users from the API (`POST /users`), the first mission control account is created from the command line, and demo mode creates one account for each role with simulated data.
- The hosted demo therefore shows the astronaut experience. The role rules are checked by `test_permissions.py` and `test_role_access_api.py`.

#### Primary user and optional oversight
The **astronaut is the primary user**. An astronaut gets guidance straight after each reading and needs no one else to use the software. The clinician and mission control roles are an **optional oversight layer** for a real deployment.

#### Intended set-up in a real deployment
| Step | Who | What happens |
|---|---|---|
| 1 | Administrator (mission control) | The first mission control account is created on the server from the command line. There is normally one administrator, or a small number. |
| 2 | Administrator | Signs in, then creates the mission and crew records. |
| 3 | Administrator | Creates the clinician account (`POST /users`). A mission may have one or several clinicians. |
| 4 | Astronaut | Registers or is given an account, linked to their own crew record, and records readings. Guidance appears immediately. |
| 5 | Clinician | Reviews any crew member's readings and status, and adds readings for them. |
| 6 | Administrator | Manages accounts and reads the audit log of who did what. |

#### Why the duties are separate
- **Astronaut privacy:** an astronaut can never see another crew member's data.
- **Medical review:** the clinician has the crew-wide medical view but cannot manage users or read the audit log.
- **Access control:** the administrator manages accounts and audits actions. Every sensitive action is recorded in a tamper-evident audit log that holds no health values, so access is accountable.

#### How to try each role
- **Demo mode (own computer, simulated data only):** sign in as `astronaut.demo`, `clinician.demo` or `control.demo`.
- **Own accounts:** create a mission control account with `python -m astronaut_health_monitor.management create-user --username <name> --role mission_control`, sign in, then create a clinician with `POST /users` on the `/docs` page.

### 1.4 Operating environment
Python 3.12 server (FastAPI) with SQLite or PostgreSQL; the dashboard runs in a modern browser and in an Android
WebView app. The server needs no internet after installation.

### 1.5 Assumptions and constraints
- Readings come from the user, a file, a report photo or a Bluetooth sensor, never from real NASA crew records.
- Clinical ranges come from published sources and are not clinically validated.
- Bluetooth heart rate has not yet been tested with real sensor hardware.
- There is no database migration tool; a schema change means recreating the database.

## 2. Functional requirements

### 2.1 Recording readings
| ID | Requirement | Verified by |
|---|---|---|
| FR-1 | The system shall record a reading for one of eleven indicators: heart rate, systolic and diastolic blood pressure, blood glucose, body temperature, sleep duration, mood, fatigue, stress, physical activity and radiation dose. | `test_api.py`, `test_wellbeing_indicators.py`, `test_radiation_dose.py` |
| FR-2 | The system shall reject impossible values and timestamps more than 5 minutes in the future, with a client error and never a crash. | `test_measurement_service.py`, `test_resilience.py` |
| FR-3 | The system shall store each reading with its unit, time (UTC), source and optional notes. | `test_api.py` |
| FR-4 | The system shall let the user enter a pulse by Bluetooth sensor, tap counter or typing, and mark the source. | `test_report_photo.py`, `test_dashboard.py` |
| FR-5 | The system shall import many readings from a CSV file, reporting how many were saved, duplicated or skipped. | `test_dashboard.py`, `test_offline_synchronization.py` |
| FR-6 | The system shall read values from a photo of a printed or handwritten report and save nothing until the user confirms. | `test_report_photo.py` |
| FR-7 | The system shall let the user save a labelled radiation estimate for the mission environment and show a running total against the 600 mSv career limit. | `test_radiation_dose.py`, `test_report_photo.py` |

### 2.2 Assessment and guidance
| ID | Requirement | Verified by |
|---|---|---|
| FR-8 | The system shall judge each reading as normal, caution or critical using documented ranges and sources. | `test_health_status_rules.py` |
| FR-9 | The system shall compare a reading with the astronaut's own recent readings once at least 5 exist, and flag a drift or trend. | `test_personal_baseline.py`, `test_health_assessment_service.py` |
| FR-10 | The system shall give, for each out-of-range reading, an explanation, likely causes, recommended actions and warning signs. | `test_guidance.py` |
| FR-11 | The system shall give a "contact the flight surgeon" instruction for every critical reading. | `test_guidance.py`, `test_health_assessment_api.py` |
| FR-12 | The system shall give an overall status for an astronaut from the latest reading of each indicator. | `test_health_assessment_api.py` |
| FR-13 | The system shall flag unusual days (Isolation Forest) and forecast risk (linear regression) per astronaut. Rule-based status shall remain the safety decision. | `test_health_analytics.py`, `test_health_analytics_api.py` |
| FR-14 | The system shall describe the spaceflight hazards (radiation, isolation, distance, gravity, closed environment) and relate them to the indicators. | `test_spaceflight_context.py`, `test_spaceflight_context_api.py` |

### 2.3 Dashboard
| ID | Requirement | Verified by |
|---|---|---|
| FR-15 | The system shall show one overall answer, at most three next steps, and a card per reading. Status shall always use a symbol and a word, not colour alone. | `test_dashboard.py` |
| FR-16 | The system shall show an interactive body map with clickable regions, status colouring and a precautions panel. | `test_dashboard.py` |
| FR-17 | The system shall show a history chart with the healthy range shaded. | `test_dashboard.py` |
| FR-18 | The system shall run on phone screens, be installable as an app (PWA) and be available as an Android app. | `test_dashboard.py` |

### 2.4 Offline operation
| ID | Requirement | Verified by |
|---|---|---|
| FR-19 | The system shall store readings taken without a connection in a durable queue and send them later in batches of up to 500. | `test_offline_measurement_queue.py`, `test_offline_synchronization.py` |
| FR-20 | The system shall never create duplicates when a batch is retried (unique client reference). | `test_measurement_idempotency.py`, `test_offline_synchronization.py` |
| FR-21 | The system shall keep valid items when one item in a batch is bad, and report each item's result. | `test_measurement_batch_service.py`, `test_resilience.py` |
| FR-22 | The system shall report a damaged queue file instead of silently discarding it. | `test_resilience.py` |

### 2.5 Accounts and access
| ID | Requirement | Verified by |
|---|---|---|
| FR-23 | The system shall let a person register an astronaut account (switchable off) and sign in and out. | `test_self_registration_api.py`, `test_authentication_api.py` |
| FR-24 | The system shall refuse every protected endpoint to anonymous requests. | `test_authentication_api.py` |
| FR-25 | The system shall enforce the three roles: astronauts see and write only their own data. | `test_permissions.py`, `test_role_access_api.py` |
| FR-26 | The system shall let only mission control create users, manage missions and crew, and read the audit log. | `test_role_access_api.py` |
| FR-27 | The system shall record who did what in a tamper-evident audit log that holds no health values. | `test_audit_service.py`, `test_role_access_api.py` |

## 3. Non-functional requirements

| ID | Category | Requirement | Verified by |
|---|---|---|---|
| NFR-1 | Security | Passwords shall be stored only as hashes; sessions shall store only a token hash. | `test_authentication_service.py`, `test_security.py` |
| NFR-2 | Security | After 5 wrong passwords an account shall lock for 15 minutes, and wrong username and wrong password shall look identical. | `test_authentication_service.py`, `test_authentication_api.py` |
| NFR-3 | Security | Sessions shall end after 30 minutes idle or 8 hours total. | `test_authentication_service.py` |
| NFR-4 | Security | Names, values and notes shall be encrypted in the database; wrong keys and tampering shall be detected. | `test_field_encryption.py`, `test_role_access_api.py` |
| NFR-5 | Security | The server shall send security headers and block cross-site state-changing requests. | `test_authentication_api.py` |
| NFR-6 | Availability | The server shall work with no internet after installation; the dashboard shall use no external fonts, scripts or images. | `test_dashboard.py` |
| NFR-7 | Reliability | Unknown records shall return 404, bad bodies a client error, and no input shall cause a server crash. | `test_resilience.py` |
| NFR-8 | Quality | The code base shall keep at least 80% test coverage (currently about 98%), pass lint and strict type checks in CI. | CI workflow |
| NFR-9 | Usability | The dashboard shall be understandable to non-technical users: plain words, one answer first, help on every measurement. | `test_dashboard.py` |
| NFR-10 | Portability | The same code shall run on SQLite (local) and PostgreSQL (hosted). | `test_hosting_settings.py` |
| NFR-11 | Honesty | Estimated, imported, tapped, Bluetooth and simulated readings shall be labelled as such and never presented as measured by the app. | `test_dashboard.py`, `test_radiation_dose.py` |

## 4. External interfaces

- **User interface:** the single-page dashboard served at `/` (see [system_design.md](system_design.md)).
- **HTTP API:** JSON REST endpoints with interactive documentation at `/docs`.
- **Bluetooth:** standard Heart Rate service (0x180D) through Web Bluetooth in browsers and a native bridge in the Android app.
- **Files:** CSV import; image input for report reading (processed in the browser).
- **Database:** SQLite file or PostgreSQL through SQLAlchemy.

## 5. Out of scope and known limits
See "Limitations" in the [README](../README.md). In short: not a medical device; no real crew data; no radiation
sensing; tap and Bluetooth readings are only as accurate as the person or sensor; no migration tool.

## 6. Traceability
Requirement IDs (FR-n, NFR-n) can be searched in this file; the "Verified by" column names the test module that
checks each one. Run `pytest` to confirm them all.
