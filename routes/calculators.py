"""
SolarCalc Pro — Route handlers for all calculator views.
Each step POSTs form data, runs the engine, stores results in session,
then either renders the next step or redirects.
"""

from flask import (
    Blueprint, render_template, request,
    session, redirect, url_for, jsonify
)
from engine import (
    LoadCalculator, SolarCalculator,
    BatteryCalculator, CableCalculator,
)

bp = Blueprint("calc", __name__)

# ──────────────────────────────────────────────
#  HOME
# ──────────────────────────────────────────────
@bp.route("/")
def home():
    return render_template("home.html")


# ──────────────────────────────────────────────
#  STEP 1 — LOAD ANALYSIS
# ──────────────────────────────────────────────
@bp.route("/load-analysis", methods=["GET", "POST"])
def load_analysis():
    if request.method == "POST":
        # Collect appliance rows from the dynamic table
        names  = request.form.getlist("app_name[]")
        watts  = request.form.getlist("app_watts[]")
        qtys   = request.form.getlist("app_qty[]")
        hours  = request.form.getlist("app_hours[]")

        appliances = []
        for n, w, q, h in zip(names, watts, qtys, hours):
            try:
                appliances.append({
                    "name": n,
                    "watts": float(w),
                    "quantity": int(q),
                    "hours_per_day": float(h),
                })
            except (ValueError, TypeError):
                continue

        voltage_raw = request.form.get("system_voltage", "24")
        voltage = int("".join(filter(str.isdigit, voltage_raw.split("V")[0])))
        safety = float(request.form.get("safety_factor", 25))

        result = LoadCalculator().calculate(appliances, voltage, safety)
        session["load"] = result.to_dict()

        return redirect(url_for("calc.solar_sizing"))

    # GET — pre-populate with default appliances if nothing in session
    prev = session.get("load", {})
    return render_template("load_analysis.html", prev=prev)


# ──────────────────────────────────────────────
#  STEP 2 — SOLAR SIZING
# ──────────────────────────────────────────────
@bp.route("/solar-sizing", methods=["GET", "POST"])
def solar_sizing():
    load = session.get("load")
    if not load:
        return redirect(url_for("calc.load_analysis"))

    if request.method == "POST":
        psh     = float(request.form.get("psh", 5.5))
        wattage_raw = request.form.get("panel_wattage", "400")
        wattage = int("".join(filter(str.isdigit, wattage_raw.split("W")[0])))
        sys_eff = float(request.form.get("system_efficiency", 80))
        inv_eff = float(request.form.get("inverter_efficiency", 90))

        result = SolarCalculator().calculate(
            daily_wh=load["total_daily_wh_with_safety"],
            system_voltage=load["system_voltage"],
            peak_sun_hours=psh,
            panel_wattage=wattage,
            system_efficiency_pct=sys_eff,
            inverter_efficiency_pct=inv_eff,
        )
        session["solar"] = result.to_dict()
        return redirect(url_for("calc.battery_bank"))

    prev = session.get("solar", {})
    return render_template("solar_sizing.html", load=load, prev=prev)


# ──────────────────────────────────────────────
#  STEP 3 — BATTERY BANK
# ──────────────────────────────────────────────
@bp.route("/battery-bank", methods=["GET", "POST"])
def battery_bank():
    load  = session.get("load")
    solar = session.get("solar")
    if not load:
        return redirect(url_for("calc.load_analysis"))

    if request.method == "POST":
        autonomy    = int(request.form.get("days_autonomy", 2))
        dod         = float(request.form.get("dod_pct", 50))
        batt_type   = request.form.get("battery_type", "Lead-Acid")
        batt_v_raw  = request.form.get("battery_voltage", "12")
        batt_v      = int("".join(filter(str.isdigit, batt_v_raw.split("V")[0])))
        batt_ah     = float(request.form.get("battery_ah", 200))

        result = BatteryCalculator().calculate(
            daily_wh=load["total_daily_wh_with_safety"],
            system_voltage=load["system_voltage"],
            days_autonomy=autonomy,
            dod_pct=dod,
            battery_type=batt_type,
            battery_voltage=batt_v,
            battery_ah=batt_ah,
        )
        session["battery"] = result.to_dict()
        return redirect(url_for("calc.cable_sizing"))

    prev = session.get("battery", {})
    return render_template("battery_bank.html", load=load, solar=solar, prev=prev)


# ──────────────────────────────────────────────
#  STEP 4 — CABLE SIZING
# ──────────────────────────────────────────────
@bp.route("/cable-sizing", methods=["GET", "POST"])
def cable_sizing():
    load    = session.get("load")
    battery = session.get("battery")
    if not load:
        return redirect(url_for("calc.load_analysis"))

    if request.method == "POST":
        length      = float(request.form.get("cable_length", 10))
        current     = float(request.form.get("load_current", load.get("total_current_a", 100)))
        vdrop_max   = float(request.form.get("max_vdrop_pct", 3))
        conductor   = request.form.get("conductor", "Copper")
        installation= request.form.get("installation", "Clipped direct to surface")
        temp        = float(request.form.get("ambient_temp", 30))

        result = CableCalculator().calculate(
            load_current_a=current,
            cable_length_m=length,
            max_vdrop_pct=vdrop_max,
            conductor=conductor,
            installation=installation,
            ambient_temp_c=temp,
            system_voltage=load["system_voltage"],
        )
        session["cable"] = result.to_dict()
        return redirect(url_for("calc.results"))

    prev = session.get("cable", {})
    return render_template("cable_sizing.html", load=load, battery=battery, prev=prev)


# ──────────────────────────────────────────────
#  STEP 5 — RESULTS
# ──────────────────────────────────────────────
@bp.route("/results")
def results():
    load    = session.get("load")
    solar   = session.get("solar")
    battery = session.get("battery")
    cable   = session.get("cable")

    if not all([load, solar, battery, cable]):
        return redirect(url_for("calc.load_analysis"))

    return render_template(
        "results.html",
        load=load,
        solar=solar,
        battery=battery,
        cable=cable,
    )


# ──────────────────────────────────────────────
#  CLEAR SESSION (start over)
# ──────────────────────────────────────────────
@bp.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("calc.home"))
