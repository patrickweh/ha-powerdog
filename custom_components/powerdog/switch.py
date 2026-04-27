"""Support for PowerDog switches."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import PowerDogError
from .const import DOMAIN
from .entity import PowerDogEntity

_LOGGER = logging.getLogger(__name__)

SWITCH_HARDWARE = {"ManualValue", "ManualSwitch", "ManualAutoSwitch"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerDog switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_key, device_props in coordinator.device_properties.items():
        if not (device_props["is_regulation"] and device_props["is_setable"]):
            continue
        if device_props.get("hardware") not in SWITCH_HARDWARE:
            continue
        entities.append(PowerDogSwitch(coordinator, device_key))

    if entities:
        async_add_entities(entities)


class PowerDogSwitch(PowerDogEntity, SwitchEntity):
    """Representation of a PowerDog switch.

    Toggles the manual mode of a regulation. Read state from OnOff (ManualValue)
    or SwitchMode (ManualSwitch / ManualAutoSwitch). The actual percentage is
    exposed by the matching number entity.
    """

    def __init__(self, coordinator, device_key):
        super().__init__(coordinator, device_key)
        # Match deployed unique_id so existing entity_ids (switch.q_h_0_100, ...) survive.
        self._attr_unique_id = f"powerdog_switch_{device_key}"
        if "onoff" in self._setable_params:
            self._toggle_param = "onoff"
            self._state_field = "OnOff"
        elif "manual" in self._setable_params:
            self._toggle_param = "manual"
            self._state_field = "SwitchMode"
        else:
            self._toggle_param = None
            self._state_field = None

    @property
    def is_on(self):
        """Return true if the regulation is in manual mode."""
        if not self._state_field:
            return False
        device_data = self.get_current_device_data()
        raw = device_data.get(self._state_field)
        if raw is None:
            return False
        try:
            return float(str(raw).replace(",", ".")) > 0
        except (TypeError, ValueError):
            return str(raw).lower() in ("1", "true", "on")

    async def async_turn_on(self, **kwargs):
        await self._async_set(True)

    async def async_turn_off(self, **kwargs):
        await self._async_set(False)

    async def _async_set(self, on: bool) -> None:
        if not self._toggle_param:
            raise HomeAssistantError(
                f"PowerDog regulation {self._device_key} has no boolean toggle parameter"
            )
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_regulation_parameter,
                self._device_key,
                self._toggle_param,
                on,
            )
        except PowerDogError as err:
            raise HomeAssistantError(
                f"Failed to set {self._device_key} {self._toggle_param}={on}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
