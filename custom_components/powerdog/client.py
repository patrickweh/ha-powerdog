"""PowerDog XML-RPC client."""
import logging
import re
import socket
import time
import xmlrpc.client
import threading
from typing import Any, Dict, List, Optional, Union

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
SET_VERIFY_DELAY = 0.5


class PowerDogError(Exception):
    """Raised when PowerDog API returns an error or cannot be reached."""


class _TimeoutTransport(xmlrpc.client.Transport):
    """XML-RPC transport with a configurable socket timeout."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._timeout = timeout

    def make_connection(self, host):
        connection = super().make_connection(host)
        connection.timeout = self._timeout
        return connection


class PowerDogClient:
    """PowerDog XML-RPC client."""

    def __init__(self, host: str, password: str, port: int = 20000, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the PowerDog client."""
        self.host = host
        self.password = password
        self.port = port
        self.timeout = timeout
        self.server_url = f"http://{host}:{port}"
        self.server: Optional[xmlrpc.client.ServerProxy] = None
        self._lock = threading.Lock()
        self._connect()

        # Cache for device definitions to reduce API calls
        self._devices_cache: Optional[Dict] = None
        self._sensors_cache: Optional[Dict] = None
        self._counters_cache: Optional[Dict] = None
        self._regulations_cache: Optional[Dict] = None

    def _connect(self) -> None:
        """Connect to the PowerDog server."""
        try:
            transport = _TimeoutTransport(timeout=self.timeout)
            self.server = xmlrpc.client.ServerProxy(self.server_url, transport=transport, allow_none=True)
            _LOGGER.debug("Connected to PowerDog server at %s", self.server_url)
        except Exception as e:
            _LOGGER.error("Failed to connect to PowerDog server: %s", e)
            self.server = None

    def _call_with_retry(self, method: str, *args: Any, retries: int = 3) -> Dict:
        """Call a method with retry and connection handling.

        Returns the parsed result dict on success. Raises PowerDogError on
        any unrecoverable failure (no silent fallbacks).
        """
        with self._lock:
            last_error: Optional[BaseException] = None
            for attempt in range(1, retries + 1):
                try:
                    if self.server is None:
                        self._connect()
                        if self.server is None:
                            last_error = PowerDogError("not connected")
                            continue

                    func = getattr(self.server, method)
                    result = func(*args)

                    if isinstance(result, dict) and "ErrorCode" in result:
                        if result["ErrorCode"] == 0:
                            _LOGGER.debug("PowerDog %s ok (attempt %d)", method, attempt)
                            return result
                        last_error = PowerDogError(
                            f"{method} returned ErrorCode={result['ErrorCode']} "
                            f"ErrorString={result.get('ErrorString', '')}"
                        )
                        _LOGGER.warning(
                            "PowerDog %s error (attempt %d/%d): %s",
                            method, attempt, retries, last_error,
                        )
                    else:
                        return result if isinstance(result, dict) else {"Reply": result, "ErrorCode": 0}

                except (xmlrpc.client.ProtocolError, xmlrpc.client.Fault, ConnectionError, socket.timeout, OSError) as e:
                    last_error = e
                    _LOGGER.warning(
                        "PowerDog %s transport error (attempt %d/%d): %s",
                        method, attempt, retries, e,
                    )
                    self.server = None
                except Exception as e:
                    last_error = e
                    _LOGGER.warning(
                        "PowerDog %s unexpected error (attempt %d/%d): %s",
                        method, attempt, retries, e,
                    )
                    self.server = None

                if attempt < retries:
                    time.sleep(0.3 * attempt)

            raise PowerDogError(f"All {retries} attempts to call {method} failed: {last_error}")

    def get_powerdog_info(self) -> Dict[str, str]:
        """Get PowerDog device information."""
        try:
            result = self._call_with_retry("getDeviceInfo", self.password)
            return result.get("Reply", {}) or {
                "SerialNumber": f"PowerDog-{self.host}",
                "HardwareRevision": "PowerDog",
                "FullVersion": "Unknown",
                "Version": "Unknown",
            }
        except PowerDogError as e:
            _LOGGER.error("Error getting device info: %s", e)
            return {
                "SerialNumber": f"PowerDog-{self.host}",
                "HardwareRevision": "PowerDog",
                "FullVersion": "Unknown",
                "Version": "Unknown",
            }

    def get_linear_devices(self) -> Dict:
        """Get all linear devices from PowerDog."""
        if self._devices_cache is None:
            result = self._call_with_retry("getLinearDevices", self.password)
            self._devices_cache = result.get("Reply", {}) or {}
        return self._devices_cache

    def get_sensors(self) -> Dict:
        """Get all sensors from PowerDog."""
        if self._sensors_cache is None:
            result = self._call_with_retry("getSensors", self.password)
            self._sensors_cache = result.get("Reply", {}) or {}
        return self._sensors_cache

    def get_counters(self) -> Dict:
        """Get all counters from PowerDog."""
        if self._counters_cache is None:
            result = self._call_with_retry("getCounters", self.password)
            self._counters_cache = result.get("Reply", {}) or {}
        return self._counters_cache

    def get_regulations(self) -> Dict:
        """Get all regulations from PowerDog."""
        if self._regulations_cache is None:
            result = self._call_with_retry("getRegulations", self.password)
            self._regulations_cache = result.get("Reply", {}) or {}
        return self._regulations_cache

    def clear_cache(self) -> None:
        """Clear all cached device definitions."""
        self._devices_cache = None
        self._sensors_cache = None
        self._counters_cache = None
        self._regulations_cache = None

    def get_all_current_values(self) -> Dict:
        """Get current values for all devices."""
        result = self._call_with_retry("getAllCurrentLinearValues", self.password)
        reply = result.get("Reply", {}) or {}
        if not reply:
            raise PowerDogError("getAllCurrentLinearValues returned empty Reply")
        return reply

    def get_current_values(self, keys: List[str]) -> Dict:
        """Get current values for specific devices."""
        if not keys:
            return {}

        chunk_size = 20
        all_values: Dict = {}

        for i in range(0, len(keys), chunk_size):
            chunk_keys = keys[i:i + chunk_size]
            keys_str = ",".join(chunk_keys)
            result = self._call_with_retry("getCurrentLinearValues", self.password, keys_str)
            reply = result.get("Reply", {}) or {}
            all_values.update(reply)

        return all_values

    def set_linear_sensor_value(self, key: str, value: Union[int, float, str]) -> bool:
        """Set a value for a PowerDog Sensor."""
        try:
            self._call_with_retry("setLinearSensorDevice", self.password, key, str(value))
            return True
        except PowerDogError as e:
            _LOGGER.error("Error setting sensor value for %s: %s", key, e)
            raise

    def set_linear_counter_value(
        self, key: str, value: Union[int, float, str], meter_reading: Union[int, float, str]
    ) -> bool:
        """Set a value for a PowerDog Counter."""
        try:
            self._call_with_retry(
                "setLinearCounterDevice", self.password, key, str(value), str(meter_reading)
            )
            return True
        except PowerDogError as e:
            _LOGGER.error("Error setting counter value for %s: %s", key, e)
            raise

    def set_regulation_parameter(self, key: str, parameter: str, value: Union[int, float, str, bool]) -> bool:
        """Set an arbitrary parameter on a PowerDog Regulation.

        Raises PowerDogError on failure. Returns True on success.
        """
        if isinstance(value, bool):
            payload = "1" if value else "0"
        else:
            payload = str(value)

        _LOGGER.debug(
            "PowerDog set %s parameter=%s value=%s", key, parameter, payload,
        )
        self._call_with_retry("setRegulationParameter", self.password, key, parameter, payload)
        return True

    def set_regulation_value(self, key: str, value: Union[int, float, str]) -> bool:
        """Set the 'value' parameter on a PowerDog Regulation (the percentage)."""
        return self.set_regulation_parameter(key, "value", value)

    def set_regulation_onoff(self, key: str, on: bool) -> bool:
        """Set the 'onoff' parameter on a ManualValue regulation."""
        return self.set_regulation_parameter(key, "onoff", bool(on))

    def set_regulation_manual(self, key: str, on: bool) -> bool:
        """Set the 'manual' parameter on a ManualSwitch / ManualAutoSwitch regulation."""
        return self.set_regulation_parameter(key, "manual", bool(on))

    @staticmethod
    def parse_setable(setable: str) -> Dict[str, str]:
        """Parse a regulation Setable string into {param_name: type}.

        Examples::

            "setRegulationParameter:onoff(bool),value(double)"
              -> {"onoff": "bool", "value": "double"}
            "setRegulationParameter:manual(bool),value(double)"
              -> {"manual": "bool", "value": "double"}
        """
        if not setable:
            return {}
        if ":" in setable:
            _, _, params_str = setable.partition(":")
        else:
            params_str = setable
        params: Dict[str, str] = {}
        for part in params_str.split(","):
            part = part.strip()
            match = re.match(r"^(\w+)\(([^)]+)\)$", part)
            if match:
                params[match.group(1)] = match.group(2)
        return params

    def reset_connection(self) -> None:
        """Reset the connection to the PowerDog server."""
        self.server = None
        self._connect()
