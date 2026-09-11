"""
Element qualification test baseline logic — ECSS-E-ST-10C §6.2, Tables 6-1/6-2.
Paraphrased procedure; cite standard+clause only. No verbatim ECSS text.
"""

# ── Valid value sets ─────────────────────────────────────────────────────────

VALID_ELEMENT_CATEGORIES = frozenset({
    "flight_model",
    "protoflight_model",
    "engineering_model",
    "breadboard",
})

VALID_QUAL_CATEGORIES = frozenset({"full_qualification", "protoflight"})

VALID_TEST_TYPES = frozenset({
    "sine_vibration",
    "random_vibration",
    "shock",
    "thermal_cycling",
    "thermal_vacuum",
    "acoustic",
    "quasi_static",
})

VALID_ENVIRONMENT_DRIVERS = frozenset({
    "launch_vibration",
    "launch_acoustic",
    "launch_shock",
    "on_orbit_thermal",
    "pyrotechnic_shock",
})

# ── Margins (paraphrased from §6.2 Table 6-1) ───────────────────────────────
# vibration / acoustic / shock: +3 dB over acceptance
# thermal: +10 °C upper, -10 °C lower
# quasi-static: ×1.5 load factor

LEVEL_MARGINS = {
    "sine_vibration":   {"margin_type": "db",     "margin": 3.0},
    "random_vibration": {"margin_type": "db",     "margin": 3.0},
    "acoustic":         {"margin_type": "db",     "margin": 3.0},
    "shock":            {"margin_type": "db",     "margin": 3.0},
    "thermal_cycling":  {"margin_type": "degc",   "margin": 10.0},
    "thermal_vacuum":   {"margin_type": "degc",   "margin": 10.0},
    "quasi_static":     {"margin_type": "factor", "margin": 1.5},
}

# ── Duration rules (paraphrased from §6.2 Table 6-2) ────────────────────────
# sine_vibration: 2× acceptance duration
# random_vibration: 4× acceptance duration, minimum 120 s per axis
# acoustic: 2× acceptance duration
# shock: minimum 3 shots per axis, factor 1× (acceptance shots count)
# thermal_cycling: 2× acceptance cycle count
# thermal_vacuum: acceptance soak + 2 h extra per level
# quasi_static: same duration as acceptance (load is the margin)

DURATION_RULES = {
    "sine_vibration":   {"factor": 2.0, "min_s": None,  "extra_hrs": None, "min_shots": None},
    "random_vibration": {"factor": 4.0, "min_s": 120.0, "extra_hrs": None, "min_shots": None},
    "acoustic":         {"factor": 2.0, "min_s": None,  "extra_hrs": None, "min_shots": None},
    "shock":            {"factor": 1.0, "min_s": None,  "extra_hrs": None, "min_shots": 3},
    "thermal_cycling":  {"factor": 2.0, "min_s": None,  "extra_hrs": None, "min_shots": None},
    "thermal_vacuum":   {"factor": 1.0, "min_s": None,  "extra_hrs": 2.0,  "min_shots": None},
    "quasi_static":     {"factor": 1.0, "min_s": None,  "extra_hrs": None, "min_shots": None},
}

# ── Environment driver → required test types ─────────────────────────────────

ENVIRONMENT_TEST_MAP = {
    "launch_vibration":  frozenset({"sine_vibration", "random_vibration", "quasi_static"}),
    "launch_acoustic":   frozenset({"acoustic"}),
    "launch_shock":      frozenset({"shock"}),
    "on_orbit_thermal":  frozenset({"thermal_cycling", "thermal_vacuum"}),
    "pyrotechnic_shock": frozenset({"shock"}),
}


# ── Public API ───────────────────────────────────────────────────────────────

