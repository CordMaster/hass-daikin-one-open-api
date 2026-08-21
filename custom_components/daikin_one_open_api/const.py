"""Constants for daikin_one_open_api."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "daikin_one_open_api"
ATTRIBUTION = (
    "Data provided by https://www.daikinone.com/openapi/documentation/index.html"
)

ENTRY_DATA_API_KEY = "api_key"
ENTRY_DATA_EMAIL = "email"
ENTRY_DATA_INTEGRATIOR_TOKEN = "integrator_token"  # noqa: S105
ENTRY_DATA_SELECTED_DEVICES = "selected_devices"

STORAGE_VERSION = 1
STORAGE_AUTH_TOKEN_PREFIX = DOMAIN + "_auth_token_"
