from __future__ import annotations

"""Classes for interacting with the Glowmarkt API."""
from pprint import pprint
from typing import TYPE_CHECKING, Any, Dict, List

import requests
from hbmqtt.client import MQTTClient
from hbmqtt.mqtt.constants import QOS_1
from homeassistant import exceptions

from .mqttpayload import MQTTPayload

if TYPE_CHECKING:
    from .sensor import GlowConsumptionCurrent


class Glow:
    """Bindings for the Hildebrand Glow Platform API."""

    BASE_URL = "https://api.glowmarkt.com/api/v0-1"

    username: str
    password: str

    token: str

    hardwareId: str
    broker: MQTTClient

    sensors: Dict[str, GlowConsumptionCurrent] = dict()

    def __init__(self, app_id: str, username: str, password: str):
        """Create an authenticated Glow object."""
        self.app_id = app_id
        self.username = username
        self.password = password

    def authenticate(self) -> None:
        """
        Attempt to authenticate with Glowmarkt.

        Returns a time-limited access token.
        """
        url = f"{self.BASE_URL}/auth"
        auth = {"username": self.username, "password": self.password}
        headers = {"applicationId": self.app_id}

        try:
            response = requests.post(url, json=auth, headers=headers)
        except requests.Timeout:
            raise CannotConnect

        data = response.json()

        if data["valid"]:
            self.token = data["token"]
        else:
            pprint(data)
            raise InvalidAuth

    def retrieve_devices(self) -> List[Dict[str, Any]]:
        """Retrieve the Zigbee devices known to Glowmarkt for the authenticated user."""
        url = f"{self.BASE_URL}/device"
        headers = {"applicationId": self.app_id, "token": self.token}

        try:
            response = requests.get(url, headers=headers)
        except requests.Timeout:
            raise CannotConnect

        if response.status_code != 200:
            raise InvalidAuth

        data = response.json()
        return data

    def retrieve_cad_hardwareId(self) -> str:
        """Locate the Consumer Access Device's hardware ID from the devices list."""
        ZIGBEE_GLOW_STICK = "1027b6e8-9bfd-4dcb-8068-c73f6413cfaf"

        devices = self.retrieve_devices()

        cad: Dict[str, Any] = next(
            (dev for dev in devices if dev["deviceTypeId"] == ZIGBEE_GLOW_STICK), None
        )

        self.hardwareId = cad["hardwareId"]

        return self.hardwareId

    async def connect_mqtt(self) -> None:
        """Connect the internal MQTT client to the discovered CAD."""
        HILDEBRAND_MQTT_HOST = (
            f"mqtts://{self.username}:{self.password}@glowmqtt.energyhive.com/"
        )
        HILDEBRAND_MQTT_TOPIC = f"SMART/HILD/{self.hardwareId}"

        self.broker = MQTTClient()

        await self.broker.connect(HILDEBRAND_MQTT_HOST)

        await self.broker.subscribe(
            [
                (HILDEBRAND_MQTT_TOPIC, QOS_1),
            ]
        )

    async def retrieve_mqtt(self) -> None:
        while True:
            message = await self.broker.deliver_message()
            packet = message.publish_packet.payload.data.decode()

            payload = MQTTPayload(packet)

            if "electricity.consumption" in self.sensors:
                self.sensors["electricity.consumption"].update_state(payload)

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

    def register_sensor(self, sensor, resource):
        self.sensors[resource["classifier"]] = sensor


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
