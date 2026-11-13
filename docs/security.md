# Security (Phase 4)

> Educational prototype. These measures show good practice for a hackathon project; they are not a certified
> security design for real spaceflight or medical use.

## Sign-in and sessions

- Passwords are hashed with **scrypt** (a deliberately slow hash) and a random salt; the password itself is never stored.
  Minimum 12 characters.
- A wrong username and a wrong password give the **same message** and take a similar time, so an attacker cannot learn
  which usernames exist.
- **Lockout:** 5 wrong passwords lock the account for 15 minutes.
- A successful sign-in creates a random session token. The server stores only its **SHA-256 hash**, so a leaked
  database cannot be used to take over sessions.
- Sessions end after **30 minutes without activity** or **8 hours in total**, and **sign-out ends the session on the
  server**, so a copied cookie stops working.
- The cookie is `HttpOnly` (page scripts cannot read it), `SameSite=Strict`, and `Secure` when
  `ASTRONAUT_HEALTH_MONITOR_SECURE_COOKIES=true` (use this behind HTTPS).

## Roles (enforced on the server for every request)

| Capability | Astronaut | Clinician | Mission control |
|---|---|---|---|
| Read own health data | yes | yes | yes |
| Write own health data | yes | yes | yes |
| Read / write any crew member's health data | no | yes | yes |
| Create missions, crew members and users | no | no | yes |
| Read the audit log | no | no | yes |

Hiding a button in the page is never the protection; a request without the right role is refused with 403, and an
astronaut asking for someone else's data is refused and **recorded in the audit log**. Every endpoint except the page,
its image and `/health` requires sign-in (401 otherwise); a test checks this for each endpoint.

## Registration

The sign-in screen has a **Register** link. Anyone can create their own account, but only an **astronaut** account:
it is linked to a brand-new crew record and can see and record only its own data. The role cannot be chosen in the
request, so clinician and mission-control accounts can never be created this way (mission control creates them with
`POST /users` or the `create-user` command). Passwords must be at least 12 characters. A registration is written to the
audit log (`user.self_registered`). For a real mission, switch it off with
`ASTRONAUT_HEALTH_MONITOR_ALLOW_SELF_REGISTRATION=false`; accounts are then created by mission control only.

## Audit log

Sign-ins (successful, failed, locked), sign-outs, refused actions, creation of users, crew and missions, every recorded
measurement, and every time a clinician or mission control views another person's health data. Entries never contain
passwords, tokens or measured values.
Entries form a **hash chain**: each stores a hash covering its own content and the previous entry. Editing or deleting an
old entry breaks the chain, and `GET /audit-log` (mission control) reports whether the chain is intact.

## Encryption at rest

- Astronaut names, **measured values** and **notes** are encrypted before they are written to the database (Fernet:
  AES with an integrity check). A wrong key or altered data is reported as an error, never accepted silently.
- The **offline queue file** can be encrypted with the same key.
- The key comes from `ASTRONAUT_HEALTH_MONITOR_ENCRYPTION_KEY`, or a key file (`.data_encryption_key`, readable only by
  the owner, excluded from Git). **Losing the key means losing the data.**
- Not encrypted: measurement times, indicator names, mission data, usernames and roles (needed to search and sort).

## Other protections

- Cross-site request blocking (requests from another website's origin are refused) plus `SameSite=Strict`.
- Security headers: `nosniff`, no framing, no referrer, a content security policy on the page, and `no-store` on data
  responses so they are not cached by the browser.
- Dashboard text from the server is inserted as text, not HTML.

## Demo mode

`ASTRONAUT_HEALTH_MONITOR_DEMO_MODE=true` creates simulated data and accounts `astronaut.demo`, `clinician.demo` and
`control.demo` with the **public** password `demo-passphrase-2026`. Use it only for demonstrations, never with real data.

## What this does NOT protect against (honest limits)

- Someone with access to both the database file **and** the key (or the running server) can read everything.
- Someone with full database access can rewrite the entire audit chain; keep copies of the log elsewhere for real use.
- Traffic is not encrypted unless the app is served over HTTPS (use a proper HTTPS proxy and `SECURE_COOKIES=true`).
- No two-factor sign-in, no password reset, no key rotation, no per-session device list.
- Lockout counters are per account and could be used to lock a victim out (a trade-off of lockout).
- The prototype is not certified for any medical or spaceflight use.
