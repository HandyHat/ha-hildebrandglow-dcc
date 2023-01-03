"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time, timedelta
import logging

from glowmarkt import BrightClient
import requests

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable
) -> bool:
    """Set up the sensor platform."""
    entities = []
    meters = {}

    # Get API object from the config flow
    glowmarkt = hass.data[DOMAIN][entry.entry_id]

    # Gather all virtual entities on the account
    virtual_entities: dict = {}
    try:
        virtual_entities = await hass.async_add_executor_job(
            glowmarkt.get_virtual_entities
        )
    except requests.Timeout as ex:
        _LOGGER.error("Timeout: %s", ex)
    except requests.exceptions.ConnectionError as ex:
        _LOGGER.error("Cannot connect: %s", ex)
    # Can't use the RuntimeError exception from the library as it's not a subclass of Exception
    except Exception as ex:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception: %s. Please open an issue", ex)
    _LOGGER.debug("Successful GET to %svirtualentity", glowmarkt.url)

    for virtual_entity in virtual_entities:
        # Gather all resources for each virtual entity
        resources: dict = {}
        try:
            resources = await hass.async_add_executor_job(virtual_entity.get_resources)
        except requests.Timeout as ex:
            _LOGGER.error("Timeout: %s", ex)
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.error("Cannot connect: %s", ex)
        # Can't use the RuntimeError exception from the library as it's not a subclass of Exception
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception: %s. Please open an issue", ex)
        _LOGGER.debug(
            "Successful GET to %svirtualentity/%s/resources",
            glowmarkt.url,
            virtual_entity.id,
        )

        # Loop through all resources and create sensors
        for resource in resources:
            if resource.classifier in ["electricity.consumption", "gas.consumption"]:
                usage_sensor = Usage(hass, resource, virtual_entity, entry)
                entities.append(usage_sensor)
                # Save the usage sensor as a meter so that the cost sensor can reference it
                meters[resource.classifier] = usage_sensor

                # Standing and Rate sensors are handled by the coordinator
                coordinator = TariffCoordinator(hass, glowmarkt, resource, entry)
                standing_sensor = Standing(coordinator, resource, virtual_entity)
                entities.append(standing_sensor)
                rate_sensor = Rate(coordinator, resource, virtual_entity)
                entities.append(rate_sensor)
                # await coordinator.async_config_entry_first_refresh() # This isn't necessary as update_before_add is already specified

        # Cost sensors must be created after usage sensors as they reference them as a meter
        for resource in resources:
            if resource.classifier == "gas.consumption.cost":
                cost_sensor = Cost(hass, resource, virtual_entity, entry)
                cost_sensor.meter = meters["gas.consumption"]
                entities.append(cost_sensor)
            elif resource.classifier == "electricity.consumption.cost":
                cost_sensor = Cost(hass, resource, virtual_entity, entry)
                cost_sensor.meter = meters["electricity.consumption"]
                entities.append(cost_sensor)

    # Get data for all entities on initial startup
    async_add_entities(entities, update_before_add=True)

    return True


def supply_type(resource) -> str:
    """Return supply type."""
    if "electricity.consumption" in resource.classifier:
        return "electricity"
    if "gas.consumption" in resource.classifier:
        return "gas"
    _LOGGER.error("Unknown classifier: %s. Please open an issue", resource.classifier)
    return "unknown"


def device_name(resource, virtual_entity) -> str:
    """Return device name. Includes name of virtual entity if it exists."""
    supply = supply_type(resource)
    # First letter of device name should be capitalised
    if virtual_entity.name is not None:
        name = f"{virtual_entity.name} smart {supply} meter"
    else:
        name = f"Smart {supply} meter"
    return name


async def should_update() -> bool:
    """Check if time is between 0-5 or 30-35 minutes past the hour."""
    minutes = datetime.now().minute
    if (0 <= minutes <= 5) or (30 <= minutes <= 35):
        return True
    return False


