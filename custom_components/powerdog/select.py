import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN]["hub"]
    entities = [PowerDogModeSelect(hub, entry, entity_id, entity) for entity_id, entity in hub.selects.items()]

    async_add_entities(entities, True)

class PowerDogModeSelect(SelectEntity):
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        self._state = entity_info.get("Current_Value", None)
        self._unit = entity_info.get("Unit", "")
        self._attr_unique_id = f"powerdog_{self._entity_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},  # Nutze `entry_id`
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

        self._attr_options = ["Auto", "On", "Off"]

        switch_mode = entity_info.get("SwitchMode", "0")  # Standard: Auto
        switch_state = entity_info.get("SwitchState", "0")

        if switch_mode == "0":
            self._attr_current_option = "Auto"
        elif switch_state == "100":
            self._attr_current_option = "On"
        else:
            self._attr_current_option = "Off"

        _LOGGER.debug(f"🔍 {self._name} initialisiert mit Modus: {self._attr_current_option}")

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    def select_option(self, option):
        """Setzt den Modus auf Auto, On oder Off."""
        _LOGGER.debug(f"🔄 Moduswechsel auf {option} für {self._attr_name}")

        try:
            if option == "Auto":
                response = self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "manual", "0"
                )
            else:
                # In Manuell-Modus wechseln
                self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "manual", "1"
                )
                if option == "On":
                    response = self._hub.client.setRegulationParameter(
                        self._hub.password, self._entity_id, "value", "100"
                    )
                else:
                    response = self._hub.client.setRegulationParameter(
                        self._hub.password, self._entity_id, "value", "0"
                    )

            self._attr_current_option = option
        except Exception as e:
            _LOGGER.error(f"❌ Fehler beim Setzen des Modus für {self._attr_name}: {e}")

    async def async_update(self):
        """Aktualisiert den Wert aus dem Hub."""
        if self._entity_id not in self._hub.selects:
            _LOGGER.warning(f"⚠️ Entität {self._entity_id} existiert nicht mehr im Hub-Datenbestand!")
            return

        value = self._hub.selects[self._entity_id].get("Current_Value")
        if value is not None:
            self._state = value

        # ✅ Erst updaten, wenn die Entität wirklich registriert wurde
        if self.registry_entry:
            self.async_write_ha_state()
            _LOGGER.debug(f"🔄 {self._name} aktualisiert auf {self._state} von {value}")
        else:
            _LOGGER.warning(f"⚠️ HA hat {self._name} noch nicht registriert!")
