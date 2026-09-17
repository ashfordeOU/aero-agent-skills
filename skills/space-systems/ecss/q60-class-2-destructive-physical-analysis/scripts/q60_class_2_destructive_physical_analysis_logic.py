"""Destructive physical analysis of Class 2 EEE lots.

Anchor: ECSS-Q-ST-60C clause 5.3.9 (Class 2 EEE components -- sample teardown
analysis per lot or date code confirming construction quality). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Partition the delivered units into date-code groups. A shipment spanning
   several date codes is several populations, and each owes its own teardown.
2. Credit a group whose previous teardown still sits inside its validity
   window down to a confirmation sample, rather than repeating a full
   teardown on construction that has already been evidenced.
3. Size the sample each remaining group owes and check it against the spare
   units left once the build demand is set aside, because teardown units are
   destroyed and never return to stock.
4. Categorize every construction observation against a project register as
   critical, major or minor. A code the register never carried is refused.
5. Judge die-attach voiding as a fraction of the die area and every wire bond
   pull against the minimum the wire diameter carries, reporting the margin
   rather than a bare yes or no.
6. Return the lot disposition: accepted, owing a second sample, referred to
   the parts control board, or rejected.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "FINDING_CATEGORIES",
    "DEFAULT_SAMPLE_FRACTION",
    "MINIMUM_SAMPLE",
    "MAXIMUM_SAMPLE",
    "CONFIRMATION_SAMPLE",
    "DEFAULT_CREDIT_WINDOW_MONTHS",
    "DEFAULT_MINOR_ALLOWANCE",
    "DEFAULT_VOID_LIMIT_FRACTION",
    "WIRE_BOND_MINIMUM_PULL_G",
    "partition_by_date_code",
    "teardown_sample_size",
    "prior_teardown_credited",
    "teardown_plan",
    "categorize_finding",
    "summarize_findings",
    "die_attach_void_fraction",
    "void_within_limit",
    "minimum_pull_force",
    "evaluate_bond_pulls",
    "assess_class_2_teardown",
]

# Void fractions, pull margins and proportional sample sizes are quotients of
# measured values; a case meant to land exactly on a bound can sit a few ULP
# either side of it. Absorb the representation error here, never by moving the
# bound itself.
BOUND_TOLERANCE = 1e-9

# A construction observation is categorized, never judged at the bench.
FINDING_CATEGORIES = ("critical", "major", "minor")

DEFAULT_SAMPLE_FRACTION = 0.02
MINIMUM_SAMPLE = 2
MAXIMUM_SAMPLE = 4
CONFIRMATION_SAMPLE = 1
DEFAULT_CREDIT_WINDOW_MONTHS = 12
DEFAULT_MINOR_ALLOWANCE = 2
DEFAULT_VOID_LIMIT_FRACTION = 0.10

# Minimum bond pull force in grams by bond wire diameter in micrometres. The
# register is the acceptance criterion: a diameter it does not carry is
# refused, never interpolated between two neighbouring entries.
WIRE_BOND_MINIMUM_PULL_G = {
    18: 1.2,
    25: 2.5,
    33: 4.0,
    38: 5.0,
    50: 7.0,
}


def _positive_int(value, label):
    """Return value as a positive integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _non_negative_int(value, label):
    """Return value as a non-negative integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _positive_real(value, label):
    """Return value as a finite positive float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _non_negative_real(value, label):
    """Return value as a finite non-negative float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _clean_token(value, label):
    """Return a stripped lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def _at_most(value, bound):
    """Return True when value sits at or under bound, tolerant of float noise."""
    return value < bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def _at_least(value, bound):
    """Return True when value sits at or above bound, tolerant of float noise."""
    return value > bound or math.isclose(
        value, bound, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    )


def partition_by_date_code(units):
    """Partition the delivered units into date-code groups.

    units is a sequence of mappings carrying a serial and a date code. Serials
    have to be unique across the shipment: a repeated serial means the delivery
    record cannot say how many parts actually arrived.
    """
    if not isinstance(units, (list, tuple)) or not units:
        raise ValueError("units must be a non-empty sequence of unit records")
    groups = {}
    seen = set()
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            raise ValueError("unit %d must be a mapping" % index)
        for key in ("serial", "date_code"):
            if key not in unit:
                raise ValueError("unit %d missing key '%s'" % (index, key))
        serial = _clean_token(unit["serial"], "unit %d serial" % index)
        date_code = _clean_token(unit["date_code"], "unit %d date_code" % index)
        if serial in seen:
            raise ValueError("serial '%s' appears more than once in the shipment" % serial)
        seen.add(serial)
        groups.setdefault(date_code, []).append(serial)
    return {code: tuple(serials) for code, serials in groups.items()}


