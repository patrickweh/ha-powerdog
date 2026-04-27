"""Shared test constants and sample API payloads."""
from __future__ import annotations

from typing import Any

DEVICE_INFO: dict[str, str] = {
    "SerialNumber": "TEST-0001",
    "HardwareRevision": "Test",
    "FullVersion": "1.0.0",
    "Version": "1.0.0",
}

REGULATIONS: dict[str, dict[str, Any]] = {
    # ManualValue: settable via onoff(bool)/value(double)
    "regulation_1": {
        "Name": "q-H 0-100%",
        "Hardware": "ManualValue",
        "Setable": "setRegulationParameter:onoff(bool),value(double)",
        "Type": "Percent",
        "Unit": "%",
        "Min": "0",
        "Max": "100",
        "Current_Value": "0",
        "OnOff": "0",
        "Valid": True,
    },
    # ManualAutoSwitch: settable via manual(bool)/value(double)
    "regulation_2": {
        "Name": "Pumpe q-H H/A",
        "Hardware": "ManualAutoSwitch",
        "Setable": "setRegulationParameter:manual(bool),value(double)",
        "Type": "Percent",
        "Unit": "%",
        "Min": "0",
        "Max": "100",
        "Current_Value": "0",
        "SwitchMode": "0",
        "SwitchState": "0",
        "Valid": True,
    },
    # ManualValue with non-percent range (PV surplus threshold)
    "regulation_3": {
        "Name": "Ueberschuss PV",
        "Hardware": "ManualValue",
        "Setable": "setRegulationParameter:onoff(bool),value(double)",
        "Type": "Energy",
        "Unit": "W",
        "Min": "0",
        "Max": "7000",
        "Current_Value": "250",
        "OnOff": "1",
        "Valid": True,
    },
    # Non-setable regulation -> exposed as sensor
    "regulation_4": {
        "Name": "q-Hybrid",
        "Hardware": "AnalogPIDRegulator",
        "Setable": "",
        "Type": "Percent",
        "Unit": "%",
        "Max": "100",
        "Current_Value": "42",
        "Valid": True,
    },
}

SENSORS: dict[str, dict[str, Any]] = {
    "remotesensor_1": {
        "Name": "Puffer oben",
        "Type": "Temperature",
        "Unit": "°C",
        "Current_Value": "55",
        "Valid": True,
    },
}

COUNTERS: dict[str, dict[str, Any]] = {
    "buscounter_1": {
        "Name": "Quantum",
        "Type": "Energy",
        "Unit": "W",
        "Unit_Time_Add": "h",
        "Current_Value": "0",
        "Today_Usage": "1234",
        "30Day_Usage": "5678",
        "Year_Usage": "98765",
        "Valid": True,
    },
}

LINEAR_DEVICES: dict[str, dict[str, Any]] = {}

CURRENT_VALUES: dict[str, dict[str, Any]] = {
    **{key: dict(value) for key, value in REGULATIONS.items()},
    **{key: dict(value) for key, value in SENSORS.items()},
    **{key: dict(value) for key, value in COUNTERS.items()},
}
