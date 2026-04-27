"""Tests for the PowerDog number platform."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powerdog.client import PowerDogError


async def test_number_uses_api_min_max(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Numbers expose the Min/Max values reported by the regulation."""
    percent = hass.states.get("number.powerdog_test_0001_q_h_0_100")
    assert percent is not None
    assert float(percent.attributes["min"]) == 0.0
    assert float(percent.attributes["max"]) == 100.0
    assert percent.attributes["unit_of_measurement"] == "%"

    energy = hass.states.get("number.powerdog_test_0001_ueberschuss_pv")
    assert energy is not None
    assert float(energy.attributes["max"]) == 7000.0
    assert energy.attributes["unit_of_measurement"] == "W"


async def test_set_number_writes_value_parameter(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """Sliding the number control writes the regulation `value` parameter."""
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.powerdog_test_0001_q_h_0_100", "value": 75},
        blocking=True,
    )
    mock_powerdog_client.set_regulation_value.assert_called_once_with(
        "regulation_1", 75
    )


async def test_set_number_propagates_api_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """A device rejecting the set call surfaces as HomeAssistantError."""
    mock_powerdog_client.set_regulation_value.side_effect = PowerDogError("rejected")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.powerdog_test_0001_q_h_0_100", "value": 50},
            blocking=True,
        )
