import logging
import asyncio
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import PERCENTAGE
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Number-Setup for PowerDog."""
    _LOGGER.debug("async_setup_entry for Numbers called!")

    hub = hass.data[DOMAIN]["hub"]
    entities = [PowerDogNumber(hub, entry, entity_id, entity) for entity_id, entity in hub.numbers.items()]

    async_add_entities(entities, True)
    _LOGGER.debug(f"{len(entities)} NUMBER entities added successfully!")

class PowerDogNumber(NumberEntity):
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        _LOGGER.debug(f"Initializing Number {self._name}...")
        self._state = entity_info.get("Current_Value", None)
        self._unit = entity_info.get("Unit", "")
        self._attr_unique_id = f"powerdog_{self._entity_id}"
        self._value = float(entity_info.get("Current_Value", 0))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

        self._attr_native_value = float(entity_info.get("Current_Value", 0))
        self._attr_native_min_value = float(entity_info.get("Min", 0))
        self._attr_native_max_value = float(entity_info.get("Max", 100))

        if "percent" in self._name.lower():
            self._attr_native_unit_of_measurement = PERCENTAGE

    async def async_added_to_hass(self):
        """Called when entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Number {self._name} added to hass")

    @property
    def name(self):
        return self._name

    async def async_set_native_value(self, value: float):
        """Set a new value asynchronously."""
        _LOGGER.debug(f"Setting {self._name} to {value}...")

        def sync_call():
            """Execute the blocking API call in a separate thread."""
            try:
                return self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "value", str(value)
                )
            except Exception as e:
                _LOGGER.error(f"API error setting {self._name}: {e}")
                return None

        response = await asyncio.to_thread(sync_call)

        if response and response.get("ErrorCode") == 0:
            self._attr_native_value = value
            self._hub.numbers[self._entity_id]["Current_Value"] = value
            _LOGGER.debug(f"{self._name} successfully set to {value}")
        else:
            _LOGGER.error(f"Error setting {self._name}: {response}")

    async def async_update(self):
        """Update the value from the hub."""
        if self._entity_id not in self._hub.numbers:
            _LOGGER.warning(f"Entity {self._entity_id} no longer exists in hub data!")
            return

        value = self._hub.numbers.get(self._entity_id, {}).get("Current_Value")
        if value is not None:
            self._attr_native_value = value
            _LOGGER.debug(f"{self._name} updated to {value}")