def determine_qual_category(element_category, dedicated_proto_tested):
    """
    Determine the qualification approach for a hardware item.

    A dedicated prototype that has been fully tested before the flight article
    enables full_qualification (separate articles, each at their respective
    levels). When a single article must serve as both the qualification unit
    and the flight unit, protoflight applies (qualification levels, acceptance
    durations).

    Args:
        element_category (str): one of VALID_ELEMENT_CATEGORIES.
        dedicated_proto_tested (bool): True when a dedicated prototype model
            has already completed the full qualification test sequence.

    Returns:
        str: "full_qualification" or "protoflight".

    Raises:
        ValueError: for unknown element_category or breadboard items.
        TypeError: if dedicated_proto_tested is not bool.
    """
    if element_category not in VALID_ELEMENT_CATEGORIES:
        raise ValueError(
            "Unknown element_category '{}'. Expected one of {}.".format(
                element_category, sorted(VALID_ELEMENT_CATEGORIES)
            )
        )
    if element_category == "breadboard":
        raise ValueError(
            "Breadboard items do not carry a flight qualification category "
            "and cannot be assigned a qualification test baseline."
        )
    if not isinstance(dedicated_proto_tested, bool):
        raise TypeError(
            "dedicated_proto_tested must be bool, got {}.".format(
                type(dedicated_proto_tested).__name__
            )
        )

    if element_category == "protoflight_model" or not dedicated_proto_tested:
        return "protoflight"
    return "full_qualification"


def determine_required_tests(environment_drivers):
    """
    Map a list of environment driver strings to the minimum required test types
    for the element qualification baseline per §6.2.

    Args:
        environment_drivers (list[str]): non-empty list of driver names from
            VALID_ENVIRONMENT_DRIVERS.

    Returns:
        set[str]: test type names from VALID_TEST_TYPES.

    Raises:
        ValueError: if the list is empty or contains unrecognized drivers.
    """
    if not environment_drivers:
        raise ValueError(
            "At least one environment driver must be provided."
        )
    unknown = [d for d in environment_drivers if d not in VALID_ENVIRONMENT_DRIVERS]
    if unknown:
        raise ValueError(
            "Unrecognized environment drivers: {}. Expected subset of {}.".format(
                unknown, sorted(VALID_ENVIRONMENT_DRIVERS)
            )
        )
    required = set()
    for driver in environment_drivers:
        required |= ENVIRONMENT_TEST_MAP[driver]
    return required


def compute_qual_level(test_type, acceptance_level, upper=True):
    """
    Compute the qualification level for a given test type.

    For vibration, acoustic, shock: qual_level = acceptance_level + 3 dB.
    For thermal (upper bound): qual_level = acceptance_level + 10 °C.
    For thermal (lower bound, upper=False): qual_level = acceptance_level - 10 °C.
    For quasi_static: qual_level = acceptance_level × 1.5.

    Args:
        test_type (str): one of VALID_TEST_TYPES.
        acceptance_level (float): baseline acceptance value.
        upper (bool): for thermal types, whether to apply the upper (+) or
            lower (-) margin. Ignored for non-thermal test types.

    Returns:
        dict: {test_type, acceptance_level, qual_level, margin, margin_type}.

    Raises:
        ValueError: for unknown test type or non-finite acceptance_level.
    """
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(
            "Unknown test type '{}'. Expected one of {}.".format(
                test_type, sorted(VALID_TEST_TYPES)
            )
        )
    try:
        acceptance_level = float(acceptance_level)
    except (TypeError, ValueError):
        raise ValueError(
            "acceptance_level must be numeric, got {!r}.".format(acceptance_level)
        )

    rule = LEVEL_MARGINS[test_type]
    margin_type = rule["margin_type"]
    margin = rule["margin"]

    if margin_type == "db":
        qual_level = acceptance_level + margin
    elif margin_type == "degc":
        qual_level = acceptance_level + margin if upper else acceptance_level - margin
    elif margin_type == "factor":
        qual_level = acceptance_level * margin
    else:
        raise ValueError("Unhandled margin_type '{}'.".format(margin_type))

    return {
        "test_type": test_type,
        "acceptance_level": acceptance_level,
        "qual_level": qual_level,
        "margin": margin,
        "margin_type": margin_type,
    }


