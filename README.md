# SparkyFitness — Home Assistant Integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for self-hosted
[SparkyFitness](https://github.com/CodeWithCJ/SparkyFitness). It pulls your daily
dashboard stats into Home Assistant as read-only sensors so you can put them on
dashboards or trigger automations.

## Sensors

### Nutrition & activity — `GET /api/dashboard/stats`

| Sensor | Unit | Source field |
|--------|------|--------------|
| Calories Eaten | kcal | `eaten` |
| Calories Burned | kcal | `burned` |
| Calories Remaining | kcal | `remaining` |
| Steps | steps | `steps` |

This is the same endpoint the
[gethomepage widget](https://gethomepage.dev/widgets/services/sparkyfitness/) uses.

### Sleep — `GET /api/sleep/details` (latest entry)

| Sensor | Unit | Source field |
|--------|------|--------------|
| Sleep Duration | h | `duration_in_seconds` |
| Time Asleep | h | `time_asleep_in_seconds` |
| Sleep Score | — | `sleep_score` |
| Deep Sleep | h | `deep_sleep_seconds` |
| Light Sleep | h | `light_sleep_seconds` |
| REM Sleep | h | `rem_sleep_seconds` |
| Awake Time | h | `awake_sleep_seconds` |
| Bedtime | timestamp | `bedtime` |
| Wake Time | timestamp | `wake_time` |
| Resting Heart Rate | bpm | `resting_heart_rate` |

Sleep sensors reflect the most recent sleep entry within the last
3 days (sleep is often logged against the previous day). They're best suited to
data synced in from Google/Apple Health, Garmin, or Polar.

### Body composition

| Sensor | Unit | Source |
|--------|------|--------|
| Weight | kg | check-in `weight` |
| Body Fat | % | check-in `body_fat_percentage` |
| *(dynamic)* Muscle Mass, Fat Mass, Bone Mass, … | per category | custom measurements |

Weight and body fat come from the standard check-in range
(`GET /api/measurements/check-in-measurements-range/{start}/{end}`, most recent
within 30 days). **Muscle mass, fat mass and bone mass are custom measurement
categories** — the integration discovers them automatically from
`/api/measurements/custom-categories` + `/api/measurements/custom-entries` and
creates one sensor per category, using the category's own name and unit. So they
appear exactly as your scale sync labels them, and any other custom measurements
(BMI, visceral fat, etc.) show up too.

> Weight assumes **kg**. Custom-measurement units come straight from each
> category's configured unit. Like sleep, all body sensors are best-effort: if
> the API key can't read these endpoints they show "unavailable" without
> affecting anything else. New custom categories appear after a reload of the
> integration.

> **Sleep auth caveat:** the dashboard-stats endpoint authenticates with an API
> key. The sleep endpoint is normally called with a logged-in session, and it is
> not documented whether an API key also authorizes it. If your key can't read
> sleep, the **sleep sensors simply show "unavailable"** and a one-time warning
> is logged — the nutrition/steps sensors keep working. Verify with:
>
> ```bash
> curl -H "X-API-Key: <KEY>" \
>   "http://<host>:3004/api/sleep/details?startDate=2026-06-17&endDate=2026-06-20"
> ```
>
> A JSON array means it works; `401`/`403` means the key isn't accepted for sleep.

## Requirements

- Home Assistant 2024.4.0 or newer
- A reachable SparkyFitness instance
- A SparkyFitness **API key** (read access to health data)

## Installation (HACS)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Search for **SparkyFitness**, install, and restart Home Assistant.

### Manual installation

Copy `custom_components/sparkyfitness/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

1. Create an API key in SparkyFitness (Settings → API keys). Give it permission to
   read health data.
2. In Home Assistant: **Settings → Devices & Services → Add Integration →
   SparkyFitness**.
3. Enter:
   - **Base URL** — e.g. `http://192.168.1.10:3004` (your SparkyFitness server or
     frontend, reachable from the HA host).
   - **API key** — the key from step 1.

The integration validates the connection before finishing. Done — four sensors
appear under a single **SparkyFitness** device.

### Options

Change the **polling interval** (default 5 minutes) under the integration's
**Configure** button.

## Notes & gotchas

- **URL reachability:** Home Assistant polls server-side. If HA and SparkyFitness
  run in Docker, point the URL at an address HA can actually reach (a LAN IP, or a
  shared Docker network hostname). Don't use a public URL that sits behind an auth
  proxy (e.g. Cloudflare Access) — the auth gate will block the API call.
- **Auth headers:** the client sends the key both as `Authorization: Bearer <key>`
  and `X-API-Key: <key>`, so it works regardless of which your deployment expects.
- **Read-only:** this version only reads. Writing data back to SparkyFitness
  (`POST /api/health-data`) could be added later as HA services.

## License

MIT
