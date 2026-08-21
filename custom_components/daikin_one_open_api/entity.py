"""DaikinOneOpenApiEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import DaikinOneOpenApiDataUpdateCoordinator

if TYPE_CHECKING:
    from .data import DaikinOneOpenApiConfigEntryDeviceData


class DaikinOneOpenApiEntity(CoordinatorEntity[DaikinOneOpenApiDataUpdateCoordinator]):
    """DaikinOneOpenApiEntityntEntity class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, device: DaikinOneOpenApiConfigEntryDeviceData) -> None:
        """Initialize."""
        super().__init__(device.coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, device.device_metadata.id),
            },
            name=device.device_metadata.name,
            model=device.device_metadata.model,
            sw_version=device.device_metadata.firmware_version,
        )
