import asyncio
import logging
import xmlrpc.client

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN  # Hier wird DOMAIN aus const.py importiert

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Setze die Konfigurationsdatei ein (configuration.yaml)."""
    _LOGGER.debug("🔄 async_setup() in __init__.py wurde aufgerufen!")
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setze die Konfiguration über die UI ein."""
    _LOGGER.debug("🚀 async_setup_entry() wurde aufgerufen! Registriere Plattformen...")

    hub = PowerDogHub(
        hass,
        entry.data["host"],
        entry.data.get("port", 20000),
        entry.data["password"],
        entry.data.get("interval", 30)
    )

    await hub.async_fetch_data()
    hass.data[DOMAIN]["hub"] = hub

    # Starte das periodische Update
    hass.loop.create_task(hub.async_update_loop())

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "switch", "select", "number"])
    _LOGGER.debug("✅ Plattformen erfolgreich registriert!")
    return True


class PowerDogHub:
    """Verwaltet die Kommunikation mit der PowerDog API."""

    def __init__(self, hass: HomeAssistant, host: str, port: int, password: str, interval: int):
        """Initialisiere PowerDog API-Verbindung."""
        self.hass = hass
        self.host = host
        self.port = port
        self.password = password
        self.interval = interval
        self.client = xmlrpc.client.ServerProxy(f"http://{host}:{port}/")

        self.sensors = {}
        self.switches = {}
        self.selects = {}
        self.numbers = {}

    async def async_fetch_data(self):
        """Lade ALLE Sensordaten in separaten API-Requests."""
        _LOGGER.debug("📡 Hole Sensordaten von PowerDog API...")

        def fetch(method):
            """Synchrone API-Abfrage in separatem Thread."""
            try:
                response = getattr(self.client, method)(self.password)
                if response.get("ErrorCode") == 0:
                    return response.get("Reply", {})
                else:
                    _LOGGER.error(f"⚠️ Fehler bei API-Aufruf {method}: {response}")
                    return {}
            except Exception as e:
                _LOGGER.error(f"❌ PowerDog API-Fehler bei {method}: {e}")
                return {}

        # ❗ **Jetzt ALLE API-Methoden getrennt abrufen!**
        sensors_data = await asyncio.to_thread(fetch, "getSensors")
        counters_data = await asyncio.to_thread(fetch, "getCounters")
        regulations_data = await asyncio.to_thread(fetch, "getRegulations")
        linear_devices_data = await asyncio.to_thread(fetch, "getLinearDevices")

        all_data = {**sensors_data, **counters_data, **regulations_data, **linear_devices_data}

        if not all_data:
            _LOGGER.error("❌ API-Antwort ist leer!")
            return

        _LOGGER.debug(f"📊 API-Rohdaten geladen: {len(all_data)} Einträge")

        for entity_id, entity_info in all_data.items():
            key = entity_info.get("Key")  # Eindeutige Geräte-ID

            setable = entity_info.get("Setable", "")
            linear_type = entity_info.get("LinearType", "")

            if "onoff(bool)" in setable:
                self.switches[key] = entity_info
            if "manual(bool)" in setable:
                self.selects[key] = entity_info
            if "value(double)" in setable:
                self.numbers[key] = entity_info

            if not setable:
                self.sensors[key] = entity_info  # Standard-Sensor

            # Zusätzliche Zählerwerte nur für Counter speichern
            if linear_type == "counter":
                for usage_type in ["30Day_Usage", "Today_Usage", "Year_Usage"]:
                    if usage_type in entity_info:
                        usage_entity_id = f"{key}_{usage_type.lower()}"

                        if usage_entity_id not in self.sensors:
                            base_unit = entity_info.get("Unit", "W")
                            time_unit = entity_info.get("Unit_Time_Add", "")

                            if time_unit.lower() == "h":
                                correct_unit = base_unit + "h"  # z.B. "Wh", "kWh", "MWh"
                            else:
                                correct_unit = base_unit

                            self.sensors[usage_entity_id] = {
                                "Name": f"{entity_info.get('Name', 'Unknown')} {usage_type.replace('_', ' ')}",
                                "Current_Value": entity_info[usage_type],
                                "Unit": correct_unit,
                            }
            else:
                # log the entity info for debug purposes
                _LOGGER.debug(f"🔍 {entity_info.get('Name', key)}: {entity_info}")



        _LOGGER.debug(f"✅ PowerDog API-Daten geladen: {len(self.sensors)} Sensoren, {len(self.switches)} Switches, {len(self.numbers)} Numbers")

    async def async_update_loop(self):
        """Regelmäßige Aktualisierung der PowerDog API-Werte."""
        while True:
            _LOGGER.debug("🔄 PowerDog Update wurde getriggert.")
            await self.async_update_values()
            await asyncio.sleep(self.interval)  # Alle 60 Sekunden abrufen

    async def async_update_values(self):
        """Holt aktuelle Werte von PowerDog und speichert sie."""
        _LOGGER.debug("📡 Rufe aktuelle Werte über getAllCurrentLinearValues ab...")

        def fetch():
            """Synchrone API-Abfrage für aktuelle Werte."""
            try:
                response = self.client.getAllCurrentLinearValues(self.password)
                if isinstance(response, dict) and response.get("ErrorCode") == 0:
                    return response.get("Reply", {})
                else:
                    _LOGGER.error(f"⚠️ Fehlerhafte Antwort von getAllCurrentLinearValues: {response}")
                    return {}
            except Exception as e:
                _LOGGER.error(f"❌ Fehler beim Abrufen der aktuellen Werte: {e}")
                return {}

        values = await asyncio.to_thread(fetch)

        if not values:
            _LOGGER.warning("⚠️ Keine aktuellen Werte erhalten.")
            return

        _LOGGER.debug(f"📊 {len(values)} aktuelle Werte von PowerDog erhalten.")

        # Setze die aktuellen Werte in den Entitäten
        for entity_id, value_data in values.items():
            current_value = value_data.get("Current_Value")

            if entity_id in self.sensors:
                self.sensors[entity_id]["Current_Value"] = current_value
            if entity_id in self.switches:
                self.switches[entity_id]["Current_Value"] = current_value
            if entity_id in self.numbers:
                self.numbers[entity_id]["Current_Value"] = current_value
            if entity_id in self.selects:
                self.selects[entity_id]["Current_Value"] = current_value

            # Falls es ein Counter ist, auch die Usage-Werte aktualisieren
            if entity_id in self.sensors and self.sensors[entity_id].get("LinearType") == "counter":
                for usage_type in ["30Day_Usage", "Today_Usage", "Year_Usage"]:
                    usage_entity_id = f"{entity_id}_{usage_type.lower()}"
                    if usage_entity_id in self.sensors:
                        self.sensors[usage_entity_id]["Current_Value"] = value_data.get(usage_type, 0)

        _LOGGER.debug("✅ PowerDog Werte erfolgreich aktualisiert!")