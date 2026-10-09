"""Support for PowerDog sensors."""
import logging
from typing import Dict, List, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfPower,
    UnitOfPressure,
    PERCENTAGE,
)

from .const import (
    DOMAIN,
    ENERGY_UNIT_MAPPING,
)
from .entity import PowerDogEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerDog sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # No need to wait for refresh here - already done in integration setup
    entities = []

    # Process all devices from the consolidated device properties
    for device_key, device_props in coordinator.device_properties.items():
        # Skip non-readable or already-handled devices
        if not device_props.get("properties", {}):
            continue

        try:
            # Add sensor entities for sensor type devices
            if device_props["is_sensor"]:
                entities.append(PowerDogSensor(coordinator, device_key))

            # Non-setable regulations are read-only sensors (preserve old entity_ids).
            elif device_props["is_regulation"] and not device_props["is_setable"]:
                entities.append(PowerDogSensor(coordinator, device_key))

            # Add counter entities with energy usage tracking
            elif device_props["is_counter"]:
                entities.append(PowerDogCounterSensor(coordinator, device_key))

            # Usage sensors for every counter that reports them (as on main).
            if device_props["is_counter"]:
                device_data = coordinator.data["current_values"].get(device_key, {})
                for usage_key, period in (
                    ("Today_Usage", "Today"),
                    ("30Day_Usage", "30 Days"),
                    ("Year_Usage", "Year"),
                ):
                    if usage_key in device_data:
                        entities.append(
                            PowerDogEnergySensor(coordinator, device_key, usage_key, period)
                        )
        except Exception as e:
            _LOGGER.warning(
                "Error processing device %s for sensors: %s - skipping",
                device_key, e
            )

    # Add all entities at once to avoid multiple updates
    if entities:
        async_add_entities(entities)


class PowerDogSensor(PowerDogEntity, SensorEntity):
    """Representation of a PowerDog sensor."""

    def __init__(self, coordinator, device_key):
        """Initialize the sensor."""
        super().__init__(coordinator, device_key)

        # Get the appropriate unit from the device info
        self._attr_native_unit_of_measurement = self._unit

        # Set the device class based on the unit and type
        if self._unit == "°C":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif self._unit == "hPa":
            self._attr_device_class = SensorDeviceClass.PRESSURE
            self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        elif self._unit == "%":
            if self._type == "Humidity":
                self._attr_device_class = SensorDeviceClass.HUMIDITY
            else:
                self._attr_device_class = SensorDeviceClass.POWER_FACTOR
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif self._unit == "W":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
        elif self._unit == "kW":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT

        # Set the appropriate state class for all sensors
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.current_value

    @property
    def extra_state_attributes(self):
        """Return additional attributes for the sensor."""
        attrs = {}

        # Include all available attributes from the current data
        device_data = self.get_current_device_data()
        for key, value in device_data.items():
            if key not in ["Current_Value", "Name", "Key", "Valid", "Unit"]:
                attrs[key] = value

        return attrs


class PowerDogCounterSensor(PowerDogSensor):
    """Representation of a PowerDog counter as a sensor."""

    def __init__(self, coordinator, device_key):
        """Initialize the counter sensor."""
        super().__init__(coordinator, device_key)

        # Check if this is an energy counter (to distinguish from power readings)
        # Energy counters measure accumulated energy and should have Wh units
        if self._time_unit == "h" and self._unit in ["W", "kW"]:
            # This is an energy counter in Wh or kWh
            if self._unit == "W":
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
            elif self._unit == "kW":
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

            # Use TOTAL instead of TOTAL_INCREASING to avoid the warning
            # since these values might occasionally decrease due to corrections
            self._attr_state_class = SensorStateClass.TOTAL


class PowerDogEnergySensor(PowerDogEntity, SensorEntity):
    """Representation of a PowerDog energy usage sensor."""

    def __init__(self, coordinator, device_key, usage_key, period):
        """Initialize the energy usage sensor."""
        super().__init__(coordinator, device_key)

        self._usage_key = usage_key
        self._period = period
        self._attr_name = f"PowerDog {self._name} Usage {period}"
        self._attr_unique_id = f"powerdog_{device_key}_{usage_key.lower()}"

        # Unit as on main: base unit + "h" for hourly counters, Wh shown as kWh.
        unit = self._unit + "h" if self._time_unit.lower() == "h" else self._unit
        self._divisor = 1
        if unit == "Wh":
            unit = UnitOfEnergy.KILO_WATT_HOUR
            self._divisor = 1000
        self._attr_native_unit_of_measurement = unit

        if unit in (UnitOfEnergy.KILO_WATT_HOUR, UnitOfEnergy.MEGA_WATT_HOUR):
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL
        else:
            self._attr_device_class = None
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the energy usage sensor."""
        device_data = self.get_current_device_data()
        if device_data and self._usage_key in device_data:
            try:
                value = device_data[self._usage_key]
                if isinstance(value, str):
                    # Convert comma decimal separator to period for float conversion
                    value = value.replace(',', '.')
                return round(float(value) / self._divisor, 3)
            except (ValueError, TypeError):
                return 0
        return 0