"""
Custom integration to integrate Daikin One Open API with Home Assistant.

For more details about this integration, please refer to
https://github.com/CordMaster/unofficial-hass-daikin-one-open-api
"""

from __future__ import annotations

from asyncio import TaskGroup
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .api import DaikinOneOpenApiClient, DaikinOneOpenApiClientAuthenticationError
from .const import (
    ENTRY_DATA_API_KEY,
    ENTRY_DATA_EMAIL,
    ENTRY_DATA_INTEGRATIOR_TOKEN,
    ENTRY_DATA_SELECTED_DEVICES,
    LOGGER,
)
from .coordinator import DaikinOneOpenApiDataUpdateCoordinator
from .data import DaikinOneOpenApiConfigEntryData, DaikinOneOpenApiConfigEntryDeviceData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import DaikinOneOpenApiConfigEntry

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: DaikinOneOpenApiConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    client = DaikinOneOpenApiClient(
        hass,
        async_get_clientsession(hass),
        entry.data[ENTRY_DATA_API_KEY],
        entry.data[ENTRY_DATA_EMAIL],
        entry.data[ENTRY_DATA_INTEGRATIOR_TOKEN],
    )

    # Make sure selections are correct.
    try:
        got_devices_map = {
            device.id: device
            for location in await client.get_devices()
            for device in location.devices
        }
    except DaikinOneOpenApiClientAuthenticationError as exception:
        raise ConfigEntryAuthFailed(exception) from exception

    device_selections_to_remove = set(
        entry.data[ENTRY_DATA_SELECTED_DEVICES]
    ).difference(set(got_devices_map.keys()))
    if len(device_selections_to_remove) > 0:
        LOGGER.warning(
            f"Removing devices as they no longer exist: {device_selections_to_remove}."
        )

        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                ENTRY_DATA_SELECTED_DEVICES: list(
                    set(entry.data[ENTRY_DATA_SELECTED_DEVICES]).difference(
                        device_selections_to_remove
                    )
                ),
            },
        )

    devices = {
        device_id: DaikinOneOpenApiConfigEntryDeviceData(
            device_metadata=got_devices_map[device_id],
            coordinator=DaikinOneOpenApiDataUpdateCoordinator(
                hass=hass,
                logger=LOGGER,
                config_entry=entry,
                device_id=device_id,
            ),
        )
        for device_id in entry.data[ENTRY_DATA_SELECTED_DEVICES]
    }

    entry.runtime_data = DaikinOneOpenApiConfigEntryData(
        integration=async_get_loaded_integration(hass, entry.domain),
        client=client,
        devices=devices,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    async with TaskGroup() as first_refresh_group:
        for device in devices.values():
            first_refresh_group.create_task(
                device.coordinator.async_config_entry_first_refresh()
            )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: DaikinOneOpenApiConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
