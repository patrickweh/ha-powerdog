"""Test integration setup, unload and update behaviour."""
from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powerdog.client import PowerDogError


async def test_setup_creates_entities(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Loading the entry registers switches, numbers and sensors."""
    assert init_integration.state is ConfigEntryState.LOADED

    # Setable ManualValue regulation -> switch + number
    assert hass.states.get("switch.powerdog_test_0001_q_h_0_100") is not None
    assert hass.states.get("number.powerdog_test_0001_q_h_0_100") is not None

    # Energy-typed setable -> number with API max (no switch — no Percent slider).
    ueberschuss = hass.states.get("number.powerdog_test_0001_ueberschuss_pv")
    assert ueberschuss is not None
    assert float(ueberschuss.state) == 250.0
    assert float(ueberschuss.attributes["max"]) == 7000.0

    # Non-setable regulation surfaces as a sensor (preserves old entity_ids).
    assert hass.states.get("sensor.powerdog_test_0001_q_hybrid") is not None


async def test_unload_entry(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Unloading the entry removes the entities and tears down platforms."""
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_nan_value_renders_as_unknown(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """PowerDog occasionally returns 'nan' (e.g. Anforderung WP idle) — HA must
    not raise on numeric sensors but render the state as ``unknown``."""
    from copy import deepcopy

    from .const import CURRENT_VALUES

    bad = deepcopy(CURRENT_VALUES)
    bad["regulation_4"]["Current_Value"] = "nan"
    mock_powerdog_client.get_all_current_values.return_value = bad

    coordinator = hass.data["powerdog"][init_integration.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.powerdog_test_0001_q_hybrid")
    assert state is not None
    assert state.state == "unknown"


async def test_coordinator_marks_entities_unavailable_on_api_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_powerdog_client: MagicMock,
) -> None:
    """When the device starts failing, entities flip to unavailable on the next refresh."""
    mock_powerdog_client.get_all_current_values.side_effect = PowerDogError("offline")

    coordinator = hass.data["powerdog"][init_integration.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    assert hass.states.get("switch.powerdog_test_0001_q_h_0_100").state == STATE_UNAVAILABLE
