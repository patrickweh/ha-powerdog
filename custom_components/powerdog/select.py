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
        self._unit = entity_info.get("Unit", "")
        self._attr_unique_id = f"powerdog_{self._entity_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.entry_id))},
            name="PowerDog",
            manufacturer="PowerDog",
            model="API"
        )

        self._attr_options = ["Auto", "On", "Off"]

        switch_mode = entity_info.get("SwitchMode", "0")
        switch_state = entity_info.get("SwitchState", "0")

        if switch_mode == "0":
            self._attr_current_option = "Auto"
        elif switch_state == "100":
            self._attr_current_option = "On"
        else:
            self._attr_current_option = "Off"

        _LOGGER.debug(f"{self._name} initialized with mode: {self._attr_current_option}")

    async def async_added_to_hass(self):
        """Called when entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug(f"Select {self._name} added to hass")

    @property
    def name(self):
        return self._name

    async def async_select_option(self, option: str):
        """Set the mode to Auto, On or Off."""
        _LOGGER.debug(f"Mode change to {option} for {self._name}")

        try:
            if option == "Auto":
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "manual", "0"
                )
            else:
                await self.hass.async_add_executor_job(
                    self._hub.client.setRegulationParameter,
                    self._hub.password, self._entity_id, "manual", "1"
                )
                if option == "On":
                    await self.hass.async_add_executor_job(
                        self._hub.client.setRegulationParameter,
                        self._hub.password, self._entity_id, "value", "100"
                    )
                else:
                    await self.hass.async_add_executor_job(
                        self._hub.client.setRegulationParameter,
                        self._hub.password, self._entity_id, "value", "0"
                    )

            self._attr_current_option = option
            _LOGGER.debug(f"{self._name} mode set to {option}")
        except Exception as e:
            _LOGGER.error(f"Error setting mode for {self._name}: {e}")

    async def async_update(self):
        """Update the value from the hub."""
        if self._entity_id not in self._hub.selects:
            _LOGGER.warning(f"Entity {self._entity_id} no longer exists in hub data!")
            return

        entity_info = self._hub.selects.get(self._entity_id, {})
        switch_mode = entity_info.get("SwitchMode", "0")
        switch_state = entity_info.get("SwitchState", "0")

        if switch_mode == "0":
            self._attr_current_option = "Auto"
        elif switch_state == "100":
            self._attr_current_option = "On"
        else:
            self._attr_current_option = "Off"

        _LOGGER.debug(f"{self._name} updated to {self._attr_current_option}")
