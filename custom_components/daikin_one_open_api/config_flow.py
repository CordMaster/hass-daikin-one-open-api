"""Adds config flow for the Daikin One Open API Integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectOptionDict, SelectSelectorMode
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .api import (
    DaikinOneOpenApiClient,
    DaikinOneOpenApiClientAuthenticationError,
    DaikinOneOpenApiClientCommunicationError,
    DaikinOneOpenApiClientError,
)
from .const import (
    DOMAIN,
    ENTRY_DATA_API_KEY,
    ENTRY_DATA_EMAIL,
    ENTRY_DATA_INTEGRATIOR_TOKEN,
    ENTRY_DATA_SELECTED_DEVICES,
    LOGGER,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .api_types import DaikinOneOpenApiDevicesResponse
    from .data import DaikinOneOpenApiConfigEntry


class DaikinOneOpenApiFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the Daikin One Open API Integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Config flow for the Daikin One Open API Integration."""
        super().__init__()

        self._client: DaikinOneOpenApiClient | None = None
        self._discovered_devices: DaikinOneOpenApiDevicesResponse | None = None

    ############
    ### USER ###
    ############

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a new flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                self._client = await self._validate_credentials_and_get_client(
                    user_input[ENTRY_DATA_API_KEY],
                    user_input[ENTRY_DATA_EMAIL],
                    user_input[ENTRY_DATA_INTEGRATIOR_TOKEN],
                )
            except DaikinOneOpenApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except DaikinOneOpenApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except DaikinOneOpenApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    unique_id=slugify(user_input[ENTRY_DATA_EMAIL])
                )
                self._abort_if_unique_id_configured()

                return await self.async_step_select_devices()

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        user_input_safe = user_input if user_input is not None else {}

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ENTRY_DATA_EMAIL,
                        default=user_input_safe.get(ENTRY_DATA_EMAIL, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(
                        ENTRY_DATA_API_KEY,
                        default=user_input_safe.get(ENTRY_DATA_API_KEY, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Required(
                        ENTRY_DATA_INTEGRATIOR_TOKEN,
                        default=user_input_safe.get(
                            ENTRY_DATA_INTEGRATIOR_TOKEN, vol.UNDEFINED
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    ###################
    ### RECONFIGURE ###
    ###################

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration."""
        reconfigure_entry: DaikinOneOpenApiConfigEntry = self._get_reconfigure_entry()
        email = reconfigure_entry.data[ENTRY_DATA_EMAIL]
        _errors = {}
        if user_input is not None:
            self._client = reconfigure_entry.runtime_data.client

            # Skip re-creating client if not needed.
            if (
                email == self._client.email
                and user_input[ENTRY_DATA_API_KEY] == self._client.api_key
                and user_input[ENTRY_DATA_INTEGRATIOR_TOKEN]
                == self._client.integrator_token
            ):
                return await self.async_step_select_devices()

            try:
                self._client = await self._validate_credentials_and_get_client(
                    user_input[ENTRY_DATA_API_KEY],
                    email,
                    user_input[ENTRY_DATA_INTEGRATIOR_TOKEN],
                )
            except DaikinOneOpenApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except DaikinOneOpenApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except DaikinOneOpenApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return await self.async_step_select_devices()

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        user_input_safe = user_input if user_input is not None else {}

        return self.async_show_form(
            step_id="reconfigure",
            description_placeholders={
                "email": email,
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ENTRY_DATA_API_KEY,
                        default=(user_input_safe).get(
                            ENTRY_DATA_API_KEY,
                            reconfigure_entry.data.get(
                                ENTRY_DATA_API_KEY, vol.UNDEFINED
                            ),
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Required(
                        ENTRY_DATA_INTEGRATIOR_TOKEN,
                        default=(user_input_safe).get(
                            ENTRY_DATA_INTEGRATIOR_TOKEN,
                            reconfigure_entry.data.get(
                                ENTRY_DATA_INTEGRATIOR_TOKEN, vol.UNDEFINED
                            ),
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    ######################
    ### REAUHTENTICATE ###
    ######################

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],  # noqa: ARG002
    ) -> config_entries.ConfigFlowResult:
        """Handle reauth."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reauth."""
        old_config_data = self._get_reauth_entry().data
        email = old_config_data[ENTRY_DATA_EMAIL]
        _errors = {}
        if user_input is not None:
            try:
                self._client = await self._validate_credentials_and_get_client(
                    user_input[ENTRY_DATA_API_KEY],
                    email,
                    user_input[ENTRY_DATA_INTEGRATIOR_TOKEN],
                )
            except DaikinOneOpenApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except DaikinOneOpenApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except DaikinOneOpenApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={
                        ENTRY_DATA_API_KEY: self._client.api_key,
                        ENTRY_DATA_INTEGRATIOR_TOKEN: self._client.integrator_token,
                    },
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        user_input_safe = user_input if user_input is not None else {}

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={
                "email": email,
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ENTRY_DATA_API_KEY,
                        default=(user_input_safe).get(
                            ENTRY_DATA_API_KEY,
                            old_config_data.get(ENTRY_DATA_API_KEY, vol.UNDEFINED),
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Required(
                        ENTRY_DATA_INTEGRATIOR_TOKEN,
                        default=(user_input_safe).get(
                            ENTRY_DATA_INTEGRATIOR_TOKEN,
                            old_config_data.get(
                                ENTRY_DATA_INTEGRATIOR_TOKEN, vol.UNDEFINED
                            ),
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    #############
    ### UTILS ###
    #############

    async def async_step_select_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle user device selection."""
        old_config_data = {}

        if self.source == config_entries.SOURCE_RECONFIGURE:
            old_config_data = self._get_reconfigure_entry().as_dict()

        if self._client is None:
            if self.source == config_entries.SOURCE_USER:
                return await self.async_step_user()
            if self.source == config_entries.SOURCE_RECONFIGURE:
                return await self.async_step_reconfigure()
            return self.async_abort(reason="unknown")
        assert self._client is not None  # noqa: S101

        discovered_devices = (
            self._discovered_devices
            if self._discovered_devices is not None
            else await self._client.get_devices()
        )

        devices = {
            device.id: f"{location.location_name}: {device.name} ({device.model})"
            for location in discovered_devices
            for device in location.devices
        }

        if user_input is not None:
            if self.source == config_entries.SOURCE_USER:
                return self.async_create_entry(
                    title=self._client.email,
                    data={
                        ENTRY_DATA_API_KEY: self._client.api_key,
                        ENTRY_DATA_EMAIL: self._client.email,
                        ENTRY_DATA_INTEGRATIOR_TOKEN: self._client.integrator_token,
                        ENTRY_DATA_SELECTED_DEVICES: user_input[
                            ENTRY_DATA_SELECTED_DEVICES
                        ],
                    },
                )
            if self.source == config_entries.SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    title=self._client.email,
                    data_updates={
                        ENTRY_DATA_API_KEY: self._client.api_key,
                        ENTRY_DATA_INTEGRATIOR_TOKEN: self._client.integrator_token,
                        ENTRY_DATA_SELECTED_DEVICES: user_input[
                            ENTRY_DATA_SELECTED_DEVICES
                        ],
                    },
                )

        devices_options: list[SelectOptionDict] = [
            {"value": k, "label": v} for k, v in devices.items()
        ]

        return self.async_show_form(
            step_id="select_devices",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        ENTRY_DATA_SELECTED_DEVICES,
                        default=old_config_data.get(
                            ENTRY_DATA_SELECTED_DEVICES, list(devices.keys())
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=devices_options,
                            mode=SelectSelectorMode.LIST,
                            multiple=True,
                        ),
                    ),
                },
            ),
        )

    async def _validate_credentials_and_get_client(
        self, api_key: str, email: str, integrator_token: str
    ) -> DaikinOneOpenApiClient:
        """Validate credentials."""
        client = DaikinOneOpenApiClient(
            self.hass,
            async_get_clientsession(self.hass),
            api_key,
            email,
            integrator_token,
        )
        await client.reauth()
        return client
