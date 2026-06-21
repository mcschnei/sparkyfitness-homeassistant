"""Constants for the SparkyFitness integration."""

from __future__ import annotations

DOMAIN = "sparkyfitness"

# Config keys (CONF_URL and CONF_API_KEY come from homeassistant.const)
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_NAME = "SparkyFitness"
DEFAULT_SCAN_INTERVAL = 5  # minutes
MIN_SCAN_INTERVAL = 1
MAX_SCAN_INTERVAL = 1440

# API
STATS_ENDPOINT = "/api/dashboard/stats"
SLEEP_ENDPOINT = "/api/sleep/details"
# Standard body measurements (weight, body fat %, etc.) over a date range:
# the full path is CHECKIN_RANGE_ENDPOINT/{start}/{end}.
CHECKIN_RANGE_ENDPOINT = "/api/measurements/check-in-measurements-range"
# Custom measurement categories (muscle mass, fat mass, bone mass, ...).
CUSTOM_CATEGORIES_ENDPOINT = "/api/measurements/custom-categories"
CUSTOM_ENTRIES_ENDPOINT = "/api/measurements/custom-entries"
REQUEST_TIMEOUT = 30  # seconds

# How many days back to look for the most recent sleep entry. Sleep is often
# logged against the previous calendar day, so a small window is safest.
SLEEP_LOOKBACK_DAYS = 3
# Weight/body measurements may not be recorded daily — use a wider window.
BODY_LOOKBACK_DAYS = 30
# How many recent custom-measurement entries to pull when finding the latest
# value per category.
CUSTOM_ENTRIES_LIMIT = 100

# Standard check-in measurement fields
CHECKIN_WEIGHT = "weight"
CHECKIN_BODY_FAT = "body_fat_percentage"
CHECKIN_ENTRY_DATE = "entry_date"

# Stat keys returned by /api/dashboard/stats
STAT_EATEN = "eaten"
STAT_BURNED = "burned"
STAT_REMAINING = "remaining"
STAT_STEPS = "steps"

# Sleep entry fields returned by /api/sleep/details
SLEEP_DURATION = "duration_in_seconds"
SLEEP_ASLEEP = "time_asleep_in_seconds"
SLEEP_SCORE = "sleep_score"
SLEEP_DEEP = "deep_sleep_seconds"
SLEEP_LIGHT = "light_sleep_seconds"
SLEEP_REM = "rem_sleep_seconds"
SLEEP_AWAKE = "awake_sleep_seconds"
SLEEP_BEDTIME = "bedtime"
SLEEP_WAKETIME = "wake_time"
SLEEP_RESTING_HR = "resting_heart_rate"
SLEEP_ENTRY_DATE = "entry_date"
