import logging
from homeassistant.helpers.entity import Entity
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

class PowerDogSensor(Entity):
    """Ein PowerDog Sensor."""
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        self._state = entity_info.get("Current_Value", None)
        self._unit = entity_info.get("Unit", "")
        self._attr_unique_id = f"powerdog_{self._entity_id}"
        # Wert setzen
        self._value = float(entity_info.get("Current_Value", 0))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},  # Nutze `entry_id`
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

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
        _LOGGER.debug(f"✅ {self._name} wurde zu Home Assistant hinzugefügt!")

    async def async_update(self):
        """Aktualisiert den Wert aus dem Hub."""
        if self._entity_id not in self._hub.sensors:
            _LOGGER.warning(f"⚠️ Entität {self._entity_id} existiert nicht mehr im Hub-Datenbestand!")
            return

        value = self._hub.sensors[self._entity_id].get("Current_Value")
        if value is not None:
            self._state = value

        # ✅ Erst updaten, wenn die Entität wirklich registriert wurde
        if self.registry_entry:
            self.async_write_ha_state()
            _LOGGER.debug(f"🔄 {self._name} aktualisiert auf {self._state}")
        else:
            _LOGGER.warning(f"⚠️ HA hat {self._name} noch nicht registriert!")
