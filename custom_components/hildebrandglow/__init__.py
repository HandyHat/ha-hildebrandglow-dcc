"""The Hildebrand Glow integration."""
import asyncio
from typing import Any, Dict

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .config_flow import config_object
from .const import APP_ID, DOMAIN
from .glow import Glow, InvalidAuth
from .sensor import GlowConsumptionCurrent

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Hildebrand Glow component."""
    hass.data[DOMAIN] = {}

    return True


async def handle_failed_auth(config: ConfigEntry, hass: HomeAssistant) -> None:
    """Attempt to refresh the current Glow token."""
    glow_auth = await hass.async_add_executor_job(
        Glow.authenticate,
        APP_ID,
        config.data["username"],
        config.data["password"],
    )

    current_config = dict(config.data.copy())
    new_config = config_object(current_config, glow_auth)
    hass.config_entries.async_update_entry(entry=config, data=new_config)

    glow = Glow(APP_ID, glow_auth["token"])
    hass.data[DOMAIN][config.entry_id] = glow


async def retrieve_cad_hardwareId(hass: HomeAssistant, glow: Glow) -> str:
    """Locate the Consumer Access Device's hardware ID from the devices list."""
    ZIGBEE_GLOW_STICK = "1027b6e8-9bfd-4dcb-8068-c73f6413cfaf"

    devices = await hass.async_add_executor_job(glow.retrieve_devices)

    cad: Dict[str, Any] = next(
        (dev for dev in devices if dev["deviceTypeId"] == ZIGBEE_GLOW_STICK), None
    )

    return cad["hardwareId"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hildebrand Glow from a config entry."""
    glow = Glow(APP_ID, entry.data["token"])

    try:
        hardwareId: str = await retrieve_cad_hardwareId(hass, glow)
        mqtt_topic: str = f"SMART/HILD/{hardwareId}"

        resources = await hass.async_add_executor_job(glow.retrieve_resources)

    except InvalidAuth:
        try:
            await handle_failed_auth(entry, hass)
            return False
        except InvalidAuth:
            return False

    hass.data[DOMAIN][entry.entry_id] = glow

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