async def daily_data(self) -> float:
    """Get daily usage from the API."""
    # If it's before 01:06, we need to fetch yesterday's data
    # Should only need to be before 00:36 but gas data can be 30 minutes behind electricity data
    if datetime.now().time() <= time(1, 5):
        _LOGGER.debug("Fetching yesterday's data")
        now = datetime.now() - timedelta(days=1)
    else:
        now = datetime.now()
    # Round to the day to set time to 00:00:00
    t_from = await self.hass.async_add_executor_job(self.resource.round, now, "P1D")
    # Round to the minute
    t_to = await self.hass.async_add_executor_job(self.resource.round, now, "PT1M")

    # Tell Hildebrand to pull latest DCC data
    try:
        await self.hass.async_add_executor_job(self.resource.catchup)
    except requests.Timeout as ex:
        _LOGGER.error("Timeout: %s", ex)
    except requests.exceptions.ConnectionError as ex:
        _LOGGER.error("Cannot connect: %s", ex)
    # Can't use the RuntimeError exception from the library as it's not a subclass of Exception
    except Exception as ex:  # pylint: disable=broad-except
        if "Request failed" in str(ex):
            _LOGGER.debug("Non-200 Status Code. Refreshing auth")
            await refresh_token(self)
            try:
                await self.hass.async_add_executor_job(self.resource.catchup)
            except requests.Timeout as secondary_ex:
                _LOGGER.error("Timeout: %s", secondary_ex)
            except requests.exceptions.ConnectionError as secondary_ex:
                _LOGGER.error("Cannot connect: %s", secondary_ex)
            except Exception as secondary_ex:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected exception: %s. Please open an issue", secondary_ex
                )
        else:
            _LOGGER.exception("Unexpected exception: %s. Please open an issue", ex)
    _LOGGER.debug(
        "Successful GET to https://api.glowmarkt.com/api/v0-1/resource/%s/catchup",
        self.resource.id,
    )

    try:
        readings = await self.hass.async_add_executor_job(
            self.resource.get_readings, t_from, t_to, "P1D", "sum", True
        )
    except requests.Timeout as ex:
        _LOGGER.error("Timeout: %s", ex)
    except requests.exceptions.ConnectionError as ex:
        _LOGGER.error("Cannot connect: %s", ex)
    # Can't use the RuntimeError exception from the library as it's not a subclass of Exception
    except Exception as ex:  # pylint: disable=broad-except
        if "Request failed" in str(ex):
            _LOGGER.debug("Non-200 Status Code. Refreshing auth")
            await refresh_token(self)
            try:
                readings = await self.hass.async_add_executor_job(
                    self.resource.get_readings, t_from, t_to, "P1D", "sum", True
                )
            except requests.Timeout as secondary_ex:
                _LOGGER.error("Timeout: %s", secondary_ex)
            except requests.exceptions.ConnectionError as secondary_ex:
                _LOGGER.error("Cannot connect: %s", secondary_ex)
            except Exception as secondary_ex:  # pylint: disable=broad-except
                _LOGGER.exception(
                    "Unexpected exception: %s. Please open an issue", secondary_ex
                )
        else:
            _LOGGER.exception("Unexpected exception: %s. Please open an issue", ex)
    _LOGGER.debug("Successfully got daily usage for resource id %s", self.resource.id)
    return readings[0][1].value


async def tariff_data(self) -> float:
    """Get tariff data from the API."""
    try:
        tariff = await self.hass.async_add_executor_job(self.resource.get_tariff)
        _LOGGER.debug(
            "Successful GET to %sresource/%s/tariff",
            self.glowmarkt.url,
            self.resource.id,
        )
        return tariff
    except UnboundLocalError:
        supply = supply_type(self.resource)
        _LOGGER.warning(
            "No tariff data found for %s meter (id: %s). If you don't see tariff data for this meter in the Bright app, please disable the associated rate and standing charge sensors",
            supply,
            self.resource.id,
        )
    except requests.Timeout as ex:
        _LOGGER.error("Timeout: %s", ex)
    except requests.exceptions.ConnectionError as ex:
        _LOGGER.error("Cannot connect: %s", ex)
    # Can't use the RuntimeError exception from the library as it's not a subclass of Exception
    except Exception as ex:  # pylint: disable=broad-except
        if "Request failed" in str(ex) and not self.auth_refreshed:
            _LOGGER.debug("Non-200 Status Code. Refreshing auth")
            await refresh_token(self)
            self.auth_refreshed = True
            await tariff_data(self)
        _LOGGER.exception("Unexpected exception: %s. Please open an issue", ex)
    return None


async def refresh_token(self):
    """Refresh the glowmarkt API token"""
    try:
        glowmarkt = await self.hass.async_add_executor_job(
            BrightClient, self.entry.data["username"], self.entry.data["password"]
        )
    except requests.Timeout as ex:
        raise ConfigEntryNotReady(f"Timeout: {ex}") from ex
    except requests.exceptions.ConnectionError as ex:
        raise ConfigEntryNotReady(f"Cannot connect: {ex}") from ex
    except Exception as ex:  # pylint: disable=broad-except
        raise ConfigEntryNotReady(
            f"Unexpected exception: {ex}. Please open an issue."
        ) from ex
    else:
        _LOGGER.debug("Successful Post to %sauth", glowmarkt.url)

    # Set API object
    self.hass.data[DOMAIN][self.entry.entry_id] = glowmarkt


