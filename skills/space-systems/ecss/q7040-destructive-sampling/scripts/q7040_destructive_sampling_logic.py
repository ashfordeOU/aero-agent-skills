#!/usr/bin/env python3
"""Destructive sampling of brazements: metallography and peel testing.

Anchor: ECSS-Q-ST-70-40 quality clause on destructive verification of
brazed joints. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Non-destructive inspection of a brazement sees the outside of a fillet.
The two things that decide whether the joint carries load — how much of
the faying area the filler actually wetted, and whether the voids in it
are scattered or joined into one unbonded run — are inside it. That is
what destructive sampling buys, and it buys it by destroying flight
parts, so the plan has to be decided rather than assumed.

Which test applies comes from the geometry. A lap joint peels, and the
peeled faces show the wetted area directly. A butt or sleeve joint
cannot be peeled without tearing the parent, so it is sectioned and read
under a microscope. A fillet-only joint is sectioned too.

How many come from the lot size and the criticality, and the plan has a
floor and a ceiling: below the floor a single bad joint is not visible
at all, and above the ceiling the sampling costs more parts than the
delivery is worth. When the required sample approaches the lot itself,
the answer is not to destroy the lot; it is to braze representative
coupons alongside it in the same run, on the same fixture, out of the
same filler batch.

Reading the result: a joint fails on coverage, on total void fraction,
or on a single continuous void longer than the run the joint can bridge
— and the third one is the reason total void fraction alone is not
enough, because the same void area spread out is a sound joint and
joined up is a crack starter.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

GEOMETRY_LAP = "lap-joint"
GEOMETRY_BUTT = "butt-joint"
GEOMETRY_SLEEVE = "sleeve-joint"
GEOMETRY_FILLET = "fillet-only-joint"

GEOMETRIES = (GEOMETRY_LAP, GEOMETRY_BUTT, GEOMETRY_SLEEVE, GEOMETRY_FILLET)

TEST_METALLOGRAPHIC = "metallographic-section"
TEST_PEEL = "peel-test"
TEST_TENSILE_SHEAR = "tensile-shear-test"

DESTRUCTIVE_TESTS = (TEST_METALLOGRAPHIC, TEST_PEEL, TEST_TENSILE_SHEAR)

_TESTS_BY_GEOMETRY = {
    GEOMETRY_LAP: (TEST_PEEL, TEST_METALLOGRAPHIC),
    GEOMETRY_BUTT: (TEST_METALLOGRAPHIC, TEST_TENSILE_SHEAR),
    GEOMETRY_SLEEVE: (TEST_METALLOGRAPHIC, TEST_TENSILE_SHEAR),
    GEOMETRY_FILLET: (TEST_METALLOGRAPHIC,),
}

CRITICALITIES = ("critical", "major", "minor")

# One sample per this many joints, with a floor and a ceiling on the plan.
_SAMPLING_DIVISOR = {"critical": 10, "major": 25, "minor": 50}
_SAMPLE_FLOOR = {"critical": 2, "major": 1, "minor": 1}
_SAMPLE_CEILING = {"critical": 10, "major": 6, "minor": 3}

# Above this fraction of the lot, sampling costs more than the delivery
# is worth and representative coupons are brazed alongside instead.
COUPON_SWITCH_FRACTION = 0.25

STRATEGY_SAMPLE_LOT = "destructively-sample-from-the-lot"
STRATEGY_COUPONS = "braze-representative-coupons-with-the-lot"

# Acceptance limits, as percentages of the faying area.
_MINIMUM_COVERAGE_PCT = {"critical": 85.0, "major": 75.0, "minor": 65.0}
_MAXIMUM_VOID_PCT = {"critical": 10.0, "major": 20.0, "minor": 30.0}
_MAXIMUM_CONTINUOUS_VOID_PCT = {"critical": 5.0, "major": 10.0, "minor": 15.0}

# Floating-point representation tolerance on a percentage comparison.
PERCENT_TOLERANCE = 1e-9

LOT_ACCEPTED = "lot-accepted"
LOT_REJECTED = "lot-rejected"
LOT_RESAMPLE = "lot-held-for-double-sampling"


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (name, value))
    return value


def _require_percent(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if value < 0.0 or value > 100.0:
        raise ValueError(
            "%s is a percentage of the faying area and must lie in 0..100, "
            "got %r" % (name, value)
        )
    return float(value)


def applicable_tests(geometry):
    """Destructive tests the joint geometry can actually be read by."""
    _require_choice("geometry", geometry, GEOMETRIES)
    return list(_TESTS_BY_GEOMETRY[geometry])


def sample_size(lot_size, criticality):
    """Joints the plan calls for, before the coupon switch is considered."""
    lot = _require_positive_int("lot_size", lot_size)
    _require_choice("criticality", criticality, CRITICALITIES)
    raw = -(-lot // _SAMPLING_DIVISOR[criticality])
    planned = max(_SAMPLE_FLOOR[criticality], raw)
    planned = min(planned, _SAMPLE_CEILING[criticality])
    return min(planned, lot)


def sampling_plan(lot_size, criticality, geometry):
    """The plan: how many joints, read by which tests, taken from where."""
    lot = _require_positive_int("lot_size", lot_size)
    _require_choice("criticality", criticality, CRITICALITIES)
    tests = applicable_tests(geometry)
    planned = sample_size(lot, criticality)
    fraction = planned / lot
    use_coupons = fraction - COUPON_SWITCH_FRACTION > PERCENT_TOLERANCE
    return {
        "lot_size": lot,
        "criticality": criticality,
        "geometry": geometry,
        "sample_size": planned,
        "sampled_fraction": fraction,
        "applicable_tests": tests,
        "strategy": STRATEGY_COUPONS if use_coupons else STRATEGY_SAMPLE_LOT,
        "coupons_required": use_coupons,
        "coupon_rationale": (
            "the plan would consume %d of %d joints; coupons brazed in the "
            "same run, on the same fixture and out of the same filler batch "
            "carry the evidence instead" % (planned, lot)
        )
        if use_coupons
        else "",
    }


def evaluate_section(sample, criticality):
    """Read one sectioned or peeled sample against the acceptance limits."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping, got %r" % (sample,))
    _require_choice("criticality", criticality, CRITICALITIES)
    sample_id = sample.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample_id must be a non-empty string, got %r" % (sample_id,))
    coverage = _require_percent("coverage_pct", sample.get("coverage_pct"))
    voids = _require_percent("void_pct", sample.get("void_pct"))
    longest = _require_percent(
        "longest_continuous_void_pct", sample.get("longest_continuous_void_pct")
    )
    if longest - voids > PERCENT_TOLERANCE:
        raise ValueError(
            "the longest continuous void (%.3f%%) cannot exceed the total void "
            "fraction (%.3f%%) of the same section" % (longest, voids)
        )
    if coverage + voids - 100.0 > PERCENT_TOLERANCE:
        raise ValueError(
            "coverage (%.3f%%) and voids (%.3f%%) together exceed the faying "
            "area of the section" % (coverage, voids)
        )
    min_coverage = _MINIMUM_COVERAGE_PCT[criticality]
    max_voids = _MAXIMUM_VOID_PCT[criticality]
    max_continuous = _MAXIMUM_CONTINUOUS_VOID_PCT[criticality]
    findings = []
    if min_coverage - coverage > PERCENT_TOLERANCE:
        findings.append(
            "coverage %.3f%% is short of the %.3f%% a %s joint owes"
            % (coverage, min_coverage, criticality)
        )
    if voids - max_voids > PERCENT_TOLERANCE:
        findings.append(
            "void fraction %.3f%% is over the %.3f%% limit"
            % (voids, max_voids)
        )
    if longest - max_continuous > PERCENT_TOLERANCE:
        findings.append(
            "a single continuous void runs %.3f%% of the faying area against a "
            "%.3f%% limit; joined-up voids start a crack that scattered ones "
            "of the same area do not" % (longest, max_continuous)
        )
    return {
        "sample_id": sample_id,
        "coverage_pct": coverage,
        "void_pct": voids,
        "longest_continuous_void_pct": longest,
        "minimum_coverage_pct": min_coverage,
        "maximum_void_pct": max_voids,
        "maximum_continuous_void_pct": max_continuous,
        "acceptable": not findings,
        "findings": findings,
    }


