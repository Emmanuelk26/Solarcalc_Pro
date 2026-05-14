"""
SolarCalc Pro — Solar Array Sizing Engine
Calculates number of panels, array capacity and charge controller rating.
"""

import math
from dataclasses import dataclass


@dataclass
class SolarResult:
    """Output of the solar sizing calculation."""
    daily_wh_required: float
    system_voltage: int
    peak_sun_hours: float
    panel_wattage: int
    system_efficiency: float    # 0.0 – 1.0
    inverter_efficiency: float  # 0.0 – 1.0

    # Calculated
    effective_daily_wh: float = 0.0   # after losses
    panels_required: int = 0
    total_array_watts: float = 0.0
    array_current_a: float = 0.0      # short-circuit / sizing current
    charge_controller_a: float = 0.0  # next standard MPPT size

    def to_dict(self) -> dict:
        return {
            "daily_wh_required": round(self.daily_wh_required, 1),
            "system_voltage": self.system_voltage,
            "peak_sun_hours": self.peak_sun_hours,
            "panel_wattage": self.panel_wattage,
            "system_efficiency_pct": round(self.system_efficiency * 100, 1),
            "inverter_efficiency_pct": round(self.inverter_efficiency * 100, 1),
            "effective_daily_wh": round(self.effective_daily_wh, 1),
            "panels_required": self.panels_required,
            "total_array_watts": round(self.total_array_watts, 1),
            "array_current_a": round(self.array_current_a, 1),
            "charge_controller_a": self.charge_controller_a,
        }


class SolarCalculator:
    """
    Sizes a PV array given load demand and site parameters.

    Formula chain:
        Effective Wh = daily_wh / (system_eff × inverter_eff)
        Array W      = Effective Wh / PSH
        Panels       = ceil(Array W / panel_wattage)
        Total Array  = panels × panel_wattage
        Array I      = Total Array W / system_voltage
        CC Rating    = next standard MPPT size above Array I × 1.25
    """

    # Standard MPPT charge controller sizes (A)
    CC_SIZES = [10, 20, 30, 40, 50, 60, 80, 100, 120, 150, 200]

    def calculate(
        self,
        daily_wh: float,
        system_voltage: int,
        peak_sun_hours: float,
        panel_wattage: int,
        system_efficiency_pct: float = 80.0,
        inverter_efficiency_pct: float = 90.0,
    ) -> SolarResult:
        """
        Parameters
        ----------
        daily_wh               : total daily energy demand (Wh) from load analysis
        system_voltage         : int — 12, 24, or 48 V
        peak_sun_hours         : float — PSH for site (e.g. 5.5)
        panel_wattage          : int — rated wattage of each panel
        system_efficiency_pct  : float — derating % (default 80)
        inverter_efficiency_pct: float — inverter % (default 90)

        Returns
        -------
        SolarResult with all fields populated.
        """
        sys_eff = system_efficiency_pct / 100.0
        inv_eff = inverter_efficiency_pct / 100.0
        combined_eff = sys_eff * inv_eff

        # Energy the panels must actually produce
        effective_wh = daily_wh / combined_eff if combined_eff else daily_wh

        # Required array wattage
        array_w = effective_wh / peak_sun_hours if peak_sun_hours else effective_wh

        # Number of panels (always round up)
        panels = math.ceil(array_w / panel_wattage) if panel_wattage else 1

        total_array = panels * panel_wattage
        array_current = total_array / system_voltage if system_voltage else 0

        # Charge controller: array current × 1.25 safety, then next standard
        cc_a = self._next_cc(array_current * 1.25)

        return SolarResult(
            daily_wh_required=daily_wh,
            system_voltage=system_voltage,
            peak_sun_hours=peak_sun_hours,
            panel_wattage=panel_wattage,
            system_efficiency=sys_eff,
            inverter_efficiency=inv_eff,
            effective_daily_wh=effective_wh,
            panels_required=panels,
            total_array_watts=total_array,
            array_current_a=round(array_current, 2),
            charge_controller_a=cc_a,
        )

    def _next_cc(self, required_a: float) -> float:
        for size in self.CC_SIZES:
            if size >= required_a:
                return float(size)
        return math.ceil(required_a / 10) * 10
