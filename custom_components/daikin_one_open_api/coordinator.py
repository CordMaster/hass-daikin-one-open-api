"""DataUpdateCoordinator for daikin_one_open_api."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    DaikinOneOpenApiClientAuthenticationError,
    DaikinOneOpenApiClientError,
    DaikinOneOpenApiClientRateLimitError,
)
from .api_types import (
    DaikinOneOpenApiThermostatStateResponse,
)
from .const import DOMAIN

if TYPE_CHECKING:
    import logging

    from homeassistant.core import HomeAssistant

    from .api_types import (
        FanCirculateSchedule,
        FanCirculateSpeed,
        ThermostatMode,
    )
    from .data import DaikinOneOpenApiConfigEntry

# Per https://www.daikinone.com/openapi/documentation/index.html
UPDATE_INTERVAL_MINUTES = 3


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class DaikinOneOpenApiDataUpdateCoordinator(
    DataUpdateCoordinator[DaikinOneOpenApiThermostatStateResponse]
):
    """Class to manage fetching data from the API; only manages a single device."""

    config_entry: DaikinOneOpenApiConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        config_entry: DaikinOneOpenApiConfigEntry,
        device_id: str,
    ) -> None:
        """Construct a DaikinOneOpenApiDataUpdateCoordinator."""
        super().__init__(
            hass,
            logger,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
            config_entry=config_entry,
        )

        self._device_id = device_id

    async def set_device_mode_and_setpoints(
        self,
        *,
        mode: ThermostatMode | None = None,
        heat_setpoint: float | None = None,
        cool_setpoint: float | None = None,
    ) -> None:
        """Set device mode and setpoints."""
        mode = self.data.mode if mode is None else mode
        heat_setpoint = (
            self.data.heat_setpoint if heat_setpoint is None else heat_setpoint
        )
        cool_setpoint = (
            self.data.cool_setpoint if cool_setpoint is None else cool_setpoint
        )

        try:
            await self.config_entry.runtime_data.client.set_device_mode_and_setpoints(
                self._device_id,
                mode,
                heat_setpoint,
                cool_setpoint,
            )
        except DaikinOneOpenApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except DaikinOneOpenApiClientError:
            return

        self.async_set_updated_data(
            self.data.model_copy(
                update={
                    "mode": mode,
                    "heat_setpoint": heat_setpoint,
                    "cool_setpoint": cool_setpoint,
                }
            )
        )

    async def set_device_schedule(
        self,
        *,
        schedule_enabled: bool | None = None,
    ) -> None:
        """Set device schedule state."""
        schedule_enabled = (
            self.data.schedule_enabled if schedule_enabled is None else schedule_enabled
        )

        try:
            await self.config_entry.runtime_data.client.set_device_schedule(
                self._device_id,
                schedule_enabled,
            )
        except DaikinOneOpenApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except DaikinOneOpenApiClientError:
            return

        self.async_set_updated_data(
            self.data.model_copy(
                update={
                    "schedule_enabled": schedule_enabled,
                }
            )
        )

    async def set_device_fan_mode(
        self,
        *,
        fan_circulate: FanCirculateSchedule | None = None,
        fan_circulate_speed: FanCirculateSpeed | None = None,
    ) -> None:
        """Set device fan mode."""
        fan_circulate = (
            self.data.fan_circulate if fan_circulate is None else fan_circulate
        )
        fan_circulate_speed = (
            self.data.fan_circulate_speed
            if fan_circulate_speed is None
            else fan_circulate_speed
        )

        try:
            await self.config_entry.runtime_data.client.set_device_fan_mode(
                self._device_id,
                fan_circulate,
                fan_circulate_speed,
            )
        except DaikinOneOpenApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except DaikinOneOpenApiClientError:
            return

        self.async_set_updated_data(
            self.data.model_copy(
                update={
                    "fan_circulate": fan_circulate,
                    "fan_circulate_speed": fan_circulate_speed,
                }
            )
        )

    async def _async_update_data(self) -> Any:
        """Update data via library."""
        try:
            return await self.config_entry.runtime_data.client.get_device_state(
                self._device_id
            )
        except DaikinOneOpenApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except DaikinOneOpenApiClientRateLimitError as exception:
            raise UpdateFailed(
                exception,
                retry_after=exception.retry_after,
            ) from exception
        except DaikinOneOpenApiClientError as exception:
            raise UpdateFailed(exception) from exception
