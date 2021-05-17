"""Platform for sensor integration."""
from typing import Any, Callable, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_POWER, POWER_WATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .glow import Glow, InvalidAuth
from .mqttpayload import Meter


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
            return False

        for resource in resources:
            if resource["classifier"] in GlowConsumptionCurrent.knownClassifiers:
                sensor = GlowConsumptionCurrent(glow, resource)
                glow.register_sensor(sensor, resource)
                new_entities.append(sensor)

        async_add_entities(new_entities)

    return True


class GlowConsumptionCurrent(Entity):
    """Sensor object for the Glowmarkt resource's current consumption."""

    hass: HomeAssistant

    knownClassifiers = ["gas.consumption", "electricity.consumption"]

    available = True
    should_poll = False

    def __init__(self, glow: Glow, resource: Dict[str, Any]):
        """Initialize the sensor."""
        self._state: Optional[Meter] = None
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
            "identifiers": {(DOMAIN, self.resource["resourceId"])},
            "name": f"Smart Meter, {human_type}",
        }

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        if self._state:
            return self._state.consumption
        else:
            return None

    def update_state(self, meter) -> None:
        """Receive an MQTT update from Glow and update the internal state."""
        self._state = meter.electricity
        self.async_write_ha_state()

    @property
    def device_class(self) -> str:
        """Return the device class (always DEVICE_CLASS_POWER)."""
        return DEVICE_CLASS_POWER

    @property
    def unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self._state is not None:
            return POWER_WATT
        else:
            return None
