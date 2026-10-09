"""PowerDog integration for Home Assistant.

For more details about this integration, please refer to the documentation at
https://www.home-assistant.io/integrations/powerdog/
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_PORT,
    Platform,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .coordinator import PowerDogCoordinator
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

# Platform definitions - expanded to include all supported platforms
PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

# Configuration schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): cv.time_period,
                vol.Optional(
                    CONF_PORT, default=DEFAULT_PORT
                ): cv.port,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config):
    """Set up the PowerDog component."""
    if DOMAIN not in config:
        return True

    host = config[DOMAIN][CONF_HOST]
    password = config[DOMAIN][CONF_PASSWORD]
    scan_interval = config[DOMAIN][CONF_SCAN_INTERVAL]
    port = config[DOMAIN][CONF_PORT]

    # Store configuration for platform setup
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = {
        "host": host,
        "password": password,
        "scan_interval": scan_interval,
        "port": port,
    }

    # Set up services
    from .services import async_setup_services
    await async_setup_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PowerDog from a config entry."""
    host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    # Convert scan_interval to timedelta if it's an integer (seconds)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    if isinstance(scan_interval, int):
        scan_interval = timedelta(seconds=scan_interval)

    # Create data update coordinator
    coordinator = PowerDogCoordinator(hass, host, password, scan_interval, port)

    # Initial refresh to load device definitions
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Error refreshing PowerDog data: %s", err)
        # We'll continue anyway and let the error handling in the coordinator deal with it

    # Store coordinator for platforms to access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register reload handler for when config entry is updated
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Set up services
    from .services import async_setup_services
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove this config entry from data
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unload services if this is the last config entry
        if not hass.data[DOMAIN]:
            from .services import async_unload_services
            await async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)