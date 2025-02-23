import logging
import asyncio
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import PERCENTAGE  # ⚠️ Hier den richtigen Wert importieren
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Number-Setup für PowerDog."""
    _LOGGER.debug("🔄 async_setup_entry für Numbers wurde aufgerufen!")

    hub = hass.data[DOMAIN]["hub"]
    entities = [PowerDogNumber(hub, entry, entity_id, entity) for entity_id, entity in hub.numbers.items()]

    async_add_entities(entities, True)
    _LOGGER.debug(f"🚀 {len(entities)} NUMBER-Entitäten erfolgreich hinzugefügt!")

class PowerDogNumber(NumberEntity):
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        _LOGGER.debug(f"🔧 Initialisiere Number {self._name}...")
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

        self._attr_native_value = float(entity_info.get("Current_Value", 0))
        self._attr_native_min_value = float(entity_info.get("Min", 0))
        self._attr_native_max_value = float(entity_info.get("Max", 100))

        # Falls die Einheit Prozent ist, setze sie explizit
        self._attr_native_unit_of_measurement = PERCENTAGE if "percent" in self._name.lower() else None

    @property
    def unique_id(self):
        """Gibt eine eindeutige ID für die Entität zurück."""
        return f"powerdog_number_{self._entity_id}"

    @property
    def name(self):
        return self._name

    async def async_set_native_value(self, value: float):
        """Setzt einen neuen Wert asynchron."""
        _LOGGER.debug(f"🔄 Setze {self._name} auf {value}...")

        def sync_call():
            """Führe den blockierenden API-Call in einem separaten Thread aus."""
            try:
                return self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "value", str(value)
                )
            except Exception as e:
                _LOGGER.error(f"❌ API-Fehler beim Setzen von {self._name}: {e}")
                return None

        response = await asyncio.to_thread(sync_call)

        if response and response.get("ErrorCode") == 0:
            self._attr_native_value = value
            self.async_write_ha_state()
            self._hub.numbers[self._entity_id]["Current_Value"] = value
            _LOGGER.debug(f"✅ {self._name} erfolgreich auf {value} gesetzt")
        else:
            _LOGGER.error(f"❌ Fehler beim Setzen von {self._name}: {response}")

    async def async_update(self):
            """Aktualisiert den Wert aus dem Hub."""
            if self._entity_id not in self._hub.numbers:
                _LOGGER.warning(f"⚠️ Entität {self._entity_id} existiert nicht mehr im Hub-Datenbestand!")
                return

            value = self._hub.numbers.get(self._entity_id, {}).get("Current_Value")
            if value is not None:
                self._attr_native_value = value

            # ✅ Erst updaten, wenn die Entität wirklich registriert wurde
            if self.registry_entry:
                self.async_write_ha_state()
                _LOGGER.debug(f"🔄 {self._name} aktualisiert auf {self._state}")
