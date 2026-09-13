#!/usr/bin/env python3
"""Post-cycling substrate structural-integrity inspection of a coupon.

Anchor: ECSS-E-ST-20-08C Rev.2 clause 5.5.3.10.1. The procedure below is
a paraphrase into implementable steps; no standard text is reproduced.

Once a coupon has finished its thermal cycling, the substrate underneath
the cells has to be looked at as a structure rather than as a surface.
Cycling works on it through the mismatch between a thin facesheet, an
adhesive layer and a honeycomb core that all move by different amounts,
and the damage it leaves is mostly subsurface: a bondline that has let
go, a core cell that has crushed, a dielectric that has delaminated
under an otherwise perfect facesheet.

Three things decide whether the resulting record is worth anything:

    sequence    the survey belongs after the cycling is credited and
                after the coupon has come back to ambient and settled.
                Inspected hot, a disbond can still be held closed; left
                too long, the record no longer describes the coupon as
                it came out of the chamber
    coverage    each zone of the substrate has its own failure mode and
                its own set of methods that can actually see it. A
                bondline surveyed by eye is an unsurveyed bondline, and
                the zones that hide their damage need more than one
                method before they count as covered
    capture     an indication is only usable downstream when its kind,
                zone, method and size are all recorded, and when the
                method that found it could resolve a feature that small

This step deliberately stops short of accept or reject. The thresholds
that decide that are not in the standard, they are in the assembly
control drawing, and they are applied in the pass/fail criteria step
that follows. What this step owes is a complete, sequenced, method-valid
set of indications for that decision to run on.

The zones, admissible methods and detection thresholds below are a
declared project policy, not a physical constant.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SUBSTRATE_ZONES = (
    "front-facesheet",
    "rear-facesheet",
    "honeycomb-core",
    "facesheet-core-bondline",
    "edge-closeout",
    "insert-region",
)

INSPECTION_METHODS = (
    "visual",
    "tap-test",
    "ultrasonic",
    "thermographic",
    "dimensional",
)

INDICATION_KINDS = (
    "facesheet-crack",
    "facesheet-core-disbond",
    "core-crush",
    "edge-closeout-separation",
    "insert-pullout",
    "dielectric-delamination",
)

DEFAULT_INSPECTION_POLICY = {
    "required_zones": SUBSTRATE_ZONES,
    # Methods that can actually see each zone's failure modes.
    "admissible_methods": {
        "front-facesheet": ("visual", "dimensional", "thermographic"),
        "rear-facesheet": ("visual", "dimensional", "thermographic"),
        "honeycomb-core": ("ultrasonic", "thermographic"),
        "facesheet-core-bondline": ("tap-test", "ultrasonic", "thermographic"),
        "edge-closeout": ("visual", "tap-test", "dimensional"),
        "insert-region": ("tap-test", "ultrasonic", "dimensional"),
    },
    # Zones that hide their damage need corroboration before they count.
    "minimum_methods_per_zone": {
        "front-facesheet": 1,
        "rear-facesheet": 1,
        "honeycomb-core": 1,
        "facesheet-core-bondline": 2,
        "edge-closeout": 1,
        "insert-region": 2,
    },
    "method_detection_threshold_mm": {
        "visual": 0.5,
        "tap-test": 6.0,
        "ultrasonic": 2.0,
        "thermographic": 3.0,
        "dimensional": 0.2,
    },
    "minimum_stabilisation_h": 2.0,
    "maximum_delay_h": 72.0,
}

INSPECTION_COMPLETE = "substrate-inspection-complete"
INSPECTION_INCOMPLETE = "substrate-inspection-incomplete"
INSPECTION_INVALID = "substrate-inspection-invalid"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_int(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
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


def validate_inspection_policy(policy):
    """Check the zone, method and timing policy is complete and sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    required = policy.get("required_zones")
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("policy required_zones must be a non-empty sequence")
    for zone in required:
        _require_choice("required_zones entry", zone, SUBSTRATE_ZONES)
    admissible = policy.get("admissible_methods")
    minimums = policy.get("minimum_methods_per_zone")
    if not isinstance(admissible, dict) or not isinstance(minimums, dict):
        raise ValueError(
            "policy admissible_methods and minimum_methods_per_zone must be mappings"
        )
    for zone in required:
        if zone not in admissible:
            raise ValueError("policy admissible_methods is missing zone %r" % (zone,))
        methods = admissible[zone]
        if not isinstance(methods, (list, tuple)) or not methods:
            raise ValueError(
                "policy admissible_methods[%s] must be a non-empty sequence" % (zone,)
            )
        for method in methods:
            _require_choice("admissible_methods[%s] entry" % zone, method, INSPECTION_METHODS)
        floor = _require_int(
            "minimum_methods_per_zone[%s]" % zone, minimums.get(zone), minimum=1
        )
        if floor > len(methods):
            raise ValueError(
                "zone %s demands %d methods but only %d are admissible for it"
                % (zone, floor, len(methods))
            )
    thresholds = policy.get("method_detection_threshold_mm")
    if not isinstance(thresholds, dict):
        raise ValueError("policy method_detection_threshold_mm must be a mapping")
    for method in INSPECTION_METHODS:
        _require_positive("method_detection_threshold_mm[%s]" % method, thresholds.get(method))
    stabilisation = _require_positive(
        "minimum_stabilisation_h", policy.get("minimum_stabilisation_h")
    )
    delay = _require_positive("maximum_delay_h", policy.get("maximum_delay_h"))
    if not delay > stabilisation:
        raise ValueError(
            "maximum_delay_h %g must be above minimum_stabilisation_h %g"
            % (delay, stabilisation)
        )
    return policy


