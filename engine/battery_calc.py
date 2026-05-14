"""
SolarCalc Pro — Battery Bank Sizing Engine
Calculates required Ah capacity, series/parallel configuration and total unit count.
"""

import math
from dataclasses import dataclass


@dataclass
class BatteryResult:
    """Output of the battery bank calculation."""
    daily_wh: float
    system_voltage: int
    days_autonomy: int
    dod_pct: float
    battery_type: str
    battery_voltage: int    # V per cell/unit
    battery_ah: float       # Ah per unit

    # Calculated
    required_ah: float = 0.0         # at system voltage
    series_count: int = 1             # batteries in series per string
    parallel_strings: int = 1         # strings in parallel
    total_batteries: int = 1
    actual_capacity_ah: float = 0.0   # delivered capacity

    def to_dict(self) -> dict:
        return {
            "daily_wh": round(self.daily_wh, 1),
            "system_voltage": self.system_voltage,
            "days_autonomy": self.days_autonomy,
            "dod_pct": self.dod_pct,
            "battery_type": self.battery_type,
            "battery_voltage": self.battery_voltage,
            "battery_ah": self.battery_ah,
            "required_ah": round(self.required_ah, 1),
            "series_count": self.series_count,
            "parallel_strings": self.parallel_strings,
            "total_batteries": self.total_batteries,
            "actual_capacity_ah": round(self.actual_capacity_ah, 1),
            "configuration_label": f"{self.series_count}S × {self.parallel_strings}P",
        }


class BatteryCalculator:
    """
    Sizes and configures a battery bank.

    Formula chain:
        Required Wh     = daily_wh × days_autonomy
        Required Ah     = Required Wh / system_voltage / (DoD / 100)
        Series per str  = system_voltage / battery_voltage
        Parallel strs   = ceil(Required Ah / battery_ah)
        Total batteries = series × parallel
        Actual cap Ah   = parallel × battery_ah
    """

    def calculate(
        self,
        daily_wh: float,
        system_voltage: int,
        days_autonomy: int,
        dod_pct: float,
        battery_type: str,
        battery_voltage: int,
        battery_ah: float,
    ) -> BatteryResult:
        """
        Parameters
        ----------
        daily_wh       : Wh/day from load analysis
        system_voltage : system bus voltage (12/24/48 V)
        days_autonomy  : days without sun the bank must sustain
        dod_pct        : allowable depth of discharge (%)
        battery_type   : 'Lead-Acid' | 'AGM' | 'LiFePO4 (Lithium)'
        battery_voltage: voltage of one battery unit (V)
        battery_ah     : capacity of one battery unit (Ah)

        Returns
        -------
        BatteryResult with all fields populated.
        """
        dod = dod_pct / 100.0 if dod_pct > 1 else dod_pct

        # Total Wh the bank must store
        total_wh_needed = daily_wh * days_autonomy

        # Required Ah at the system voltage after accounting for DoD
        req_ah = total_wh_needed / system_voltage / dod if (system_voltage and dod) else 0

        # How many batteries in series to reach system voltage
        series = max(1, round(system_voltage / battery_voltage)) if battery_voltage else 1

        # How many parallel strings to reach required Ah
        parallel = math.ceil(req_ah / battery_ah) if battery_ah else 1

        total_batt = series * parallel
        actual_cap = parallel * battery_ah  # total Ah at system voltage

        return BatteryResult(
            daily_wh=daily_wh,
            system_voltage=system_voltage,
            days_autonomy=days_autonomy,
            dod_pct=dod_pct,
            battery_type=battery_type,
            battery_voltage=battery_voltage,
            battery_ah=battery_ah,
            required_ah=req_ah,
            series_count=series,
            parallel_strings=parallel,
            total_batteries=total_batt,
            actual_capacity_ah=actual_cap,
        )
