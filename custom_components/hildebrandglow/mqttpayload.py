import json
from enum import Enum
from typing import Any, Dict


class Meter:
    class ReadingInformationSet:
        current_summation_delivered: int
        current_summation_received: int
        current_max_demand_delivered: int
        reading_snapshot_time: str
        supply_status: int

        def __init__(self, payload: Dict[str, Any]):
            reading_information_set = (
                payload["0702"]["00"] if "00" in payload["0702"] else {}
            )

            self.current_summation_delivered = (
                int(reading_information_set["00"], 16)
                if "00" in reading_information_set
                else None
            )
            self.current_summation_received = (
                int(reading_information_set["01"], 16)
                if "01" in reading_information_set
                else None
            )
            self.current_max_demand_delivered = (
                int(reading_information_set["02"], 16)
                if "02" in reading_information_set
                else None
            )
            self.reading_snapshot_time = (
                int(reading_information_set["07"], 16)
                if "07" in reading_information_set
                else None
            )
            self.supply_status = (
                int(reading_information_set["07"], 16)
                if "07" in reading_information_set
                else None
            )

    class MeterStatus:
        status: str

        def __init__(self, payload: Dict[str, Any]):
            meter_status = payload["0702"]["02"] if "02" in payload["0702"] else {}

            self.status = meter_status.get("00")

    class Formatting:
        class UnitofMeasure(Enum):
            KWH = "00"
            M3 = "01"

        class MeteringDeviceType(Enum):
            ELECTRIC = "00"
            GAS = "80"

        unit_of_measure: UnitofMeasure
        multiplier: int
        divisor: int
        summation_formatting: str
        demand_formatting: str
        metering_device_type: MeteringDeviceType
        siteID: str
        meter_serial_number: str
        alternative_unit_of_measure: UnitofMeasure

        def __init__(self, payload: Dict[str, Any]):
            formatting = payload["0702"]["03"] if "03" in payload["0702"] else {}

            self.unit_of_measure = self.UnitofMeasure(formatting.get("00", "00"))
            self.multiplier = int(formatting["01"], 16) if "01" in formatting else None
            self.divisor = int(formatting["02"], 16) if "02" in formatting else None
            self.summation_formatting = formatting.get("03")
            self.demand_formatting = formatting.get("04")
            self.metering_device_type = (
                self.MeteringDeviceType(formatting["06"])
                if "06" in formatting
                else None
            )
            self.siteID = formatting.get("07")
            self.meter_serial_number = formatting.get("08")
            self.alternative_unit_of_measure = (
                self.UnitofMeasure(formatting["12"]) if "12" in formatting else None
            )

    class HistoricalConsumption:
        instantaneous_demand: int
        current_day_consumption_delivered: int
        current_week_consumption_delivered: int
        current_month_consumption_delivered: int

        def __init__(self, payload: Dict[str, Any]):
            historical_consumption = (
                payload["0702"]["04"] if "04" in payload["0702"] else {}
            )

            self.instantaneous_demand = (
                int(historical_consumption["00"], 16)
                if "00" in historical_consumption
                else None
            )
            self.current_day_consumption_delivered = (
                int(historical_consumption["01"], 16)
                if "01" in historical_consumption
                else None
            )
            self.current_week_consumption_delivered = (
                int(historical_consumption["30"], 16)
                if "30" in historical_consumption
                else None
            )
            self.current_week_consumption_delivered = (
                int(historical_consumption["40"], 16)
                if "40" in historical_consumption
                else None
            )

    class AlternativeHistoricalConsumption:
        current_day_consumption_delivered: int
        current_week_consumption_delivered: int
        current_month_consumption_delivered: int

        def __init__(self, payload: Dict[str, Any]):
            alternative_historical_consumption = (
                payload["0702"]["0C"] if "0C" in payload["0702"] else {}
            )

            self.current_day_consumption_delivered = (
                int(alternative_historical_consumption["01"], 16)
                if "01" in alternative_historical_consumption
                else None
            )
            self.current_week_consumption_delivered = (
                int(alternative_historical_consumption["30"], 16)
                if "30" in alternative_historical_consumption
                else None
            )
            self.current_week_consumption_delivered = (
                int(alternative_historical_consumption["40"], 16)
                if "40" in alternative_historical_consumption
                else None
            )

    def __init__(self, payload: Dict[str, Any]):
        self.reading_information_set = self.ReadingInformationSet(payload)
        self.meter_status = self.MeterStatus(payload)
        self.formatting = self.Formatting(payload)
        self.historical_consumption = self.HistoricalConsumption(payload)
        self.alternative_historical_consumption = self.AlternativeHistoricalConsumption(
            payload
        )

        self.meter = (
            int(payload["0702"]["00"]["00"], 16)
            if "00" in payload["0702"]["00"]
            else None
        )


class MQTTPayload:
    electricity: Meter
    gas: Meter

    def __init__(self, payload: str):
        payload = json.loads(payload)
        self.electricity = (
            Meter(payload["elecMtr"]) if "03" in payload["elecMtr"]["0702"] else None
        )
        self.gas = (
            Meter(payload["gasMtr"]) if "03" in payload["gasMtr"]["0702"] else None
        )
