"""Blood pressure classifier following AHA guidelines.

Pure function. Takes systolic + diastolic integers and returns a
classification dict. When systolic and diastolic fall into *different*
categories the **higher** (more severe) classification is used, per AHA
guidance.

Dependencies: None — pure Python, zero imports.
"""

from typing import Any, Dict


# ── AHA thresholds (upper-bound inclusive for the *lower* category) ──────────
# Each tuple: (max_systolic_for_category, max_diastolic_for_category, metadata)
# We iterate top-down so the *first* match wins.

_BP_CATEGORIES: list[Dict[str, Any]] = [
    {
        "category": "crisis",
        "label": "Hypertensive Crisis",
        "severity": 5,
        "color": "red_bg",
        "action": "Call emergency services. Do not wait.",
        "requires_second_reading": True,
        "systolic_min": 181,
        "diastolic_min": 121,
    },
    {
        "category": "stage_2",
        "label": "Stage 2 Hypertension",
        "severity": 4,
        "color": "red",
        "action": "Urgent referral + lifestyle plan",
        "requires_second_reading": True,
        "systolic_min": 140,
        "diastolic_min": 90,
    },
    {
        "category": "stage_1",
        "label": "Stage 1 Hypertension",
        "severity": 3,
        "color": "orange",
        "action": "Lifestyle changes + follow-up in 3-6 months",
        "requires_second_reading": True,
        "systolic_min": 130,
        "diastolic_min": 80,
    },
    {
        "category": "elevated",
        "label": "Elevated Blood Pressure",
        "severity": 2,
        "color": "yellow",
        "action": "Lifestyle modifications recommended",
        "requires_second_reading": True,
        "systolic_min": 120,
        "diastolic_min": 80,  # diastolic stays < 80 for elevated
    },
    {
        "category": "normal",
        "label": "Normal Blood Pressure",
        "severity": 1,
        "color": "green",
        "action": "Maintain healthy lifestyle",
        "requires_second_reading": False,
        "systolic_min": 0,
        "diastolic_min": 0,
    },
]


def _category_for_value(
    value: int,
    is_systolic: bool,
) -> Dict[str, Any]:
    """Return the matching category dict for a single axis value.

    Args:
        value: The systolic or diastolic reading.
        is_systolic: True when classifying systolic, False for diastolic.

    Returns:
        The category dict whose range the value falls into.
    """
    key = "systolic_min" if is_systolic else "diastolic_min"
    for cat in _BP_CATEGORIES:
        if value >= cat[key]:
            return cat
    # Fallback — should never happen after validation.
    return _BP_CATEGORIES[-1]  # normal


def classify_bp(systolic: int, diastolic: int) -> Dict[str, Any]:
    """Classify a blood-pressure reading per AHA guidelines.

    When the systolic and diastolic values fall into different categories
    the **higher** (more severe) classification is returned (AHA rule).

    Args:
        systolic: Systolic pressure in mmHg (valid range 60-300).
        diastolic: Diastolic pressure in mmHg (valid range 30-200).

    Returns:
        A dict with keys: category, label, severity, color, action,
        requires_second_reading.

    Raises:
        ValueError: If either value is outside its valid range.

    Example:
        >>> classify_bp(142, 91)
        {'category': 'stage_2', 'label': 'Stage 2 Hypertension', ...}
    """
    # ── Input validation ────────────────────────────────────────────────
    if not isinstance(systolic, int) or not isinstance(diastolic, int):
        raise ValueError("Systolic and diastolic must be integers.")
    if systolic < 60 or systolic > 300:
        raise ValueError(
            f"Invalid systolic value {systolic}: must be between 60 and 300."
        )
    if diastolic < 30 or diastolic > 200:
        raise ValueError(
            f"Invalid diastolic value {diastolic}: must be between 30 and 200."
        )

    # ── Classify each axis independently ────────────────────────────────
    sys_cat = _category_for_value(systolic, is_systolic=True)
    dia_cat = _category_for_value(diastolic, is_systolic=False)

    # ── "Elevated" is a systolic-only category (120-129 AND <80) ────────
    # Per AHA: Elevated = systolic 120-129 AND diastolic < 80.
    # If diastolic >= 80 with systolic 120-129, it's actually Stage 1.
    # Our lookup already handles this because diastolic_min for stage_1 is 80.
    # However, if systolic < 120 but diastolic >= 80, diastolic drives it to
    # stage_1 via the "higher wins" rule below.

    # ── Higher severity wins (AHA guideline) ────────────────────────────
    winner = sys_cat if sys_cat["severity"] >= dia_cat["severity"] else dia_cat

    return {
        "category": winner["category"],
        "label": winner["label"],
        "severity": winner["severity"],
        "color": winner["color"],
        "action": winner["action"],
        "requires_second_reading": winner["requires_second_reading"],
    }
