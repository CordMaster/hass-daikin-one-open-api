"""Sensor platform for daikin_one_open_api."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .api_types import ModeEmergencyHeatAvailable
from .entity import DaikinOneOpenApiEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api_types import DaikinOneOpenApiThermostatStateResponse
    from .data import DaikinOneOpenApiConfigEntry, DaikinOneOpenApiConfigEntryDeviceData


@dataclasses.dataclass(frozen=True, kw_only=True)
class DaikinOneOpenApiBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A custom sensor entity description."""

    value_fn: Callable[[DaikinOneOpenApiThermostatStateResponse], bool | None]


ENTITY_DESCRIPTIONS = [
    DaikinOneOpenApiBinarySensorEntityDescription(
        key="emergency_heat_mode_available",
        name="Emergency Heat Mode Available",
        icon="mdi:heating-coil",
        entity_registry_visible_default=False,
        value_fn=lambda data: (
            data.mode_em_heat_available == ModeEmergencyHeatAvailable.AVAILABLE
        ),
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
                DaikinOneOpenApiBinarySensor(
                    device,
                    entity_description,
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ]
        )


class DaikinOneOpenApiBinarySensor(DaikinOneOpenApiEntity, BinarySensorEntity):
    """Binary sensor class."""

    entity_description: DaikinOneOpenApiBinarySensorEntityDescription

    def __init__(
        self,
        device: DaikinOneOpenApiConfigEntryDeviceData,
        entity_description: DaikinOneOpenApiBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(device)
        self.entity_description = dataclasses.replace(
            entity_description,
            key=f"{device.device_metadata.id}_{entity_description.key}",
            name=f"{device.device_metadata.name} {entity_description.name}",
        )

        self._attr_unique_id = self.entity_description.key

    @property
    def is_on(self) -> bool | None:
        """Return the value of the binary sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
