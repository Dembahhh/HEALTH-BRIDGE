"""Blood glucose classifier supporting random and fasting test types.

Pure function. Takes a glucose value, test type (random | fasting), and
an optional unit (mmol_l | mg_dl). Returns a classification dict.

Thresholds (mmol/L)
-------------------
+---------------+---------------------+---------------------+
| Category      | Random (mmol/L)     | Fasting (mmol/L)    |
+---------------+---------------------+---------------------+
| Normal        | < 7.8               | < 5.6               |
| Pre-diabetic  | 7.8 – 11.0          | 5.6 – 6.9           |
| Diabetic      | > 11.0              | >= 7.0              |
+---------------+---------------------+---------------------+

Thresholds (mg/dL)
------------------
+---------------+---------------------+---------------------+
| Category      | Random (mg/dL)      | Fasting (mg/dL)     |
+---------------+---------------------+---------------------+
| Normal        | < 140               | < 100               |
| Pre-diabetic  | 140 – 199           | 100 – 125           |
| Diabetic      | >= 200              | >= 126              |
+---------------+---------------------+---------------------+

Using native mg/dL thresholds (ADA standard) avoids rounding errors
from the mmol/L ÷ 18 conversion at boundary values.

Dependencies: None — pure Python, zero imports.
"""

from typing import Any, Dict, Literal


# ── Conversion constant ─────────────────────────────────────────────────
_MG_DL_TO_MMOL_L = 1.0 / 18.0


# ── Threshold tables  ───────────────────────────────────────────────────
# Each list is ordered from highest severity down.
# Tuple: (lower_bound_inclusive, category, label, severity, color, action)

_RANDOM_MMOL: list[tuple[float, str, str, int, str, str]] = [
    (11.1, "diabetic", "Diabetic range", 3, "red",
     "Refer for HbA1c confirmation + lifestyle plan"),
    (7.8, "pre_diabetic", "Elevated / Pre-diabetic range", 2, "orange",
     "Lifestyle plan + recommend fasting glucose lab test"),
    (0.0, "normal", "Normal blood glucose", 1, "green",
     "Maintain healthy diet and regular activity"),
]

_FASTING_MMOL: list[tuple[float, str, str, int, str, str]] = [
    (7.0, "diabetic", "Diabetic range (fasting)", 3, "red",
     "Refer for HbA1c confirmation + lifestyle plan"),
    (5.6, "pre_diabetic", "Elevated / Pre-diabetic range (fasting)", 2,
     "orange", "Lifestyle plan + recommend follow-up fasting test"),
    (0.0, "normal", "Normal fasting glucose", 1, "green",
     "Maintain healthy diet and regular activity"),
]

_RANDOM_MGDL: list[tuple[float, str, str, int, str, str]] = [
    (200.0, "diabetic", "Diabetic range", 3, "red",
     "Refer for HbA1c confirmation + lifestyle plan"),
    (140.0, "pre_diabetic", "Elevated / Pre-diabetic range", 2, "orange",
     "Lifestyle plan + recommend fasting glucose lab test"),
    (0.0, "normal", "Normal blood glucose", 1, "green",
     "Maintain healthy diet and regular activity"),
]

_FASTING_MGDL: list[tuple[float, str, str, int, str, str]] = [
    (126.0, "diabetic", "Diabetic range (fasting)", 3, "red",
     "Refer for HbA1c confirmation + lifestyle plan"),
    (100.0, "pre_diabetic", "Elevated / Pre-diabetic range (fasting)", 2,
     "orange", "Lifestyle plan + recommend follow-up fasting test"),
    (0.0, "normal", "Normal fasting glucose", 1, "green",
     "Maintain healthy diet and regular activity"),
]

# Quick lookup: (test_type, unit) → threshold table
_THRESHOLD_MAP = {
    ("random", "mmol_l"): _RANDOM_MMOL,
    ("fasting", "mmol_l"): _FASTING_MMOL,
    ("random", "mg_dl"): _RANDOM_MGDL,
    ("fasting", "mg_dl"): _FASTING_MGDL,
}


def convert_mg_dl_to_mmol_l(mg_dl_value: float) -> float:
    """Convert a mg/dL glucose reading to mmol/L.

    Args:
        mg_dl_value: Glucose value in mg/dL.

    Returns:
        Equivalent value in mmol/L, rounded to 2 decimal places.

    Example:
        >>> convert_mg_dl_to_mmol_l(140)
        7.78
    """
    return round(mg_dl_value * _MG_DL_TO_MMOL_L, 2)


def classify_glucose(
    value: float,
    test_type: Literal["random", "fasting"],
    unit: Literal["mmol_l", "mg_dl"] = "mmol_l",
) -> Dict[str, Any]:
    """Classify a blood-glucose reading.

    Supports both random and fasting test types, and both mmol/L and
    mg/dL input units.  When mg/dL is provided the classification uses
    native ADA mg/dL thresholds to avoid rounding-boundary issues; the
    normalised mmol/L value is still included in the return dict.

    Args:
        value: Glucose reading (in the unit specified by ``unit``).
        test_type: Either ``"random"`` or ``"fasting"``.
        unit: Either ``"mmol_l"`` (default) or ``"mg_dl"``.

    Returns:
        A dict with keys: category, label, severity, color, action,
        test_type, unit, value_mmol.

    Raises:
        ValueError: If value is negative / zero, test_type is invalid,
            or unit is invalid.

    Example:
        >>> classify_glucose(9.0, "random")
        {'category': 'pre_diabetic', 'label': 'Elevated / Pre-diabetic range', ...}
    """
    # ── Input validation ────────────────────────────────────────────────
    if test_type not in ("random", "fasting"):
        raise ValueError(
            f"Invalid test_type '{test_type}': must be 'random' or 'fasting'."
        )

    if unit not in ("mmol_l", "mg_dl"):
        raise ValueError(
            f"Invalid unit '{unit}': must be 'mmol_l' or 'mg_dl'."
        )

    if not isinstance(value, (int, float)):
        raise ValueError("Glucose value must be a number.")

    if value <= 0:
        raise ValueError(
            f"Invalid glucose value {value}: must be a positive number."
        )

    # ── Always store the normalised mmol/L value ────────────────────────
    value_mmol: float = (
        convert_mg_dl_to_mmol_l(value) if unit == "mg_dl" else round(float(value), 2)
    )

    # ── Classify using native thresholds for the given unit ─────────────
    thresholds = _THRESHOLD_MAP[(test_type, unit)]

    for lower_bound, category, label, severity, color, action in thresholds:
        if float(value) >= lower_bound:
            return {
                "category": category,
                "label": label,
                "severity": severity,
                "color": color,
                "action": action,
                "test_type": test_type,
                "unit": unit,
                "value_mmol": value_mmol,
            }

    # Fallback — should never be reached after validation.
    return {
        "category": "normal",
        "label": "Normal blood glucose",
        "severity": 1,
        "color": "green",
        "action": "Maintain healthy diet and regular activity",
        "test_type": test_type,
        "unit": unit,
        "value_mmol": value_mmol,
    }
