"""Sensor platform for daikin_one_open_api."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from .entity import DaikinOneOpenApiEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api_types import DaikinOneOpenApiThermostatStateResponse
    from .data import DaikinOneOpenApiConfigEntry, DaikinOneOpenApiConfigEntryDeviceData


@dataclasses.dataclass(frozen=True, kw_only=True)
class DaikinOneOpenApiSensorEntityDescription(SensorEntityDescription):
    """A custom sensor entity description."""

    value_fn: Callable[[DaikinOneOpenApiThermostatStateResponse], float | str | None]


ENTITY_DESCRIPTIONS = [
    DaikinOneOpenApiSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        icon="mdi:thermometer",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.temp_outdoor,
    ),
    DaikinOneOpenApiSensorEntityDescription(
        key="outdoor_humidity",
        name="Outdoor Humidity",
        icon="mdi:water-percent",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement="%",
        value_fn=lambda data: data.hum_outdoor,
    ),
    DaikinOneOpenApiSensorEntityDescription(
        key="setpoint_delta",
        name="Setpoint Delta",
        icon="mdi:delta",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE_DELTA,
        entity_registry_visible_default=False,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.setpoint_delta,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: DaikinOneOpenApiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    for device in entry.runtime_data.devices.values():
        async_add_entities(
            [
                DaikinOneOpenApiSensor(
                    device,
                    entity_description,
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ]
        )


class DaikinOneOpenApiSensor(DaikinOneOpenApiEntity, SensorEntity):
    """Sensor class."""

    entity_description: DaikinOneOpenApiSensorEntityDescription

    def __init__(
        self,
        device: DaikinOneOpenApiConfigEntryDeviceData,
        entity_description: DaikinOneOpenApiSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(device)
        self.entity_description = dataclasses.replace(
            entity_description,
            key=f"{device.device_metadata.id}_{entity_description.key}",
            name=f"{device.device_metadata.name} {entity_description.name}",
        )

        self._attr_unique_id = self.entity_description.key

    @property
    def native_value(self) -> float | str | None:
        """Return the native value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
