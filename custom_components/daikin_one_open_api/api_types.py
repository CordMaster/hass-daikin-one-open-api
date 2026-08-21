"""Types for interacting with the API."""

from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class BaseDaikinOneOpenApiModel(BaseModel):
    """Base model."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DaikinOneOpenApiAuthRequest(BaseDaikinOneOpenApiModel):
    """Base request to get an auth token."""

    email: str
    integrator_token: str


class DaikinOneOpenApiAuthResponse(BaseDaikinOneOpenApiModel):
    """Base response for getting an auth token."""

    access_token: str
    access_token_expires_in: int
    token_type: Literal["Bearer"]


class DaikinOneOpenApiDevicesResponseDevice(BaseDaikinOneOpenApiModel):
    """Device in a base response for getting an device list."""

    id: str
    name: str
    model: str
    firmware_version: str


class DaikinOneOpenApiDevicesResponseLocation(BaseDaikinOneOpenApiModel):
    """Location in a base response for getting an device list."""

    location_name: str
    devices: list[DaikinOneOpenApiDevicesResponseDevice]


type DaikinOneOpenApiDevicesResponse = list[DaikinOneOpenApiDevicesResponseLocation]


class EquipmentStatus(IntEnum):
    """Enum representing the status of the AC."""

    UNKNOWN = 0
    COOL = 1
    OVERCOOL_FOR_DEHUMIDIFY = 2
    HEAT = 3
    FAN = 4
    IDLE = 5


class ModeEmergencyHeatAvailable(IntEnum):
    """Enum representing whether or not emergency heat is available."""

    UNAVAILABLE = 0
    AVAILABLE = 1


class ThermostatMode(IntEnum):
    """Enum representing the status of the thermostat."""

    OFF = 0
    HEAT = 1
    COOL = 2
    AUTO = 3
    EMERGENCY_HEAT = 4


class ModeLimit(IntEnum):
    """Enum representing the mode limit of the thermostat."""

    NONE = 0
    ALL = 1
    HEAT_ONLY = 2
    COOL_ONLY = 3


class FanState(IntEnum):
    """Enum representing the state of the system fan."""

    AUTO = 0
    ON = 1


class FanCirculateSchedule(IntEnum):
    """Enum representing the schedule of the fan."""

    OFF = 0
    ALWAYS_ON = 1
    SCHEDULE = 2


class FanCirculateSpeed(IntEnum):
    """Enum representing the spped of the fan."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2


class DaikinOneOpenApiThermostatStateResponse(BaseDaikinOneOpenApiModel):
    """
    Response indicating a thermostat's current state.

    Temperature is expressed as celcius.
    Humudity is expressed as a percentage (0-100).
    """

    equipment_status: EquipmentStatus
    mode: ThermostatMode
    mode_limit: ModeLimit
    mode_em_heat_available: ModeEmergencyHeatAvailable
    fan: FanState
    fan_circulate: FanCirculateSchedule
    fan_circulate_speed: FanCirculateSpeed

    heat_setpoint: float
    cool_setpoint: float
    setpoint_delta: float
    setpoint_minimum: float
    setpoint_maximum: float
    temp_indoor: float
    hum_indoor: float
    temp_outdoor: float
    hum_outdoor: float
    schedule_enabled: bool
    geofencing_enabled: bool


class DaikinOneOpenApiThermostatSetModeAndSetpointsRequest(BaseDaikinOneOpenApiModel):
    """Request to set the mode and both setpoints."""

    mode: ThermostatMode
    heat_setpoint: float
    cool_setpoint: float

    @model_validator(mode="after")
    def verify_setpoints(self) -> DaikinOneOpenApiThermostatSetModeAndSetpointsRequest:
        """Verify that the setpoints are valid."""
        if not (self.heat_setpoint < self.cool_setpoint):
            msg = "Heat setpoint must be less than cool setpoint."
            raise ValueError(msg)

        return self


class DaikinOneOpenApiThermostatSetScheduleRequest(BaseDaikinOneOpenApiModel):
    """Request to set the schedule."""

    schedule_enabled: bool


class DaikinOneOpenApiThermostatSetFanRequest(BaseDaikinOneOpenApiModel):
    """Request to set the fan mode."""

    fan_circulate: FanCirculateSchedule
    fan_circulate_speed: FanCirculateSpeed
