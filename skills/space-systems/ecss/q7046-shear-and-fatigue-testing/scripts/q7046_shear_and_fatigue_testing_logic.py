#!/usr/bin/env python3
"""Shear and fatigue testing of threaded fasteners, where the
application calls for them.

Anchor: ECSS-Q-ST-70-46 testing clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Neither test is owed by every fastener. A shear-loaded joint owes
shear; a cyclically loaded joint owes fatigue; a fracture-critical
fastener owes both whatever the duty looks like.

The shear allowable depends on the plane the joint loads. A plate
interface crossing the plain shank works on the full shank section; an
interface landing on the threads works on the minor-diameter section,

    d_minor = d - 1.226869 * P

which is smaller, and smaller again once squared. Double shear crosses
two planes, so the load carried doubles while the stress in the
fastener does not. Shear strength is a fraction of the ultimate tensile
strength, and that fraction belongs to the material family.

A fatigue specimen has three outcomes: it failed below the required
life, it passed on its own cycles, or it reached the run-out limit and
survived the test. A set below the minimum specimen count has measured
no scatter and therefore has no verdict.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

#: Relative slack on a comparison whose two sides are both computed.
LOAD_REL_TOL = 1e-9

#: Multiple of the pitch subtracted from the nominal for the minor diameter.
MINOR_DIAMETER_PITCH_FACTOR = 1.226869

PLANE_SHANK = "plain-shank"
PLANE_THREAD = "threaded-section"
SHEAR_PLANES = (PLANE_SHANK, PLANE_THREAD)

LOAD_MODE_TENSION = "tension-dominated"
LOAD_MODE_SHEAR = "shear-dominated"
LOAD_MODE_COMBINED = "combined-tension-and-shear"
LOAD_MODES = (LOAD_MODE_TENSION, LOAD_MODE_SHEAR, LOAD_MODE_COMBINED)

CRITICALITIES = ("fracture-critical", "structural", "non-structural")

TEST_SHEAR = "shear-strength"
TEST_FATIGUE = "axial-fatigue"

#: Cycles below which a duty is treated as static rather than cyclic.
CYCLIC_THRESHOLD = 1000

#: Fatigue specimens needed before a set says anything about scatter.
MIN_FATIGUE_SPECIMENS = 5

FATIGUE_FAILED = "failed-below-required-life"
FATIGUE_PASSED = "passed-on-cycles"
FATIGUE_RUNOUT = "run-out-survived"

RESULT_PASS = "pass"
RESULT_FAIL = "fail"

VERDICT_ACCEPT = "shear-and-fatigue-accepted"
VERDICT_REJECT = "shear-or-fatigue-rejected"
VERDICT_SET_TOO_SMALL = "fatigue-set-below-minimum"
VERDICT_NOT_REQUIRED = "no-shear-or-fatigue-testing-owed"

#: Ultimate tensile stress in MPa and the shear fraction of the family.
_MATERIAL_CLASSES = {
    "8.8": {"ultimate_mpa": 800.0, "shear_ratio": 0.60},
    "10.9": {"ultimate_mpa": 1040.0, "shear_ratio": 0.60},
    "12.9": {"ultimate_mpa": 1220.0, "shear_ratio": 0.60},
    "A2-70": {"ultimate_mpa": 700.0, "shear_ratio": 0.55},
    "A4-80": {"ultimate_mpa": 800.0, "shear_ratio": 0.55},
    "Ti-6Al-4V": {"ultimate_mpa": 900.0, "shear_ratio": 0.58},
}

PROPERTY_CLASSES = tuple(sorted(_MATERIAL_CLASSES))


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, bound, rel_tol=LOAD_REL_TOL):
    return value >= bound - abs(bound) * rel_tol


def testing_required(application):
    """Which of shear and fatigue this application owes, and why."""
    if not isinstance(application, dict):
        raise ValueError("application must be a mapping, got %r" % (application,))
    load_mode = _require_choice(
        "load_mode", application.get("load_mode"), LOAD_MODES
    )
    criticality = _require_choice(
        "criticality", application.get("criticality"), CRITICALITIES
    )
    cycles = application.get("expected_cycles", 0)
    _require_count("expected_cycles", cycles)
    cyclic = bool(application.get("cyclic_loading", False))

    owed = []
    reasons = {}
    if load_mode in (LOAD_MODE_SHEAR, LOAD_MODE_COMBINED):
        owed.append(TEST_SHEAR)
        reasons[TEST_SHEAR] = "the joint is %s" % load_mode
    elif criticality == "fracture-critical":
        owed.append(TEST_SHEAR)
        reasons[TEST_SHEAR] = (
            "a fracture-critical fastener owes shear evidence whatever the "
            "nominal load mode"
        )

    if criticality == "fracture-critical" and cyclic:
        owed.append(TEST_FATIGUE)
        reasons[TEST_FATIGUE] = "a fracture-critical fastener under cyclic duty"
    elif cyclic and cycles >= CYCLIC_THRESHOLD and criticality != "non-structural":
        owed.append(TEST_FATIGUE)
        reasons[TEST_FATIGUE] = (
            "cyclic duty of %d cycles, at or above the %d-cycle threshold"
            % (cycles, CYCLIC_THRESHOLD)
        )

    return {
        "load_mode": load_mode,
        "criticality": criticality,
        "tests_owed": owed,
        "reasons": reasons,
    }


def shear_plane_area_mm2(nominal_diameter_mm, pitch_mm, plane):
    """Area of the section the shear plane crosses, in mm^2."""
    diameter = _require_positive("nominal_diameter_mm", nominal_diameter_mm)
    pitch = _require_positive("pitch_mm", pitch_mm)
    _require_choice("plane", plane, SHEAR_PLANES)
    if plane == PLANE_SHANK:
        return math.pi / 4.0 * diameter * diameter
    minor = diameter - MINOR_DIAMETER_PITCH_FACTOR * pitch
    if minor <= 0.0:
        raise ValueError(
            "pitch %.4f mm leaves no minor diameter on a %.4f mm thread"
            % (pitch, diameter)
        )
    return math.pi / 4.0 * minor * minor


def shear_strength_mpa(property_class):
    """Shear strength of the class, as its family fraction of ultimate."""
    if property_class not in _MATERIAL_CLASSES:
        raise ValueError(
            "property_class must be one of %s, got %r"
            % (", ".join(PROPERTY_CLASSES), property_class)
        )
    spec = _MATERIAL_CLASSES[property_class]
    return spec["ultimate_mpa"] * spec["shear_ratio"]


def shear_allowable_n(nominal_diameter_mm, pitch_mm, plane, property_class, planes=1):
    """Load the joint may carry, over one or two shear planes."""
    count = _require_count("planes", planes, minimum=1)
    if count > 2:
        raise ValueError(
            "planes must be 1 for single shear or 2 for double shear, got %d"
            % count
        )
    area = shear_plane_area_mm2(nominal_diameter_mm, pitch_mm, plane)
    return area * shear_strength_mpa(property_class) * count


def evaluate_shear_test(measured_load_n, allowable_load_n):
    """Judge one shear specimen against the allowable for its fixture."""
    measured = _require_positive("measured_load_n", measured_load_n)
    allowable = _require_positive("allowable_load_n", allowable_load_n)
    if _at_least(measured, allowable):
        return {
            "result": RESULT_PASS,
            "measured_load_n": measured,
            "allowable_load_n": allowable,
            "findings": [],
        }
    return {
        "result": RESULT_FAIL,
        "measured_load_n": measured,
        "allowable_load_n": allowable,
        "findings": [
            "shear load %.1f N is below the allowable of %.1f N"
            % (measured, allowable)
        ],
    }


def evaluate_fatigue_result(cycles, required_cycles, runout_cycles):
    """Score one fatigue specimen as failed, passed or run out."""
    achieved = _require_count("cycles", cycles)
    required = _require_count("required_cycles", required_cycles, minimum=1)
    runout = _require_count("runout_cycles", runout_cycles, minimum=1)
    if runout < required:
        raise ValueError(
            "runout_cycles %d is below required_cycles %d; the test would end "
            "before the life it is meant to demonstrate" % (runout, required)
        )
    if achieved >= runout:
        outcome = FATIGUE_RUNOUT
    elif achieved >= required:
        outcome = FATIGUE_PASSED
    else:
        outcome = FATIGUE_FAILED
    return {
        "outcome": outcome,
        "cycles": achieved,
        "required_cycles": required,
        "runout_cycles": runout,
        "passed": outcome != FATIGUE_FAILED,
    }


def assess_fatigue_set(
    cycles_list,
    required_cycles,
    runout_cycles,
    min_specimens=MIN_FATIGUE_SPECIMENS,
):
    """Roll a fatigue set up, refusing a verdict on too small a set."""
    if isinstance(cycles_list, (str, dict)) or not isinstance(
        cycles_list, (list, tuple)
    ):
        raise ValueError(
            "cycles_list must be a sequence of cycle counts, got %r" % (cycles_list,)
        )
    minimum = _require_count("min_specimens", min_specimens, minimum=1)
    results = [
        evaluate_fatigue_result(value, required_cycles, runout_cycles)
        for value in cycles_list
    ]
    findings = []
    failures = [r for r in results if r["outcome"] == FATIGUE_FAILED]
    runouts = [r for r in results if r["outcome"] == FATIGUE_RUNOUT]
    on_cycles = [r for r in results if r["outcome"] == FATIGUE_PASSED]
    worst = min((r["cycles"] for r in results if r["outcome"] != FATIGUE_RUNOUT),
                default=None)
    if len(results) < minimum:
        findings.append(
            "%d fatigue specimen(s) tested; %d are needed before the set says "
            "anything about scatter" % (len(results), minimum)
        )
    for result in failures:
        findings.append(
            "a specimen failed at %d cycles, below the required life of %d"
            % (result["cycles"], result["required_cycles"])
        )
    return {
        "results": results,
        "specimen_count": len(results),
        "failures": len(failures),
        "runouts": len(runouts),
        "passed_on_cycles": len(on_cycles),
        "worst_life_cycles": worst,
        "set_large_enough": len(results) >= minimum,
        "findings": findings,
    }


def assess_shear_and_fatigue(case):
    """Requirement, shear allowable and fatigue set in one verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    requirement = testing_required(case.get("application", {}))
    owed = requirement["tests_owed"]
    findings = []

    shear_report = None
    if TEST_SHEAR in owed:
        planes = case.get("shear_planes", 1)
        allowable = shear_allowable_n(
            case.get("nominal_diameter_mm"),
            case.get("pitch_mm"),
            _require_choice("shear_plane", case.get("shear_plane"), SHEAR_PLANES),
            case.get("property_class"),
            planes,
        )
        measured = case.get("measured_shear_loads_n", ())
        if isinstance(measured, (str, dict)) or not isinstance(
            measured, (list, tuple)
        ):
            raise ValueError(
                "measured_shear_loads_n must be a sequence, got %r" % (measured,)
            )
        results = [evaluate_shear_test(value, allowable) for value in measured]
        for index, result in enumerate(results):
            for note in result["findings"]:
                findings.append("shear specimen %d: %s" % (index + 1, note))
        if not results:
            findings.append("shear testing is owed but no specimen was recorded")
        shear_report = {
            "allowable_load_n": allowable,
            "planes": planes,
            "results": results,
            "failures": sum(1 for r in results if r["result"] == RESULT_FAIL),
            "recorded": len(results),
        }

    fatigue_report = None
    if TEST_FATIGUE in owed:
        fatigue_report = assess_fatigue_set(
            case.get("fatigue_cycles", ()),
            case.get("required_cycles"),
            case.get("runout_cycles"),
            case.get("min_fatigue_specimens", MIN_FATIGUE_SPECIMENS),
        )
        findings.extend(fatigue_report["findings"])

    if not owed:
        verdict = VERDICT_NOT_REQUIRED
    elif fatigue_report is not None and not fatigue_report["set_large_enough"]:
        verdict = VERDICT_SET_TOO_SMALL
    elif shear_report is not None and (
        shear_report["failures"] or shear_report["recorded"] == 0
    ):
        verdict = VERDICT_REJECT
    elif fatigue_report is not None and fatigue_report["failures"]:
        verdict = VERDICT_REJECT
    else:
        verdict = VERDICT_ACCEPT

    return {
        "requirement": requirement,
        "shear": shear_report,
        "fatigue": fatigue_report,
        "findings": findings,
        "verdict": verdict,
    }
