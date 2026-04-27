"""Tests for the PowerDog switch platform."""
from __future__ import annotations

from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powerdog.client import PowerDogError

from .const import CURRENT_VALUES


async def test_switch_state_for_manualvalue(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """ManualValue regulations expose OnOff as the boolean switch state."""
    state = hass.states.get("switch.powerdog_test_0001_q_h_0_100")
    assert state is not None
    assert state.state == STATE_OFF


async def test_switch_state_for_manualautoswitch(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """ManualAutoSwitch regulations expose SwitchMode as the boolean state."""
    state = hass.states.get("switch.powerdog_test_0001_pumpe_q_h_h_a")
    assert state is not None
    assert state.state == STATE_OFF


async def test_turn_on_manualvalue_uses_onoff_param(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """Turning a ManualValue switch on writes the `onoff` parameter."""
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.powerdog_test_0001_q_h_0_100"},
        blocking=True,
    )
    mock_powerdog_client.set_regulation_parameter.assert_called_with(
        "regulation_1", "onoff", True
    )


async def test_turn_off_manualautoswitch_uses_manual_param(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """Turning a ManualAutoSwitch off writes the `manual` parameter."""
    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.powerdog_test_0001_pumpe_q_h_h_a"},
        blocking=True,
    )
    mock_powerdog_client.set_regulation_parameter.assert_called_with(
        "regulation_2", "manual", False
    )


async def test_switch_reflects_updated_state_after_refresh(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """After a refresh the switch picks up the new device state."""
    new_values = deepcopy(CURRENT_VALUES)
    new_values["regulation_1"]["OnOff"] = "1"
    mock_powerdog_client.get_all_current_values.return_value = new_values

    coordinator = hass.data["powerdog"][init_integration.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("switch.powerdog_test_0001_q_h_0_100").state == STATE_ON


async def test_turn_on_propagates_api_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """When the device rejects the set call, HA surfaces it as HomeAssistantError."""
    mock_powerdog_client.set_regulation_parameter.side_effect = PowerDogError("nope")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.powerdog_test_0001_q_h_0_100"},
            blocking=True,
        )
