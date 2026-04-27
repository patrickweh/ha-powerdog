"""Support for PowerDog numbers."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import PowerDogError
from .const import DOMAIN
from .entity import PowerDogEntity

_LOGGER = logging.getLogger(__name__)

NUMBER_HARDWARE = {"ManualValue", "ManualSwitch", "ManualAutoSwitch"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PowerDog numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device_key, device_props in coordinator.device_properties.items():
        if not (device_props["is_regulation"] and device_props["is_setable"]):
            continue
        if device_props.get("hardware") not in NUMBER_HARDWARE:
            continue
        if "value" not in device_props.get("setable_params", {}):
            continue
        entities.append(PowerDogNumber(coordinator, device_key))

    if entities:
        async_add_entities(entities)


def _to_float(value, default: float) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


class PowerDogNumber(PowerDogEntity, NumberEntity):
    """Representation of a PowerDog setable regulation as a number."""

    def __init__(self, coordinator, device_key):
        super().__init__(coordinator, device_key)
        # Match deployed unique_id so existing entity_ids (number.q_h_0_100, ...) survive.
        self._attr_unique_id = f"powerdog_number_{device_key}"

        self._attr_native_min_value = _to_float(self._min_value, 0.0)
        self._attr_native_max_value = _to_float(self._max_value, 100.0)
        self._attr_native_step = 1.0
        self._attr_mode = "slider"
        self._attr_native_unit_of_measurement = self._unit or "%"

    @property
    def native_value(self):
        """Return the current value."""
        return self.current_value

    async def async_set_native_value(self, value):
        """Set the regulation 'value' parameter."""
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.api.set_regulation_value,
                self._device_key,
                value,
            )
        except PowerDogError as err:
            raise HomeAssistantError(
                f"Failed to set {self._device_key} value={value}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
