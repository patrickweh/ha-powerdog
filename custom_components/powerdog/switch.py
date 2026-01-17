import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN]["hub"]
    entities = [PowerDogSwitch(hub, entry, entity_id, entity) for entity_id, entity in hub.switches.items()]

    async_add_entities(entities, True)

    async def handle_set_auto_mode(call):
        entity_id = call.data.get("entity_id")
        for switch in entities:
            if switch.entity_id == entity_id:
                await switch.async_set_auto_mode()

    hass.services.async_register(DOMAIN, "set_auto_mode", handle_set_auto_mode)

class PowerDogSwitch(SwitchEntity):
    def __init__(self, hub, entry, entity_id, entity_info):
        self._hub = hub
        self._entry = entry
        self._entity_id = entity_id
        self._name = f"{entity_info.get('Name', entity_id)}"
        self._attr_unique_id = f"powerdog_{self._entity_id}"
        self._value = float(entity_info.get("Current_Value", 0))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

        self._is_onoff_switch = "onoff(bool)" in entity_info.get("Setable", "").lower()

        switch_mode = entity_info.get("SwitchMode")
        switch_state = entity_info.get("SwitchState")
        on_off = entity_info.get("OnOff")

        if self._is_onoff_switch:
            self._state = bool(int(on_off)) if on_off is not None else False
        else:
            if switch_mode == "1":
                self._state = switch_state == "100"
            else:
                self._state = False

    async def async_added_to_hass(self):
        """Called when entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Switch {self._name} added to hass")

    async def async_turn_on(self, **kwargs):
        """Turn on the switch."""
        try:
            if self._is_onoff_switch:
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "onoff", "1"
                )
            else:
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "manual", "1"
                )
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "value", "100"
                )

            self._state = True
        except Exception as e:
            _LOGGER.error(f"Error turning on {self._name}: {e}")

    async def async_turn_off(self, **kwargs):
        """Turn off the switch."""
        try:
            if self._is_onoff_switch:
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "onoff", "0"
                )
            else:
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "manual", "1"
                )
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "value", "0"
                )

            self._state = False
        except Exception as e:
            _LOGGER.error(f"Error turning off {self._name}: {e}")

    async def async_set_auto_mode(self):
        """Set the switch to auto mode."""
        try:
            await self.hass.async_add_executor_job(
                self._hub.client.setRegulationParameter,
                self._hub.password, self._entity_id, "manual", "0"
            )
            self._state = False
        except Exception as e:
            _LOGGER.error(f"Error setting auto mode for {self._name}: {e}")

    @property
    def is_on(self):
        """Return the current state."""
        return self._state

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    async def async_update(self):
        """Update the value from the hub."""
        if self._entity_id not in self._hub.switches:
            _LOGGER.warning(f"Entity {self._entity_id} no longer exists in hub data!")
            return

        value = self._hub.switches.get(self._entity_id, {}).get("Current_Value")
        if value is not None:
            self._state = bool(int(value))
            _LOGGER.debug(f"{self._name} updated to {self._state}")
