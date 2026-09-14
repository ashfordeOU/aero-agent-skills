#!/usr/bin/env python3
"""Supplier-built magnetic components and their screening at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.6.8. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

At the intermediate assurance class a magnetic component is usually not
bought from a catalogue and not wound on the prime's own bench either. It is
built by a supplier to the project's drawing, which moves two things at once:
the build basis stops being a datasheet and becomes the supplier's released
process at a stated issue, and the screening stops being something the
manufacturer certified and becomes something the delivery lot has to
demonstrate.

Three ideas follow, and each is a way a lot gets accepted that should not be.

A build standard without an issue is not a build standard. Two deliveries
against the same drawing number can be two different parts if the process
moved between them, so the issue travels with the acceptance data or the lot
has no traceable basis at all.

Screening at this class splits in two. Some steps are owed by every delivered
unit because they find the defect that kills one unit -- an insulation
weakness, a mis-terminated winding. Others are owed by a sample drawn from
the lot because they characterise the build rather than the piece. Reading a
sample step as though it covered the lot, or running a per-unit step on a
sample, are the same mistake in opposite directions.

A sample is a count, not a gesture. The required sample follows the lot size
through a declared fraction, is floored at a minimum number of units so a
small lot is not screened by one piece, and can never exceed the lot.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

VISUAL_AND_WORKMANSHIP_INSPECTION = "visual-and-workmanship-inspection"
WINDING_RESISTANCE_MEASUREMENT = "winding-resistance-measurement"
INSULATION_RESISTANCE_MEASUREMENT = "insulation-resistance-measurement"
DIELECTRIC_WITHSTAND_MEASUREMENT = "dielectric-withstand-measurement"
INDUCTANCE_AND_TURNS_RATIO_CHECK = "inductance-and-turns-ratio-check"
WOUND_ASSEMBLY_THERMAL_CYCLING = "wound-assembly-thermal-cycling"
ENCAPSULATION_SECTIONING = "encapsulation-sectioning"

FULL_SCREENING_STEPS = (
    VISUAL_AND_WORKMANSHIP_INSPECTION,
    WINDING_RESISTANCE_MEASUREMENT,
    INSULATION_RESISTANCE_MEASUREMENT,
    DIELECTRIC_WITHSTAND_MEASUREMENT,
)

SAMPLE_SCREENING_STEPS = (
    INDUCTANCE_AND_TURNS_RATIO_CHECK,
    WOUND_ASSEMBLY_THERMAL_CYCLING,
    ENCAPSULATION_SECTIONING,
)

RECOGNISED_SCREENING_STEPS = FULL_SCREENING_STEPS + SAMPLE_SCREENING_STEPS

BUILD_BASIS_NOT_ESTABLISHED = "supplier-build-basis-not-established"
DESIGN_MARGIN_NOT_DEMONSTRATED = "magnetic-design-margin-not-demonstrated"
SCREENING_COVERAGE_SHORTFALL = "magnetic-screening-coverage-shortfall"
MAGNETIC_MEETS_CLASS_TWO = "supplier-built-magnetic-meets-class-two"

DEFAULT_SCREENING_POLICY = {
    "sample_fraction": 0.1,
    "min_sample_units": 2,
    "max_flux_utilization": 0.8,
    "max_current_density_a_per_mm2": 6.0,
    "min_insulation_margin_k": 10.0,
    "min_withstand_ratio": 2.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


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


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of units, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


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


def validate_screening_policy(policy):
    """Check the screening and margin policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_positive("sample_fraction", policy.get("sample_fraction"))
    if fraction > 1.0:
        raise ValueError(
            "sample_fraction %g is above one; a sample cannot exceed its lot"
            % fraction
        )
    _require_count("min_sample_units", policy.get("min_sample_units"))
    utilization = _require_positive(
        "max_flux_utilization", policy.get("max_flux_utilization")
    )
    if utilization > float(DEFAULT_SCREENING_POLICY["max_flux_utilization"]):
        raise ValueError(
            "max_flux_utilization %g is looser than the %g the class allows; a "
            "project may tighten a ceiling, never widen it"
            % (utilization, DEFAULT_SCREENING_POLICY["max_flux_utilization"])
        )
    _require_positive(
        "max_current_density_a_per_mm2",
        policy.get("max_current_density_a_per_mm2"),
    )
    _require_non_negative(
        "min_insulation_margin_k", policy.get("min_insulation_margin_k")
    )
    ratio = _require_positive("min_withstand_ratio", policy.get("min_withstand_ratio"))
    if ratio < 1.0:
        raise ValueError(
            "min_withstand_ratio %g is below one; a withstand at or under the "
            "working voltage demonstrates nothing" % ratio
        )
    return policy


