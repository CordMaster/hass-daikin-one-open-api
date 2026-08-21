"""Sensor platform for daikin_one_open_api."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)

from .api_types import FanCirculateSpeed
from .entity import DaikinOneOpenApiEntity

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api_types import DaikinOneOpenApiThermostatStateResponse
    from .coordinator import DaikinOneOpenApiDataUpdateCoordinator
    from .data import DaikinOneOpenApiConfigEntry, DaikinOneOpenApiConfigEntryDeviceData


@dataclasses.dataclass(frozen=True, kw_only=True)
class DaikinOneOpenApiSelectEntityDescription(SelectEntityDescription):
    """A custom select entity description."""

    value_fn: Callable[[DaikinOneOpenApiThermostatStateResponse], str | None]
    change_fn: Callable[[DaikinOneOpenApiDataUpdateCoordinator, str], Awaitable[None]]


FAN_CIRCULATE_SPEED_TO_STR = {
    FanCirculateSpeed.LOW: "Low",
    FanCirculateSpeed.MEDIUM: "Medium",
    FanCirculateSpeed.HIGH: "High",
}
STR_TO_FAN_CIRCULATE_SPEED = {
    "Low": FanCirculateSpeed.LOW,
    "Medium": FanCirculateSpeed.MEDIUM,
    "High": FanCirculateSpeed.HIGH,
}


async def _handle_fan_speed_change(
    coordinator: DaikinOneOpenApiDataUpdateCoordinator,
    desired_state: str,
) -> None:
    """Handle schedule enabled change."""
    await coordinator.set_device_fan_mode(
        fan_circulate_speed=STR_TO_FAN_CIRCULATE_SPEED[desired_state]
    )


ENTITY_DESCRIPTIONS = [
    DaikinOneOpenApiSelectEntityDescription(
        key="manual_fan_speed",
        name="Manual Fan Speed",
        icon="mdi:fan",
        options=["Low", "Medium", "High"],
        value_fn=lambda data: FAN_CIRCULATE_SPEED_TO_STR[data.fan_circulate_speed],
        change_fn=_handle_fan_speed_change,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: DaikinOneOpenApiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    for device in entry.runtime_data.devices.values():
        async_add_entities(
            [
                DaikinOneOpenApiSelect(
                    device,
                    entity_description,
                )
                for entity_description in ENTITY_DESCRIPTIONS
            ]
        )


class DaikinOneOpenApiSelect(DaikinOneOpenApiEntity, SelectEntity):
    """Select class."""

    entity_description: DaikinOneOpenApiSelectEntityDescription

    def __init__(
        self,
        device: DaikinOneOpenApiConfigEntryDeviceData,
        entity_description: DaikinOneOpenApiSelectEntityDescription,
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
    def current_option(self) -> str | None:
        """Return the value of the select."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Set the value of the select."""
        await self.entity_description.change_fn(self.coordinator, option)
