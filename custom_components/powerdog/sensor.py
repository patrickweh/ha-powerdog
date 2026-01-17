import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Sensor-Setup für PowerDog."""
    _LOGGER.debug("🔄 async_setup_entry für Sensoren wurde aufgerufen!")

    hub = hass.data[DOMAIN]["hub"]
    entities = [PowerDogSensor(hub, entry, entity_id, entity) for entity_id, entity in hub.sensors.items()]

    async_add_entities(entities, True)
    _LOGGER.debug(f"🚀 {len(entities)} SENSOR-Entitäten erfolgreich hinzugefügt!")

class PowerDogSensor(SensorEntity):
    """Ein PowerDog Sensor."""
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        self._unit = entity_info.get("Unit", "")
        self._attr_unique_id = f"powerdog_{self._entity_id}"

        # Convert Wh to kWh
        self._convert_to_kwh = self._unit == "Wh"
        if self._convert_to_kwh:
            self._unit = "kWh"

        raw_value = entity_info.get("Current_Value", None)
        if raw_value is not None and self._convert_to_kwh:
            self._state = round(float(raw_value) / 1000, 3)
        else:
            self._state = raw_value
        self._value = float(raw_value) if raw_value else 0

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},  # Nutze `entry_id`
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

        # Prüfen, ob es sich um einen Energiezähler handelt
        if self._unit in ["kWh", "MWh"] or self._convert_to_kwh:
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        else:
            self._attr_device_class = None
            self._attr_state_class = SensorStateClass.MEASUREMENT

    def update(self):
        """Hole aktuelle Daten von der API."""
        self._state = self._hub.sensors.get(self._entity_id, {}).get("Current_Value", None)

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    async def async_added_to_hass(self):
        """Wird aufgerufen, wenn die Entität zu Home Assistant hinzugefügt wurde."""
        await self.async_update()
        _LOGGER.debug(f"✅ {self._name} wurde zu Home Assistant hinzugefügt!")

    async def async_update(self):
        """Aktualisiert den Wert aus dem Hub."""
        if self._entity_id not in self._hub.sensors:
            _LOGGER.warning(f"Entity {self._entity_id} no longer exists in hub data!")
            return

        value = self._hub.sensors[self._entity_id].get("Current_Value")
        if value is not None:
            if self._convert_to_kwh:
                self._state = round(float(value) / 1000, 3)
            else:
                self._state = value
            _LOGGER.debug(f"{self._name} updated to {self._state}")
