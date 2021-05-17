"""Helper classes for Zigbee Smart Energy Profile data."""
import json
from enum import Enum
from typing import Any, Dict, Optional


class Meter:
    """Information received regarding a single smart meter."""

    class ReadingInformationSet:
        """Attributes providing remote access to meter readings."""

        class SupplyStatus(Enum):
            """Meter supply states."""

            OFF = "00"
            ARMED = "01"
            ON = "02"

        current_summation_delivered: Optional[int]
        """Import energy usage"""

        current_summation_received: Optional[int]
        """Export energy usage"""

        current_max_demand_delivered: Optional[int]
        """Maximum import energy usage rate"""

        reading_snapshot_time: Optional[int]
        """Last time all of the reported attributed were updated"""

        supply_status: Optional[SupplyStatus]
        """Current state of the meter's supply."""

        def __init__(self, payload: Dict[str, Any]):
            """Parse meter readings from the received payload."""
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
            self.supply_status = self.SupplyStatus(
                reading_information_set.get("14", "00")
            )

    class MeterStatus:
        """Information about the meter's error conditions."""

        status: Optional[str]
        """Meter error conditions"""

        def __init__(self, payload: Dict[str, Any]):
            """Parse meter error conditions from the received payload."""
            meter_status = payload["0702"]["02"] if "02" in payload["0702"] else {}

            self.status = meter_status.get("00")

    class Formatting:
        """Information about the format used for metering data."""

        class UnitofMeasure(Enum):
            """Units of Measurement."""

            KWH = "00"
            M3 = "01"

        class MeteringDeviceType(Enum):
            """Metering Device Types."""

            ELECTRIC = "00"
            GAS = "80"

        unit_of_measure: Optional[UnitofMeasure]
        """Unit for the measured value."""

        multiplier: Optional[int]
        """Multiplier value for smart meter readings."""

        divisor: Optional[int]
        """Divisor value for smart meter readings."""

        summation_formatting: Optional[str]
        """Bitmap representing decimal places in Summation readings."""

        demand_formatting: Optional[str]
        """Bitmap representing decimal places in Demand readings."""

        metering_device_type: Optional[MeteringDeviceType]
        """Smart meter device type."""

        siteID: Optional[str]
        """Electricicity MPAN / Gas MPRN."""

        meter_serial_number: Optional[str]
        """Smart meter serial number."""

        alternative_unit_of_measure: Optional[UnitofMeasure]
        """Alternative unit for the measured value."""

        def __init__(self, payload: Dict[str, Any]):
            """Parse formatting data from the received payload."""
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
        """Information about the meter's historical readings."""

        instantaneous_demand: Optional[int]
        """Instantaneous import energy usage rate"""

        current_day_consumption_delivered: Optional[int]
        """Import energy used in the current day."""

        current_week_consumption_delivered: Optional[int]
        """Import energy used in the current week."""

        current_month_consumption_delivered: Optional[int]
        """Import energy used in the current month."""

        def __init__(self, payload: Dict[str, Any]):
            """Parse historical meter readings from the received payload."""
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
        """Information about the meter's altenative historical readings."""

        current_day_consumption_delivered: Optional[int]
        """Import energy used in the current day."""

        current_week_consumption_delivered: Optional[int]
        """Import energy used in the current week."""

        current_month_consumption_delivered: Optional[int]
        """Import energy used in the current month."""

        def __init__(self, payload: Dict[str, Any]):
            """Parse alternative historical meter readings from the received payload."""
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
        """Parse meter data from the received payload using helper classes."""
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
    """Object representing a payload received over MQTT."""

    electricity: Optional[Meter]
    """Data interpreted from an electricity meter."""

    gas: Optional[Meter]
    """Data interpreted from a gas meter."""

    def __init__(self, input: str):
        """Create internal Meter instances based off the unprocessed payload."""
        payload: Dict[str, Any] = json.loads(input)
        self.electricity = (
            Meter(payload["elecMtr"]) if "03" in payload["elecMtr"]["0702"] else None
        )
        self.gas = (
            Meter(payload["gasMtr"]) if "03" in payload["gasMtr"]["0702"] else None
        )
