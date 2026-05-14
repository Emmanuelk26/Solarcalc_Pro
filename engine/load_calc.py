"""
SolarCalc Pro — Load Analysis Engine
Calculates total daily energy demand, peak power, system current and breaker sizing.
"""

import math
from dataclasses import dataclass, field
from typing import List


@dataclass
class Appliance:
    """Represents a single load item."""
    name: str
    watts: float        # rated power in Watts
    quantity: int       # number of units
    hours_per_day: float  # daily usage hours

    @property
    def daily_wh(self) -> float:
        """Daily energy consumption in Watt-hours."""
        return self.watts * self.quantity * self.hours_per_day

    @property
    def peak_watts(self) -> float:
        """Maximum simultaneous draw from this appliance."""
        return self.watts * self.quantity


@dataclass
class LoadResult:
    """Output of the load analysis calculation."""
    appliances: List[Appliance]
    system_voltage: int          # V  (12 / 24 / 48)
    safety_factor: float         # e.g. 1.25

    # Calculated fields
    total_daily_wh: float = 0.0
    total_daily_wh_with_safety: float = 0.0
    peak_watts: float = 0.0
    peak_watts_with_safety: float = 0.0
    total_current_a: float = 0.0
    recommended_breaker_a: float = 0.0

    def to_dict(self) -> dict:
        return {
            "system_voltage": self.system_voltage,
            "safety_factor": self.safety_factor,
            "total_daily_wh": round(self.total_daily_wh, 1),
            "total_daily_wh_with_safety": round(self.total_daily_wh_with_safety, 1),
            "peak_watts": round(self.peak_watts, 1),
            "peak_watts_with_safety": round(self.peak_watts_with_safety, 1),
            "total_current_a": round(self.total_current_a, 1),
            "recommended_breaker_a": round(self.recommended_breaker_a, 0),
            "appliances": [
                {
                    "name": a.name,
                    "watts": a.watts,
                    "quantity": a.quantity,
                    "hours_per_day": a.hours_per_day,
                    "daily_wh": round(a.daily_wh, 1),
                    "peak_watts": round(a.peak_watts, 1),
                }
                for a in self.appliances
            ],
        }


class LoadCalculator:
    """
    Performs load analysis given a list of appliances and system parameters.

    Formula chain:
        Daily Wh  = sum(watts × qty × hrs)
        Derated   = Daily Wh × safety_factor
        Peak W    = sum(watts × qty)  × safety_factor
        Current   = Peak W / system_voltage
        Breaker   = Current × 1.25  (next standard size)
    """

    # Standard breaker sizes (A)
    BREAKER_SIZES = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100,
                     125, 160, 200, 250, 315, 400, 500, 630]

    def calculate(
        self,
        appliances: List[dict],
        system_voltage: int,
        safety_factor_pct: float = 25.0,
    ) -> LoadResult:
        """
        Parameters
        ----------
        appliances       : list of dicts with keys name, watts, quantity, hours_per_day
        system_voltage   : int  — 12, 24, or 48 V
        safety_factor_pct: float — extra % on top (default 25 → ×1.25)

        Returns
        -------
        LoadResult with all calculated fields populated.
        """
        factor = 1.0 + (safety_factor_pct / 100.0)

        app_objs: List[Appliance] = []
        for a in appliances:
            try:
                obj = Appliance(
                    name=str(a.get("name", "Unknown")),
                    watts=float(a.get("watts", 0)),
                    quantity=int(a.get("quantity", 1)),
                    hours_per_day=float(a.get("hours_per_day", 0)),
                )
                app_objs.append(obj)
            except (ValueError, TypeError):
                continue  # skip malformed rows

        total_wh = sum(a.daily_wh for a in app_objs)
        peak_w = sum(a.peak_watts for a in app_objs)

        total_wh_safe = total_wh * factor
        peak_w_safe = peak_w * factor
        current_a = peak_w_safe / system_voltage if system_voltage else 0
        breaker_a = self._next_breaker(current_a * 1.25)

        result = LoadResult(
            appliances=app_objs,
            system_voltage=system_voltage,
            safety_factor=factor,
            total_daily_wh=total_wh,
            total_daily_wh_with_safety=total_wh_safe,
            peak_watts=peak_w,
            peak_watts_with_safety=peak_w_safe,
            total_current_a=round(current_a, 2),
            recommended_breaker_a=breaker_a,
        )
        return result

    def _next_breaker(self, required_a: float) -> float:
        """Return the next standard breaker size >= required_a."""
        for size in self.BREAKER_SIZES:
            if size >= required_a:
                return float(size)
        return math.ceil(required_a / 10) * 10  # fallback
