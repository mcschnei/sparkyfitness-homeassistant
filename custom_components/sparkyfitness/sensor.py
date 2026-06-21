"""Sensor platform for SparkyFitness."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SparkyFitnessConfigEntry
from .const import (
    CHECKIN_BODY_FAT,
    CHECKIN_WEIGHT,
    DEFAULT_NAME,
    DOMAIN,
    SLEEP_ASLEEP,
    SLEEP_AWAKE,
    SLEEP_BEDTIME,
    SLEEP_DEEP,
    SLEEP_DURATION,
    SLEEP_LIGHT,
    SLEEP_REM,
    SLEEP_RESTING_HR,
    SLEEP_SCORE,
    SLEEP_WAKETIME,
    STAT_BURNED,
    STAT_EATEN,
    STAT_REMAINING,
    STAT_STEPS,
)
from .coordinator import SparkyFitnessCoordinator

SECTION_STATS = "stats"
SECTION_SLEEP = "sleep"
SECTION_BODY = "body"
SECTION_CUSTOM = "custom"


def _to_number(value: Any) -> float | int | None:
    """Coerce an API value to a number, or None if missing/invalid."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else round(number, 2)


def _seconds_to_hours(value: Any) -> float | None:
    """Convert a seconds value to hours (2 decimals)."""
    number = _to_number(value)
    if number is None:
        return None
    return round(number / 3600, 2)


def _to_timestamp(value: Any) -> datetime | None:
    """Parse an ISO datetime string into a timezone-aware datetime."""
    if not value:
        return None
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        # Assume UTC if the API returned a naive timestamp.
        parsed = parsed.replace(tzinfo=dt_util.UTC)
    return parsed


@dataclass(frozen=True, kw_only=True)
class SparkyFitnessSensorDescription(SensorEntityDescription):
    """Describes a SparkyFitness sensor."""

    section: str
    value_fn: Callable[[dict[str, Any]], Any]


def _stat(key: str) -> Callable[[dict[str, Any]], Any]:
    """Build a value function reading a numeric field from the stats section."""
    return lambda data: _to_number((data.get(SECTION_STATS) or {}).get(key))


def _sleep_hours(key: str) -> Callable[[dict[str, Any]], Any]:
    """Build a value function converting a sleep seconds field to hours."""
    return lambda data: _seconds_to_hours((data.get(SECTION_SLEEP) or {}).get(key))


def _sleep_number(key: str) -> Callable[[dict[str, Any]], Any]:
    """Build a value function reading a numeric sleep field."""
    return lambda data: _to_number((data.get(SECTION_SLEEP) or {}).get(key))


def _sleep_ts(key: str) -> Callable[[dict[str, Any]], Any]:
    """Build a value function reading a sleep timestamp field."""
    return lambda data: _to_timestamp((data.get(SECTION_SLEEP) or {}).get(key))


def _body(key: str) -> Callable[[dict[str, Any]], Any]:
    """Build a value function reading a numeric field from the body section."""
    return lambda data: _to_number((data.get(SECTION_BODY) or {}).get(key))


