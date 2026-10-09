"""PowerDog Data Update Coordinator."""
import logging
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .client import PowerDogClient, PowerDogError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowerDogCoordinator(DataUpdateCoordinator):
    """Data update coordinator for PowerDog."""

    def __init__(self, hass: HomeAssistant, host: str, password: str, scan_interval, port=20000):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )
        self.api = PowerDogClient(host, password, port)
        self.device_info = None
        self.linear_devices = {}
        self.sensors = {}
        self.counters = {}
        self.regulations = {}

        # Device properties indexed by device key
        self.device_properties = {}

        # Flag to track if we've loaded the device definitions
        self._device_definitions_loaded = False

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from PowerDog. Raises UpdateFailed on failure."""
        try:
            if self.device_info is None:
                self.device_info = await self.hass.async_add_executor_job(
                    self.api.get_powerdog_info
                )

            if not self._device_definitions_loaded:
                _LOGGER.debug("Loading PowerDog device definitions")
                definitions = await self.hass.async_add_executor_job(
                    self._load_all_definitions
                )
                self.linear_devices = definitions["linear_devices"]
                self.sensors = definitions["sensors"]
                self.counters = definitions["counters"]
                self.regulations = definitions["regulations"]
                self._process_device_properties()
                self._device_definitions_loaded = True
                _LOGGER.debug(
                    "Loaded PowerDog definitions: %d linear, %d sensors, %d counters, %d regulations",
                    len(self.linear_devices), len(self.sensors),
                    len(self.counters), len(self.regulations),
                )

            current_values = await self.hass.async_add_executor_job(
                self.api.get_all_current_values
            )
        except PowerDogError as err:
            self.api.reset_connection()
            raise UpdateFailed(f"PowerDog API error: {err}") from err

        return {
            "device_info": self.device_info,
            "linear_devices": self.linear_devices,
            "sensors": self.sensors,
            "counters": self.counters,
            "regulations": self.regulations,
            "device_properties": self.device_properties,
            "current_values": current_values,
        }

    def _load_all_definitions(self) -> Dict[str, Dict]:
        """Load all device definitions from PowerDog in a single executor job."""
        return {
            "linear_devices": self.api.get_linear_devices() or {},
            "sensors": self.api.get_sensors() or {},
            "counters": self.api.get_counters() or {},
            "regulations": self.api.get_regulations() or {},
        }

    def _process_device_properties(self) -> None:
        """Process and merge device properties from all definitions."""
        self.device_properties = {}

        # Process linear devices first (base properties)
        for key, device in self.linear_devices.items():
            self.device_properties[key] = {
                "key": key,
                "name": device.get("Name", key),
                "device_type": "linear",
                "unit": device.get("Unit", ""),
                "time_unit": device.get("Unit_Time_Add", ""),
                "type": device.get("Type", "Unknown"),
                "is_counter": False,
                "is_regulation": False,
                "is_sensor": False,
                "is_setable": device.get("Setable", "") != "",
                "max_value": device.get("Max", "100"),
                "properties": device,
            }

        # Add/override with sensor-specific properties
        for key, device in self.sensors.items():
            if key in self.device_properties:
                self.device_properties[key].update({
                    "device_type": "sensor",
                    "is_sensor": True,
                    "properties": {**self.device_properties[key]["properties"], **device},
                })
            else:
                self.device_properties[key] = {
                    "key": key,
                    "name": device.get("Name", key),
                    "device_type": "sensor",
                    "unit": device.get("Unit", ""),
                    "time_unit": device.get("Unit_Time_Add", ""),
                    "type": device.get("Type", "Unknown"),
                    "is_counter": False,
                    "is_regulation": False,
                    "is_sensor": True,
                    "is_setable": device.get("Setable", "") != "",
                    "max_value": device.get("Max", "100"),
                    "properties": device,
                }

        # Add/override with counter-specific properties
        for key, device in self.counters.items():
            if key in self.device_properties:
                self.device_properties[key].update({
                    "device_type": "counter",
                    "is_counter": True,
                    "properties": {**self.device_properties[key]["properties"], **device},
                })
            else:
                self.device_properties[key] = {
                    "key": key,
                    "name": device.get("Name", key),
                    "device_type": "counter",
                    "unit": device.get("Unit", ""),
                    "time_unit": device.get("Unit_Time_Add", ""),
                    "type": device.get("Type", "Unknown"),
                    "is_counter": True,
                    "is_regulation": False,
                    "is_sensor": False,
                    "is_setable": device.get("Setable", "") != "",
                    "max_value": device.get("Max", "100"),
                    "properties": device,
                }

        # Add/override with regulation-specific properties
        for key, device in self.regulations.items():
            setable = device.get("Setable", "") or ""
            setable_params = PowerDogClient.parse_setable(setable)
            hardware = device.get("Hardware", "")
            extra = {
                "hardware": hardware,
                "setable_raw": setable,
                "setable_params": setable_params,
                "min_value": device.get("Min", "0"),
            }
            if key in self.device_properties:
                self.device_properties[key].update({
                    "device_type": "regulation",
                    "is_regulation": True,
                    "properties": {**self.device_properties[key]["properties"], **device},
                    **extra,
                })
            else:
                self.device_properties[key] = {
                    "key": key,
                    "name": device.get("Name", key),
                    "device_type": "regulation",
                    "unit": device.get("Unit", "%"),
                    "time_unit": device.get("Unit_Time_Add", ""),
                    "type": device.get("Type", "Percent"),
                    "is_counter": False,
                    "is_regulation": True,
                    "is_sensor": False,
                    "is_setable": setable != "",
                    "max_value": device.get("Max", "100"),
                    "properties": device,
                    **extra,
                }

    def get_device_property(self, device_key: str, property_name: str, default: Any = None) -> Any:
        """Get a property value for a device with fallback to default."""
        device_props = self.device_properties.get(device_key, {})
        return device_props.get(property_name, default)

    def reload_device_definitions(self) -> None:
        """Reload all device definitions from the API."""
        self._device_definitions_loaded = False
        self.api.clear_cache()