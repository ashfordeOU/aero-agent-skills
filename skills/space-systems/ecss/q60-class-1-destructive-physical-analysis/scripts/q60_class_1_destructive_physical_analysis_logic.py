"""Destructive physical analysis of Class 1 EEE lots.

Anchor: ECSS-Q-ST-60C clause 4.3.9 (Class 1 EEE components -- destructive
physical analysis of a sample per lot or date code to confirm construction
quality). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Partition the delivered units into date-code groups. A shipment that spans
   several date codes is several populations, and each of them owes its own
   teardown sample -- one sample drawn from the whole shipment evidences only
   the date code it happened to come from.
2. Size the sample each group owes from a fraction of the group, floored at a
   minimum and capped, and refuse a group that cannot give the sample up
   without eating into the units the build needs.
3. Grade every construction anomaly the teardown found as major or minor
   against a project defect register. A code the register never listed is
   refused, because an ungraded anomaly cannot be counted either way.
4. Test the wire bond pull forces against the minimum the wire diameter
   carries. The diameter drives the minimum; an unlisted diameter is refused
   rather than interpolated.
5. Return the lot disposition: accepted, rejected, or owing a second sample
   where the minor count is over its allowance and a second sample is still
   permitted.
"""

import math

__all__ = [
    "STRENGTH_TOLERANCE",
    "DEFECT_GRADES",
    "DEFAULT_DPA_FRACTION",
    "MINIMUM_DPA_SAMPLE",
    "MAXIMUM_DPA_SAMPLE",
    "DEFAULT_MINOR_ALLOWANCE",
    "WIRE_BOND_MINIMUM_PULL_G",
    "group_by_date_code",
    "dpa_sample_size",
    "sampling_plan",
    "grade_defect",
    "summarise_defects",
    "minimum_pull_strength",
    "evaluate_bond_pulls",
    "assess_dpa",
]

# Pull forces are read off a gauge in grams; an intentional equality with a
# minimum can land a few ULP either side of it once it has been averaged.
STRENGTH_TOLERANCE = 1e-12

DEFECT_GRADES = ("major", "minor")

DEFAULT_DPA_FRACTION = 0.01
MINIMUM_DPA_SAMPLE = 2
MAXIMUM_DPA_SAMPLE = 5
DEFAULT_MINOR_ALLOWANCE = 1

# Minimum bond pull force in grams by bond wire diameter in micrometres. The
# register is the authority: a diameter it does not list is refused, never
# interpolated between two neighbours.
WIRE_BOND_MINIMUM_PULL_G = {
    18: 1.5,
    25: 3.0,
    33: 5.0,
    38: 6.0,
    50: 8.0,
}


