import logging
import asyncio
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN]["hub"]
    entities = [PowerDogSwitch(hub, entry, entity_id, entity) for entity_id, entity in hub.switches.items()]

    async_add_entities(entities, True)

    # **Neuen Service für den Auto-Modus registrieren**
    async def handle_set_auto_mode(call):
        entity_id = call.data.get("entity_id")
        for switch in entities:
            if switch.entity_id == entity_id:
                switch.set_auto_mode()

    hass.services.async_register(DOMAIN, "set_auto_mode", handle_set_auto_mode)

class PowerDogSwitch(SwitchEntity):
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        self._attr_unique_id = f"powerdog_{self._entity_id}"
        # Wert setzen
        self._value = float(entity_info.get("Current_Value", 0))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},  # Nutze `entry_id`
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

        # **Erkennen, ob es ein OnOff- oder Manual-Switch ist**
        self._is_onoff_switch = "onoff(bool)" in entity_info.get("Setable", "").lower()

        # **Status lesen**
        switch_mode = entity_info.get("SwitchMode")  # Auto (0) oder Manuell (1)
        switch_state = entity_info.get("SwitchState")  # 0 = AUS, 100 = AN
        on_off = entity_info.get("OnOff")

        if self._is_onoff_switch:
            self._state = bool(int(on_off)) if on_off is not None else False
        else:
            # Falls es ein Manual/Auto-Switch ist
            if switch_mode == "1":
                self._state = switch_state == "100"
            else:
                self._state = False  # Auto-Modus → wird als AUS angezeigt

    def turn_on(self, **kwargs):
        """Schalte den Switch an."""

        try:
            if self._is_onoff_switch:
                response = self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "onoff", "1"
                )
            else:
                # Manual/Auto-Switch zuerst auf manuellen Modus setzen, dann aktivieren
                self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "manual", "1"
                )
                response = self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "value", "100"
                )

            self._state = True
        except Exception as e:
            _LOGGER.error(f"❌ Fehler beim Einschalten von {self._name}: {e}")

    def turn_off(self, **kwargs):
        try:
            if self._is_onoff_switch:
                response = self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "onoff", "0"
                )
            else:
                # Manual/Auto-Switch zuerst auf manuellen Modus setzen, dann deaktivieren
                self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "manual", "1"
                )
                response = self._hub.client.setRegulationParameter(
                    self._hub.password, self._entity_id, "value", "0"
                )

            self._state = False
        except Exception as e:
            _LOGGER.error(f"❌ Fehler beim Ausschalten von {self._name}: {e}")

    def set_auto_mode(self):
        try:
            response = self._hub.client.setRegulationParameter(
                self._hub.password, self._entity_id, "manual", "0"
            )
            self._state = False  # Auto-Modus → wird als AUS angezeigt
        except Exception as e:
            _LOGGER.error(f"❌ Fehler beim Setzen auf Auto-Modus für {self._name}: {e}")

    @property
    def is_on(self):
        """Gibt den aktuellen Status zurück."""
        return self._state

    @property
    def name(self):
        """Gibt den Namen des Switches zurück."""
        return self._name

    @property
    def unique_id(self):
        """Gibt eine eindeutige ID für die Entität zurück."""
        return f"powerdog_switch_{self._entity_id}"

    async def async_update(self):
        """Aktualisiert den Wert aus dem Hub."""
        if self._entity_id not in self._hub.switches:
            _LOGGER.warning(f"⚠️ Entität {self._entity_id} existiert nicht mehr im Hub-Datenbestand!")
            return

        value = self._hub.switches.get(self._entity_id, {}).get("Current_Value")
        if value is not None:
            self._state = bool(int(value))  # ✅ Status korrekt setzen

        # ✅ Erst updaten, wenn die Entität wirklich registriert wurde
        if self.registry_entry:
            self.async_write_ha_state()
            _LOGGER.debug(f"🔄 {self._name} aktualisiert auf {self._state}")