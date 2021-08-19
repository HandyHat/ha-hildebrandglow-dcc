"""Config flow for Hildebrand Glow integration."""
import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries, core, data_entry_flow

from .const import APP_ID, DOMAIN
from .glow import CannotConnect, Glow, InvalidAuth

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({"username": str, "password": str})


def config_object(data: dict, glow: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a ConfigEntity with authentication data and a temporary token."""
    return {
        "name": glow["name"],
        "username": data["username"],
        "password": data["password"],
        "token": glow["token"],
        "token_exp": glow["exp"],
    }


async def validate_input(hass: core.HomeAssistant, data: dict) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    glow = await hass.async_add_executor_job(
        Glow.authenticate, APP_ID, data["username"], data["password"]
    )

    # Return some info we want to store in the config entry.
    return config_object(data, glow)


class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hildebrand Glow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.SOURCE_USER

    async def async_step_user(
        self, user_input: Dict = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                assert self.hass is not None
                info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=info["name"], data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
