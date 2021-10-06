"""Platform for sensor integration."""
import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_MONETARY,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .glow import Glow, InvalidAuth

_LOGGER = logging.getLogger(__name__)

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
                _LOGGER.error("calling auth failed")
                await Glow.handle_failed_auth(config, hass)
            except InvalidAuth:
                return False

            glow = hass.data[DOMAIN][entry]
            resources = await hass.async_add_executor_job(glow.retrieve_resources)
        for resource in resources:
            if resource["classifier"] in GlowConsumptionCurrent.knownClassifiers:
                sensor = GlowConsumptionCurrent(glow, resource, config)
                new_entities.append(sensor)
                if resource["classifier"] == "gas.consumption":
                    buddysensor = GlowConsumptionCurrentMetric(
                        glow, resource, config, sensor
                    )
                    new_entities.append(buddysensor)

                sensor = GlowTariff(glow, resource, config)
                new_entities.append(sensor)
                buddysensor = GlowTariffRate(glow, resource, config, sensor, False)
                new_entities.append(buddysensor)
                buddysensor = GlowTariffRate(glow, resource, config, sensor, True)
                new_entities.append(buddysensor)

        async_add_entities(new_entities)

    return True


class GlowConsumptionCurrent(SensorEntity):

    """Sensor object for the Glowmarkt resource's current consumption."""

    hass: HomeAssistant

    knownClassifiers = ["gas.consumption", "electricity.consumption"]

    _attr_state_class = STATE_CLASS_TOTAL_INCREASING

    def __init__(self, glow: Glow, resource: Dict[str, Any], config: ConfigEntry):
        """Initialize the sensor."""
        self._state: Optional[Dict[str, Any]] = None
        self.glow = glow
        self.resource = resource
        self.config = config

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

        return None

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
        if self.resource["classifier"] == "gas.consumption":
            return DEVICE_CLASS_GAS
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
            _LOGGER.error("calling auth failed 2")
            Glow.handle_failed_auth(self.config, self.hass)


class GlowConsumptionCurrentMetric(GlowConsumptionCurrent):
    """Metric version of the sensor."""

    def __init__(
        self,
        glow: Glow,
        resource: Dict[str, Any],
        config: ConfigEntry,
        buddy: GlowConsumptionCurrent,
    ):
        """Initialize the sensor."""
        super().__init__(glow, resource, config)
        
        self.buddy = buddy

        self.conversion_factor = 1
        if "correction" in config and "calorific" in config:
            self.conversion = 3.6 / self.correction / self.calorific

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Gas Consumption Metric (Today)"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor. - read from Buddy"""
        kwh = self.buddy._state
        self._state = kwh * self.conversion


class GlowTariff(SensorEntity):

    """Sensor object for the Glowmarkt resource's standing tariff."""

    hass: HomeAssistant

    knownClassifiers = ["gas.consumption", "electricity.consumption"]

    def __init__(self, glow: Glow, resource: Dict[str, Any], config: ConfigEntry):
        """Initialize the sensor."""
        self._state: Optional[Dict[str, Any]] = None
        self.glow = glow
        self.resource = resource
        self.config = config

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        return self.resource["resourceId"]

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            return "Gas Price Standing"

        if self.resource["classifier"] == "electricity.consumption":
            return "Electric Price Standing"

        return None

    @property
    def icon(self) -> Optional[str]:
        """Icon to use in the frontend, if any."""
        return "mdi:GBP"

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self._state:
            """ TODO - add error checking """
            return self._state["data"][0]["structure"][0]["PlanDetail"][0]["standing"]
        return None

    @property
    def device_class(self) -> str:
        """Return the device class."""
        return DEVICE_CLASS_MONETARY

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return "GBP/kWh"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        try:
            self._state = await self.hass.async_add_executor_job(
                self.glow.current_tariff, self.resource["resourceId"]
            )
        except InvalidAuth:
            _LOGGER.error("calling auth failed 2")
            Glow.handle_failed_auth(self.config, self.hass)


class GlowTariffRate(GlowTariff):
    """Sensor object for the Glowmarkt resource's current unit tariff."""

    hass: HomeAssistant

    knownClassifiers = ["gas.consumption", "electricity.consumption"]

    def __init__(
        self,
        glow: Glow,
        resource: Dict[str, Any],
        config: ConfigEntry,
        buddy: GlowTariff,
        metric: bool,
    ):
        """Initialize the sensor."""
        super().__init__(glow, resource, config)

        self.buddy = buddy
        self.metric = metric

        if metric:
            if "correction" in config and "calorific" in config:
                self.conversion = 3.6 / self.correction / self.calorific

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            if self.metric:
                return "Gas Price Rate (Metric)"
            return "Gas Price Rate"

        if self.resource["classifier"] == "electricity.consumption":
            return "Electric Rate"

        return None

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self.metric:
            return "GBP/m³"
        return "GBP/kWh"

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self._state:
            """ TODO - add error checking """
            return self._state["data"][0]["structure"][0]["PlanDetail"][0]["standing"]
        return None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        if self.metric:
            self._state = self.buddy._state / self.buddy.conversion
        else:
            self._state = self.buddy._state
