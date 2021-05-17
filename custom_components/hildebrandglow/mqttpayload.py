import json
from typing import Any, Dict


class Meter:
    def __init__(self, payload: Dict[str, Any]):
        historical_consumption = (
            payload["0702"]["04"] if "04" in payload["0702"] else {}
        )

        self.consumption = (
            int(historical_consumption["00"], 16)
            if "00" in historical_consumption
            else None
        )
        self.daily_consumption = (
            int(historical_consumption["01"], 16)
            if "01" in historical_consumption
            else None
        )
        self.weekly_consumption = (
            int(historical_consumption["30"], 16)
            if "30" in historical_consumption
            else None
        )
        self.monthly_consumption = (
            int(historical_consumption["40"], 16)
            if "40" in historical_consumption
            else None
        )

        formatting = payload["0702"]["03"] if "03" in payload["0702"] else {}
        self.multiplier = int(formatting["01"], 16) if "01" in formatting else None
        self.divisor = int(formatting["02"], 16) if "02" in formatting else None

        self.meter = (
            int(payload["0702"]["00"]["00"], 16)
            if "00" in payload["0702"]["00"]
            else None
        )


class MQTTPayload:
    payload: Dict[str, Any]

    def __init__(self, payload: str):
        self.payload = json.loads(payload)
        self.electricity = Meter(self.payload["elecMtr"])
        self.gas = Meter(self.payload["gasMtr"])
