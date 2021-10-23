"""Platform for sensor integration."""
import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

from homeassistant.components.sensor import (
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_MONETARY,
    STATE_CLASS_MEASUREMENT,
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
    # pylint: disable=too-many-locals
    new_entities = []

    cost_classifiers = [
        "gas.consumption.cost",
        "electricity.consumption.cost",
    ]
    meter_classifiers = [
        "gas.consumption",
        "electricity.consumption",
    ]

    for entry in hass.data[DOMAIN]:
        glow = hass.data[DOMAIN][entry]

        resources: dict = {}
        meters = {}

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
            if resource["classifier"] in meter_classifiers:
                base_sensor = GlowUsage(glow, resource, config)
                new_entities.append(base_sensor)
                meters[resource["classifier"]] = base_sensor

                cumulative_sensor = GlowCumulative(glow, resource, config)
                new_entities.append(cumulative_sensor)

                rate_sensor = GlowStanding(glow, resource, config)
                new_entities.append(rate_sensor)
                tariff_sensor = GlowRate(glow, resource, config, rate_sensor)
                new_entities.append(tariff_sensor)

        for resource in resources:
            if resource["classifier"] in cost_classifiers:
                sensor = GlowUsage(glow, resource, config)
                if resource["classifier"] == "gas.consumption.cost":
                    sensor.meter = meters["gas.consumption"]
                else:
                    sensor.meter = meters["electricity.consumption"]
                new_entities.append(sensor)

        async_add_entities(new_entities)

    return True


class GlowUsage(SensorEntity):
    """Sensor object for the Glowmarkt resource's current consumption."""

    def __init__(self, glow: Glow, resource: Dict[str, Any], config: ConfigEntry):
        """Initialize the sensor."""
        self._attr_state_class = STATE_CLASS_TOTAL_INCREASING
        self._state: Optional[Dict[str, Any]] = None
        self.glow = glow
        self.resource = resource
        self.config = config
        self.meter = None

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
        if self.device_class == DEVICE_CLASS_MONETARY:
            icon = "mdi:cash"

        return icon

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return information about the sensor data source."""
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "ELEC":
            human_type = "Electricity"
        elif self.resource["dataSourceResourceTypeInfo"]["type"] == "GAS":
            human_type = "Gas"
        else:
            _err = self.resource["dataSourceResourceTypeInfo"]["type"]
            _LOGGER.debug("Unknown type: %s", _err)

        if self.meter:
            resource = self.meter.resource["resourceId"]
        else:
            resource = self.resource["resourceId"]

        return {
            "identifiers": {(DOMAIN, resource)},
            "manufacturer": "Hildebrand",
            "model": "Glow",
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
        if self._state is not None:
            try:
                res = self._state["data"][0][1]
                if self._state["units"] == "pence":
                    res = float(res) / 100.0
                    return round(res, 2)
                return round(res, 3)
            except (KeyError, IndexError, TypeError) as _error:
                _LOGGER.error("Lookup Error - data (%s): (%s)",
                              _error, self._state)
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

    async def _glow_update(self, func: Callable) -> None:
        """Get updated data from Glow"""
        try:
            self._state = await self.hass.async_add_executor_job(
                func, self.resource["resourceId"]
            )
        except InvalidAuth:
            _LOGGER.debug("calling auth failed 2")
            await Glow.handle_failed_auth(self.config, self.hass)

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        await self._glow_update(self.glow.current_usage)


class GlowCumulative(GlowUsage):
    """Sensor object for the Glowmarkt resource's current yearly consumption."""

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        return self.resource["resourceId"] + "-cumulative"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            return "Gas Consumption (Year)"
        if self.resource["classifier"] == "electricity.consumption":
            return "Electric Consumption (Year)"
        return None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        await self._glow_update(self.glow.cumulative_usage)


class GlowStanding(GlowUsage):
    """Sensor object for the Glowmarkt resource's standing tariff."""

    def __init__(self, glow: Glow, resource: Dict[str, Any], config: ConfigEntry):
        """Initialize the sensor."""
        super().__init__(glow, resource, config)
        self._attr_state_class = STATE_CLASS_MEASUREMENT

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
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        plan = None
        if self._state is not None:
            try:
                plan = self._state["data"][0]["currentRates"]
                standing = plan["standingCharge"]
                standing = float(standing) / 100
                return standing

            except (KeyError, IndexError, TypeError) as _error:
                if plan is None:
                    _LOGGER.error("Lookup Error - plan (%s): (%s)",
                                  _error, self._state)
                else:
                    _LOGGER.error(
                        "Lookup Error - standing (%s): (%s)", _error, plan)
                return None

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
        await self._glow_update(self.glow.current_tariff)


class GlowRate(GlowStanding):
    """Sensor object for the Glowmarkt resource's current unit tariff."""

    def __init__(
        self,
        glow: Glow,
        resource: Dict[str, Any],
        config: ConfigEntry,
        buddy: GlowStanding,
    ):
        """Initialize the sensor."""
        super().__init__(glow, resource, config)

        self.buddy = buddy

    @property
    def unique_id(self) -> str:
        """Return a unique identifier string for the sensor."""
        return self.resource["resourceId"] + "-rate"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.resource["classifier"] == "gas.consumption":
            return "Gas Tariff Rate"

        if self.resource["classifier"] == "electricity.consumption":
            return "Electric Tariff Rate"

        return None

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        return "GBP/kWh"

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        plan = None
        if self._state is not None:
            try:
                plan = self._state["data"][0]["currentRates"]
                rate = plan["rate"]
                rate = float(rate) / 100

                return round(rate, 4)

            except (KeyError, IndexError, TypeError) as _error:
                if plan is None:
                    _LOGGER.error("Key Error - plan (%s): (%s)",
                                  _error, self._state)
                else:
                    _LOGGER.error("Key Error - rate (%s): (%s)", _error, plan)
                return None

        return None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        self._state = self.buddy.rawdata
