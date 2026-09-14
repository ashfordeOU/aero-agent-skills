"""Lot-screening assessment for lowest-assurance commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 6.3.3 (the screening applied, where it is
needed, to a lot of commercial electrical, electronic and electromechanical
parts bought at the lowest assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Screening is not blanket at this class. It is owed where a condition on the
lot or its application calls for it, and the conditions decide which elements
are owed. A lot with no such condition is closed clean rather than screened
for form.

Procedure implemented here
--------------------------
1. Validate the screening policy: the sample fraction as a ratio of integers,
   the minimum sample count, the activation energy and the reference burn-in
   duration and temperature.
2. Validate the lot: its size and the maximum temperature the part is rated
   for, because a screen run above that rating damages what it grades.
3. Validate the declared trigger conditions and derive the required elements
   from them. No trigger means no screening is owed.
4. Validate every declared screening step: its element, whether it was run on
   every unit or on a sample, the sample count, and the burn-in duration and
   temperature.
5. Hold an every-unit element to the whole lot and size a sampled element
   against the lot with integer arithmetic, so the sample threshold does not
   move between platforms.
6. Convert a burn-in run at another temperature into reference-equivalent
   hours through an Arrhenius acceleration factor before judging its duration,
   and refuse a burn-in above the part's rated maximum.
7. Record screening declared beyond the required set as additional rather than
   as a finding, and close on one verdict carrying every finding.
"""

import math

__all__ = [
    "SCREENING_ELEMENTS",
    "EVERY_UNIT_ELEMENTS",
    "TRIGGER_CONDITIONS",
    "SCREENING_BASES",
    "BOLTZMANN_EV_PER_KELVIN",
    "ABSOLUTE_ZERO_C",
    "EQUIVALENCE_TOLERANCE",
    "validate_screening_policy",
    "validate_lot",
    "validate_triggers",
    "required_elements",
    "validate_screening_step",
    "collect_steps",
    "required_sample_size",
    "burn_in_equivalent_hours",
    "grade_screening_element",
    "assess_class3_screening",
]

# The screening elements a lot at this class may be put through.
SCREENING_ELEMENTS = (
    "external-visual-inspection",
    "electrical-measurement-at-room-temperature",
    "temperature-cycling",
    "burn-in",
    "electrical-measurement-at-temperature-extremes",
    "particle-impact-noise-detection",
    "seal-or-package-integrity-check",
    "authenticity-and-origin-verification",
)

# The elements that only mean anything applied to the whole lot. A sampled
# burn-in leaves the units that were never stressed in the flight build.
EVERY_UNIT_ELEMENTS = (
    "external-visual-inspection",
    "electrical-measurement-at-room-temperature",
    "temperature-cycling",
    "burn-in",
    "electrical-measurement-at-temperature-extremes",
    "particle-impact-noise-detection",
)

# The conditions that make screening owed, and what each one demands.
TRIGGER_CONDITIONS = {
    "criticality-bearing-function": (
        "external-visual-inspection",
        "electrical-measurement-at-room-temperature",
        "burn-in",
        "electrical-measurement-at-temperature-extremes",
    ),
    "wide-temperature-range-application": (
        "temperature-cycling",
        "electrical-measurement-at-temperature-extremes",
    ),
    "unverified-supply-origin": (
        "external-visual-inspection",
        "authenticity-and-origin-verification",
    ),
    "cavity-package-device": (
        "particle-impact-noise-detection",
        "seal-or-package-integrity-check",
    ),
    "extended-storage-since-date-code": (
        "external-visual-inspection",
        "electrical-measurement-at-room-temperature",
    ),
}

# How an element may be applied.
SCREENING_BASES = ("every-unit", "sample")

# Physical constants and limits used by the burn-in equivalence.
BOLTZMANN_EV_PER_KELVIN = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15

