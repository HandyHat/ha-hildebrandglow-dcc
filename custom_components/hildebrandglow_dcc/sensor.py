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
from homeassistant.const import ENERGY_KILO_WATT_HOUR, VOLUME_CUBIC_METERS
from homeassistant.core import HomeAssistant

from .const import DEFAULT_CALORIFIC_VALUE, DEFAULT_VOLUME_CORRECTION, DOMAIN
from .glow import Glow, InvalidAuth

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=2)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: Callable
) -> bool:
    """Set up the sensor platform."""
    new_entities = []

    known_classifiers = [
        "gas.consumption",
        "electricity.consumption",
        "gas.consumption.cost",
        "electricity.consumption.cost",
    ]
    tariff_classifiers = [
        "gas.consumption",
        "electricity.consumption",
    ]

    for entry in hass.data[DOMAIN]:
        glow = hass.data[DOMAIN][entry]

        resources: dict = {}

        try:
            resources = await hass.async_add_executor_job(glow.retrieve_resources)
        except InvalidAuth:
            try:
                _LOGGER.debug("calling auth failed")
                await Glow.handle_failed_auth(config, hass)
            except InvalidAuth:
                return False

            glow = hass.data[DOMAIN][entry]
            resources = await hass.async_add_executor_job(glow.retrieve_resources)

        for resource in resources:
            if resource["classifier"] in known_classifiers:
                base_sensor = GlowConsumptionCurrent(glow, resource, config)
                new_entities.append(base_sensor)

                if resource["classifier"] in tariff_classifiers:
                    rate_sensor = GlowTariff(glow, resource, config)
                    new_entities.append(rate_sensor)
                    tariff_sensor = GlowTariffRate(
                        glow, resource, config, rate_sensor, False
                    )
                    new_entities.append(tariff_sensor)

                if resource["classifier"] == "gas.consumption":
                    m3sensor = GlowConsumptionCurrentMetric(
                        glow, resource, config, base_sensor
                    )
                    new_entities.append(m3sensor)

                    t3sensor = GlowTariffRate(glow, resource, config, rate_sensor, True)
                    new_entities.append(t3sensor)

        async_add_entities(new_entities)

    return True


class GlowConsumptionCurrent(SensorEntity):

    """Sensor object for the Glowmarkt resource's current consumption."""

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
        if self.resource["classifier"] == "electricity.consumption.cost":
            return "Electric Cost (Today)"
        if self.resource["classifier"] == "gas.consumption.cost":
            return "Gas Cost (Today)"

        return None

    @property
    def icon(self) -> Optional[str]:
        """Icon to use in the frontend, if any."""
        icon = ""
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "ELEC":
            icon = "mdi:flash"
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "GAS":
            icon = "mdi:fire"
        if self.resource["baseUnit"] == "pence":
            icon = "mdi:cash"
        return icon

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
    def device_class(self) -> str:
        """Return the device class."""
        if self._state is not None and self._state["units"] == "kWh":
            return DEVICE_CLASS_ENERGY
        if self._state is not None and self._state["units"] == "pence":
            return DEVICE_CLASS_MONETARY
        return None

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self._state:
            try:
                if self._state["units"] == "pence":
                    return self._state["data"][0][1] / 100.0
                return self._state["data"][0][1]
            except (KeyError, IndexError, TypeError):
                _LOGGER.error("Lookup Error - data (%s)", self._state)
                return None
        return None

    @property
    def rawdata(self) -> Optional[str]:
        """Return the raw state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self._state is not None and self._state["units"] == "kWh":
            return ENERGY_KILO_WATT_HOUR
        if self._state is not None and self._state["units"] == "pence":
            return "GBP"
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
            _LOGGER.debug("calling auth failed 2")
            await Glow.handle_failed_auth(self.config, self.hass)


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

        correction = DEFAULT_VOLUME_CORRECTION
        calorific = DEFAULT_CALORIFIC_VALUE

        if "correction" in config.data:
            correction = config.data["correction"]
        if "calorific" in config.data:
            calorific = config.data["calorific"]
        self.conversion = 3.6 / correction / calorific

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        return self.resource["resourceId"] + "-metric"

    @property
    def device_class(self) -> str:
        """Return the device class (always DEVICE_CLASS_GAS)."""
        return DEVICE_CLASS_GAS

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self._state is not None:
            return VOLUME_CUBIC_METERS
        return None

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        kwh = self.buddy.state
        if kwh:
            return kwh * self.conversion
        return None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Gas Consumption Metric (Today)"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor. - read from Buddy"""
        self._state = self.buddy.rawdata


class GlowTariff(SensorEntity):
    """Sensor object for the Glowmarkt resource's standing tariff."""

    def __init__(self, glow: Glow, resource: Dict[str, Any], config: ConfigEntry):
        """Initialize the sensor."""
        self._state: Optional[Dict[str, Any]] = None
        self.glow = glow
        self.resource = resource
        self.config = config

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        return self.resource["resourceId"] + "-tariff"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            return "Gas Tariff Standing"

        if self.resource["classifier"] == "electricity.consumption":
            return "Electric Tariff Standing"

        return None

    @property
    def icon(self) -> Optional[str]:
        """Icon to use in the frontend, if any."""
        return "mdi:currency-gbp"

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        plan = None
        if self._state:
            try:
                plan = self._state["data"][0]["currentRates"]
                standing = plan["standingCharge"]
                standing = standing / 100
                return standing

            except KeyError:
                if plan is None:
                    _LOGGER.error("Lookup Error - plan (%s)", self._state)
                else:
                    _LOGGER.error("Lookup Error - standing (%s)", plan)
                return None

        return None

    @property
    def rawdata(self) -> Optional[str]:
        """Return the raw state of the sensor."""
        return self._state

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
            _LOGGER.debug("calling auth failed 2")
            await Glow.handle_failed_auth(self.config, self.hass)


class GlowTariffRate(GlowTariff):
    """Sensor object for the Glowmarkt resource's current unit tariff."""

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
            correction = DEFAULT_VOLUME_CORRECTION
            calorific = DEFAULT_CALORIFIC_VALUE

            if "correction" in config.data:
                correction = config.data["correction"]
            if "calorific" in config.data:
                calorific = config.data["calorific"]
            self.conversion = 3.6 / correction / calorific

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        if self.metric:
            return self.resource["resourceId"] + "-rate-metric"
        return self.resource["resourceId"] + "-rate"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            if self.metric:
                return "Gas Tariff Rate (Metric)"
            return "Gas Tariff Rate"

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
        plan = None
        if self._state:
            try:
                plan = self._state["data"][0]["currentRates"]
                rate = plan["rate"]
                rate = rate / 100
                if self.metric:
                    rate = rate / self.conversion

                return rate

            except (KeyError, IndexError, TypeError):
                if plan is None:
                    _LOGGER.error("Key Error - plan (%s)", self._state)
                else:
                    _LOGGER.error("Key Error - rate (%s)", rate)
                return None

        return None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._state = self.buddy.rawdata
