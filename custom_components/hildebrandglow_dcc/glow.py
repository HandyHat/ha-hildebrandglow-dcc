"""Classes for interacting with the Glowmarkt API."""
import logging
import time
from datetime import datetime
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
        self.update_token(token)
        self.http = requests.Session()

    @classmethod
    def update_token(cls, value):
        """Set the token in the class, so it is available to all instances"""
        cls.token = value

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
            _LOGGER.debug("Post 1: (%s)", url)
            response = requests.post(url, json=auth, headers=headers)
        except requests.Timeout as _timeout:
            raise CannotConnect from _timeout

        data = response.json()

        if data["valid"]:
            return data

        _LOGGER.debug("Invalid data: %s", data)
        raise InvalidAuth

    @classmethod
    async def handle_failed_auth(cls, config: ConfigEntry, hass: HomeAssistant) -> None:
        """Attempt to refresh the current Glow token."""
        _LOGGER.debug("handle_failed_auth")
        glow_auth = await hass.async_add_executor_job(
            Glow.authenticate,
            APP_ID,
            config.data["username"],
            config.data["password"],
        )

        # pylint: disable=import-outside-toplevel
        from .config_flow import config_object  # isort: skip

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
            _LOGGER.debug("get 1: (%s)", url)
            response = self.http.get(url, headers=headers)
        except requests.Timeout as _timeout:
            raise CannotConnect from _timeout

        if response.status_code != 200:
            raise InvalidAuth

        data = response.json()
        return data

    def _current_data(
        self, resource: Dict[str, Any], url: str, catchup: bool
    ) -> Dict[str, Any]:
        """Retrieve the current data for a specified resource."""
        headers = {"applicationId": self.app_id, "token": self.token}

        try:
            if catchup:
                catchup_url = f"{self.BASE_URL}/resource/{resource}/catchup"
                response = self.http.get(catchup_url, headers=headers)

            _LOGGER.debug("get 2: (%s)", url)
            response = self.http.get(url, headers=headers)

        except requests.Timeout as err:
            _LOGGER.warning("Timeout connecting to Glow %s", err)
            return None

        except requests.RequestException as err:
            _LOGGER.warning("Error connecting to Glow %s", err)
            return None

        if response.status_code != 200:
            if response.json()["error"] == "incorrect elements -from in the future":
                err = "Attempted to load data from future"
                err = err + " - expected if the day has just changed"
                _LOGGER.info(err)
                return None

            if response.status_code == 401:
                raise InvalidAuth

            if response.status_code == 404:
                _LOGGER.debug("404 error - treating as 401: (%s)", url)
                raise InvalidAuth

            status = str(response.status_code)
            _LOGGER.error("Glow response status code: %s (%s)", status, url)
            return None

        return response.json()

    @staticmethod
    def calc_offset() -> str:
        """Calculate the time, and DST offset"""
        if time.daylight and (time.localtime().tm_isdst > 0):
            utc_offset = time.altzone
        else:
            utc_offset = time.timezone

        if utc_offset != 0:
            utc_offset = int(utc_offset / 60)
            utc_str = f"&offset={utc_offset}"
        else:
            utc_str = "&offset=0"
        return utc_str

    def current_usage(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the current usage for a specified resource."""
        # Need to pull updated data from DCC first
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        utc_str = self.calc_offset()
        url = (
            f"{self.BASE_URL}/resource/{resource}/readings?from="
            + current_date
            + "T00:00:00&to="
            + current_date
            + "T23:59:59&period=P1D"
            + utc_str
            + "&function=sum"
        )

        return self._current_data(resource, url, True)

    def cumulative_usage(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the current usage for a specified resource."""
        # Need to pull updated data from DCC first
        current_time = datetime.now()
        current_date = current_time.strftime("%Y-%m-%d")
        current_year = current_time.strftime("%Y-01-01")
        utc_str = self.calc_offset()
        url = (
            f"{self.BASE_URL}/resource/{resource}/readings?from="
            + current_year
            + "T00:00:00&to="
            + current_date
            + "T23:59:59&period=P1Y"
            + utc_str
            + "&function=sum"
        )

        return self._current_data(resource, url, False)

    def current_tariff(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the current tariff for a specified resource."""
        url = f"{self.BASE_URL}/resource/{resource}/tariff"

        return self._current_data(resource, url, False)

    def usage_now(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the usage now specified resource."""
        url = f"{self.BASE_URL}/resource/{resource}/current"

        return self._current_data(resource, url, False)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
