"""
SolarCalc Pro — Cable Sizing Engine
Calculates minimum cable cross-sectional area and voltage drop for a DC cable run.
"""

import math
from dataclasses import dataclass
from typing import Optional


# IEC 60228 / BS 6004 current-carrying capacity (A) for copper clipped direct
# Index maps to STANDARD_SIZES below. Values are approximate; derate for other methods.
COPPER_CLIPPED_CCC = {
    1.5: 19, 2.5: 26, 4: 35, 6: 46, 10: 63, 16: 85,
    25: 110, 35: 133, 50: 159, 70: 200, 95: 241,
    120: 278, 150: 318, 185: 362, 240: 424, 300: 486,
}

# Temperature correction factors (base 30 °C, XLPE/PVC insulation)
TEMP_CORRECTION = {
    25: 1.03, 30: 1.00, 35: 0.96, 40: 0.91,
    45: 0.87, 50: 0.82, 55: 0.76, 60: 0.71,
}

STANDARD_SIZES = sorted(COPPER_CLIPPED_CCC.keys())


@dataclass
class CableResult:
    """Output of the cable sizing calculation."""
    load_current_a: float
    cable_length_m: float
    max_vdrop_pct: float
    conductor: str              # 'Copper' | 'Aluminium'
    installation: str
    ambient_temp_c: float
    system_voltage: int

    # Calculated
    resistivity: float = 0.0
    min_csa_by_vdrop_mm2: float = 0.0   # from voltage-drop formula
    min_csa_by_ccc_mm2: float = 0.0     # from current-carrying capacity
    selected_csa_mm2: float = 0.0       # larger of the two (next standard size)
    actual_vdrop_v: float = 0.0
    actual_vdrop_pct: float = 0.0
    is_safe: bool = True

    @property
    def safety_label(self) -> str:
        return "SAFE ✓" if self.is_safe else "EXCEEDS LIMIT ✗"

    def to_dict(self) -> dict:
        return {
            "load_current_a": round(self.load_current_a, 1),
            "cable_length_m": self.cable_length_m,
            "max_vdrop_pct": self.max_vdrop_pct,
            "conductor": self.conductor,
            "installation": self.installation,
            "ambient_temp_c": self.ambient_temp_c,
            "system_voltage": self.system_voltage,
            "min_csa_by_vdrop_mm2": round(self.min_csa_by_vdrop_mm2, 2),
            "min_csa_by_ccc_mm2": self.min_csa_by_ccc_mm2,
            "selected_csa_mm2": self.selected_csa_mm2,
            "actual_vdrop_v": round(self.actual_vdrop_v, 3),
            "actual_vdrop_pct": round(self.actual_vdrop_pct, 2),
            "is_safe": self.is_safe,
            "safety_label": "SAFE ✓" if self.is_safe else "EXCEEDS LIMIT ✗",
        }


class CableCalculator:
    """
    DC cable sizing per IEC/BS voltage-drop and CCC methods.

    Voltage-drop formula (DC, both conductors):
        CSA (mm²) = (2 × ρ × L × I) / V_drop_allowed

    Current-carrying capacity:
        Derated CCC = CCC_base × temp_correction_factor
        Select smallest standard size where derated CCC >= load current
    """

    RESISTIVITY = {
        "Copper": 0.0172,
        "Aluminium": 0.0282,
    }

    # Installation method derating multipliers
    INSTALL_DERATING = {
        "Clipped direct to surface": 1.00,
        "In conduit / trunking": 0.80,
        "Underground": 0.90,
    }

    def calculate(
        self,
        load_current_a: float,
        cable_length_m: float,
        max_vdrop_pct: float,
        conductor: str,
        installation: str,
        ambient_temp_c: float,
        system_voltage: int,
    ) -> CableResult:
        """
        Parameters
        ----------
        load_current_a  : design current (A)
        cable_length_m  : one-way run length (m)  — formula uses 2× for return path
        max_vdrop_pct   : allowable voltage drop (%)
        conductor       : 'Copper' | 'Aluminium'
        installation    : installation method string
        ambient_temp_c  : ambient temperature (°C)
        system_voltage  : DC bus voltage (V)

        Returns
        -------
        CableResult with all fields populated.
        """
        rho = self.RESISTIVITY.get(conductor, 0.0172)
        v_drop_allowed = system_voltage * (max_vdrop_pct / 100.0)

        # --- Method 1: Voltage drop ---
        # CSA = (2 × rho × L × I) / V_drop_max
        if v_drop_allowed > 0:
            csa_vdrop = (2 * rho * cable_length_m * load_current_a) / v_drop_allowed
        else:
            csa_vdrop = 0

        # --- Method 2: Current-carrying capacity ---
        install_factor = self.INSTALL_DERATING.get(installation, 1.0)
        temp_factor = self._temp_factor(ambient_temp_c)
        combined_factor = install_factor * temp_factor

        csa_ccc = 0.0
        for size in STANDARD_SIZES:
            derated = COPPER_CLIPPED_CCC[size] * combined_factor
            if conductor == "Aluminium":
                # Aluminium carries ~78% of copper at same size
                derated *= 0.78
            if derated >= load_current_a:
                csa_ccc = size
                break

        # --- Select the larger of the two ---
        min_required = max(csa_vdrop, csa_ccc)
        selected = self._next_standard(min_required)

        # --- Recalculate actual voltage drop at selected size ---
        resistance = (2 * rho * cable_length_m) / selected if selected else 0
        actual_vdrop_v = load_current_a * resistance
        actual_vdrop_pct = (actual_vdrop_v / system_voltage) * 100 if system_voltage else 0

        return CableResult(
            load_current_a=load_current_a,
            cable_length_m=cable_length_m,
            max_vdrop_pct=max_vdrop_pct,
            conductor=conductor,
            installation=installation,
            ambient_temp_c=ambient_temp_c,
            system_voltage=system_voltage,
            resistivity=rho,
            min_csa_by_vdrop_mm2=csa_vdrop,
            min_csa_by_ccc_mm2=csa_ccc,
            selected_csa_mm2=selected,
            actual_vdrop_v=actual_vdrop_v,
            actual_vdrop_pct=actual_vdrop_pct,
            is_safe=actual_vdrop_pct <= max_vdrop_pct,
        )

    def _temp_factor(self, temp_c: float) -> float:
        """Interpolate temperature correction factor."""
        temps = sorted(TEMP_CORRECTION.keys())
        if temp_c <= temps[0]:
            return TEMP_CORRECTION[temps[0]]
        if temp_c >= temps[-1]:
            return TEMP_CORRECTION[temps[-1]]
        # Linear interpolation between nearest entries
        for i in range(len(temps) - 1):
            t0, t1 = temps[i], temps[i + 1]
            if t0 <= temp_c <= t1:
                f0, f1 = TEMP_CORRECTION[t0], TEMP_CORRECTION[t1]
                return f0 + (f1 - f0) * (temp_c - t0) / (t1 - t0)
        return 1.0

    def _next_standard(self, required_mm2: float) -> float:
        """Return the next standard cable size >= required_mm2."""
        for size in STANDARD_SIZES:
            if size >= required_mm2:
                return size
        return STANDARD_SIZES[-1]
