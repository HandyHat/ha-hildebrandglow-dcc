"""Classes for interacting with the Glowmarkt API."""
from pprint import pprint
from typing import Any, Dict, List

import requests
from homeassistant import exceptions


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
        url = f"{self.BASE_URL}/resource/{resource}/current"
        headers = {"applicationId": self.app_id, "token": self.token}

        try:
            response = requests.get(url, headers=headers)
        except requests.Timeout:
            raise CannotConnect

        if response.status_code != 200:
            raise InvalidAuth

        data = response.json()
        return data


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
