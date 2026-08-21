"""Custom types for daikin_one_open_api."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import DaikinOneOpenApiClient
    from .api_types import DaikinOneOpenApiDevicesResponseDevice
    from .coordinator import DaikinOneOpenApiDataUpdateCoordinator


type DaikinOneOpenApiConfigEntry = ConfigEntry[DaikinOneOpenApiConfigEntryData]


@dataclass
class DaikinOneOpenApiConfigEntryDeviceData:
    """Data for a single device in the daikin_one_open_api integration."""

    device_metadata: DaikinOneOpenApiDevicesResponseDevice
    coordinator: DaikinOneOpenApiDataUpdateCoordinator


@dataclass
class DaikinOneOpenApiConfigEntryData:
    """Data for the daikin_one_open_api integration."""

    integration: Integration
    client: DaikinOneOpenApiClient
    devices: dict[str, DaikinOneOpenApiConfigEntryDeviceData]
