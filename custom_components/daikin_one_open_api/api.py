"""API Client for communicating with the Daikin One Open API."""

from __future__ import annotations

import asyncio
import datetime
import math
import socket
from collections.abc import Sequence
from contextlib import suppress
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, overload
from urllib.parse import urljoin

import aiohttp
from homeassistant.helpers.storage import Store
from pydantic import BaseModel, TypeAdapter

from .api_types import (
    BaseDaikinOneOpenApiModel,
    DaikinOneOpenApiAuthRequest,
    DaikinOneOpenApiAuthResponse,
    DaikinOneOpenApiDevicesResponse,
    DaikinOneOpenApiDevicesResponseLocation,
    DaikinOneOpenApiThermostatSetFanRequest,
    DaikinOneOpenApiThermostatSetModeAndSetpointsRequest,
    DaikinOneOpenApiThermostatSetScheduleRequest,
    DaikinOneOpenApiThermostatStateResponse,
    FanCirculateSchedule,
    FanCirculateSpeed,
    ThermostatMode,
)
from .const import STORAGE_AUTH_TOKEN_PREFIX, STORAGE_VERSION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


BASE_URL = "https://integrator-api.daikinskyport.com"

# Per https://www.daikinone.com/openapi/documentation/index.html
MAX_CONCURRENT_REQUESTS = 3


class DaikinOneOpenApiAuthToken(BaseModel):
    """An auth token."""

    token: str
    expiry: datetime.datetime


class DaikinOneOpenApiClientError(Exception):
    """Exception to indicate a general API error."""


class DaikinOneOpenApiClientCommunicationError(
    DaikinOneOpenApiClientError,
):
    """Exception to indicate a communication error."""


class DaikinOneOpenApiClientAuthenticationError(
    DaikinOneOpenApiClientError,
):
    """Exception to indicate an authentication error."""


class DaikinOneOpenApiClientRateLimitError(
    DaikinOneOpenApiClientCommunicationError,
):
    """Exception to indicate the API is rate limiting us."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Store the backoff period requested by the API."""
        super().__init__(message)

        self._retry_after = retry_after

    @property
    def retry_after(self) -> int | None:
        """Retry after."""
        return self._retry_after


def _parse_retry_after(response: aiohttp.ClientResponse) -> int:
    """Return the backoff period (whole seconds) from the Retry-After header."""
    value: float | None = None
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        with suppress(ValueError):
            value = float(retry_after)
    if value is not None and math.isfinite(value) and value >= 0:
        return math.ceil(value)
    return 60


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        msg = "Invalid credentials"
        raise DaikinOneOpenApiClientAuthenticationError(
            msg,
        )
    if response.status == HTTPStatus.TOO_MANY_REQUESTS:
        msg = "Rate limited by the API"
        raise DaikinOneOpenApiClientRateLimitError(
            msg,
            retry_after=_parse_retry_after(response),
        )
    response.raise_for_status()


