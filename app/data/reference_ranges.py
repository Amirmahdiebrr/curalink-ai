"""
Reference ranges for common laboratory parameters.

Note:
These are general adult ranges.
They must be configurable in future
based on age, sex, and laboratory source.
"""


REFERENCE_RANGES = {

    "Hb": {
        "min": 12,
        "max": 17,
        "unit": "g/dL",
    },


    "WBC": {
        "min": 4000,
        "max": 11000,
        "unit": "/µL",
    },


    "RBC": {
        "min": 4,
        "max": 6,
        "unit": "million/µL",
    },


    "Platelet": {
        "min": 150000,
        "max": 450000,
        "unit": "/µL",
    },


    "Glucose": {
        "min": 70,
        "max": 100,
        "unit": "mg/dL",
    },


    "Creatinine": {
        "min": 0.6,
        "max": 1.3,
        "unit": "mg/dL",
    },


    "TSH": {
        "min": 0.4,
        "max": 4,
        "unit": "mIU/L",
    },

}