def validate_part_identity(part):
    """Read the identity and build basis of one supplier-built magnetic."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    designation = _require_label("designation", part.get("designation"))
    if not designation:
        raise ValueError("designation must not be blank")
    supplier = _require_label("supplier", part.get("supplier"))
    if not supplier:
        raise ValueError("supplier must not be blank; a build basis needs a builder")
    standard = _require_label("build_standard", part.get("build_standard"))
    issue = _require_label("build_standard_issue", part.get("build_standard_issue"))
    released = _require_flag(
        "supplier_process_released", part.get("supplier_process_released")
    )
    delivered = _require_flag(
        "acceptance_data_delivered", part.get("acceptance_data_delivered")
    )
    return {
        "designation": designation,
        "supplier": supplier,
        "build_standard": standard,
        "build_standard_issue": issue,
        "supplier_process_released": released,
        "acceptance_data_delivered": delivered,
    }


def build_basis_findings(part):
    """Name every reason the supplier build basis is not traceable."""
    record = validate_part_identity(part)
    findings = []
    if not record["build_standard"]:
        findings.append(
            "no build standard is referenced, so the delivered units answer to "
            "no drawing"
        )
    if not record["build_standard_issue"]:
        findings.append(
            "the build standard carries no issue; two lots to the same number "
            "can be two different parts"
        )
    if not record["supplier_process_released"]:
        findings.append(
            "the supplier winding process is not released, so the build is "
            "undocumented work whatever it measures at"
        )
    if not record["acceptance_data_delivered"]:
        findings.append(
            "no acceptance data was delivered with the lot, so nothing the "
            "supplier measured can be reviewed"
        )
    return tuple(findings)


def validate_build_lot(lot):
    """Read the delivery lot: its identifier, its size and what arrived."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    identifier = _require_label("lot id", lot.get("id"))
    if not identifier:
        raise ValueError("lot id must not be blank")
    size = _require_count("lot_size", lot.get("lot_size"))
    delivered = _require_count("delivered_units", lot.get("delivered_units"))
    if delivered > size:
        raise ValueError(
            "delivered_units %d exceeds the lot size %d; the delivery and the "
            "lot record disagree" % (delivered, size)
        )
    return {"id": identifier, "lot_size": size, "delivered_units": delivered}


def required_sample_units(lot, policy=DEFAULT_SCREENING_POLICY):
    """Units the sample-drawn screening steps owe, from the lot size."""
    validate_screening_policy(policy)
    record = validate_build_lot(lot)
    fraction = float(policy["sample_fraction"])
    floor = int(policy["min_sample_units"])
    scaled = int(math.ceil(fraction * record["lot_size"] - 1e-9))
    return min(record["lot_size"], max(floor, scaled))


def sample_shortfall_units(lot, screened_units, policy=DEFAULT_SCREENING_POLICY):
    """How many sample units the lot is short, zero when the sample is met."""
    required = required_sample_units(lot, policy)
    if isinstance(screened_units, bool) or not isinstance(screened_units, int):
        raise ValueError(
            "screened_units must be a whole number of units, got %r" % (screened_units,)
        )
    if screened_units < 0:
        raise ValueError("screened_units must not be negative, got %r" % (screened_units,))
    record = validate_build_lot(lot)
    if screened_units > record["delivered_units"]:
        raise ValueError(
            "screened_units %d exceeds the %d units delivered"
            % (screened_units, record["delivered_units"])
        )
    return max(0, required - screened_units)


