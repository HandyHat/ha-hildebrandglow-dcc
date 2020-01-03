"""Platform for sensor integration."""
from homeassistant.const import POWER_WATT, DEVICE_CLASS_POWER
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    
    new_entities = []

    for entry in hass.data[DOMAIN]:
        glow = hass.data[DOMAIN][entry]

        resources = await glow.retrieve_resources()

        for resource in resources:
            if resource['resourceTypeId'] in GlowConsumptionCurrent.resourceTypeId:
                sensor = GlowConsumptionCurrent(glow, resource)
                new_entities.append(sensor)
        
    async_add_entities([sensor])

    return True


class GlowConsumptionCurrent(Entity):
    resourceTypeId = [
        "ea02304a-2820-4ea0-8399-f1d1b430c3a0", # Smart Meter, electricity consumption
        "672b8071-44ff-4f23-bca2-f50c6a3ddd02" # Smart Meter, gas consumption
    ]

    def __init__(self, glow, resource):
        """Initialize the sensor."""
        self._state = None
        self.glow = glow
        self.resource = resource

    @property
    def unique_id(self):
        return self.resource['resourceId']

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.resource['label']

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self.resource['dataSourceResourceTypeInfo']['type'] == 'ELEC':
            return "mdi:flash"
        elif self.resource['dataSourceResourceTypeInfo']['type'] == 'GAS':
            return "mdi:fire"

    @property
    def device_info(self):
        if self.resource['dataSourceResourceTypeInfo']['type'] == 'ELEC':
            human_type = 'electricity'
        elif self.resource['dataSourceResourceTypeInfo']['type'] == 'GAS':
            human_type = 'gas'

        return {
            'identifiers': {
                (DOMAIN, self.resource['dataSourceUnitInfo']['shid'])
            },
            'name': f'Smart Meter, {human_type}'
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._state:
            return self._state['data'][0][1]
        else:
            return None

    @property
    def device_class(self):
        return DEVICE_CLASS_POWER
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if not self._state:
            return None
        elif self._state['units'] == "W":
            return POWER_WATT

    async def async_update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = await self.glow.current_usage(self.resource['resourceId'])