def assess_lot(case):
    """Disposition the lot on the destructive samples that were read."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot_id = case.get("lot_id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("lot_id must be a non-empty string, got %r" % (lot_id,))
    lot_size = _require_positive_int("lot_size", case.get("lot_size"))
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITIES
    )
    geometry = _require_choice("geometry", case.get("geometry"), GEOMETRIES)
    samples = case.get("samples")
    if not isinstance(samples, (list, tuple)):
        raise ValueError("samples must be a sequence of sample mappings")
    plan = sampling_plan(lot_size, criticality, geometry)
    already_resampled = case.get("already_resampled", False)
    if not isinstance(already_resampled, bool):
        raise ValueError(
            "already_resampled must be True or False, got %r" % (already_resampled,)
        )

    results = [evaluate_section(sample, criticality) for sample in samples]
    failures = [r for r in results if not r["acceptable"]]
    findings = []
    if len(samples) < plan["sample_size"]:
        findings.append(
            "%d sample(s) were read against a plan of %d; the lot has not been "
            "sampled to plan" % (len(samples), plan["sample_size"])
        )
    for failed in failures:
        findings.append(
            "sample %s: %s" % (failed["sample_id"], "; ".join(failed["findings"]))
        )

    if findings and len(samples) < plan["sample_size"]:
        disposition = LOT_RESAMPLE
    elif not failures:
        disposition = LOT_ACCEPTED
    elif criticality == "critical" or already_resampled or len(failures) > 1:
        disposition = LOT_REJECTED
    else:
        disposition = LOT_RESAMPLE
    return {
        "lot_id": lot_id,
        "plan": plan,
        "samples_read": len(samples),
        "sample_results": results,
        "failed_samples": [r["sample_id"] for r in failures],
        "disposition": disposition,
        "findings": findings,
    }
