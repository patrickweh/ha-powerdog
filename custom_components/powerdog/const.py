"""Constants for the PowerDog integration."""
from datetime import timedelta

from homeassistant.const import (
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfPower,
    UnitOfPressure,
    PERCENTAGE,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)

DOMAIN = "powerdog"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_PORT = 20000

# Energy unit mappings
ENERGY_UNIT_MAPPING = {
    "W": UnitOfEnergy.WATT_HOUR,
    "kW": UnitOfEnergy.KILO_WATT_HOUR,
    "MW": UnitOfEnergy.MEGA_WATT_HOUR,
}

# Power unit mappings
POWER_UNIT_MAPPING = {
    "W": UnitOfPower.WATT,
    "kW": UnitOfPower.KILO_WATT,
    "MW": UnitOfPower.MEGA_WATT,
}

# Temperature unit mappings
TEMPERATURE_UNIT_MAPPING = {
    "°C": UnitOfTemperature.CELSIUS,
    "C": UnitOfTemperature.CELSIUS,
    "°F": UnitOfTemperature.FAHRENHEIT,
    "F": UnitOfTemperature.FAHRENHEIT,
}

# Pressure unit mappings
PRESSURE_UNIT_MAPPING = {
    "hPa": UnitOfPressure.HPA,
    "bar": UnitOfPressure.BAR,
    "mbar": UnitOfPressure.MBAR,
}

# PowerDog device types
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_COUNTER = "counter"
DEVICE_TYPE_REGULATION = "regulation"
DEVICE_TYPE_LINEAR = "linear"

# PowerDog API methods
API_METHOD_GET_LINEAR_DEVICES = "getLinearDevices"
API_METHOD_GET_SENSORS = "getSensors"
API_METHOD_GET_COUNTERS = "getCounters"
API_METHOD_GET_REGULATIONS = "getRegulations"
API_METHOD_GET_ALL_CURRENT_VALUES = "getAllCurrentLinearValues"
API_METHOD_GET_CURRENT_VALUES = "getCurrentLinearValues"
API_METHOD_SET_LINEAR_SENSOR = "setLinearSensorDevice"
API_METHOD_SET_LINEAR_COUNTER = "setLinearCounterDevice"
API_METHOD_SET_REGULATION = "setRegulationParameter"