def teardown_sample_size(
    group_size,
    fraction=DEFAULT_SAMPLE_FRACTION,
    minimum=MINIMUM_SAMPLE,
    maximum=MAXIMUM_SAMPLE,
):
    """Return the teardown sample one date-code group owes."""
    group_size = _positive_int(group_size, "group_size")
    minimum = _positive_int(minimum, "minimum")
    maximum = _positive_int(maximum, "maximum")
    if maximum < minimum:
        raise ValueError(
            "maximum sample %d sits below the minimum sample %d" % (maximum, minimum)
        )
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
        raise ValueError("fraction must be a real number, got %r" % (fraction,))
    fraction = float(fraction)
    if not math.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("fraction must lie in (0, 1], got %r" % (fraction,))
    if group_size < minimum:
        raise ValueError(
            "a date-code group of %d unit(s) cannot supply the minimum teardown "
            "sample of %d" % (group_size, minimum)
        )
    proportional = int(math.ceil(group_size * fraction - BOUND_TOLERANCE))
    return min(group_size, maximum, max(minimum, proportional))


def prior_teardown_credited(age_months, window_months=DEFAULT_CREDIT_WINDOW_MONTHS):
    """Return True when a previous teardown still sits inside its window.

    A teardown evidences the construction of the date code it was drawn from,
    and that evidence does not expire the day after it was taken. Inside the
    window the group owes a confirmation sample instead of a full teardown; an
    age sitting exactly on the window is still inside it.
    """
    age = _non_negative_real(age_months, "age_months")
    window = _positive_real(window_months, "window_months")
    return _at_most(age, window)


def teardown_plan(
    groups,
    prior_teardown_ages=None,
    flight_demand=None,
    fraction=DEFAULT_SAMPLE_FRACTION,
    minimum=MINIMUM_SAMPLE,
    maximum=MAXIMUM_SAMPLE,
    window_months=DEFAULT_CREDIT_WINDOW_MONTHS,
):
    """Return the teardown every date-code group owes, credits included.

    prior_teardown_ages maps a date code to the age in months of the last
    teardown on that construction. flight_demand maps a date code to the units
    the build needs from it; a group that cannot give its sample up and still
    meet that demand is refused rather than quietly under-sampled.
    """
    if not isinstance(groups, dict) or not groups:
        raise ValueError("groups must be a non-empty mapping of date code to units")
    if prior_teardown_ages is None:
        prior_teardown_ages = {}
    if not isinstance(prior_teardown_ages, dict):
        raise ValueError("prior_teardown_ages must be a mapping of date code to months")
    if flight_demand is None:
        flight_demand = {}
    if not isinstance(flight_demand, dict):
        raise ValueError("flight_demand must be a mapping of date code to a count")
    plan = {}
    for code, serials in groups.items():
        if isinstance(serials, int) and not isinstance(serials, bool):
            group_size = _positive_int(serials, "group size for '%s'" % code)
        elif isinstance(serials, (list, tuple)):
            group_size = len(serials)
            if group_size == 0:
                raise ValueError("date-code group '%s' holds no units" % code)
        else:
            raise ValueError(
                "date-code group '%s' must be a unit sequence or a count" % code
            )
        credited = False
        if code in prior_teardown_ages:
            credited = prior_teardown_credited(prior_teardown_ages[code], window_months)
        if credited:
            sample = min(group_size, CONFIRMATION_SAMPLE)
        else:
            sample = teardown_sample_size(group_size, fraction, minimum, maximum)
        demand = _non_negative_int(
            flight_demand.get(code, 0), "flight demand for '%s'" % code
        )
        spare = group_size - demand
        if spare < 0:
            raise ValueError(
                "flight demand of %d on date-code group '%s' exceeds the %d unit(s) "
                "delivered" % (demand, code, group_size)
            )
        if sample > spare:
            raise ValueError(
                "date-code group '%s' owes a teardown of %d unit(s) but only %d "
                "is/are spare after a flight demand of %d" % (code, sample, spare, demand)
            )
        plan[code] = {
            "group_size": group_size,
            "sample_size": sample,
            "credited": credited,
            "flight_demand": demand,
            "spare_units": spare,
        }
    return plan


