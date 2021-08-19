"""Platform for sensor integration."""
from datetime import datetime, time, timedelta
from typing import Any, Callable, Dict, Optional

import pytz
from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .glow import Glow, InvalidAuth

SCAN_INTERVAL = timedelta(minutes=2)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: Callable
) -> bool:
    """Set up the sensor platform."""
    new_entities = []

    for entry in hass.data[DOMAIN]:
        glow = hass.data[DOMAIN][entry]

        resources: dict = {}

        try:
            resources = await hass.async_add_executor_job(glow.retrieve_resources)
        except InvalidAuth:
            try:
                await Glow.handle_failed_auth(config, hass)
            except InvalidAuth:
                return False

            glow = hass.data[DOMAIN][entry]
            resources = await hass.async_add_executor_job(glow.retrieve_resources)
        for resource in resources:
            if resource["classifier"] in GlowConsumptionCurrent.knownClassifiers:
                sensor = GlowConsumptionCurrent(glow, resource)
                new_entities.append(sensor)

        async_add_entities(new_entities)

    return True


class GlowConsumptionCurrent(SensorEntity):
    """Sensor object for the Glowmarkt resource's current consumption."""

    hass: HomeAssistant

    knownClassifiers = ["gas.consumption", "electricity.consumption"]

    available = True

    _attr_state_class = STATE_CLASS_TOTAL_INCREASING

    def __init__(self, glow: Glow, resource: Dict[str, Any]):
        """Initialize the sensor."""
        self._state: Optional[Dict[str, Any]] = None
        self.glow = glow
        self.resource = resource

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        return self.resource["resourceId"]

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            return "Gas Consumption (Today)"
        if self.resource["classifier"] == "electricity.consumption":
            return "Electric Consumption (Today)"

    @property
    def icon(self) -> Optional[str]:
        """Icon to use in the frontend, if any."""
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "ELEC":
            return "mdi:flash"
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "GAS":
            return "mdi:fire"
        return None

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return information about the sensor data source."""
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "ELEC":
            human_type = "Electricity"
        elif self.resource["dataSourceResourceTypeInfo"]["type"] == "GAS":
            human_type = "Gas"

        return {
            "identifiers": {(DOMAIN, self.resource["resourceId"])},
            "name": f"Smart {human_type} Meter",
        }

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self._state:
            return self._state["data"][0][1]
        return None

    @property
    def device_class(self) -> str:
        """Return the device class (always DEVICE_CLASS_ENERGY)."""
        return DEVICE_CLASS_ENERGY

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self._state is not None and self._state["units"] == "kWh":
            return ENERGY_KILO_WATT_HOUR
        return None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            self._state = await self.hass.async_add_executor_job(
                self.glow.current_usage, self.resource["resourceId"]
            )
        except InvalidAuth:
            Glow.handle_failed_auth(ConfigEntry, HomeAssistant)