class Usage(SensorEntity):
    """Sensor object for daily usage."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_has_entity_name = True
    _attr_name = "Usage (today)"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self, hass: HomeAssistant, resource, virtual_entity, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = resource.id

        self.entry = entry
        self.hass = hass
        self.initialised = False
        self.resource = resource
        self.virtual_entity = virtual_entity

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.resource.id)},
            manufacturer="Hildebrand",
            model="Glow (DCC)",
            name=device_name(self.resource, self.virtual_entity),
        )

    @property
    def icon(self) -> str | None:
        """Icon to use in the frontend."""
        # Only the gas usage sensor needs an icon as the others inherit from their device class
        if self.resource.classifier == "gas.consumption":
            return "mdi:fire"

    async def async_update(self) -> None:
        """Fetch new data for the sensor."""
        # Get data on initial startup
        if not self.initialised:
            value = await daily_data(self)
            self._attr_native_value = round(value, 2)
            self.initialised = True
        else:
            # Only update the sensor if it's between 0-5 or 30-35 minutes past the hour
            if await should_update():
                value = await daily_data(self)
                self._attr_native_value = round(value, 2)


class Cost(SensorEntity):
    """Sensor usage for daily cost."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_has_entity_name = True
    _attr_name = "Cost (today)"
    _attr_native_unit_of_measurement = "GBP"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self, hass: HomeAssistant, resource, virtual_entity, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = resource.id

        self.entry = entry
        self.hass = hass
        self.initialised = False
        self.meter = None
        self.resource = resource
        self.virtual_entity = virtual_entity

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            # Get the identifier from the meter so that the cost sensors have the same device
            identifiers={(DOMAIN, self.meter.resource.id)},
            manufacturer="Hildebrand",
            model="Glow (DCC)",
            name=device_name(self.resource, self.virtual_entity),
        )

    async def async_update(self) -> None:
        """Fetch new data for the sensor."""
        if not self.initialised:
            value = await daily_data(self) / 100
            self._attr_native_value = round(value, 2)
            self.initialised = True
        else:
            # Only update the sensor if it's between 0-5 or 30-35 minutes past the hour
            if await should_update():
                value = await daily_data(self) / 100
                self._attr_native_value = round(value, 2)


class TariffCoordinator(DataUpdateCoordinator):
    """Data update coordinator for the tariff sensors."""

    def __init__(self, hass: HomeAssistant, glowmarkt, resource, entry: ConfigEntry):
        """Initialize tariff coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="tariff",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self.glowmarkt = glowmarkt
        self.rate_initialised = False
        self.standing_initialised = False
        self.resource = resource

    async def _async_update_data(self):
        """Fetch data from tariff API endpoint."""
        # This needs 2 loops to ensure both the rate and the standing sensors get initial values
        if not self.standing_initialised:
            if not self.rate_initialised:
                self.rate_initialised = True
                return await tariff_data(self)
            self.standing_initialised = True
            return await tariff_data(self)
        # Only poll when updated data might be available
        if await should_update():
            tariff = await tariff_data(self)
            return tariff


class Standing(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_has_entity_name = True
    _attr_name = "Standing charge"
    _attr_native_unit_of_measurement = "GBP"
    _attr_entity_registry_enabled_default = (
        False  # Don't enable by default as less commonly used
    )

    def __init__(self, coordinator, resource, virtual_entity):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

        self._attr_unique_id = resource.id + "-tariff"

        self.resource = resource
        self.virtual_entity = virtual_entity

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            value = (
                float(self.coordinator.data.current_rates.standing_charge.value) / 100
            )
            self._attr_native_value = round(value, 4)
            self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.resource.id)},
            manufacturer="Hildebrand",
            model="Glow (DCC)",
            name=device_name(self.resource, self.virtual_entity),
        )


class Rate(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    _attr_device_class = None
    _attr_has_entity_name = True
    _attr_icon = (
        "mdi:cash-multiple"  # Need to provide an icon as doesn't have a device class
    )
    _attr_name = "Rate"
    _attr_native_unit_of_measurement = "GBP/kWh"
    _attr_entity_registry_enabled_default = (
        False  # Don't enable by default as less commonly used
    )

    def __init__(self, coordinator, resource, virtual_entity):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

        self._attr_unique_id = resource.id + "-rate"

        self.resource = resource
        self.virtual_entity = virtual_entity

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data:
            value = float(self.coordinator.data.current_rates.rate.value) / 100
            self._attr_native_value = round(value, 4)
            self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.resource.id)},
            manufacturer="Hildebrand",
            model="Glow (DCC)",
            name=device_name(self.resource, self.virtual_entity),
        )
