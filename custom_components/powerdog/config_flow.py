"""Config flow for PowerDog integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_PORT,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .client import PowerDogClient
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)


class PowerDogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PowerDog."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the user input
            host = user_input[CONF_HOST]
            password = user_input[CONF_PASSWORD]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Create test client
            client = PowerDogClient(host, password, port)

            # Test connection by getting linear devices - most reliable endpoint
            try:
                devices = await self.hass.async_add_executor_job(client.get_linear_devices)

                # Check if we got a valid response
                if devices is not None:
                    # Connection successful, create the config entry
                    return self.async_create_entry(
                        title=f"PowerDog {host}",
                        data=user_input,
                    )
                else:
                    errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Error during connection test: %s", e)
                errors["base"] = "cannot_connect"

        # Show the configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PowerDogOptionsFlowHandler(config_entry)


class PowerDogOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle PowerDog options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        # Don't store config_entry directly - this is what causes the warning
        # Instead, store just the values we need
        self.entry_id = config_entry.entry_id
        self.current_options = config_entry.options

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current options or defaults
        current_scan_interval = self.current_options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()
        )

        # Show form with current options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_scan_interval,
                    ): int,
                }
            ),
            description_placeholders={
                "current_scan_interval": current_scan_interval,
            },
        )