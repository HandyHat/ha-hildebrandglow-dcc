"""Classes for interacting with the Glowmarkt API."""
from __future__ import annotations

from pprint import pprint
from typing import TYPE_CHECKING, Any, Dict, List

import paho.mqtt.client as mqtt
import requests
from homeassistant import exceptions

from .mqttpayload import MQTTPayload

if TYPE_CHECKING:
    from .sensor import GlowConsumptionCurrent


class Glow:
    """Bindings for the Hildebrand Glow Platform API."""

    BASE_URL = "https://api.glowmarkt.com/api/v0-1"
    HILDEBRAND_MQTT_HOST = "glowmqtt.energyhive.com"
    HILDEBRAND_MQTT_TOPIC = "SMART/HILD/{hardwareId}"

    username: str
    password: str

    token: str

    hardwareId: str
    broker: mqtt.Client

    sensors: Dict[str, GlowConsumptionCurrent] = {}

    def __init__(self, app_id: str, username: str, password: str):
        """Create an authenticated Glow object."""
        self.app_id = app_id
        self.username = username
        self.password = password

        self.broker = mqtt.Client()
        self.broker.username_pw_set(username=self.username, password=self.password)
        self.broker.on_connect = self._cb_on_connect
        self.broker.on_message = self._cb_on_message

        self.broker_active = False

    def authenticate(self) -> None:
        """Attempt to authenticate with Glowmarkt."""
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

    def connect_mqtt(self) -> None:
        """Connect the internal MQTT client to the discovered CAD."""
        self.broker.connect(self.HILDEBRAND_MQTT_HOST)

        self.broker.loop_start()

    def _cb_on_connect(self, client, userdata, flags, rc):
        """Receive a CONNACK message from the server."""
        client.subscribe(self.HILDEBRAND_MQTT_TOPIC.format(hardwareId=self.hardwareId))

        self.broker_active = True

    def _cb_on_disconnect(self, client, userdata, rc):
        """Receive notice the MQTT connection has disconnected."""
        self.broker_active = False

    def _cb_on_message(self, client, userdata, msg):
        """Receive a PUBLISH message from the server."""
        payload = MQTTPayload(msg.payload)

        if "electricity.consumption" in self.sensors:
            self.sensors["electricity.consumption"].update_state(payload)

        if "gas.consumption" in self.sensors:
            self.sensors["gas.consumption"].update_state(payload)

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
        """Register a live sensor for dispatching MQTT messages."""
        self.sensors[resource["classifier"]] = sensor


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
