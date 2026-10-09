"""Common fixtures for the PowerDog integration tests."""
from __future__ import annotations

from collections.abc import Generator
from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.powerdog.client import PowerDogClient as RealPowerDogClient
from custom_components.powerdog.const import DOMAIN

from .const import (
    COUNTERS,
    CURRENT_VALUES,
    DEVICE_INFO,
    LINEAR_DEVICES,
    REGULATIONS,
    SENSORS,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable custom integrations in every test."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mocked PowerDog config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="PowerDog 192.0.2.10",
        data={
            "host": "192.0.2.10",
            "password": "secret",
            "port": 20000,
        },
        unique_id="TEST-0001",
        version=1,
    )


@pytest.fixture
def mock_powerdog_client() -> Generator[MagicMock, None, None]:
    """Return a mocked PowerDogClient with a realistic data set.

    The client sits behind both the integration entry point and the config
    flow, so a single patch covers all setup paths.
    """
    with patch(
        "custom_components.powerdog.coordinator.PowerDogClient", autospec=True
    ) as coordinator_client_cls, patch(
        "custom_components.powerdog.config_flow.PowerDogClient", autospec=True
    ) as flow_client_cls:
        # The static parse_setable is also called via the patched class — keep
        # it pointing at the real implementation so the coordinator can parse
        # `Setable` strings exactly like in production.
        coordinator_client_cls.parse_setable.side_effect = RealPowerDogClient.parse_setable
        flow_client_cls.parse_setable.side_effect = RealPowerDogClient.parse_setable
        client = MagicMock()
        client.get_powerdog_info.return_value = dict(DEVICE_INFO)
        client.get_linear_devices.return_value = deepcopy(LINEAR_DEVICES)
        client.get_sensors.return_value = deepcopy(SENSORS)
        client.get_counters.return_value = deepcopy(COUNTERS)
        client.get_regulations.return_value = deepcopy(REGULATIONS)
        client.get_all_current_values.return_value = deepcopy(CURRENT_VALUES)
        client.set_regulation_parameter.return_value = True
        client.set_regulation_value.return_value = True
        client.set_regulation_onoff.return_value = True
        client.set_regulation_manual.return_value = True
        coordinator_client_cls.return_value = client
        flow_client_cls.return_value = client
        yield client


@pytest.fixture
async def init_integration(hass, mock_config_entry, mock_powerdog_client):
    """Set up the PowerDog integration for a test."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
