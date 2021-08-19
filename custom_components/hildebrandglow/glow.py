"""Classes for interacting with the Glowmarkt API."""
import logging
from datetime import datetime
from pprint import pprint
from typing import Any, Dict, List

import requests
from homeassistant import exceptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import APP_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)


class Glow:
    """Bindings for the Hildebrand Glow Platform API."""

    BASE_URL = "https://api.glowmarkt.com/api/v0-1"

    def __init__(self, app_id: str, token: str):
        """Create an authenticated Glow object."""
        self.app_id = app_id
        self.token = token

    @classmethod
    def authenticate(cls, app_id: str, username: str, password: str) -> Dict[str, Any]:
        """
        Attempt to authenticate with Glowmarkt.

        Returns a time-limited access token.
        """
        url = f"{cls.BASE_URL}/auth"
        auth = {"username": username, "password": password}
        headers = {"applicationId": app_id}

        try:
            response = requests.post(url, json=auth, headers=headers)
        except requests.Timeout:
            raise CannotConnect

        data = response.json()

        if data["valid"]:
            return data
        else:
            pprint(data)
            raise InvalidAuth

    async def handle_failed_auth(self, config: ConfigEntry, hass: HomeAssistant) -> None:
        """Attempt to refresh the current Glow token."""
        glow_auth = await hass.async_add_executor_job(
            Glow.authenticate,
            APP_ID,
            config.data["username"],
            config.data["password"],
        )
        from .config_flow import config_object

        current_config = dict(config.data.copy())
        new_config = config_object(current_config, glow_auth)
        hass.config_entries.async_update_entry(entry=config, data=new_config)

        glow = Glow(APP_ID, glow_auth["token"])
        hass.data[DOMAIN][config.entry_id] = glow

    def retrieve_resources(self) -> List[Dict[str, Any]]:
        """Retrieve the resources known to Glowmarkt for the authenticated user."""
        url = f"{self.BASE_URL}/resource"
        headers = {"applicationId": self.app_id, "token": self.token}

        try:
            response = requests.get(url, headers=headers)
        except requests.Timeout:
            raise CannotConnect

        if response.status_code != 200:
            raise InvalidAuth

        data = response.json()
        return data

    def current_usage(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the current usage for a specified resource."""

        # Get today's date
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")

        # Need to pull updated data from DCC first
        catchup_url = f"{self.BASE_URL}/resource/{resource}/catchup"

        url = f"{self.BASE_URL}/resource/{resource}/readings?from=" + current_date + "T00:00:00&to=" + current_date + "T23:59:59&period=P1D&offset=-60&function=sum"
        headers = {"applicationId": self.app_id, "token": self.token}

        try:
            response = requests.get(catchup_url, headers=headers)
            response = requests.get(url, headers=headers)
        except requests.Timeout:
            raise CannotConnect

        if response.status_code != 200:
            if response.json()["error"] == "incorrect elements -from in the future":
                _LOGGER.info("Attempted to load data from the future - expected if the day has just changed")
                return
            elif response.status_code == 401:
                raise InvalidAuth
            else:
                _LOGGER.error("Response Status Code:" + str(response.status_code))
                self.available = False

        data = response.json()
        return data


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
