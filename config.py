"""
SolarCalc Pro — Application Configuration
"""

import os


class Config:
    # Flask core
    SECRET_KEY = os.environ.get("SECRET_KEY", "solarcalc-dev-secret-2024")
    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

    # App meta
    APP_NAME = "SolarCalc Pro"
    APP_VERSION = "1.0.0"

    # Calculation defaults
    DEFAULT_SAFETY_FACTOR = 1.25        # NEC 125% rule
    DEFAULT_SYSTEM_EFFICIENCY = 0.80    # 80% derating
    DEFAULT_INVERTER_EFFICIENCY = 0.90  # 90% inverter efficiency
    DEFAULT_DOD_LEAD_ACID = 50          # % depth of discharge - Lead Acid
    DEFAULT_DOD_LITHIUM = 80            # % depth of discharge - LiFePO4

    # Cable conductor resistivity (ohm.mm2/m)
    RESISTIVITY_COPPER = 0.0172
    RESISTIVITY_ALUMINIUM = 0.0282

    # Standard cable sizes (mm2) - IEC/BS selection table
    STANDARD_CABLE_SIZES = [
        1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300
    ]

    # Common panel wattages (W)
    PANEL_WATTAGES = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600]

    # Battery voltages available
    BATTERY_VOLTAGES = [2, 6, 12, 24]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