def compute_qual_duration(test_type, acceptance_duration, qual_category):
    """
    Compute the qualification test duration.

    Full qualification applies the §6.2 Table 6-2 duration factors (or adds
    the thermal-vacuum soak margin) and enforces floor minimums.
    Protoflight uses qualification levels but acceptance durations; minimums
    (e.g. random-vibration 120 s, shock 3 shots) still apply.

    Args:
        test_type (str): one of VALID_TEST_TYPES.
        acceptance_duration (float): acceptance value (seconds for vibration/
            acoustic, hours for thermal, shots for shock, cycles for thermal
            cycling).
        qual_category (str): "full_qualification" or "protoflight".

    Returns:
        dict: {test_type, acceptance_duration, qual_duration, factor, notes}.

    Raises:
        ValueError: for invalid inputs or non-positive acceptance_duration.
    """
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(
            "Unknown test type '{}'.".format(test_type)
        )
    if qual_category not in VALID_QUAL_CATEGORIES:
        raise ValueError(
            "Unknown qual_category '{}'. Expected one of {}.".format(
                qual_category, sorted(VALID_QUAL_CATEGORIES)
            )
        )
    try:
        acceptance_duration = float(acceptance_duration)
    except (TypeError, ValueError):
        raise ValueError(
            "acceptance_duration must be numeric, got {!r}.".format(
                acceptance_duration
            )
        )
    if acceptance_duration <= 0:
        raise ValueError(
            "acceptance_duration must be positive, got {}.".format(
                acceptance_duration
            )
        )

    rule = DURATION_RULES[test_type]
    notes = []

    if qual_category == "protoflight":
        qual_duration = acceptance_duration
        factor = 1.0
        notes.append("protoflight: qualification level, acceptance duration")
    else:
        # full_qualification: apply duration factor
        if test_type == "thermal_vacuum":
            extra = rule["extra_hrs"]
            qual_duration = acceptance_duration + extra
            factor = None
            notes.append("added {} h soak margin per Table 6-2".format(extra))
        else:
            factor = rule["factor"]
            qual_duration = acceptance_duration * factor

    # Enforce minimums regardless of qual_category
    min_s = rule["min_s"]
    if min_s is not None and qual_duration < min_s:
        qual_duration = min_s
        notes.append("enforced floor minimum {} s per axis".format(min_s))

    min_shots = rule["min_shots"]
    if min_shots is not None and qual_duration < min_shots:
        qual_duration = float(min_shots)
        notes.append("enforced floor minimum {} shots per axis".format(min_shots))

    return {
        "test_type": test_type,
        "acceptance_duration": acceptance_duration,
        "qual_duration": qual_duration,
        "factor": factor,
        "notes": notes,
    }


def validate_test_plan(plan_items, qual_category):
    """
    Check a proposed test plan against the element qualification baseline.

    Each item in plan_items must be a dict with:
        test_type (str), proposed_level (float), acceptance_level (float),
        proposed_duration (float), acceptance_duration (float).

    For thermal test types the level check uses the upper-bound rule
    (upper=True); include a separate item with upper=False for the cold
    extreme if needed.

    Args:
        plan_items (list[dict]): proposed test items.
        qual_category (str): "full_qualification" or "protoflight".

    Returns:
        list[dict]: findings. Empty list = fully compliant. Each finding:
            {test_type, field, required, proposed, status}.

    Raises:
        ValueError: if qual_category is not recognised.
    """
    if qual_category not in VALID_QUAL_CATEGORIES:
        raise ValueError(
            "Unknown qual_category '{}'.".format(qual_category)
        )

    findings = []

    for item in plan_items:
        test_type = item.get("test_type")
        if test_type not in VALID_TEST_TYPES:
            findings.append({
                "test_type": test_type,
                "field": "test_type",
                "required": "one of {}".format(sorted(VALID_TEST_TYPES)),
                "proposed": test_type,
                "status": "INVALID",
            })
            continue

        acc_level = item.get("acceptance_level")
        prop_level = item.get("proposed_level")

        if acc_level is None or prop_level is None:
            findings.append({
                "test_type": test_type,
                "field": "level",
                "required": "acceptance_level and proposed_level required",
                "proposed": None,
                "status": "MISSING",
            })
        else:
            level_result = compute_qual_level(test_type, acc_level, upper=True)
            req_level = level_result["qual_level"]
            if prop_level < req_level:
                findings.append({
                    "test_type": test_type,
                    "field": "level",
                    "required": req_level,
                    "proposed": prop_level,
                    "status": "INSUFFICIENT",
                })

        acc_dur = item.get("acceptance_duration")
        prop_dur = item.get("proposed_duration")

        if acc_dur is None or prop_dur is None:
            findings.append({
                "test_type": test_type,
                "field": "duration",
                "required": "acceptance_duration and proposed_duration required",
                "proposed": None,
                "status": "MISSING",
            })
        else:
            dur_result = compute_qual_duration(test_type, acc_dur, qual_category)
            req_dur = dur_result["qual_duration"]
            if prop_dur < req_dur:
                findings.append({
                    "test_type": test_type,
                    "field": "duration",
                    "required": req_dur,
                    "proposed": prop_dur,
                    "status": "INSUFFICIENT",
                })

    return findings
