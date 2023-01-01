"""Config flow for Hildebrand Glow (DCC) integration."""
from __future__ import annotations

import logging
from typing import Any

from glowmarkt import BrightClient
import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    glowmarkt = await hass.async_add_executor_job(
        BrightClient, data["username"], data["password"]
    )
    _LOGGER.debug("Successful Post to %sauth", glowmarkt.url)

    # Return title of the entry to be added
    return {"title": "Hildebrand Glow (DCC)"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hildebrand Glow (DCC)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # If left empty, simply show the form again
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        # Test authenticating with the API
        try:
            info = await validate_input(self.hass, user_input)
        except requests.Timeout as ex:
            _LOGGER.debug("Timeout: %s", ex)
            errors["base"] = "timeout_connect"
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.debug("Cannot connect: %s", ex)
            errors["base"] = "cannot_connect"
        # Can't use the RuntimeError exception from the library as it's not a subclass of Exception
        except Exception as ex:  # pylint: disable=broad-except
            if "Authentication failed" in str(ex):
                _LOGGER.debug("Authentication Failed")
                errors["base"] = "invalid_auth"
            elif "Expected an authentication token" in str(ex):
                _LOGGER.debug("Expected an authentication token but didn't get one")
                errors["base"] = "invalid_auth"
            else:
                _LOGGER.exception("Unexpected exception: %s", ex)
                errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
