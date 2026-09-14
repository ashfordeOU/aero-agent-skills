#!/usr/bin/env python3
"""In-house magnetic components and their screening at the lowest class.

Anchor: ECSS-Q-ST-60-13C clause 6.6.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause covers a transformer, inductor or choke the project wound
itself rather than bought. There is no manufacturer behind it, so there
is no manufacturer's qualification to lean on: the drawing, its issue,
the released winding procedure and the operator who wound it are the
whole build basis, and a batch that cannot name all four is a batch
nobody can repeat.

The design check is a heat balance, solved rather than asserted. Copper
resistance rises with temperature, the loss rises with the resistance,
and the temperature rises with the loss. Written out, that is one linear
equation in the hot spot temperature and it has a closed solution, so
the hot spot is computed in one step instead of guessed at room
temperature. The same expression carries its own stability test: the
denominator closes on zero as the copper loss coefficient approaches the
thermal conductance, and a component whose denominator has closed does
not run hot, it runs away. That condition is reported as its own outcome
rather than as a large number.

The turns ratio is checked against what was actually measured on each
delivered unit, not against the drawing alone. A ratio inside tolerance
on average is not a ratio inside tolerance, so every unit outside the
band is named.

Screening at this class splits in two and the split is the point. Some
steps are owed by every delivered unit because they catch the defect
that kills one piece: a nicked enamel, a mis-terminated winding, a
varnish void. Others are drawn from a sample because they characterise
the batch rather than the piece. Reading a sample step as though it
covered the batch, and running a per-unit step on a sample, are the same
error in opposite directions. The sample size follows the batch through
a declared fraction, is floored so a small batch is not screened by one
piece, and can never exceed the batch itself.

The policy numbers below are declared project values, not physical
constants, with the single exception of the copper temperature
coefficient, which is a material property a project may still restate
for its own conductor.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VISUAL_AND_WORKMANSHIP_INSPECTION = "visual-and-workmanship-inspection"
WINDING_CONTINUITY_AND_TURNS_RATIO_CHECK = "winding-continuity-and-turns-ratio-check"
WINDING_INSULATION_RESISTANCE_MEASUREMENT = "winding-insulation-resistance-measurement"

PER_UNIT_SCREENING_STEPS = (
    VISUAL_AND_WORKMANSHIP_INSPECTION,
    WINDING_CONTINUITY_AND_TURNS_RATIO_CHECK,
    WINDING_INSULATION_RESISTANCE_MEASUREMENT,
)

MAGNETIC_DIELECTRIC_WITHSTAND_TEST = "magnetic-dielectric-withstand-test"
MAGNETIC_THERMAL_CYCLE_CONDITIONING = "magnetic-thermal-cycle-conditioning"
IMPREGNATION_AND_VARNISH_VERIFICATION = "impregnation-and-varnish-verification"

SAMPLE_SCREENING_STEPS = (
    MAGNETIC_DIELECTRIC_WITHSTAND_TEST,
    MAGNETIC_THERMAL_CYCLE_CONDITIONING,
    IMPREGNATION_AND_VARNISH_VERIFICATION,
)

RECOGNISED_SCREENING_STEPS = PER_UNIT_SCREENING_STEPS + SAMPLE_SCREENING_STEPS

BUILD_BASIS_NOT_ESTABLISHED = "in-house-magnetic-build-basis-not-established"
WINDING_THERMAL_SOLUTION_DOES_NOT_SETTLE = "winding-thermal-solution-does-not-settle"
THERMAL_STABILITY_MARGIN_SHORT = "winding-thermal-stability-margin-short"
HOT_SPOT_OVER_INSULATION_RATING = "winding-hot-spot-over-the-insulation-rating"
TURNS_RATIO_OUT_OF_TOLERANCE = "measured-turns-ratio-out-of-tolerance"
SCREENING_COVERAGE_SHORT = "in-house-magnetic-screening-coverage-short"
MEETS_CLASS_THREE_SCOPE = "in-house-magnetic-meets-class-three-scope"

DEFAULT_MAGNETIC_POLICY = {
    "copper_temperature_coefficient_per_k": 0.00393,
    "reference_temperature_c": 20.0,
    "min_thermal_stability_margin": 2.0,
    "insulation_margin_c": 10.0,
    "turns_ratio_tolerance": 0.02,
    "sample_fraction": 0.1,
    "min_sample_units": 3,
    "require_released_procedure": True,
    "require_certified_operator": True,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15
_CEIL_GUARD = 1e-9


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive_count(name, value):
    count = _require_count(name, value)
    if count < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return count


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_magnetic_policy(policy):
    """Check the in-house magnetic policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    alpha = _require_positive(
        "copper_temperature_coefficient_per_k",
        policy.get("copper_temperature_coefficient_per_k"),
    )
    if alpha >= 1.0:
        raise ValueError(
            "copper_temperature_coefficient_per_k %g is not a conductor "
            "coefficient; it is quoted per kelvin and sits well under one"
            % (alpha,)
        )
    _require_number(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    stability = _require_number(
        "min_thermal_stability_margin", policy.get("min_thermal_stability_margin")
    )
    if stability < 1.0:
        raise ValueError(
            "min_thermal_stability_margin %g is below one; a winding at unity is "
            "already running away" % (stability,)
        )
    _require_non_negative("insulation_margin_c", policy.get("insulation_margin_c"))
    tolerance = _require_fraction(
        "turns_ratio_tolerance", policy.get("turns_ratio_tolerance")
    )
    if tolerance <= 0.0:
        raise ValueError(
            "turns_ratio_tolerance must be greater than zero, got %r" % (tolerance,)
        )
    fraction = _require_fraction("sample_fraction", policy.get("sample_fraction"))
    if fraction <= 0.0:
        raise ValueError(
            "sample_fraction must be greater than zero, got %r" % (fraction,)
        )
    _require_positive_count("min_sample_units", policy.get("min_sample_units"))
    _require_flag(
        "require_released_procedure", policy.get("require_released_procedure")
    )
    _require_flag(
        "require_certified_operator", policy.get("require_certified_operator")
    )
    return policy


def validate_winding(entry):
    """Read one winding: its turns, its cold resistance and its current."""
    if not isinstance(entry, dict):
        raise ValueError("winding entry must be a mapping, got %r" % (entry,))
    identifier = _require_label("winding identifier", entry.get("identifier"))
    if not identifier:
        raise ValueError("a winding must be named, got a blank identifier")
    turns = _require_positive_count("turns on %s" % identifier, entry.get("turns"))
    resistance = _require_positive(
        "resistance_at_reference_ohm on %s" % identifier,
        entry.get("resistance_at_reference_ohm"),
    )
    current = _require_non_negative(
        "current_a on %s" % identifier, entry.get("current_a")
    )
    return {
        "identifier": identifier,
        "turns": turns,
        "resistance_at_reference_ohm": resistance,
        "current_a": current,
    }


def validate_windings(windings):
    """Read every winding, refusing an empty or repeated set."""
    if not isinstance(windings, (list, tuple)):
        raise ValueError("windings must be a sequence of winding records")
    if not windings:
        raise ValueError("the component declares no winding")
    checked = []
    seen = set()
    for entry in windings:
        record = validate_winding(entry)
        if record["identifier"] in seen:
            raise ValueError("winding %r is declared twice" % record["identifier"])
        seen.add(record["identifier"])
        checked.append(record)
    return tuple(checked)


def validate_build_basis(case):
    """Read the in-house build basis behind the component."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    designation = _require_label("designation", case.get("designation", ""))
    drawing = _require_label("in_house_drawing", case.get("in_house_drawing", ""))
    issue = _require_label("drawing_issue", case.get("drawing_issue", ""))
    released = _require_flag(
        "winding_procedure_released", case.get("winding_procedure_released", False)
    )
    operator = _require_flag(
        "operator_certified", case.get("operator_certified", False)
    )
    first_article = _require_label(
        "first_article_record", case.get("first_article_record", "")
    )
    return {
        "designation": designation,
        "in_house_drawing": drawing,
        "drawing_issue": issue,
        "winding_procedure_released": released,
        "operator_certified": operator,
        "first_article_record": first_article,
    }


def build_basis_findings(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Every reason the build behind the batch cannot be repeated."""
    validate_magnetic_policy(policy)
    basis = validate_build_basis(case)
    findings = []
    if not basis["designation"]:
        findings.append(
            "the component carries no designation, so nothing ties the batch to a "
            "position in the design"
        )
    if not basis["in_house_drawing"]:
        findings.append(
            "no in-house drawing is named, so the winding was built to something "
            "nobody can produce again"
        )
    elif not basis["drawing_issue"]:
        findings.append(
            "drawing %s is named with no issue, so two batches built months apart "
            "can look identical on paper and be different parts"
            % basis["in_house_drawing"]
        )
    if policy["require_released_procedure"] and not basis[
        "winding_procedure_released"
    ]:
        findings.append(
            "the winding procedure is not released, so the batch was wound to a "
            "working practice rather than to a controlled one"
        )
    if policy["require_certified_operator"] and not basis["operator_certified"]:
        findings.append(
            "no certified operator is recorded, and on an in-house winding the "
            "operator is the process"
        )
    if not basis["first_article_record"]:
        findings.append(
            "no first article record is held, so the first unit off the bench was "
            "never compared against the drawing it came from"
        )
    return tuple(findings)


def validate_thermal_case(case):
    """Read the thermal inputs the heat balance is solved from."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    ambient = _require_number(
        "baseplate_temperature_c", case.get("baseplate_temperature_c")
    )
    conductance = _require_positive(
        "thermal_conductance_w_per_k", case.get("thermal_conductance_w_per_k")
    )
    core_loss = _require_non_negative("core_loss_w", case.get("core_loss_w"))
    rating = _require_positive(
        "insulation_temperature_rating_c",
        case.get("insulation_temperature_rating_c"),
    )
    return {
        "baseplate_temperature_c": ambient,
        "thermal_conductance_w_per_k": conductance,
        "core_loss_w": core_loss,
        "insulation_temperature_rating_c": rating,
    }


def copper_loss_coefficient_w(case):
    """Copper loss the windings would dissipate at the reference temperature."""
    return sum(
        record["current_a"] * record["current_a"]
        * record["resistance_at_reference_ohm"]
        for record in validate_windings(case.get("windings"))
    )


def thermal_stability_margin(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Thermal conductance over the rate at which copper loss chases itself.

    At unity the heat balance has no solution: every degree of rise adds
    exactly the loss needed to drive the next one. The margin is reported as
    unbounded when the windings carry no current at all.
    """
    validate_magnetic_policy(policy)
    thermal = validate_thermal_case(case)
    slope = (
        float(policy["copper_temperature_coefficient_per_k"])
        * copper_loss_coefficient_w(case)
    )
    if slope <= 0.0:
        return math.inf
    return thermal["thermal_conductance_w_per_k"] / slope


def thermal_solution_settles(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Whether the heat balance has a solution at all."""
    return thermal_stability_margin(case, policy) > 1.0


def winding_hot_spot_c(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Closed solution of the copper-loss heat balance for the hot spot.

    Solving the balance rather than evaluating it at room temperature is the
    whole point: the loss that sets the temperature is itself a function of
    that temperature.
    """
    validate_magnetic_policy(policy)
    if not thermal_solution_settles(case, policy):
        raise ValueError(
            "the heat balance does not settle for this winding set; the copper "
            "loss rises at least as fast as the component can shed it"
        )
    thermal = validate_thermal_case(case)
    alpha = float(policy["copper_temperature_coefficient_per_k"])
    reference = float(policy["reference_temperature_c"])
    coefficient = copper_loss_coefficient_w(case)
    conductance = thermal["thermal_conductance_w_per_k"]
    numerator = (
        conductance * thermal["baseplate_temperature_c"]
        + coefficient * (1.0 - alpha * reference)
        + thermal["core_loss_w"]
    )
    return numerator / (conductance - alpha * coefficient)


def allowed_hot_spot_c(case, policy=DEFAULT_MAGNETIC_POLICY):
    """The insulation rating less the margin the class holds back."""
    validate_magnetic_policy(policy)
    thermal = validate_thermal_case(case)
    return thermal["insulation_temperature_rating_c"] - float(
        policy["insulation_margin_c"]
    )


def declared_turns_ratio(case):
    """Read the design turns ratio, checked against the windings when it can be."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    ratio = _require_positive("design_turns_ratio", case.get("design_turns_ratio"))
    windings = validate_windings(case.get("windings"))
    if len(windings) == 2:
        from_turns = windings[0]["turns"] / windings[1]["turns"]
        if not math.isclose(ratio, from_turns, rel_tol=1e-9, abs_tol=_ABS_TOL):
            raise ValueError(
                "design_turns_ratio %g disagrees with the declared turns, which "
                "give %g; the drawing and the ratio cannot both be right"
                % (ratio, from_turns)
            )
    return ratio


def validate_batch(case):
    """Read the batch the units were drawn from."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = _require_label("batch_reference", case.get("batch_reference", ""))
    size = _require_positive_count("batch_size", case.get("batch_size"))
    return {"batch_reference": reference, "batch_size": size}


def required_sample_units(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Units the sample-drawn steps must cover for this batch.

    The fraction is taken with a guard so a batch size that lands on a whole
    number of units is not rounded up by a representation error.
    """
    validate_magnetic_policy(policy)
    batch = validate_batch(case)
    scaled = math.ceil(
        batch["batch_size"] * float(policy["sample_fraction"]) - _CEIL_GUARD
    )
    return min(
        batch["batch_size"], max(scaled, int(policy["min_sample_units"]))
    )


def validate_unit(entry):
    """Read one delivered unit, its measured ratio and the steps it ran."""
    if not isinstance(entry, dict):
        raise ValueError("unit entry must be a mapping, got %r" % (entry,))
    serial = _require_label("unit serial", entry.get("serial"))
    if not serial:
        raise ValueError("a delivered unit must carry a serial, got a blank one")
    ratio = _require_positive(
        "measured_turns_ratio on %s" % serial, entry.get("measured_turns_ratio")
    )
    steps = entry.get("steps_run", ())
    if not isinstance(steps, (list, tuple)):
        raise ValueError(
            "steps_run on %s must be a sequence of screening step names" % serial
        )
    checked = []
    for step in steps:
        name = _require_label("screening step on %s" % serial, step)
        if name not in RECOGNISED_SCREENING_STEPS:
            raise ValueError(
                "unrecognised screening step %r on unit %s; the step names are "
                "fixed" % (name, serial)
            )
        if name in checked:
            raise ValueError(
                "screening step %r is recorded twice on unit %s" % (name, serial)
            )
        checked.append(name)
    return {
        "serial": serial,
        "measured_turns_ratio": ratio,
        "steps_run": tuple(checked),
    }


def validate_units(case):
    """Read every delivered unit, refusing an over-delivery or a repeat."""
    batch = validate_batch(case)
    units = case.get("units")
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a sequence of unit records")
    if not units:
        raise ValueError("the batch delivers no unit")
    checked = []
    seen = set()
    for entry in units:
        record = validate_unit(entry)
        if record["serial"] in seen:
            raise ValueError("unit %r is delivered twice" % record["serial"])
        seen.add(record["serial"])
        checked.append(record)
    if len(checked) > batch["batch_size"]:
        raise ValueError(
            "%d units are delivered from a batch of %d; a delivery cannot be "
            "larger than the batch it came from"
            % (len(checked), batch["batch_size"])
        )
    return tuple(checked)


def turns_ratio_deviation(unit, case):
    """How far one unit's measured ratio sits from the design ratio."""
    record = validate_unit(unit)
    ratio = declared_turns_ratio(case)
    return abs(record["measured_turns_ratio"] - ratio) / ratio


def out_of_tolerance_units(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Units whose measured ratio sits outside the band, named individually."""
    validate_magnetic_policy(policy)
    tolerance = float(policy["turns_ratio_tolerance"])
    return tuple(
        record["serial"]
        for record in validate_units(case)
        if not _at_most(turns_ratio_deviation(record, case), tolerance)
    )


def step_coverage(case):
    """How many delivered units ran each recognised screening step."""
    units = validate_units(case)
    return {
        step: len([record for record in units if step in record["steps_run"]])
        for step in RECOGNISED_SCREENING_STEPS
    }


def per_unit_screening_gaps(case):
    """Per-unit steps some delivered unit never ran, with the shortfall."""
    units = validate_units(case)
    coverage = step_coverage(case)
    gaps = []
    for step in PER_UNIT_SCREENING_STEPS:
        if coverage[step] < len(units):
            gaps.append(
                {
                    "step": step,
                    "covered": coverage[step],
                    "required": len(units),
                }
            )
    return tuple(gaps)


def sample_screening_gaps(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Sample steps run on fewer units than the batch size demands."""
    required = required_sample_units(case, policy)
    coverage = step_coverage(case)
    gaps = []
    for step in SAMPLE_SCREENING_STEPS:
        if coverage[step] < required:
            gaps.append(
                {"step": step, "covered": coverage[step], "required": required}
            )
    return tuple(gaps)


def hot_spot_advisories(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Note a winding whose rise is dominated by the copper rather than the core.

    This does not move the verdict. It says where the next watt of margin has
    to come from, which is a different conversation from whether the batch
    passes.
    """
    validate_magnetic_policy(policy)
    thermal = validate_thermal_case(case)
    coefficient = copper_loss_coefficient_w(case)
    advisories = []
    if coefficient > thermal["core_loss_w"]:
        advisories.append(
            "the copper carries %.4g W against %.4g W in the core, so the hot spot "
            "moves with the winding current rather than with the switching "
            "frequency; margin bought by slowing the converter will not appear"
            % (coefficient, thermal["core_loss_w"])
        )
    return tuple(advisories)


def assess_in_house_magnetic(case, policy=DEFAULT_MAGNETIC_POLICY):
    """Full clause 6.6.8 acceptance decision for one in-house magnetic batch."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_magnetic_policy(policy)

    findings = []
    advisories = []
    result = {
        "designation": None,
        "batch_reference": None,
        "batch_size": None,
        "delivered_units": None,
        "copper_loss_coefficient_w": None,
        "thermal_stability_margin": None,
        "winding_hot_spot_c": None,
        "allowed_hot_spot_c": None,
        "design_turns_ratio": None,
        "out_of_tolerance_units": (),
        "required_sample_units": None,
        "per_unit_screening_gaps": (),
        "sample_screening_gaps": (),
        "findings": findings,
        "advisories": advisories,
    }

    basis = validate_build_basis(case)
    result["designation"] = basis["designation"]
    reasons = build_basis_findings(case, policy)
    if reasons:
        findings.extend(reasons)
        result["verdict"] = BUILD_BASIS_NOT_ESTABLISHED
        return result

    coefficient = copper_loss_coefficient_w(case)
    margin = thermal_stability_margin(case, policy)
    result["copper_loss_coefficient_w"] = coefficient
    result["thermal_stability_margin"] = margin
    advisories.extend(hot_spot_advisories(case, policy))

    if not thermal_solution_settles(case, policy):
        findings.append(
            "the heat balance does not settle: the copper loss rises with "
            "temperature at least as fast as the component sheds it, so the "
            "winding has no steady operating point to assess"
        )
        result["verdict"] = WINDING_THERMAL_SOLUTION_DOES_NOT_SETTLE
        return result

    if not _at_least(margin, float(policy["min_thermal_stability_margin"])):
        findings.append(
            "the component sheds heat only %.4g times as fast as the copper loss "
            "chases the temperature, against the %.4g the class asks for"
            % (margin, float(policy["min_thermal_stability_margin"]))
        )
        result["verdict"] = THERMAL_STABILITY_MARGIN_SHORT
        return result

    hot_spot = winding_hot_spot_c(case, policy)
    allowed = allowed_hot_spot_c(case, policy)
    result["winding_hot_spot_c"] = hot_spot
    result["allowed_hot_spot_c"] = allowed
    if not _at_most(hot_spot, allowed):
        findings.append(
            "the winding settles at %.4g C against the %.4g C left once the class "
            "margin is held back from the insulation rating"
            % (hot_spot, allowed)
        )
        result["verdict"] = HOT_SPOT_OVER_INSULATION_RATING
        return result

    ratio = declared_turns_ratio(case)
    batch = validate_batch(case)
    units = validate_units(case)
    result["design_turns_ratio"] = ratio
    result["batch_reference"] = batch["batch_reference"]
    result["batch_size"] = batch["batch_size"]
    result["delivered_units"] = len(units)

    outliers = out_of_tolerance_units(case, policy)
    result["out_of_tolerance_units"] = outliers
    if outliers:
        for serial in outliers:
            findings.append(
                "unit %s measures a turns ratio %.4g outside the %.4g band around "
                "the design ratio, so it is a different transformer wearing the "
                "same part number"
                % (
                    serial,
                    [
                        record["measured_turns_ratio"]
                        for record in units
                        if record["serial"] == serial
                    ][0],
                    float(policy["turns_ratio_tolerance"]),
                )
            )
        result["verdict"] = TURNS_RATIO_OUT_OF_TOLERANCE
        return result

    required = required_sample_units(case, policy)
    per_unit_gaps = per_unit_screening_gaps(case)
    sample_gaps = sample_screening_gaps(case, policy)
    result["required_sample_units"] = required
    result["per_unit_screening_gaps"] = per_unit_gaps
    result["sample_screening_gaps"] = sample_gaps

    if per_unit_gaps or sample_gaps:
        for gap in per_unit_gaps:
            findings.append(
                "%s ran on %d of the %d delivered units; it is owed by every unit "
                "because it catches the defect that kills one piece"
                % (gap["step"], gap["covered"], gap["required"])
            )
        for gap in sample_gaps:
            findings.append(
                "%s ran on %d units against the %d this batch size requires; it "
                "characterises the batch, and a smaller sample characterises less "
                "of it" % (gap["step"], gap["covered"], gap["required"])
            )
        result["verdict"] = SCREENING_COVERAGE_SHORT
        return result

    result["verdict"] = MEETS_CLASS_THREE_SCOPE
    return result