def categorize_finding(register, finding_code):
    """Return the category a project register gives a construction observation."""
    if not isinstance(register, dict) or not register:
        raise ValueError(
            "register must be a non-empty mapping of finding code to category"
        )
    code = _clean_token(finding_code, "finding_code")
    if code not in register:
        raise ValueError(
            "finding code '%s' is not in the project construction register" % code
        )
    category = register[code]
    if not isinstance(category, str) or category.strip().lower() not in FINDING_CATEGORIES:
        raise ValueError(
            "category for '%s' must be one of %s"
            % (code, ", ".join(FINDING_CATEGORIES))
        )
    return category.strip().lower()


def summarize_findings(observations, register, known_date_codes=None):
    """Group the teardown observations by category and by date code."""
    if observations is None:
        observations = []
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a sequence of observation records")
    known = None
    if known_date_codes is not None:
        known = {_clean_token(code, "date code") for code in known_date_codes}
    counts = {category: 0 for category in FINDING_CATEGORIES}
    by_date_code = {}
    graded = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise ValueError("observation %d must be a mapping" % index)
        for key in ("date_code", "finding_code"):
            if key not in observation:
                raise ValueError("observation %d missing key '%s'" % (index, key))
        code = _clean_token(observation["date_code"], "observation %d date_code" % index)
        if known is not None and code not in known:
            raise ValueError(
                "observation %d cites date code '%s', which the shipment does not hold"
                % (index, code)
            )
        category = categorize_finding(register, observation["finding_code"])
        counts[category] += 1
        bucket = by_date_code.setdefault(
            code, {name: 0 for name in FINDING_CATEGORIES}
        )
        bucket[category] += 1
        graded.append(
            {
                "date_code": code,
                "finding_code": _clean_token(
                    observation["finding_code"], "finding_code"
                ),
                "category": category,
            }
        )
    return {
        "observations": graded,
        "counts": counts,
        "by_date_code": by_date_code,
        "critical_count": counts["critical"],
        "major_count": counts["major"],
        "minor_count": counts["minor"],
    }


def die_attach_void_fraction(void_area_mm2, die_area_mm2):
    """Return the voided share of the die attach area."""
    die_area = _positive_real(die_area_mm2, "die_area_mm2")
    void_area = _non_negative_real(void_area_mm2, "void_area_mm2")
    if void_area > die_area and not math.isclose(
        void_area, die_area, rel_tol=BOUND_TOLERANCE, abs_tol=BOUND_TOLERANCE
    ):
        raise ValueError(
            "voided area %r mm2 exceeds the die attach area %r mm2"
            % (void_area, die_area)
        )
    return void_area / die_area


def void_within_limit(fraction, limit=DEFAULT_VOID_LIMIT_FRACTION):
    """Return True when a void fraction sits at or under its limit."""
    fraction = _non_negative_real(fraction, "fraction")
    limit = _positive_real(limit, "limit")
    if limit > 1.0:
        raise ValueError("limit must be a fraction of the die area, got %r" % (limit,))
    return _at_most(fraction, limit)


def minimum_pull_force(wire_diameter_um, table=None):
    """Return the minimum pull force a bond wire of this diameter must carry."""
    if table is None:
        table = WIRE_BOND_MINIMUM_PULL_G
    if not isinstance(table, dict) or not table:
        raise ValueError("table must be a non-empty mapping of diameter to force")
    diameter = _positive_int(wire_diameter_um, "wire_diameter_um")
    if diameter not in table:
        raise ValueError(
            "wire diameter %d um is not in the bond strength register; an unlisted "
            "diameter is refused, not interpolated" % diameter
        )
    return _positive_real(table[diameter], "minimum pull force for %d um" % diameter)


def evaluate_bond_pulls(pull_forces, wire_diameter_um, table=None):
    """Evaluate measured bond pull forces against the diameter minimum.

    The weakest pull is carried out as a margin fraction of the minimum, so a
    bond that only just held is visibly different from one with room to spare.
    """
    if not isinstance(pull_forces, (list, tuple)) or not pull_forces:
        raise ValueError("pull_forces must be a non-empty sequence of measured forces")
    minimum = minimum_pull_force(wire_diameter_um, table)
    forces = [
        _positive_real(force, "pull force %d" % index)
        for index, force in enumerate(pull_forces)
    ]
    weakest = min(forces)
    below = [force for force in forces if not _at_least(force, minimum)]
    return {
        "wire_diameter_um": wire_diameter_um,
        "minimum_required_g": minimum,
        "bonds_pulled": len(forces),
        "weakest_pull_g": weakest,
        "mean_pull_g": sum(forces) / len(forces),
        "weakest_margin_fraction": (weakest - minimum) / minimum,
        "bonds_below_minimum": len(below),
        "compliant": not below,
    }