class DaikinOneOpenApiClient:
    """DaikinOne OpenAPI Client."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        api_key: str,
        email: str,
        integrator_token: str,
    ) -> None:
        """DaikinOne OpenAPI Client."""
        self._hass = hass
        self._session = session

        self._api_key = api_key
        self._email = email
        self._integrator_token = integrator_token

        self._store = Store(
            hass,
            STORAGE_VERSION,
            DaikinOneOpenApiClient.make_auth_token_storage_key(email),
        )

        self._auth_token_lock = asyncio.Lock()
        self._auth_token: DaikinOneOpenApiAuthToken | None = None

        self._request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    @property
    def api_key(self) -> str:
        """Get the api key."""
        return self._api_key

    @property
    def email(self) -> str:
        """Get the email."""
        return self._email

    @property
    def integrator_token(self) -> str:
        """Get the integrator token."""
        return self._integrator_token

    @staticmethod
    def make_auth_token_storage_key(email: str) -> str:
        """Make the storage key."""
        return STORAGE_AUTH_TOKEN_PREFIX + email

    @property
    def auth_token_storage_key(self) -> str:
        """The storage key."""
        return DaikinOneOpenApiClient.make_auth_token_storage_key(self._email)

    async def reauth(self) -> DaikinOneOpenApiAuthToken:
        """Force reauthentication and saves the auth token."""
        async with self._auth_token_lock:
            return await self._do_reauth()

    async def _do_reauth(self) -> DaikinOneOpenApiAuthToken:
        """Force reauthentication and saves the auth token."""
        response = await self._api_wrapper_noauth(
            "POST",
            "/v1/token",
            DaikinOneOpenApiAuthRequest(
                email=self._email, integrator_token=self._integrator_token
            ),
            decode_type=DaikinOneOpenApiAuthResponse,
        )

        self._auth_token = DaikinOneOpenApiAuthToken(
            token=response.access_token,
            expiry=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(seconds=response.access_token_expires_in),
        )

        await self._store.async_save(self._auth_token.model_dump(mode="json"))

        return self._auth_token

    async def get_devices(self) -> DaikinOneOpenApiDevicesResponse:
        """Return a list of devices."""
        return await self._api_wrapper(
            "GET",
            "/v1/devices",
            decode_type=list[DaikinOneOpenApiDevicesResponseLocation],
        )

    async def get_device_state(
        self, device_id: str
    ) -> DaikinOneOpenApiThermostatStateResponse:
        """Return a device state."""
        return await self._api_wrapper(
            "GET",
            f"/v1/devices/{device_id}",
            decode_type=DaikinOneOpenApiThermostatStateResponse,
        )

    async def set_device_mode_and_setpoints(
        self,
        device_id: str,
        mode: ThermostatMode,
        heat_setpoint: float,
        cool_setpoint: float,
    ) -> None:
        """Set device mode and setpoints."""
        await self._api_wrapper(
            "PUT",
            f"/v1/devices/{device_id}/msp",
            DaikinOneOpenApiThermostatSetModeAndSetpointsRequest(
                mode=mode,
                heat_setpoint=heat_setpoint,
                cool_setpoint=cool_setpoint,
            ),
        )

    async def set_device_schedule(
        self,
        device_id: str,
        schedule_enabled: bool,  # noqa: FBT001
    ) -> None:
        """Set device schedule state."""
        await self._api_wrapper(
            "PUT",
            f"/v1/devices/{device_id}/schedule",
            DaikinOneOpenApiThermostatSetScheduleRequest(
                schedule_enabled=schedule_enabled
            ),
        )

    async def set_device_fan_mode(
        self,
        device_id: str,
        fan_circulate: FanCirculateSchedule,
        fan_circulate_speed: FanCirculateSpeed,
    ) -> None:
        """Set device fan mode."""
        await self._api_wrapper(
            "PUT",
            f"/v1/devices/{device_id}/fan",
            DaikinOneOpenApiThermostatSetFanRequest(
                fan_circulate=fan_circulate,
                fan_circulate_speed=fan_circulate_speed,
            ),
        )

    async def _get_auth_or_do_auth(self) -> DaikinOneOpenApiAuthToken:
        """Return the current auth object, or gets (and stores) a new one if needed."""
        async with self._auth_token_lock:
            # Try to load the token.
            if self._auth_token is None:
                store_data = await self._store.async_load()
                if store_data is not None:
                    self._auth_token = DaikinOneOpenApiAuthToken.model_validate(
                        store_data
                    )

            # Try to use the existing token.
            if (
                self._auth_token is not None
                and datetime.datetime.now(datetime.UTC) <= self._auth_token.expiry
            ):
                return self._auth_token

            # Reload the token.
            return await self._do_reauth()

    @overload
    async def _api_wrapper[
        DecodeTypeT: BaseDaikinOneOpenApiModel | Sequence[BaseDaikinOneOpenApiModel]
    ](
        self,
        method: str,
        url_part: str,
        data: BaseDaikinOneOpenApiModel
        | Sequence[BaseDaikinOneOpenApiModel]
        | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode_type: type[DecodeTypeT],
        allow_reauth: bool = True,
    ) -> DecodeTypeT: ...

    @overload
    async def _api_wrapper[
        DecodeTypeT: BaseDaikinOneOpenApiModel | Sequence[BaseDaikinOneOpenApiModel]
    ](
        self,
        method: str,
        url_part: str,
        data: BaseDaikinOneOpenApiModel
        | Sequence[BaseDaikinOneOpenApiModel]
        | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode_type: None = None,
        allow_reauth: bool = True,
    ) -> dict[str, Any]: ...

    async def _api_wrapper[  # noqa: PLR0913
        DecodeTypeT: BaseDaikinOneOpenApiModel | Sequence[BaseDaikinOneOpenApiModel]
    ](
        self,
        method: str,
        url_part: str,
        data: BaseDaikinOneOpenApiModel
        | Sequence[BaseDaikinOneOpenApiModel]
        | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode_type: type[DecodeTypeT] | None = None,
        allow_reauth: bool = True,
    ) -> DecodeTypeT | dict:
        """Get information from the API."""
        auth_object = await self._get_auth_or_do_auth()

        headers_with_auth = {
            "Authorization": f"Bearer {auth_object.token}",
            **(headers if headers is not None else {}),
        }

        try:
            return await self._api_wrapper_noauth(
                method, url_part, data, headers_with_auth, decode_type=decode_type
            )
        except DaikinOneOpenApiClientAuthenticationError:
            if allow_reauth:
                await self.reauth()
                return await self._api_wrapper(
                    method,
                    url_part,
                    data,
                    headers,
                    decode_type=decode_type,
                    allow_reauth=False,
                )

            raise

    @overload
    async def _api_wrapper_noauth[
        DecodeTypeT: BaseDaikinOneOpenApiModel | Sequence[BaseDaikinOneOpenApiModel]
    ](
        self,
        method: str,
        url_part: str,
        data: BaseDaikinOneOpenApiModel
        | Sequence[BaseDaikinOneOpenApiModel]
        | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode_type: type[DecodeTypeT],
    ) -> DecodeTypeT: ...

    @overload
    async def _api_wrapper_noauth[
        DecodeTypeT: BaseDaikinOneOpenApiModel | Sequence[BaseDaikinOneOpenApiModel]
    ](
        self,
        method: str,
        url_part: str,
        data: BaseDaikinOneOpenApiModel
        | Sequence[BaseDaikinOneOpenApiModel]
        | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode_type: None = None,
    ) -> dict[str, Any]: ...

    async def _api_wrapper_noauth[
        DecodeTypeT: BaseDaikinOneOpenApiModel | Sequence[BaseDaikinOneOpenApiModel]
    ](
        self,
        method: str,
        url_part: str,
        data: BaseDaikinOneOpenApiModel
        | Sequence[BaseDaikinOneOpenApiModel]
        | None = None,
        headers: dict[str, str] | None = None,
        *,
        decode_type: type[DecodeTypeT] | None = None,
    ) -> DecodeTypeT | dict:
        """Get information from the API."""
        try:
            headers = {
                "x-api-key": self._api_key,
                **(headers if headers is not None else {}),
            }

            json = None
            if data is not None:
                if isinstance(data, BaseDaikinOneOpenApiModel):
                    json = data.model_dump(by_alias=True)
                else:
                    json = [item.model_dump(by_alias=True) for item in data]

            async with self._request_semaphore, asyncio.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=urljoin(BASE_URL, url_part),
                    headers=headers,
                    json=json,
                )
                _verify_response_or_raise(response)
                json = await response.json()

                if decode_type is not None:
                    if isinstance(decode_type, BaseDaikinOneOpenApiModel):
                        return decode_type.model_validate(json)

                    return TypeAdapter(decode_type).validate_python(json)

                return json

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise DaikinOneOpenApiClientCommunicationError(
                msg,
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise DaikinOneOpenApiClientCommunicationError(
                msg,
            ) from exception
        except DaikinOneOpenApiClientError:
            # Our own typed errors (auth, rate-limit, communication) are already
            # meaningful; re-raise so callers can branch on them instead of masking
            # them with the broad handler below.
            raise
        except Exception as exception:  # pylint: disable=broad-except
            msg = f"Something really wrong happened! - {exception}"
            raise DaikinOneOpenApiClientError(
                msg,
            ) from exception
