---
type: note
tags: [homelab, homeassistant, sparkyfitness, project]
modified: 2026-06-21
---
# 🔹 SparkyFitness Home Assistant Integration

Custom Home Assistant integration (HACS-compatible, UI config flow) that pulls
SparkyFitness daily stats into Home Assistant as read-only sensors.

## Status
- **v1.2.0** — read-only nutrition/activity + sleep + body composition sensors, UI config flow, EN/DE translations. Code lives in this folder.

## What it does
Polls two endpoints and exposes sensors under one device.

**Nutrition/activity** — `GET /api/dashboard/stats` (API-key auth, same endpoint as the gethomepage widget):

| Sensor | Unit | Field |
|--------|------|-------|
| Calories Eaten | kcal | `eaten` |
| Calories Burned | kcal | `burned` |
| Calories Remaining | kcal | `remaining` |
| Steps | steps | `steps` |

**Sleep** — `GET /api/sleep/details` (latest entry, last 3 days): Sleep Duration, Time Asleep, Sleep Score, Deep/Light/REM/Awake, Bedtime, Wake Time, Resting Heart Rate. Best-effort: if the API key can't read sleep, those sensors go unavailable without affecting the rest.

**Body composition** — Weight + Body Fat % from `/api/measurements/check-in-measurements-range` (latest within 30 days). Muscle mass, fat mass, bone mass (+ any other custom measurements) discovered dynamically from `/api/measurements/custom-categories` + `/api/measurements/custom-entries` — one sensor per category, using its own name/unit. Best-effort.

## Setup
1. SparkyFitness → Settings → create an API key (health-data read).
2. HA → Settings → Devices & Services → Add Integration → **SparkyFitness**.
3. Enter base URL (e.g. `http://<lan-ip>:3004`) + API key. Polling interval is configurable (default 5 min).

See `README.md` in this folder for full install/HACS instructions.

## Gotchas
- HA polls server-side → URL must be reachable from the HA host. In Docker, use a LAN IP or shared network hostname, **not** the public Cloudflare URL if an Access policy sits in front.
- Client sends the key as both `Authorization: Bearer` and `X-API-Key` for compatibility.

## Open question
- Confirm whether the API key authorizes `GET /api/sleep/details` (vs. login-session only). Quick check on the host:
  `curl -H "X-API-Key: <KEY>" "http://localhost:3004/api/sleep/details?startDate=2026-06-17&endDate=2026-06-20"`

## Future ideas
- Write path via HA services (`POST /api/health-data`) to push weight/water/steps from other HA integrations.
- Weight / body-fat sensors from `/api/measurements/check-in` (needs JWT auth, not API key).
- More sleep metrics available in the API if wanted: SpO2 (avg/low/high), respiration, overnight HRV, sleep stress, body battery change, awake count.

## Related
- [[Projects/HomeLab/HomeLab Project]]
- SparkyFitness instance: `sparky.familyschneider.cloud` (self-hosted, Docker + Cloudflare Tunnel)
