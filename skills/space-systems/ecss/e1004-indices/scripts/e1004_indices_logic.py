#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 6.2.2 / Annex A solar and geomagnetic
activity index selection logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): F10.7
(10.7 cm solar radio flux, daily and 81-day-average forms) and Ap/Kp
(daily linear-scale and 3-hourly quasi-logarithmic geomagnetic activity
indices) are standard drivers for upper-atmosphere density models and
the EM radiation environment. Different analysis purposes need
different worst-case points on the roughly 11-year solar cycle: drag
and thermal analyses need solar maximum, deorbit/lifetime compliance
needs the opposite (solar minimum, since low density gives the
slowest decay), and EM radiation reference terms typically use the
solar-mean epoch. This module implements the index-requirement
identification, solar-cycle epoch determination, reference-value
selection, and completeness/condition verification logic; it does not
apply the selected indices inside a specific atmosphere, EM-radiation,
or geomagnetic-field model (see the sibling e1004-atmosphere,
e1004-em-radiation, e1004-geomag leaves) and it does not hold the full
tabulated Annex A solar-cycle history (see the sibling
e1004-annex-a-data reference leaf).
"""

REQUIRED_INDICES_BY_PURPOSE = {
    "drag_worst_case": ("f107_daily", "f107_81day_avg", "ap_daily"),
    "deorbit_lifetime_worst_case": ("f107_daily", "f107_81day_avg", "ap_daily"),
    "em_radiation_reference": ("f107_81day_avg",),
    "geomagnetic_field_epoch": ("kp_3hourly",),
}

REQUIRED_SOLAR_CONDITION_BY_PURPOSE = {
    "drag_worst_case": "solar_maximum",
    "deorbit_lifetime_worst_case": "solar_minimum",
    "em_radiation_reference": None,
    "geomagnetic_field_epoch": None,
}

F107_SOLAR_MIN_SFU = 70.0
F107_SOLAR_MAX_SFU = 200.0

REFERENCE_INDEX_VALUES = {
    "solar_minimum": {"f107_81day_avg": 70.0, "ap_daily": 5.0},
    "solar_mean": {"f107_81day_avg": 140.0, "ap_daily": 15.0},
    "solar_maximum": {"f107_81day_avg": 200.0, "ap_daily": 30.0},
}


def required_indices(purpose):
    """Tuple of index names required for one analysis purpose. Raises
    ValueError for an unknown purpose."""
    if purpose not in REQUIRED_INDICES_BY_PURPOSE:
        raise ValueError("unknown analysis purpose: %r" % (purpose,))
    return REQUIRED_INDICES_BY_PURPOSE[purpose]


def missing_indices(purpose, indices):
    """Names, in required order, of indices required for purpose that
    are absent or None in the indices dict."""
    return [
        name
        for name in required_indices(purpose)
        if indices.get(name) is None
    ]


def indices_complete(purpose, indices):
    """True when every index required for purpose is present and not
    None in the indices dict."""
    return len(missing_indices(purpose, indices)) == 0


def required_solar_condition(purpose):
    """Solar-cycle condition purpose fixes as its worst case
    (solar_minimum or solar_maximum), or None when the purpose has no
    fixed worst-case condition. Raises ValueError for an unknown
    purpose."""
    if purpose not in REQUIRED_SOLAR_CONDITION_BY_PURPOSE:
        raise ValueError("unknown analysis purpose: %r" % (purpose,))
    return REQUIRED_SOLAR_CONDITION_BY_PURPOSE[purpose]


def determine_solar_epoch(f107_81day_avg):
    """Determine the solar-cycle epoch an 81-day-average F10.7 value
    (solar flux units) represents: "solar_minimum" (at or below the
    solar-minimum reference), "solar_maximum" (at or above the
    solar-maximum reference), or "solar_mean". Raises ValueError when
    the value is not positive."""
    if f107_81day_avg <= 0:
        raise ValueError("F10.7 81-day average must be positive")
    if f107_81day_avg <= F107_SOLAR_MIN_SFU:
        return "solar_minimum"
    if f107_81day_avg >= F107_SOLAR_MAX_SFU:
        return "solar_maximum"
    return "solar_mean"


def reference_indices_for_epoch(epoch):
    """New dict of characteristic reference index values for a
    solar-cycle epoch ("solar_minimum", "solar_mean", or
    "solar_maximum"). Raises ValueError for an unknown epoch."""
    if epoch not in REFERENCE_INDEX_VALUES:
        raise ValueError("unknown solar-cycle epoch: %r" % (epoch,))
    return dict(REFERENCE_INDEX_VALUES[epoch])


def select_reference_indices(purpose):
    """Reference index values for the solar-cycle epoch purpose
    requires as its worst case, or for the solar-mean epoch when
    purpose has no fixed worst-case requirement. Raises ValueError for
    an unknown purpose."""
    condition = required_solar_condition(purpose)
    return reference_indices_for_epoch(condition or "solar_mean")


def assess_epoch_case(case):
    """Full index-selection and compliance assessment for one case
    dict. Required keys: id, purpose, indices (a dict of available
    index values). Returns a new dict; does not mutate the input.
    Raises ValueError when 'id' is missing or purpose is unknown."""
    if "id" not in case:
        raise ValueError("index epoch case is missing an id")
    purpose = case["purpose"]
    indices = case["indices"]
    missing = missing_indices(purpose, indices)
    complete = len(missing) == 0
    required_condition = required_solar_condition(purpose)

    solar_epoch = None
    condition_adequate = True
    f107_81day_avg = indices.get("f107_81day_avg")
    if f107_81day_avg is not None:
        solar_epoch = determine_solar_epoch(f107_81day_avg)
        if required_condition is not None:
            condition_adequate = solar_epoch == required_condition

    return {
        "id": case["id"],
        "purpose": purpose,
        "required_indices": list(required_indices(purpose)),
        "missing_indices": missing,
        "complete": complete,
        "solar_epoch": solar_epoch,
        "required_solar_condition": required_condition,
        "condition_adequate": condition_adequate,
        "compliant": complete and condition_adequate,
    }


def build_epoch_assessment(cases):
    """Assessment record: one assess_epoch_case() result per case, in
    input order. Raises ValueError on a duplicate case id."""
    record = []
    seen_ids = set()
    for case in cases:
        assessment = assess_epoch_case(case)
        if assessment["id"] in seen_ids:
            raise ValueError("duplicate index epoch case id: %r" % (assessment["id"],))
        seen_ids.add(assessment["id"])
        record.append(assessment)
    return record


def noncompliant_items(record):
    """Case ids in the record that are not compliant, in record
    order -- these cannot support handing an epoch to a consuming leaf
    as-is."""
    return [entry["id"] for entry in record if not entry["compliant"]]


def all_compliant(record):
    """True when every entry in the assessment record is compliant."""
    return len(noncompliant_items(record)) == 0
