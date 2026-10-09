"""Test the PowerDog config flow."""
from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.powerdog.const import DOMAIN


async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_powerdog_client: MagicMock
) -> None:
    """A successful user-driven config flow stores the connection details."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "192.0.2.10", "password": "secret", "port": 20000},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "PowerDog 192.0.2.10"
    assert result["data"] == {
        "host": "192.0.2.10",
        "password": "secret",
        "port": 20000,
    }


async def test_user_flow_handles_connection_error(
    hass: HomeAssistant, mock_powerdog_client: MagicMock
) -> None:
    """When the device is unreachable the form re-renders with an error."""
    mock_powerdog_client.get_linear_devices.side_effect = OSError("unreachable")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"host": "10.0.0.1", "password": "wrong", "port": 20000},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