def check_readiness(coupon_state, policy=DEFAULT_INSPECTION_POLICY):
    """Decide whether the coupon may be surveyed at all, and when."""
    validate_inspection_policy(policy)
    if not isinstance(coupon_state, dict):
        raise ValueError("coupon_state must be a mapping, got %r" % (coupon_state,))
    coupon_id = _require_text("coupon_id", coupon_state.get("coupon_id"))
    required = _require_int(
        "required_cycles", coupon_state.get("required_cycles"), minimum=1
    )
    credited = _require_int(
        "credited_cycles", coupon_state.get("credited_cycles"), minimum=0
    )
    elapsed = _require_non_negative(
        "hours_since_cycling_end", coupon_state.get("hours_since_cycling_end")
    )
    if credited < required:
        raise ValueError(
            "coupon %s has %d of %d credited cycles; the integrity survey follows "
            "the cycling, it does not run alongside it" % (coupon_id, credited, required)
        )
    findings = []
    ready = True
    if not _at_least(elapsed, float(policy["minimum_stabilisation_h"])):
        ready = False
        findings.append(
            "coupon %s surveyed %g h after cycling ended, inside the %g h "
            "stabilisation period; a bondline can still be held closed"
            % (coupon_id, elapsed, policy["minimum_stabilisation_h"])
        )
    if not _at_most(elapsed, float(policy["maximum_delay_h"])):
        findings.append(
            "coupon %s surveyed %g h after cycling ended, past the %g h window; "
            "the record no longer describes the coupon as it left the chamber"
            % (coupon_id, elapsed, policy["maximum_delay_h"])
        )
    return {
        "coupon_id": coupon_id,
        "hours_since_cycling_end": elapsed,
        "ready": ready,
        "findings": findings,
    }


def zone_coverage(applied, policy=DEFAULT_INSPECTION_POLICY):
    """Which substrate zones were surveyed by a method that can see them."""
    validate_inspection_policy(policy)
    if not isinstance(applied, dict):
        raise ValueError("applied must be a mapping of zone to methods")
    required = tuple(policy["required_zones"])
    for zone in applied:
        _require_choice("applied zone", zone, SUBSTRATE_ZONES)
    covered = []
    under_covered = []
    uncovered = []
    inadmissible = []
    for zone in required:
        methods = applied.get(zone, ())
        if not isinstance(methods, (list, tuple)):
            raise ValueError("applied[%s] must be a sequence of methods" % (zone,))
        seen = []
        for method in methods:
            _require_choice("applied[%s] method" % zone, method, INSPECTION_METHODS)
            if method in seen:
                raise ValueError(
                    "method %r is listed twice for zone %s" % (method, zone)
                )
            seen.append(method)
        allowed = tuple(policy["admissible_methods"][zone])
        good = [method for method in seen if method in allowed]
        for method in seen:
            if method not in allowed:
                inadmissible.append(
                    {
                        "zone": zone,
                        "method": method,
                        "reason": "method cannot resolve this zone's failure modes",
                    }
                )
        floor = int(policy["minimum_methods_per_zone"][zone])
        if not good:
            uncovered.append(zone)
        elif len(good) < floor:
            under_covered.append(
                {"zone": zone, "applied": len(good), "required": floor}
            )
        else:
            covered.append(zone)
    return {
        "required_zones": list(required),
        "covered_zones": covered,
        "under_covered_zones": under_covered,
        "uncovered_zones": uncovered,
        "inadmissible_applications": inadmissible,
        "coverage_fraction": len(covered) / float(len(required)),
    }


