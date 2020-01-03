"""Config flow for Octopus Energy integration."""
import logging

import voluptuous as vol

from homeassistant import core, config_entries, exceptions

from .const import DOMAIN  # pylint:disable=unused-import

from .glow import Glow, CannotConnect, InvalidAuth

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({"app_id": str, "username": str, "password": str})

async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    glow = await Glow.authenticate(data['app_id'], data['username'], data['password'])
    
    # Return some info we want to store in the config entry.
    return {"name": glow["name"], "app_id": data['app_id'], "username": data['username'], 'password': data['password'], "token": glow["token"], "token_exp": glow["exp"]}


class DomainConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Octopus Energy."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.SOURCE_USER

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
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