# The equivalence is an exponential of a small quantity; a duration landing on
# the reference must not fail on representation alone.
EQUIVALENCE_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _normalize_token(value, label):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def _positive_number(value, label):
    """Return a finite, strictly positive float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _temperature_c(value, label):
    """Return a finite temperature in degrees Celsius above absolute zero."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %g C" % (label, number))
    return number


def _positive_int(value, label):
    """Return a strictly positive integer count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def validate_screening_policy(policy):
    """Return the validated screening policy for the lot."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping")
    required = (
        "sample_numerator",
        "sample_denominator",
        "minimum_sample_units",
        "activation_energy_ev",
        "reference_burn_in_hours",
        "reference_burn_in_temperature_c",
    )
    for key in required:
        if key not in policy:
            raise ValueError("policy missing required key '%s'" % key)
    numerator = _positive_int(policy["sample_numerator"], "sample_numerator")
    denominator = _positive_int(policy["sample_denominator"], "sample_denominator")
    if numerator > denominator:
        raise ValueError(
            "sample fraction must not exceed the whole lot: %d/%d"
            % (numerator, denominator)
        )
    return {
        "sample_numerator": numerator,
        "sample_denominator": denominator,
        "minimum_sample_units": _positive_int(
            policy["minimum_sample_units"], "minimum_sample_units"
        ),
        "activation_energy_ev": _positive_number(
            policy["activation_energy_ev"], "activation_energy_ev"
        ),
        "reference_burn_in_hours": _positive_number(
            policy["reference_burn_in_hours"], "reference_burn_in_hours"
        ),
        "reference_burn_in_temperature_c": _temperature_c(
            policy["reference_burn_in_temperature_c"], "reference_burn_in_temperature_c"
        ),
    }


def validate_lot(lot):
    """Return the validated lot the screening is applied to."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    for key in ("lot_size", "rated_maximum_temperature_c"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    return {
        "lot_size": _positive_int(lot["lot_size"], "lot_size"),
        "rated_maximum_temperature_c": _temperature_c(
            lot["rated_maximum_temperature_c"], "rated_maximum_temperature_c"
        ),
    }


def validate_triggers(triggers):
    """Return the validated, de-duplicated trigger conditions on the lot."""
    if triggers is None:
        raise ValueError(
            "trigger conditions are undeclared; an empty list states that none "
            "apply, which is a different claim from saying nothing"
        )
    if not isinstance(triggers, (list, tuple)):
        raise ValueError("triggers must be a sequence")
    seen = []
    for trigger in triggers:
        token = _normalize_token(trigger, "trigger condition")
        if token not in TRIGGER_CONDITIONS:
            raise ValueError(
                "trigger condition '%s' is not recognized; expected one of %s"
                % (token, ", ".join(sorted(TRIGGER_CONDITIONS)))
            )
        if token not in seen:
            seen.append(token)
    return tuple(seen)


def required_elements(triggers):
    """Return the screening elements the declared triggers make owed."""
    active = validate_triggers(triggers)
    owed = set()
    for trigger in active:
        owed.update(TRIGGER_CONDITIONS[trigger])
    return tuple(name for name in SCREENING_ELEMENTS if name in owed)


def validate_screening_step(step):
    """Return one validated declared screening step."""
    if not isinstance(step, dict):
        raise ValueError("each screening step must be a mapping")
    for key in ("element", "basis"):
        if key not in step:
            raise ValueError("screening step missing required key '%s'" % key)
    element = _normalize_token(step["element"], "element")
    if element not in SCREENING_ELEMENTS:
        raise ValueError(
            "screening element '%s' is not recognized; expected one of %s"
            % (element, ", ".join(SCREENING_ELEMENTS))
        )
    basis = _normalize_token(step["basis"], "basis")
    if basis not in SCREENING_BASES:
        raise ValueError(
            "screening basis '%s' is not recognized; expected one of %s"
            % (basis, ", ".join(SCREENING_BASES))
        )
    units = step.get("units_screened")
    if units is not None:
        units = _positive_int(units, "units_screened")
    record = {
        "element": element,
        "basis": basis,
        "units_screened": units,
        "hours": None,
        "temperature_c": None,
    }
    if element == "burn-in":
        for key in ("hours", "temperature_c"):
            if key not in step:
                raise ValueError("burn-in step missing required key '%s'" % key)
        record["hours"] = _positive_number(step["hours"], "burn-in hours")
        record["temperature_c"] = _temperature_c(
            step["temperature_c"], "burn-in temperature_c"
        )
    return record


def collect_steps(steps):
    """Return the validated steps keyed by element, rejecting a repeat."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("screening steps must be a sequence")
    collected = {}
    for step in steps:
        record = validate_screening_step(step)
        if record["element"] in collected:
            raise ValueError(
                "screening element '%s' is declared twice" % record["element"]
            )
        collected[record["element"]] = record
    return collected