def normalise_indication(indication, policy=DEFAULT_INSPECTION_POLICY):
    """Validate one recorded indication and mark whether it is confirmed."""
    validate_inspection_policy(policy)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    indication_id = _require_text("indication_id", indication.get("indication_id"))
    kind = _require_choice("kind", indication.get("kind"), INDICATION_KINDS)
    zone = _require_choice("zone", indication.get("zone"), SUBSTRATE_ZONES)
    method = _require_choice("method", indication.get("method"), INSPECTION_METHODS)
    size = _require_positive("size_mm", indication.get("size_mm"))
    threshold = float(policy["method_detection_threshold_mm"][method])
    if not _at_least(size, threshold):
        raise ValueError(
            "indication %s is reported at %g mm by %s, below that method's %g mm "
            "detection threshold; the method cannot resolve a feature that small"
            % (indication_id, size, method, threshold)
        )
    area = indication.get("area_mm2")
    if area is not None:
        area = _require_non_negative("area_mm2", area)
    confirmed = method in tuple(policy["admissible_methods"][zone])
    return {
        "indication_id": indication_id,
        "kind": kind,
        "zone": zone,
        "method": method,
        "size_mm": size,
        "area_mm2": area,
        "confirmed": confirmed,
    }


def summarise_indications(indications, policy=DEFAULT_INSPECTION_POLICY):
    """Group the survey's indications by zone and kind for the next step."""
    if not isinstance(indications, (list, tuple)):
        raise ValueError("indications must be a list of indication records")
    normalised = []
    seen = set()
    by_zone = {}
    by_kind = {}
    total_area = 0.0
    largest = 0.0
    unconfirmed = []
    for entry in indications:
        record = normalise_indication(entry, policy)
        if record["indication_id"] in seen:
            raise ValueError(
                "indication_id %r appears twice in the survey"
                % (record["indication_id"],)
            )
        seen.add(record["indication_id"])
        normalised.append(record)
        by_zone[record["zone"]] = by_zone.get(record["zone"], 0) + 1
        by_kind[record["kind"]] = by_kind.get(record["kind"], 0) + 1
        if record["area_mm2"] is not None:
            total_area += record["area_mm2"]
        if record["size_mm"] > largest:
            largest = record["size_mm"]
        if not record["confirmed"]:
            unconfirmed.append(record["indication_id"])
    return {
        "indications": normalised,
        "count": len(normalised),
        "by_zone": by_zone,
        "by_kind": by_kind,
        "largest_size_mm": largest,
        "total_area_mm2": total_area,
        "unconfirmed": unconfirmed,
    }


def run_substrate_integrity_inspection(case, policy=DEFAULT_INSPECTION_POLICY):
    """Full clause 5.5.3.10.1 survey with a completeness verdict."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_inspection_policy(policy)
    readiness = check_readiness(case.get("coupon_state"), policy)
    coverage = zone_coverage(case.get("applied_methods", {}), policy)
    summary = summarise_indications(case.get("indications", ()), policy)
    findings = list(readiness["findings"])
    if coverage["uncovered_zones"]:
        findings.append(
            "zones surveyed by no admissible method: %s"
            % ", ".join(coverage["uncovered_zones"])
        )
    for entry in coverage["under_covered_zones"]:
        findings.append(
            "zone %s carries %d admissible method of the %d it owes"
            % (entry["zone"], entry["applied"], entry["required"])
        )
    for entry in coverage["inadmissible_applications"]:
        findings.append(
            "method %s applied to zone %s cannot resolve that zone's failure modes"
            % (entry["method"], entry["zone"])
        )
    if summary["unconfirmed"]:
        findings.append(
            "indications found by a method the zone does not admit, re-survey "
            "before disposition: %s" % ", ".join(summary["unconfirmed"])
        )
    if not readiness["ready"]:
        verdict = INSPECTION_INVALID
    elif (
        coverage["uncovered_zones"]
        or coverage["under_covered_zones"]
        or summary["unconfirmed"]
    ):
        verdict = INSPECTION_INCOMPLETE
    else:
        verdict = INSPECTION_COMPLETE
    if verdict == INSPECTION_COMPLETE and summary["count"] == 0:
        findings.append(
            "survey complete with no indications recorded; the coverage is what "
            "makes that a result rather than an absence of looking"
        )
    return {
        "coupon_id": readiness["coupon_id"],
        "verdict": verdict,
        "ready": readiness["ready"],
        "coverage": coverage,
        "summary": summary,
        "findings": findings,
        # The accept/reject thresholds live in the assembly control drawing
        # and are applied by the pass/fail criteria step, not here.
        "disposition_deferred": True,
    }
