#!/usr/bin/env python3
"""Non-destructive test selection for a brazed joint at inspection.

Anchor: the inspection provisions of the ECSS brazing standard, which
call up the non-destructive methods of ECSS-Q-ST-70-15C. The procedure
below is a paraphrase into implementable steps; no standard text is
reproduced.

Visual inspection is unconditional but sees only the joint mouth.
Coverage of the capillary gap is a volumetric question, and the joint
plane decides which volumetric method can answer it:

    butt, sleeve, tee      the gap runs along the beam -> radiography
    lap, stepped-lap       the disbond lies across the beam -> ultrasonics

Access bounds both: radiography needs a source-to-detector path across
the joint, ultrasonics needs one coupling surface parallel to it. A
joint with neither has no volumetric method, and the obligation moves
to process control with sectioned witness coupons brazed in the run.

Thickness bounds them from opposite ends: radiographic sensitivity is a
fraction of the penetrated thickness, so thick sections stop resolving
small voids, while ultrasonics needs enough sound path to separate the
joint echo from the entry surface.

Hermeticity is a separate requirement answered by a separate leak test.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

JOINT_GEOMETRIES = ("butt", "sleeve", "tee", "lap", "stepped-lap")
ACCESS_CONDITIONS = ("two-sided", "single-sided", "unreachable")
BRAZE_CLASSES = ("class-a", "class-b", "class-c")

VISUAL = "visual-inspection"
RADIOGRAPHY = "radiographic-testing"
ULTRASONICS = "ultrasonic-testing"
LEAK_TEST = "leak-testing"
WITNESS_COUPONS = "process-control-and-witness-coupons"

VOLUMETRIC_METHODS = (RADIOGRAPHY, ULTRASONICS)

# Joint planes the beam runs along are radiography-favourable; planes the
# beam crosses are the ultrasonic case.
RADIOGRAPHY_FAVOURABLE_GEOMETRIES = ("butt", "sleeve", "tee")
ULTRASONIC_FAVOURABLE_GEOMETRIES = ("lap", "stepped-lap", "sleeve")

RADIOGRAPHY_MAX_THICKNESS_MM = 25.0
ULTRASONIC_MIN_THICKNESS_MM = 1.0

# Sensitivity of each volumetric method, as a fraction of the penetrated
# thickness with an absolute floor in millimetres.
METHOD_SENSITIVITY = {
    RADIOGRAPHY: {"thickness_fraction": 0.02, "floor_mm": 0.10},
    ULTRASONICS: {"thickness_fraction": 0.01, "floor_mm": 0.50},
}

# Coverage the acceptance class demands: full inspection, or a sampled
# fraction of the lot with a floor that a small lot cannot erode. The
# fraction is held as an integer ratio, because a ceiling taken on a
# float product rounds differently between platforms exactly where the
# product lands on a whole number.
CLASS_COVERAGE = {
    "class-a": {"full": True, "numerator": 1, "denominator": 1, "floor": 1},
    "class-b": {"full": False, "numerator": 1, "denominator": 10, "floor": 3},
    "class-c": {"full": False, "numerator": 1, "denominator": 50, "floor": 1},
}

# Largest void the class still accepts, as a fraction of the wall
# thickness; used to check the method out-resolves what it must reject.
CLASS_ACCEPTED_VOID_FRACTION = {
    "class-a": 0.05,
    "class-b": 0.10,
    "class-c": 0.20,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Both sides are products of measured quantities, so a value placed
    deliberately on the limit can read a few units in the last place
    above it. The limit is never raised; only the comparison tolerates
    the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolvable_void_mm(method, thickness_mm):
    """Smallest void the method resolves through this wall thickness."""
    _require_choice("method", method, VOLUMETRIC_METHODS)
    thickness = _require_positive("thickness_mm", thickness_mm)
    spec = METHOD_SENSITIVITY[method]
    return max(spec["floor_mm"], spec["thickness_fraction"] * thickness)


def accepted_void_mm(braze_class, thickness_mm):
    """Largest void the acceptance class still accepts on this wall."""
    _require_choice("braze_class", braze_class, BRAZE_CLASSES)
    thickness = _require_positive("thickness_mm", thickness_mm)
    return CLASS_ACCEPTED_VOID_FRACTION[braze_class] * thickness


def method_out_resolves_class(method, braze_class, thickness_mm):
    """Can the method see the smallest void the class is obliged to reject."""
    return _at_most(
        resolvable_void_mm(method, thickness_mm),
        accepted_void_mm(braze_class, thickness_mm),
    )


def radiography_admissible(geometry, access, thickness_mm):
    """Is a radiographic coverage read possible on this joint at all."""
    _require_choice("geometry", geometry, JOINT_GEOMETRIES)
    _require_choice("access", access, ACCESS_CONDITIONS)
    thickness = _require_positive("thickness_mm", thickness_mm)
    if access != "two-sided":
        return False
    if geometry not in RADIOGRAPHY_FAVOURABLE_GEOMETRIES:
        return False
    return _at_most(thickness, RADIOGRAPHY_MAX_THICKNESS_MM)


def ultrasonics_admissible(geometry, access, thickness_mm):
    """Is an ultrasonic coverage read possible on this joint at all."""
    _require_choice("geometry", geometry, JOINT_GEOMETRIES)
    _require_choice("access", access, ACCESS_CONDITIONS)
    thickness = _require_positive("thickness_mm", thickness_mm)
    if access == "unreachable":
        return False
    if geometry not in ULTRASONIC_FAVOURABLE_GEOMETRIES:
        return False
    return _at_least(thickness, ULTRASONIC_MIN_THICKNESS_MM)


def select_volumetric_method(geometry, access, thickness_mm):
    """Pick the volumetric method the joint plane and access allow."""
    ut_ok = ultrasonics_admissible(geometry, access, thickness_mm)
    rt_ok = radiography_admissible(geometry, access, thickness_mm)
    findings = []
    if ut_ok and geometry in ("lap", "stepped-lap"):
        return {"method": ULTRASONICS, "findings": findings}
    if rt_ok:
        return {"method": RADIOGRAPHY, "findings": findings}
    if ut_ok:
        return {"method": ULTRASONICS, "findings": findings}
    findings.append(
        "neither radiography nor ultrasonics is admissible on a %s joint with "
        "%s access at %.3g mm; the coverage obligation moves to process "
        "control with sectioned witness coupons"
        % (geometry, access, float(thickness_mm))
    )
    return {"method": None, "findings": findings}


def ndt_sample_size(lot_size, braze_class):
    """Joints to inspect from a lot under the class coverage rule."""
    lot = _require_positive_int("lot_size", lot_size)
    _require_choice("braze_class", braze_class, BRAZE_CLASSES)
    rule = CLASS_COVERAGE[braze_class]
    if rule["full"]:
        return lot
    # Exact integer ceiling of lot * numerator / denominator.
    scaled = -((-lot * rule["numerator"]) // rule["denominator"])
    return min(lot, max(rule["floor"], scaled))


def plan_ndt(brazement):
    """Full inspection plan for one brazement: methods, coverage, findings."""
    if not isinstance(brazement, dict):
        raise ValueError("brazement must be a mapping, got %r" % (brazement,))
    geometry = _require_choice(
        "geometry", brazement.get("geometry"), JOINT_GEOMETRIES
    )
    access = _require_choice("access", brazement.get("access"), ACCESS_CONDITIONS)
    thickness = _require_positive("thickness_mm", brazement.get("thickness_mm"))
    braze_class = _require_choice(
        "braze_class", brazement.get("braze_class"), BRAZE_CLASSES
    )
    hermetic = _require_bool("hermetic", brazement.get("hermetic", False))
    lot_size = _require_positive_int("lot_size", brazement.get("lot_size", 1))
    coverage_required = _require_bool(
        "coverage_required",
        brazement.get("coverage_required", braze_class in ("class-a", "class-b")),
    )

    methods = [VISUAL]
    findings = []
    chosen = None

    if coverage_required:
        selection = select_volumetric_method(geometry, access, thickness)
        findings.extend(selection["findings"])
        chosen = selection["method"]
        if chosen is None:
            methods.append(WITNESS_COUPONS)
        else:
            methods.append(chosen)
            if not method_out_resolves_class(chosen, braze_class, thickness):
                findings.append(
                    "%s resolves %.4g mm through %.4g mm of wall, which is "
                    "coarser than the %.4g mm void %s still accepts"
                    % (
                        chosen,
                        resolvable_void_mm(chosen, thickness),
                        thickness,
                        accepted_void_mm(braze_class, thickness),
                        braze_class,
                    )
                )

    if hermetic:
        methods.append(LEAK_TEST)

    sample = ndt_sample_size(lot_size, braze_class)
    return {
        "geometry": geometry,
        "access": access,
        "thickness_mm": thickness,
        "braze_class": braze_class,
        "methods": methods,
        "volumetric_method": chosen,
        "coverage_required": coverage_required,
        "sample_size": sample,
        "lot_size": lot_size,
        "full_coverage": sample == lot_size,
        "resolvable_void_mm": (
            resolvable_void_mm(chosen, thickness) if chosen else None
        ),
        "accepted_void_mm": accepted_void_mm(braze_class, thickness),
        "findings": findings,
    }
