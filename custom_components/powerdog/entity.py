"""PowerDog base entity."""
import logging
from typing import Any, Dict, Optional

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PowerDogEntity(CoordinatorEntity):
    """Base entity for PowerDog."""

    def __init__(self, coordinator, device_key):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_key = device_key

        # Get device properties from the coordinator
        device_props = coordinator.device_properties.get(device_key, {})
        self._name = device_props.get("name", device_key)
        self._type = device_props.get("type", "Unknown")
        self._unit = device_props.get("unit", "")
        self._time_unit = device_props.get("time_unit", "")
        self._is_counter = device_props.get("is_counter", False)
        self._is_regulation = device_props.get("is_regulation", False)
        self._is_sensor = device_props.get("is_sensor", False)
        self._is_setable = device_props.get("is_setable", False)
        self._max_value = device_props.get("max_value", "100")
        self._min_value = device_props.get("min_value", "0")
        self._hardware = device_props.get("hardware", "")
        self._setable_params = device_props.get("setable_params", {})

        # Match deployed naming so the existing entity registry keeps entity_ids.
        self._attr_name = self._name
        self._attr_unique_id = f"powerdog_{device_key}"

    @property
    def device_info(self):
        """Return device information."""
        if self.coordinator.device_info:
            device_id = self.coordinator.device_info["SerialNumber"]
            if device_id.startswith("PowerDog-"):
                # For placeholder device info, use IP address as identifier
                device_id = device_id.split("-", 1)[1]

            return {
                "identifiers": {(DOMAIN, device_id)},
                "name": f"PowerDog {device_id}",
                "manufacturer": "ecodata GmbH",
                "model": "PowerDog",
                "sw_version": self.coordinator.device_info.get("FullVersion", "Unknown"),
            }
        return None

    @property
    def available(self):
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        current_values = self.coordinator.data.get("current_values", {})

        # If we don't have current values at all, entity is unavailable
        if not current_values:
            return False

        # Check if this specific device has data
        device_data = current_values.get(self._device_key, {})

        # Consider available if we have any data and Valid is not explicitly False
        valid = device_data.get("Valid", True)
        # Handle boolean or string representation of boolean
        if isinstance(valid, str):
            valid = valid.lower() not in ("false", "0", "")

        return bool(device_data) and valid

    @property
    def current_value(self):
        """Get the current value for this entity."""
        current_values = self.coordinator.data.get("current_values", {})
        device_data = current_values.get(self._device_key, {})
        if device_data:
            try:
                value = device_data.get("Current_Value", 0)
                # Handle both string and numeric values
                if isinstance(value, (int, float)):
                    return value
                elif isinstance(value, str):
                    # Convert comma decimal separator to period for float conversion
                    value = value.replace(',', '.')
                    return float(value)
                return 0
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid value for %s: %s - using 0",
                    self._device_key,
                    device_data.get("Current_Value")
                )
                return 0
        return 0

    @property
    def device_properties(self) -> Dict[str, Any]:
        """Return all properties for this device."""
        return self.coordinator.device_properties.get(self._device_key, {})

    def get_device_property(self, property_name: str, default: Any = None) -> Any:
        """Get a property for this device with fallback to default."""
        return self.coordinator.get_device_property(self._device_key, property_name, default)

    def get_current_device_data(self) -> Dict[str, Any]:
        """Get current data for this device."""
        current_values = self.coordinator.data.get("current_values", {})
        return current_values.get(self._device_key, {})