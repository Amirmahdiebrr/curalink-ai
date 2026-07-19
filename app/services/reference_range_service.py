"""
Reference range analyzer.

Compares extracted laboratory values
with normal ranges.
"""


from app.data.reference_ranges import (
    REFERENCE_RANGES,
)



class ReferenceRangeService:
    """
    Analyze laboratory values.
    """


    @staticmethod
    def check(
        parameter: str,
        value: float
    ) -> dict:
        """
        Compare value with reference range.
        """


        if parameter not in REFERENCE_RANGES:

            return {

                "status": "unknown",

                "value": value

            }



        reference = (
            REFERENCE_RANGES[parameter]
        )


        minimum = reference["min"]

        maximum = reference["max"]



        if value < minimum:

            status = "low"


        elif value > maximum:

            status = "high"


        else:

            status = "normal"



        return {

            "value": value,

            "status": status,

            "reference": {

                "min": minimum,

                "max": maximum,

                "unit": reference["unit"]

            }

        }