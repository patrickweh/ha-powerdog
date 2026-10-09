"""Pure unit tests for the PowerDogClient (no Home Assistant runtime needed)."""
from __future__ import annotations

import xmlrpc.client
from unittest.mock import MagicMock, patch

import pytest

from custom_components.powerdog.client import PowerDogClient, PowerDogError


@pytest.fixture
def server_mock() -> MagicMock:
    """Return a fresh ServerProxy mock."""
    return MagicMock()


@pytest.fixture
def client(server_mock: MagicMock):
    """Return a client with the XML-RPC layer fully mocked for the test's duration.

    `_connect()` is invoked both at construction time and after transport errors,
    so the patch stays active until the test finishes.
    """
    with patch(
        "custom_components.powerdog.client.xmlrpc.client.ServerProxy",
        return_value=server_mock,
    ):
        instance = PowerDogClient("192.0.2.10", "secret", port=20000)
        yield instance


class TestParseSetable:
    """Cover the static Setable parser."""

    def test_onoff_value(self) -> None:
        params = PowerDogClient.parse_setable(
            "setRegulationParameter:onoff(bool),value(double)"
        )
        assert params == {"onoff": "bool", "value": "double"}

    def test_manual_value(self) -> None:
        params = PowerDogClient.parse_setable(
            "setRegulationParameter:manual(bool),value(double)"
        )
        assert params == {"manual": "bool", "value": "double"}

    def test_empty_string(self) -> None:
        assert PowerDogClient.parse_setable("") == {}

    def test_without_method_prefix(self) -> None:
        params = PowerDogClient.parse_setable("manual(bool),value(double)")
        assert params == {"manual": "bool", "value": "double"}

    def test_ignores_garbage_segments(self) -> None:
        params = PowerDogClient.parse_setable(
            "setRegulationParameter:onoff(bool),garbage,value(double)"
        )
        assert params == {"onoff": "bool", "value": "double"}


class TestCallWithRetry:
    """Cover transport handling, retries and error propagation."""

    def test_returns_reply_on_success(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.someMethod.return_value = {
            "ErrorCode": 0,
            "Reply": {"value": 1},
        }
        result = client._call_with_retry("someMethod", "arg")
        assert result == {"ErrorCode": 0, "Reply": {"value": 1}}
        server_mock.someMethod.assert_called_once_with("arg")

    def test_raises_powerdog_error_after_retries(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.brokenMethod.side_effect = xmlrpc.client.ProtocolError(
            "url", 500, "boom", {}
        )
        with patch("custom_components.powerdog.client.time.sleep"):
            with pytest.raises(PowerDogError):
                client._call_with_retry("brokenMethod", retries=3)
        assert server_mock.brokenMethod.call_count == 3

    def test_resets_connection_after_transport_error(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        # First attempt raises, second succeeds — server proxy must be rebuilt.
        server_mock.flaky.side_effect = [
            ConnectionError("kaboom"),
            {"ErrorCode": 0, "Reply": "ok"},
        ]
        with patch("custom_components.powerdog.client.time.sleep"), patch.object(
            client, "_connect", wraps=client._connect
        ) as connect_spy:
            result = client._call_with_retry("flaky")
        assert result["Reply"] == "ok"
        assert connect_spy.called

    def test_non_zero_error_code_retries(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.willFail.return_value = {
            "ErrorCode": 7,
            "ErrorString": "nope",
        }
        with patch("custom_components.powerdog.client.time.sleep"):
            with pytest.raises(PowerDogError) as err:
                client._call_with_retry("willFail", retries=2)
        assert "ErrorCode=7" in str(err.value)


class TestSetters:
    """Cover the typed setter helpers."""

    def test_set_regulation_value_uses_value_param(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.setRegulationParameter.return_value = {"ErrorCode": 0}
        assert client.set_regulation_value("regulation_1", 42) is True
        server_mock.setRegulationParameter.assert_called_once_with(
            "secret", "regulation_1", "value", "42"
        )

    def test_set_regulation_onoff_serialises_bool(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.setRegulationParameter.return_value = {"ErrorCode": 0}
        client.set_regulation_onoff("regulation_1", True)
        server_mock.setRegulationParameter.assert_called_once_with(
            "secret", "regulation_1", "onoff", "1"
        )

    def test_set_regulation_manual_serialises_bool(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.setRegulationParameter.return_value = {"ErrorCode": 0}
        client.set_regulation_manual("regulation_2", False)
        server_mock.setRegulationParameter.assert_called_once_with(
            "secret", "regulation_2", "manual", "0"
        )

    def test_set_regulation_parameter_propagates_error(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.setRegulationParameter.return_value = {
            "ErrorCode": 9,
            "ErrorString": "nope",
        }
        with patch("custom_components.powerdog.client.time.sleep"):
            with pytest.raises(PowerDogError):
                client.set_regulation_value("regulation_1", 1)


class TestGetters:
    """Cover the cached getters and the bulk reader."""

    def test_get_linear_devices_caches_result(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.getLinearDevices.return_value = {
            "ErrorCode": 0,
            "Reply": {"foo": {"Name": "Foo"}},
        }
        first = client.get_linear_devices()
        second = client.get_linear_devices()
        assert first == second
        # Single XML-RPC call regardless of how many times we call the helper.
        assert server_mock.getLinearDevices.call_count == 1

    def test_clear_cache_forces_refetch(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.getRegulations.return_value = {"ErrorCode": 0, "Reply": {}}
        client.get_regulations()
        client.clear_cache()
        client.get_regulations()
        assert server_mock.getRegulations.call_count == 2

    def test_get_all_current_values_raises_on_empty(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        server_mock.getAllCurrentLinearValues.return_value = {
            "ErrorCode": 0,
            "Reply": {},
        }
        with pytest.raises(PowerDogError):
            client.get_all_current_values()

    def test_get_current_values_chunks_keys(
        self, client: PowerDogClient, server_mock: MagicMock
    ) -> None:
        # Mock returns whatever is asked so we can verify chunking by call count.
        def fake(_password: str, keys: str):
            return {
                "ErrorCode": 0,
                "Reply": {key: {"Current_Value": "1"} for key in keys.split(",")},
            }

        server_mock.getCurrentLinearValues.side_effect = fake
        keys = [f"regulation_{i}" for i in range(45)]
        result = client.get_current_values(keys)
        # Chunk size is 20, so 45 keys -> 3 calls.
        assert server_mock.getCurrentLinearValues.call_count == 3
        assert len(result) == 45
