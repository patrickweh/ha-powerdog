"""Config flow für die PowerDog Integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_PASSWORD, CONF_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Definition des Eingabeformulars für die Erstkonfiguration
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=20000): int,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_INTERVAL, default=30): int
    }
)


class PowerDogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle die Konfigurations-UI für PowerDog."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt der Konfiguration."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        _LOGGER.debug(f"🎛️ PowerDog wird mit {user_input} konfiguriert")

        return self.async_create_entry(title="PowerDog", data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        """Optionen für die Konfiguration bereitstellen."""
        return PowerDogOptionsFlowHandler(entry)


class PowerDogOptionsFlowHandler(config_entries.OptionsFlow):
    """Optionen für die PowerDog Integration."""

    def __init__(self, entry):
        """Speichere die aktuelle Konfiguration."""
        self.entry = entry

    async def async_step_init(self, user_input=None):
        """Zeige die Optionen an und erlaube Änderungen."""
        if user_input is not None:
            _LOGGER.debug(f"🔄 Neue PowerDog-Konfiguration: {user_input}")

            # Erstelle den neuen Eintrag mit den aktualisierten Werten
            return self.async_create_entry(title="", data=user_input)

        # Aktuelle Werte abrufen
        current_options = self.entry.options if self.entry.options else self.entry.data

        # Formular mit aktuellen Werten als Standardwerte
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_options.get(CONF_HOST, "")): str,
                vol.Optional(CONF_PORT, default=current_options.get(CONF_PORT, 20000)): int,
                vol.Required(CONF_PASSWORD, default=current_options.get(CONF_PASSWORD, "")): str,
                vol.Optional(CONF_INTERVAL, default=current_options.get(CONF_INTERVAL, 30)): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
