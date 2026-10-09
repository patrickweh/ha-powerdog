"""Tests for the PowerDog sensor platform."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_usage_sensor_reports_kwh(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Wh usage values are exposed in kWh under the deployed unique_id."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", "powerdog", "powerdog_buscounter_1_today_usage"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert float(state.state) == 1.234
    assert state.attributes["unit_of_measurement"] == "kWh"


async def test_usage_sensor_for_non_energy_counter_keeps_raw_unit(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Non-energy counters get usage sensors too, with raw value and unit."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", "powerdog", "powerdog_buscounter_2_today_usage"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert float(state.state) == 2.5
    assert state.attributes["unit_of_measurement"] == "m³"
    assert "device_class" not in state.attributes