SENSORS: tuple[SparkyFitnessSensorDescription, ...] = (
    # --- Nutrition / activity (from /api/dashboard/stats) ---
    SparkyFitnessSensorDescription(
        key=STAT_EATEN,
        translation_key=STAT_EATEN,
        name="Calories Eaten",
        native_unit_of_measurement="kcal",
        icon="mdi:food-apple",
        state_class=SensorStateClass.MEASUREMENT,
        section=SECTION_STATS,
        value_fn=_stat(STAT_EATEN),
    ),
    SparkyFitnessSensorDescription(
        key=STAT_BURNED,
        translation_key=STAT_BURNED,
        name="Calories Burned",
        native_unit_of_measurement="kcal",
        icon="mdi:fire",
        state_class=SensorStateClass.MEASUREMENT,
        section=SECTION_STATS,
        value_fn=_stat(STAT_BURNED),
    ),
    SparkyFitnessSensorDescription(
        key=STAT_REMAINING,
        translation_key=STAT_REMAINING,
        name="Calories Remaining",
        native_unit_of_measurement="kcal",
        icon="mdi:scale-balance",
        state_class=SensorStateClass.MEASUREMENT,
        section=SECTION_STATS,
        value_fn=_stat(STAT_REMAINING),
    ),
    SparkyFitnessSensorDescription(
        key=STAT_STEPS,
        translation_key=STAT_STEPS,
        name="Steps",
        native_unit_of_measurement="steps",
        icon="mdi:walk",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section=SECTION_STATS,
        value_fn=_stat(STAT_STEPS),
    ),
    # --- Sleep (from /api/sleep/details, latest entry) ---
    SparkyFitnessSensorDescription(
        key="sleep_duration",
        translation_key="sleep_duration",
        name="Sleep Duration",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:bed-clock",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        section=SECTION_SLEEP,
        value_fn=_sleep_hours(SLEEP_DURATION),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_asleep",
        translation_key="sleep_asleep",
        name="Time Asleep",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:sleep",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        section=SECTION_SLEEP,
        value_fn=_sleep_hours(SLEEP_ASLEEP),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_score",
        translation_key="sleep_score",
        name="Sleep Score",
        icon="mdi:star-circle",
        state_class=SensorStateClass.MEASUREMENT,
        section=SECTION_SLEEP,
        value_fn=_sleep_number(SLEEP_SCORE),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_deep",
        translation_key="sleep_deep",
        name="Deep Sleep",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:sleep",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        section=SECTION_SLEEP,
        value_fn=_sleep_hours(SLEEP_DEEP),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_light",
        translation_key="sleep_light",
        name="Light Sleep",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:sleep",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        section=SECTION_SLEEP,
        value_fn=_sleep_hours(SLEEP_LIGHT),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_rem",
        translation_key="sleep_rem",
        name="REM Sleep",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:sleep",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        section=SECTION_SLEEP,
        value_fn=_sleep_hours(SLEEP_REM),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_awake",
        translation_key="sleep_awake",
        name="Awake Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:sleep-off",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        section=SECTION_SLEEP,
        value_fn=_sleep_hours(SLEEP_AWAKE),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_bedtime",
        translation_key="sleep_bedtime",
        name="Bedtime",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:bed",
        section=SECTION_SLEEP,
        value_fn=_sleep_ts(SLEEP_BEDTIME),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_waketime",
        translation_key="sleep_waketime",
        name="Wake Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:weather-sunset-up",
        section=SECTION_SLEEP,
        value_fn=_sleep_ts(SLEEP_WAKETIME),
    ),
    SparkyFitnessSensorDescription(
        key="sleep_resting_hr",
        translation_key="sleep_resting_hr",
        name="Resting Heart Rate",
        native_unit_of_measurement="bpm",
        icon="mdi:heart-pulse",
        state_class=SensorStateClass.MEASUREMENT,
        section=SECTION_SLEEP,
        value_fn=_sleep_number(SLEEP_RESTING_HR),
    ),
    # --- Body composition (from /api/measurements/check-in-measurements-range) ---
    SparkyFitnessSensorDescription(
        key="weight",
        translation_key="weight",
        name="Weight",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        icon="mdi:scale-bathroom",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        section=SECTION_BODY,
        value_fn=_body(CHECKIN_WEIGHT),
    ),
    SparkyFitnessSensorDescription(
        key="body_fat",
        translation_key="body_fat",
        name="Body Fat",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        section=SECTION_BODY,
        value_fn=_body(CHECKIN_BODY_FAT),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SparkyFitnessConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SparkyFitness sensors from a config entry."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        SparkyFitnessSensor(coordinator, entry, description)
        for description in SENSORS
    ]

    # Dynamically add one sensor per custom measurement category that was
    # discovered on the first refresh (e.g. muscle mass, fat mass, bone mass).
    custom = (coordinator.data or {}).get(SECTION_CUSTOM) or {}
    for category_id, info in custom.items():
        entities.append(
            SparkyFitnessCustomSensor(coordinator, entry, category_id, info)
        )

    async_add_entities(entities)


class SparkyFitnessSensor(
    CoordinatorEntity[SparkyFitnessCoordinator], SensorEntity
):
    """A single SparkyFitness sensor."""

    entity_description: SparkyFitnessSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SparkyFitnessCoordinator,
        entry: SparkyFitnessConfigEntry,
        description: SparkyFitnessSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="SparkyFitness",
            model="Self-hosted",
            configuration_url=entry.data.get("url"),
        )

    @property
    def native_value(self) -> float | int | datetime | None:
        """Return the current value of the sensor."""
        if not isinstance(self.coordinator.data, dict):
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return True only if the relevant data section is present.

        Optional sensors (sleep, body) become unavailable rather than breaking
        the whole integration when their section could not be fetched.
        """
        if not super().available or not isinstance(self.coordinator.data, dict):
            return False
        section = self.coordinator.data.get(self.entity_description.section)
        return isinstance(section, dict)


class SparkyFitnessCustomSensor(
    CoordinatorEntity[SparkyFitnessCoordinator], SensorEntity
):
    """A sensor for a custom measurement category (muscle/fat/bone mass, ...)."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:human"

    def __init__(
        self,
        coordinator: SparkyFitnessCoordinator,
        entry: SparkyFitnessConfigEntry,
        category_id: str,
        info: dict[str, Any],
    ) -> None:
        """Initialise the custom-measurement sensor."""
        super().__init__(coordinator)
        self._category_id = category_id
        self._attr_unique_id = f"{entry.entry_id}_custom_{category_id}"
        self._attr_name = info.get("name") or f"Custom {category_id[:8]}"
        unit = info.get("unit")
        if unit:
            self._attr_native_unit_of_measurement = str(unit)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="SparkyFitness",
            model="Self-hosted",
            configuration_url=entry.data.get("url"),
        )

    def _entry(self) -> dict[str, Any] | None:
        """Return this category's current data, if present."""
        if not isinstance(self.coordinator.data, dict):
            return None
        return (self.coordinator.data.get(SECTION_CUSTOM) or {}).get(
            self._category_id
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the latest value for this custom category."""
        info = self._entry()
        if info is None:
            return None
        return _to_number(info.get("value"))

    @property
    def available(self) -> bool:
        """Return True if this category still has data."""
        return super().available and self._entry() is not None