def validate_winding(winding):
    """Read one winding: turns, conductor cross-section and working current."""
    if not isinstance(winding, dict):
        raise ValueError("winding must be a mapping, got %r" % (winding,))
    name = _require_label("winding name", winding.get("name"))
    if not name:
        raise ValueError("winding name must not be blank")
    turns = _require_count("turns on %s" % name, winding.get("turns"))
    area = _require_positive(
        "conductor_area_mm2 on %s" % name, winding.get("conductor_area_mm2")
    )
    current = _require_non_negative(
        "rms_current_a on %s" % name, winding.get("rms_current_a")
    )
    return {
        "name": name,
        "turns": turns,
        "conductor_area_mm2": area,
        "rms_current_a": current,
    }


def validate_windings(windings):
    """Read every winding, refusing an empty set or a repeated name."""
    if not isinstance(windings, (list, tuple)):
        raise ValueError("windings must be a sequence of winding records")
    if not windings:
        raise ValueError("no winding was declared, so there is no magnetic to assess")
    checked = []
    seen = set()
    for winding in windings:
        record = validate_winding(winding)
        if record["name"] in seen:
            raise ValueError("winding %r is declared twice" % record["name"])
        seen.add(record["name"])
        checked.append(record)
    return tuple(checked)


def winding_current_density(winding):
    """Conductor current density in ampere per square millimetre."""
    record = validate_winding(winding)
    return record["rms_current_a"] / record["conductor_area_mm2"]


def overloaded_windings(windings, policy=DEFAULT_SCREENING_POLICY):
    """Windings above the density ceiling; a winding exactly on it passes."""
    validate_screening_policy(policy)
    checked = validate_windings(windings)
    ceiling = float(policy["max_current_density_a_per_mm2"])
    return tuple(
        winding["name"]
        for winding in checked
        if not _at_most(winding_current_density(winding), ceiling)
    )


def flux_utilization(peak_flux_mt, saturation_flux_mt):
    """Peak working flux over saturation flux at the hot case."""
    peak = _require_non_negative("peak_flux_mt", peak_flux_mt)
    saturation = _require_positive("hot_case_saturation_flux_mt", saturation_flux_mt)
    return peak / saturation


def insulation_margin_k(insulation_rating_c, hot_spot_c):
    """Kelvin between the winding hot spot and the insulation system rating."""
    rating = _require_number("insulation_rating_c", insulation_rating_c)
    hot_spot = _require_number("hot_spot_c", hot_spot_c)
    return rating - hot_spot


def withstand_ratio(demonstrated_v, working_v):
    """Demonstrated withstand voltage over the voltage the winding works at."""
    demonstrated = _require_non_negative("demonstrated_withstand_v", demonstrated_v)
    working = _require_positive("working_voltage_v", working_v)
    return demonstrated / working


def validate_screening_record(declared):
    """Read the declared screening steps, refusing an unrecognised name."""
    if not isinstance(declared, (list, tuple)):
        raise ValueError("screening_steps must be a sequence of step names")
    named = []
    for step in declared:
        label = _require_label("screening step", step)
        if label not in RECOGNISED_SCREENING_STEPS:
            raise ValueError(
                "unrecognised screening step %r; the step names are fixed" % label
            )
        if label in named:
            raise ValueError("screening step %r is declared twice" % label)
        named.append(label)
    return tuple(named)


def absent_full_screening_steps(declared):
    """Per-unit steps the lot never ran."""
    named = validate_screening_record(declared)
    return tuple(step for step in FULL_SCREENING_STEPS if step not in named)


def absent_sample_screening_steps(declared):
    """Sample-drawn steps the lot never ran."""
    named = validate_screening_record(declared)
    return tuple(step for step in SAMPLE_SCREENING_STEPS if step not in named)


def screening_coverage(declared):
    """Share of the recognised screening steps the lot actually ran."""
    named = validate_screening_record(declared)
    return len(named) / len(RECOGNISED_SCREENING_STEPS)