def _positive_int(value, label):
    """Return value as a positive integer, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
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


def _meets(value, bound):
    """Return True when value is at or above bound, tolerant of float noise."""
    return value > bound or math.isclose(
        value, bound, rel_tol=STRENGTH_TOLERANCE, abs_tol=0.0
    )


def _clean_name(value, label):
    """Return a lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def group_by_date_code(units):
    """Partition delivered units into date-code groups.

    units is a sequence of mappings carrying a serial and a date code. Serials
    must be unique across the shipment: a repeated serial means the delivery
    record cannot say how many parts are really there.
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
        serial = _clean_name(unit["serial"], "unit %d serial" % index)
        date_code = _clean_name(unit["date_code"], "unit %d date_code" % index)
        if serial in seen:
            raise ValueError("serial '%s' appears more than once in the shipment" % serial)
        seen.add(serial)
        groups.setdefault(date_code, []).append(serial)
    return {code: tuple(serials) for code, serials in groups.items()}


def dpa_sample_size(
    group_size,
    fraction=DEFAULT_DPA_FRACTION,
    minimum=MINIMUM_DPA_SAMPLE,
    maximum=MAXIMUM_DPA_SAMPLE,
):
    """Return the teardown sample one date-code group owes."""
    group_size = _positive_int(group_size, "group_size")
    minimum = _positive_int(minimum, "minimum")
    maximum = _positive_int(maximum, "maximum")
    if maximum < minimum:
        raise ValueError(
            "maximum sample %d is below the minimum sample %d" % (maximum, minimum)
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
    proportional = int(math.ceil(group_size * fraction - STRENGTH_TOLERANCE))
    return min(group_size, maximum, max(minimum, proportional))


def sampling_plan(
    groups,
    flight_demand=None,
    fraction=DEFAULT_DPA_FRACTION,
    minimum=MINIMUM_DPA_SAMPLE,
    maximum=MAXIMUM_DPA_SAMPLE,
):
    """Return the teardown sample every date-code group owes.

    flight_demand maps a date code to the number of units the build needs from
    that group. A group that cannot give its sample up and still meet the demand
    is refused: teardown units are destroyed, not returned to stock.
    """
    if not isinstance(groups, dict) or not groups:
        raise ValueError("groups must be a non-empty mapping of date code to units")
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
        sample = dpa_sample_size(group_size, fraction, minimum, maximum)
        demand = flight_demand.get(code, 0)
        if isinstance(demand, bool) or not isinstance(demand, int) or demand < 0:
            raise ValueError(
                "flight demand for '%s' must be a non-negative integer" % code
            )
        spare = group_size - demand
        if sample > spare:
            raise ValueError(
                "date-code group '%s' owes a teardown sample of %d but only %d "
                "unit(s) are spare after a flight demand of %d"
                % (code, sample, spare, demand)
            )
        plan[code] = {
            "group_size": group_size,
            "sample_size": sample,
            "flight_demand": demand,
            "spare_units": spare,
        }
    return plan


def grade_defect(register, defect_code):
    """Return the grade a project register gives a construction anomaly."""
    if not isinstance(register, dict) or not register:
        raise ValueError("register must be a non-empty mapping of defect code to grade")
    code = _clean_name(defect_code, "defect_code")
    if code not in register:
        raise ValueError("defect code '%s' is not in the project defect register" % code)
    grade = register[code]
    if not isinstance(grade, str) or grade.strip().lower() not in DEFECT_GRADES:
        raise ValueError(
            "grade for '%s' must be one of %s" % (code, ", ".join(DEFECT_GRADES))
        )
    return grade.strip().lower()


def summarise_defects(observations, register, known_date_codes=None):
    """Group the teardown observations by grade and by date code."""
    if observations is None:
        observations = []
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a sequence of observation records")
    if known_date_codes is not None:
        known = {_clean_name(code, "date code") for code in known_date_codes}
    else:
        known = None
    counts = {grade: 0 for grade in DEFECT_GRADES}
    by_date_code = {}
    graded = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise ValueError("observation %d must be a mapping" % index)
        for key in ("date_code", "defect_code"):
            if key not in observation:
                raise ValueError("observation %d missing key '%s'" % (index, key))
        code = _clean_name(observation["date_code"], "observation %d date_code" % index)
        if known is not None and code not in known:
            raise ValueError(
                "observation %d cites date code '%s', which is not in the shipment"
                % (index, code)
            )
        grade = grade_defect(register, observation["defect_code"])
        counts[grade] += 1
        bucket = by_date_code.setdefault(code, {g: 0 for g in DEFECT_GRADES})
        bucket[grade] += 1
        graded.append(
            {
                "date_code": code,
                "defect_code": _clean_name(observation["defect_code"], "defect_code"),
                "grade": grade,
            }
        )
    return {
        "observations": graded,
        "counts": counts,
        "by_date_code": by_date_code,
        "major_count": counts["major"],
        "minor_count": counts["minor"],
    }


def minimum_pull_strength(wire_diameter_um, table=None):
    """Return the minimum bond pull force a wire of this diameter must carry."""
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
    """Evaluate measured bond pull forces against the diameter minimum."""
    if not isinstance(pull_forces, (list, tuple)) or not pull_forces:
        raise ValueError("pull_forces must be a non-empty sequence of measured forces")
    minimum = minimum_pull_strength(wire_diameter_um, table)
    forces = [
        _positive_real(force, "pull force %d" % index)
        for index, force in enumerate(pull_forces)
    ]
    below = [force for force in forces if not _meets(force, minimum)]
    return {
        "wire_diameter_um": wire_diameter_um,
        "minimum_required": minimum,
        "bonds_pulled": len(forces),
        "weakest_pull": min(forces),
        "mean_pull": sum(forces) / len(forces),
        "bonds_below_minimum": len(below),
        "compliant": not below,
    }


def assess_dpa(spec):
    """Run the clause 4.3.9 teardown assessment for one delivered Class 1 lot.

    spec keys: units, defect_register, wire_diameter_um, bond_pull_forces_g;
    optional observations, flight_demand, sample_fraction, minimum_sample,
    maximum_sample, minor_defect_allowance, second_sample_permitted,
    sample_index, pull_strength_table.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("units", "defect_register", "wire_diameter_um", "bond_pull_forces_g"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    groups = group_by_date_code(spec["units"])
    plan = sampling_plan(
        groups,
        spec.get("flight_demand"),
        spec.get("sample_fraction", DEFAULT_DPA_FRACTION),
        spec.get("minimum_sample", MINIMUM_DPA_SAMPLE),
        spec.get("maximum_sample", MAXIMUM_DPA_SAMPLE),
    )
    defects = summarise_defects(
        spec.get("observations"), spec["defect_register"], groups.keys()
    )
    bonds = evaluate_bond_pulls(
        spec["bond_pull_forces_g"],
        spec["wire_diameter_um"],
        spec.get("pull_strength_table"),
    )
    allowance = spec.get("minor_defect_allowance", DEFAULT_MINOR_ALLOWANCE)
    if isinstance(allowance, bool) or not isinstance(allowance, int) or allowance < 0:
        raise ValueError("minor_defect_allowance must be a non-negative integer")
    sample_index = _positive_int(spec.get("sample_index", 1), "sample_index")
    second_permitted = bool(spec.get("second_sample_permitted", False))

    findings = []
    result = {
        "date_code_groups": {code: len(serials) for code, serials in groups.items()},
        "sampling_plan": plan,
        "total_sample_size": sum(entry["sample_size"] for entry in plan.values()),
        "defects": defects,
        "bond_pulls": bonds,
        "minor_defect_allowance": allowance,
        "sample_index": sample_index,
    }

    major = defects["major_count"] > 0
    if major:
        findings.append(
            "%d major construction anomal(y/ies) found in the teardown sample"
            % defects["major_count"]
        )
    if not bonds["compliant"]:
        findings.append(
            "%d bond pull(s) fell under the %g g minimum carried by %d um wire"
            % (
                bonds["bonds_below_minimum"],
                bonds["minimum_required"],
                bonds["wire_diameter_um"],
            )
        )
    if major or not bonds["compliant"]:
        result["disposition"] = "lot-rejected"
        result["findings"] = findings
        return result

    if defects["minor_count"] > allowance:
        findings.append(
            "%d minor anomal(y/ies) against an allowance of %d"
            % (defects["minor_count"], allowance)
        )
        if second_permitted and sample_index == 1:
            result["disposition"] = "second-sample-required"
        else:
            result["disposition"] = "lot-rejected"
        result["findings"] = findings
        return result

    findings.append(
        "teardown of %d unit(s) across %d date-code group(s) found no major anomaly"
        % (result["total_sample_size"], len(groups))
    )
    result["disposition"] = "lot-accepted"
    result["findings"] = findings
    return result