def assess_class_2_teardown(spec):
    """Run the clause 5.3.9 teardown assessment for one delivered Class 2 lot.

    Required spec keys: units, finding_register, wire_diameter_um,
    bond_pull_forces_g. Optional: observations, prior_teardown_ages,
    flight_demand, sample_fraction, minimum_sample, maximum_sample,
    credit_window_months, minor_finding_allowance, second_sample_permitted,
    sample_index, pull_force_table, die_area_mm2, void_area_mm2,
    void_limit_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("units", "finding_register", "wire_diameter_um", "bond_pull_forces_g"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    groups = partition_by_date_code(spec["units"])
    plan = teardown_plan(
        groups,
        spec.get("prior_teardown_ages"),
        spec.get("flight_demand"),
        spec.get("sample_fraction", DEFAULT_SAMPLE_FRACTION),
        spec.get("minimum_sample", MINIMUM_SAMPLE),
        spec.get("maximum_sample", MAXIMUM_SAMPLE),
        spec.get("credit_window_months", DEFAULT_CREDIT_WINDOW_MONTHS),
    )
    findings = summarize_findings(
        spec.get("observations"), spec["finding_register"], groups.keys()
    )
    bonds = evaluate_bond_pulls(
        spec["bond_pull_forces_g"],
        spec["wire_diameter_um"],
        spec.get("pull_force_table"),
    )
    allowance = _non_negative_int(
        spec.get("minor_finding_allowance", DEFAULT_MINOR_ALLOWANCE),
        "minor_finding_allowance",
    )
    sample_index = _positive_int(spec.get("sample_index", 1), "sample_index")
    second_permitted = bool(spec.get("second_sample_permitted", False))

    void = None
    if "die_area_mm2" in spec or "void_area_mm2" in spec:
        if "die_area_mm2" not in spec or "void_area_mm2" not in spec:
            raise ValueError(
                "die attach voiding needs both die_area_mm2 and void_area_mm2"
            )
        limit = spec.get("void_limit_fraction", DEFAULT_VOID_LIMIT_FRACTION)
        fraction = die_attach_void_fraction(spec["void_area_mm2"], spec["die_area_mm2"])
        void = {
            "void_fraction": fraction,
            "limit_fraction": float(limit),
            "within_limit": void_within_limit(fraction, limit),
        }

    reasons = []
    result = {
        "date_code_groups": {code: len(serials) for code, serials in groups.items()},
        "teardown_plan": plan,
        "total_sample_size": sum(entry["sample_size"] for entry in plan.values()),
        "credited_groups": sorted(
            code for code, entry in plan.items() if entry["credited"]
        ),
        "findings": findings,
        "bond_pulls": bonds,
        "die_attach_voiding": void,
        "minor_finding_allowance": allowance,
        "sample_index": sample_index,
    }

    if findings["critical_count"] > 0:
        reasons.append(
            "%d critical construction finding(s) in the teardown sample"
            % findings["critical_count"]
        )
    if not bonds["compliant"]:
        reasons.append(
            "%d bond pull(s) under the %g g minimum carried by %d um wire"
            % (
                bonds["bonds_below_minimum"],
                bonds["minimum_required_g"],
                bonds["wire_diameter_um"],
            )
        )
    if void is not None and not void["within_limit"]:
        reasons.append(
            "die attach voiding of %.3f is over its limit of %.3f"
            % (void["void_fraction"], void["limit_fraction"])
        )
    if reasons:
        result["disposition"] = "lot-rejected"
        result["reasons"] = reasons
        return result

    if findings["major_count"] > 0:
        reasons.append(
            "%d major construction finding(s) in the teardown sample"
            % findings["major_count"]
        )
        if second_permitted and sample_index == 1:
            result["disposition"] = "second-sample-required"
        else:
            result["disposition"] = "lot-rejected"
        result["reasons"] = reasons
        return result

    if findings["minor_count"] > allowance:
        reasons.append(
            "%d minor construction finding(s) against an allowance of %d"
            % (findings["minor_count"], allowance)
        )
        result["disposition"] = "referred-to-parts-control-board"
        result["reasons"] = reasons
        return result

    reasons.append(
        "teardown of %d unit(s) across %d date-code group(s) found no critical or "
        "major construction finding"
        % (result["total_sample_size"], len(groups))
    )
    result["disposition"] = "lot-accepted"
    result["reasons"] = reasons
    return result