def assess_supplier_built_magnetic(case, policy=DEFAULT_SCREENING_POLICY):
    """Full clause 5.6.8 decision for one supplier-built magnetic delivery."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_screening_policy(policy)

    findings = []
    advisories = []
    result = {
        "designation": None,
        "lot_id": None,
        "required_sample_units": None,
        "sample_shortfall_units": None,
        "screening_coverage": None,
        "absent_full_screening_steps": (),
        "absent_sample_screening_steps": (),
        "overloaded_windings": (),
        "flux_utilization": None,
        "insulation_margin_k": None,
        "withstand_ratio": None,
        "findings": findings,
        "advisories": advisories,
    }

    part = case.get("part")
    if part is None:
        findings.append(
            "no magnetic part is declared, so there is no build basis to trace"
        )
        result["verdict"] = BUILD_BASIS_NOT_ESTABLISHED
        return result

    identity = validate_part_identity(part)
    result["designation"] = identity["designation"]
    basis = build_basis_findings(part)
    if basis:
        findings.extend(basis)
        result["verdict"] = BUILD_BASIS_NOT_ESTABLISHED
        return result

    lot = validate_build_lot(case.get("lot"))
    result["lot_id"] = lot["id"]

    windings = validate_windings(case.get("windings"))
    overloaded = overloaded_windings(windings, policy)
    result["overloaded_windings"] = overloaded

    utilization = flux_utilization(
        case.get("peak_flux_mt"), case.get("hot_case_saturation_flux_mt")
    )
    margin = insulation_margin_k(
        case.get("insulation_rating_c"), case.get("hot_spot_c")
    )
    ratio = withstand_ratio(
        case.get("demonstrated_withstand_v"), case.get("working_voltage_v")
    )
    result["flux_utilization"] = utilization
    result["insulation_margin_k"] = margin
    result["withstand_ratio"] = ratio

    for name in overloaded:
        findings.append(
            "winding %s works above the %.3g A/mm2 density ceiling"
            % (name, float(policy["max_current_density_a_per_mm2"]))
        )
    if not _at_most(utilization, float(policy["max_flux_utilization"])):
        findings.append(
            "core works to %.3g of hot-case saturation against the %.3g ceiling"
            % (utilization, float(policy["max_flux_utilization"]))
        )
    if not _at_least(margin, float(policy["min_insulation_margin_k"])):
        findings.append(
            "winding hot spot leaves %.3g K to the insulation rating against "
            "the %.3g K the class asks for"
            % (margin, float(policy["min_insulation_margin_k"]))
        )
    if not _at_least(ratio, float(policy["min_withstand_ratio"])):
        findings.append(
            "demonstrated withstand is %.3g times the working voltage against "
            "the %.3g times required"
            % (ratio, float(policy["min_withstand_ratio"]))
        )
    if findings:
        result["verdict"] = DESIGN_MARGIN_NOT_DEMONSTRATED
        return result

    declared = validate_screening_record(case.get("screening_steps", ()))
    result["screening_coverage"] = screening_coverage(declared)
    absent_full = absent_full_screening_steps(declared)
    absent_sample = absent_sample_screening_steps(declared)
    result["absent_full_screening_steps"] = absent_full
    result["absent_sample_screening_steps"] = absent_sample

    required_sample = required_sample_units(lot, policy)
    screened = case.get("sample_units_screened", 0)
    shortfall = sample_shortfall_units(lot, screened, policy)
    result["required_sample_units"] = required_sample
    result["sample_shortfall_units"] = shortfall

    for step in absent_full:
        findings.append("%s was not run on every delivered unit" % step)
    for step in absent_sample:
        findings.append("%s was not run on any sample unit" % step)
    if shortfall:
        findings.append(
            "the sample reached %d of the %d units the lot of %d owes"
            % (screened, required_sample, lot["lot_size"])
        )
    if lot["delivered_units"] < lot["lot_size"]:
        advisories.append(
            "only %d of the %d units in lot %s were delivered; the sample was "
            "sized on the lot, so a later delivery from the same lot inherits "
            "this screening rather than earning its own"
            % (lot["delivered_units"], lot["lot_size"], lot["id"])
        )
    if findings:
        result["verdict"] = SCREENING_COVERAGE_SHORTFALL
        return result

    result["verdict"] = MAGNETIC_MEETS_CLASS_TWO
    return result
