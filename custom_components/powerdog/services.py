"""PowerDog services."""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Service constants
SERVICE_SET_COUNTER_VALUE = "set_counter_value"
SERVICE_RELOAD_DEVICES = "reload_devices"

# Service schemas
SCHEMA_SET_COUNTER_VALUE = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("value"): cv.string,
    vol.Required("meter_reading"): cv.string,
})

SCHEMA_RELOAD_DEVICES = vol.Schema({
    vol.Optional("entity_id"): cv.entity_id,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for PowerDog integration."""

    @callback
    async def async_handle_set_counter_value(service_call: ServiceCall) -> None:
        """Handle set counter value service."""
        entity_id = service_call.data["entity_id"]
        value = service_call.data["value"]
        meter_reading = service_call.data["meter_reading"]

        # Find the entity component
        entity_component = hass.data.get("entity_components", {}).get(SENSOR_DOMAIN)
        if not entity_component:
            entity_registry = hass.helpers.entity_registry.async_get(hass)
            entity = entity_registry.async_get(entity_id)
            if not entity:
                _LOGGER.error("Entity %s not found in registry", entity_id)
                return

            # Extract the coordinator from the domain data
            entry_id = entity.config_entry_id
            if not entry_id or entry_id not in hass.data.get(DOMAIN, {}):
                _LOGGER.error("PowerDog coordinator not found for entity %s", entity_id)
                return

            coordinator = hass.data[DOMAIN][entry_id]
            device_key = entity.unique_id.replace("powerdog_", "")

        else:
            # Traditional method for finding the entity
            entity = entity_component.get_entity(entity_id)
            if not entity:
                _LOGGER.error("Entity %s not found", entity_id)
                return

            # Check if it's a PowerDog counter sensor
            if not hasattr(entity, "coordinator") or not hasattr(entity, "_device_key"):
                _LOGGER.error("Entity %s is not a PowerDog counter", entity_id)
                return

            # Get the coordinator
            coordinator = entity.coordinator
            device_key = entity._device_key

        # Call the API to set the counter value
        success = await hass.async_add_executor_job(
            coordinator.api.set_linear_counter_value,
            device_key,
            value,
            meter_reading
        )

        if success:
            # Refresh the coordinator data
            await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set counter value for %s", entity_id)

    @callback
    async def async_handle_reload_devices(service_call: ServiceCall) -> None:
        """Handle reload devices service."""
        entity_id = service_call.data.get("entity_id")

        if entity_id:
            # Reload for a specific entity's coordinator
            entity_registry = hass.helpers.entity_registry.async_get(hass)
            entity = entity_registry.async_get(entity_id)
            if not entity:
                _LOGGER.error("Entity %s not found in registry", entity_id)
                return

            entry_id = entity.config_entry_id
            if not entry_id or entry_id not in hass.data.get(DOMAIN, {}):
                _LOGGER.error("PowerDog coordinator not found for entity %s", entity_id)
                return

            coordinator = hass.data[DOMAIN][entry_id]

            # Reload device definitions and force a refresh
            coordinator.reload_device_definitions()
            await coordinator.async_request_refresh()

            _LOGGER.info("Reloaded PowerDog device definitions for %s", entity_id)
        else:
            # Reload for all PowerDog coordinators
            for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
                if hasattr(coordinator, "reload_device_definitions"):
                    coordinator.reload_device_definitions()
                    await coordinator.async_request_refresh()

            _LOGGER.info("Reloaded all PowerDog device definitions")

    # Register services
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_COUNTER_VALUE,
        async_handle_set_counter_value,
        schema=SCHEMA_SET_COUNTER_VALUE,
    )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD_DEVICES,
        async_handle_reload_devices,
        schema=SCHEMA_RELOAD_DEVICES,
    )

    return True


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload PowerDog services."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_COUNTER_VALUE):
        hass.services.async_remove(DOMAIN, SERVICE_SET_COUNTER_VALUE)

    if hass.services.has_service(DOMAIN, SERVICE_RELOAD_DEVICES):
        hass.services.async_remove(DOMAIN, SERVICE_RELOAD_DEVICES)