"""Platform for sensor integration."""
from typing import Any, Callable, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_POWER, POWER_WATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .config_flow import config_object
from .const import DOMAIN
from .glow import Glow, InvalidAuth


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities: Callable
) -> bool:
    """Set up the sensor platform."""
    new_entities = []

    async def handle_failed_auth(config: ConfigEntry, hass: HomeAssistant) -> None:
        glow_auth = await hass.async_add_executor_job(
            Glow.authenticate,
            config.data["app_id"],
            config.data["username"],
            config.data["password"],
        )

        current_config = dict(config.data.copy())
        new_config = config_object(current_config, glow_auth)
        hass.config_entries.async_update_entry(entry=config, data=new_config)

        glow = Glow(config.data["app_id"], glow_auth["token"])
        hass.data[DOMAIN][config.entry_id] = glow

    for entry in hass.data[DOMAIN]:
        glow = hass.data[DOMAIN][entry]

        resources: dict = dict()

        try:
            resources = await hass.async_add_executor_job(glow.retrieve_resources)
        except InvalidAuth:
            try:
                await handle_failed_auth(config, hass)
            except InvalidAuth:
                return False

            glow = hass.data[DOMAIN][entry]
            resources = await hass.async_add_executor_job(glow.retrieve_resources)
        for resource in resources:
            if resource["resourceTypeId"] in GlowConsumptionCurrent.resourceTypeId:
                sensor = GlowConsumptionCurrent(glow, resource)
                new_entities.append(sensor)

    async_add_entities([sensor])

    return True


class GlowConsumptionCurrent(Entity):
    """Sensor object for the Glowmarkt resource's current consumption."""

    hass: HomeAssistant

    resourceTypeId = [
        "ea02304a-2820-4ea0-8399-f1d1b430c3a0",  # Smart Meter, electricity consumption
        "672b8071-44ff-4f23-bca2-f50c6a3ddd02",  # Smart Meter, gas consumption
    ]

    available = True

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
        return self.resource["label"]

    @property
    def icon(self) -> Optional[str]:
        """Icon to use in the frontend, if any."""
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "ELEC":
            return "mdi:flash"
        elif self.resource["dataSourceResourceTypeInfo"]["type"] == "GAS":
            return "mdi:fire"
        else:
            return None

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        """Return information about the sensor data source."""
        if self.resource["dataSourceResourceTypeInfo"]["type"] == "ELEC":
            human_type = "electricity"
        elif self.resource["dataSourceResourceTypeInfo"]["type"] == "GAS":
            human_type = "gas"

        return {
            "identifiers": {(DOMAIN, self.resource["dataSourceUnitInfo"]["shid"])},
            "name": f"Smart Meter, {human_type}",
        }

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self._state:
            return self._state["data"][0][1]
        else:
            return None

    @property
    def device_class(self) -> str:
        """Return the device class (always DEVICE_CLASS_POWER)."""
        return DEVICE_CLASS_POWER

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self._state is not None and self._state["units"] == "W":
            return POWER_WATT
        else:
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
            # TODO: Trip the failed auth logic above somehow
            self.available = False
            pass