def required_sample_size(lot_size, policy):
    """Return the units a sampled element has to reach on this lot.

    The fraction is carried as a ratio of integers and the rounding is done in
    integer arithmetic, so the threshold cannot move by a unit between
    platforms the way a float ceiling can.
    """
    size = _positive_int(lot_size, "lot_size")
    graded = validate_screening_policy(policy)
    numerator = graded["sample_numerator"]
    denominator = graded["sample_denominator"]
    fractional = -((-numerator * size) // denominator)
    return min(size, max(graded["minimum_sample_units"], fractional))


def burn_in_equivalent_hours(hours, temperature_c, policy):
    """Return the reference-equivalent duration of a burn-in run off-reference.

    A burn-in run hotter than the reference buys time through an Arrhenius
    acceleration factor; one run cooler pays it back. The conversion is made
    before the duration is judged, so a short hot burn-in is not failed and a
    long cold one is not passed.
    """
    graded = validate_screening_policy(policy)
    run_hours = _positive_number(hours, "burn-in hours")
    run_kelvin = _temperature_c(temperature_c, "burn-in temperature_c") - ABSOLUTE_ZERO_C
    reference_kelvin = graded["reference_burn_in_temperature_c"] - ABSOLUTE_ZERO_C
    exponent = (graded["activation_energy_ev"] / BOLTZMANN_EV_PER_KELVIN) * (
        1.0 / reference_kelvin - 1.0 / run_kelvin
    )
    acceleration = math.exp(exponent)
    return {
        "acceleration_factor": acceleration,
        "equivalent_hours": run_hours * acceleration,
        "reference_hours": graded["reference_burn_in_hours"],
    }


def grade_screening_element(element, step, lot, policy):
    """Return the graded state of one owed screening element."""
    name = _normalize_token(element, "element")
    if name not in SCREENING_ELEMENTS:
        raise ValueError("screening element '%s' is not recognized" % name)
    graded_lot = validate_lot(lot)
    graded_policy = validate_screening_policy(policy)
    base = {"element": name, "basis": None, "state": "not-performed",
            "reason": "owed screening element not declared", "performed": False,
            "detail": {}}
    if step is None:
        return base
    if not isinstance(step, dict) or "basis" not in step:
        raise ValueError("step for '%s' must be a validated mapping" % name)
    basis = step["basis"]
    base["basis"] = basis
    if name in EVERY_UNIT_ELEMENTS and basis != "every-unit":
        base["state"] = "basis-insufficient"
        base["reason"] = "'%s' has to reach every unit of the lot" % name
        return base
    if basis == "every-unit":
        units = step.get("units_screened")
        if units is not None and units < graded_lot["lot_size"]:
            base["state"] = "lot-not-covered"
            base["reason"] = "%d of %d units screened on an every-unit element" % (
                units, graded_lot["lot_size"],
            )
            return base
    else:
        needed = required_sample_size(graded_lot["lot_size"], graded_policy)
        units = step.get("units_screened")
        if units is None:
            base["state"] = "sample-not-stated"
            base["reason"] = "a sampled element must state the units screened"
            return base
        base["detail"]["required_sample"] = needed
        base["detail"]["units_screened"] = units
        if units < needed:
            base["state"] = "sample-too-small"
            base["reason"] = "%d units sampled where %d are required on a lot of %d" % (
                units, needed, graded_lot["lot_size"],
            )
            return base
    if name == "burn-in":
        rated = graded_lot["rated_maximum_temperature_c"]
        run_temperature = step["temperature_c"]
        if run_temperature > rated and not math.isclose(
            run_temperature, rated, rel_tol=0.0, abs_tol=EQUIVALENCE_TOLERANCE
        ):
            base["state"] = "condition-outside-rating"
            base["reason"] = "burn-in at %g C exceeds the rated maximum %g C" % (
                run_temperature, rated,
            )
            return base
        equivalence = burn_in_equivalent_hours(
            step["hours"], run_temperature, graded_policy
        )
        base["detail"].update(equivalence)
        short = equivalence["equivalent_hours"] < equivalence["reference_hours"] and \
            not math.isclose(
                equivalence["equivalent_hours"],
                equivalence["reference_hours"],
                rel_tol=EQUIVALENCE_TOLERANCE,
                abs_tol=0.0,
            )
        if short:
            base["state"] = "duration-short"
            base["reason"] = (
                "burn-in worth %.1f reference-equivalent hours against %.1f required"
                % (equivalence["equivalent_hours"], equivalence["reference_hours"])
            )
            return base
    base["state"] = "performed"
    base["reason"] = None
    base["performed"] = True
    return base


def assess_class3_screening(case):
    """Run the full clause 6.3.3 screening assessment for a class 3 lot.

    case keys: policy, lot, triggers, screening.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("policy", "lot", "triggers", "screening"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)

    policy = validate_screening_policy(case["policy"])
    lot = validate_lot(case["lot"])
    triggers = validate_triggers(case["triggers"])
    owed = required_elements(triggers)
    collected = collect_steps(case["screening"])

    additional = sorted(name for name in collected if name not in owed)

    if not owed:
        return {
            "policy": policy,
            "lot": lot,
            "triggers": list(triggers),
            "required_elements": [],
            "graded": [],
            "additional_screening": additional,
            "figures": {"required_elements": 0, "elements_performed": 0,
                        "coverage": 1.0},
            "verdict": "screening not required at this class",
            "acceptable": True,
            "findings": [],
        }

    graded = [
        grade_screening_element(name, collected.get(name), lot, policy) for name in owed
    ]
    performed = [entry for entry in graded if entry["performed"]]
    figures = {
        "required_elements": len(graded),
        "elements_performed": len(performed),
        "coverage": len(performed) / len(graded),
    }

    findings = [
        "screening element '%s' is open: %s" % (entry["element"], entry["reason"])
        for entry in graded
        if not entry["performed"]
    ]

    states = {entry["state"] for entry in graded}
    if not collected:
        verdict = "screening owed but none declared"
    elif "not-performed" in states:
        verdict = "owed screening element not performed"
    elif "condition-outside-rating" in states:
        verdict = "screening condition outside the part rating"
    elif states & {"basis-insufficient", "lot-not-covered", "sample-not-stated",
                   "sample-too-small"}:
        verdict = "screening applied to too few units"
    elif "duration-short" in states:
        verdict = "burn-in short of the reference equivalent"
    else:
        verdict = "screening meets class 3 expectations"

    return {
        "policy": policy,
        "lot": lot,
        "triggers": list(triggers),
        "required_elements": list(owed),
        "graded": graded,
        "open_elements": [e["element"] for e in graded if not e["performed"]],
        "additional_screening": additional,
        "figures": figures,
        "verdict": verdict,
        "acceptable": verdict == "screening meets class 3 expectations",
        "findings": findings,
    }
