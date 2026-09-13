#!/usr/bin/env python3
"""Visual inspection of solar-array bus bars for defects that are not tolerated.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.11. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause names a short list of bus bar conditions that carry no
allowance at all -- solder that has bridged between conductors, and an
opening that has been filled in -- and sits them next to the ordinary
graded defects. The screen therefore has two halves that must not be
confused with each other:

    not tolerated   presence alone decides. There is no size below
                    which a bridge or a crack is acceptable, because
                    the failure it produces is electrical continuity
                    where the design needs isolation, or loss of the
                    conductor path itself.
    graded          splash, voids, a thin fillet and contamination are
                    measured, scaled by where they sit on the bar, and
                    dispositioned accept, rework or reject.

Defect kinds
    solder-bridging             solder spans the gap between conductors
    blocked-opening             a designed opening filled or obstructed
    solder-splash               loose solder deposited off the joint
    solder-void                 gas pocket inside the bond footprint
    bus-bar-crack               a fracture through the bar cross section
    lifted-bus-bar-segment      a run no longer bonded to the substrate
    insufficient-solder-fillet  fillet short of the wetted length needed
    surface-contamination       flux residue, adhesive or particulate

Zones
    conductor-run        the bar between terminations
    termination-pad      where the bar meets a string or a connector
    opening-margin       the land around a designed opening
    mounting-interface   where the bar is fastened or bonded down

Dispositions are accept, rework and reject. The limits below are a
declared project criteria set, not a physical constant; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BUS_BAR_DEFECT_KINDS = (
    "solder-bridging",
    "blocked-opening",
    "solder-splash",
    "solder-void",
    "bus-bar-crack",
    "lifted-bus-bar-segment",
    "insufficient-solder-fillet",
    "surface-contamination",
)

NOT_TOLERATED_KINDS = (
    "solder-bridging",
    "bus-bar-crack",
    "lifted-bus-bar-segment",
)

BUS_BAR_ZONES = (
    "conductor-run",
    "termination-pad",
    "opening-margin",
    "mounting-interface",
)

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REWORK, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

DEFAULT_BUS_BAR_CRITERIA = {
    "accept_area_mm2": {
        "solder-splash": 0.5,
        "solder-void": 1.0,
        "insufficient-solder-fillet": 0.0,
        "surface-contamination": 2.0,
    },
    "rework_area_mm2": {
        "solder-splash": 6.0,
        "solder-void": 4.0,
        "insufficient-solder-fillet": 8.0,
        "surface-contamination": 40.0,
    },
    "zone_severity_factor": {
        "conductor-run": 1.0,
        "termination-pad": 0.5,
        "opening-margin": 0.5,
        "mounting-interface": 1.0,
    },
    # Electrical isolation between adjacent conductors.
    "min_isolation_gap_mm": 0.40,
    # How much of a designed opening has to stay clear.
    "accept_clear_opening_fraction": 0.98,
    "rework_clear_opening_fraction": 0.40,
}

_GRADED_KINDS = (
    "solder-splash",
    "solder-void",
    "insufficient-solder-fillet",
    "surface-contamination",
)

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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A limit is a product of a criteria value and a zone factor, so a
    measurement sitting exactly on the limit can evaluate a few units in
    the last place above it. The limit is never raised; only the
    comparison tolerates the representation error.
    """
    return value <= limit or _close(value, limit)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_bus_bar_criteria(criteria):
    """Check a criteria set covers every graded kind and every zone."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    table_specs = (
        ("accept_area_mm2", _GRADED_KINDS),
        ("rework_area_mm2", _GRADED_KINDS),
        ("zone_severity_factor", BUS_BAR_ZONES),
    )
    for key, keys_needed in table_specs:
        table = criteria.get(key)
        if not isinstance(table, dict):
            raise ValueError("criteria %s must be a mapping" % key)
        missing = set(keys_needed) - set(table)
        if missing:
            raise ValueError(
                "criteria %s is missing entries: %s"
                % (key, ", ".join(sorted(missing)))
            )
        for entry in keys_needed:
            _require_non_negative("criteria %s[%s]" % (key, entry), table[entry])
    for kind in _GRADED_KINDS:
        if criteria["rework_area_mm2"][kind] < criteria["accept_area_mm2"][kind]:
            raise ValueError(
                "criteria rework_area_mm2[%s] is below the accept limit" % kind
            )
    for zone in BUS_BAR_ZONES:
        _require_positive(
            "criteria zone_severity_factor[%s]" % zone,
            criteria["zone_severity_factor"][zone],
        )
    _require_positive("min_isolation_gap_mm", criteria.get("min_isolation_gap_mm"))
    accept_clear = _require_positive(
        "accept_clear_opening_fraction",
        criteria.get("accept_clear_opening_fraction"),
    )
    rework_clear = _require_positive(
        "rework_clear_opening_fraction",
        criteria.get("rework_clear_opening_fraction"),
    )
    if accept_clear > 1.0 and not _close(accept_clear, 1.0):
        raise ValueError(
            "criteria accept_clear_opening_fraction cannot exceed one, got %r"
            % (accept_clear,)
        )
    if rework_clear > accept_clear and not _close(rework_clear, accept_clear):
        raise ValueError(
            "criteria rework_clear_opening_fraction is above the accept fraction"
        )
    return criteria


def zone_severity_factor(zone, criteria=DEFAULT_BUS_BAR_CRITERIA):
    """Factor the zone applies to every graded limit; below one is stricter."""
    _require_choice("zone", zone, BUS_BAR_ZONES)
    return float(criteria["zone_severity_factor"][zone])


def residual_conductor_gap_mm(designed_gap_mm, solder_spread_mm):
    """Gap left between adjacent conductors after the solder has spread.

    The spread is the total encroachment from both conductors, so the
    residual gap is the designed spacing less that spread. A residual of
    zero or less means the two conductors are joined.
    """
    designed = _require_positive("designed_gap_mm", designed_gap_mm)
    spread = _require_non_negative("solder_spread_mm", solder_spread_mm)
    return designed - spread


def is_bridged(designed_gap_mm, solder_spread_mm):
    """True when the solder spread has closed the gap between conductors."""
    gap = residual_conductor_gap_mm(designed_gap_mm, solder_spread_mm)
    return gap < 0.0 or _close(gap, 0.0)


def clear_opening_fraction(nominal_area_mm2, obstructed_area_mm2):
    """Fraction of a designed opening that is still clear."""
    nominal = _require_positive("nominal_opening_area_mm2", nominal_area_mm2)
    obstructed = _require_non_negative(
        "obstructed_area_mm2", obstructed_area_mm2
    )
    if not _at_most(obstructed, nominal):
        raise ValueError(
            "obstructed area %.3f mm2 exceeds the opening area %.3f mm2; the "
            "measurement or the opening size is wrong" % (obstructed, nominal)
        )
    if obstructed > nominal:
        obstructed = nominal
    return (nominal - obstructed) / nominal


def assess_bus_bar_defect(defect, criteria=DEFAULT_BUS_BAR_CRITERIA):
    """Disposition one bus bar indication against the criteria set."""
    validate_bus_bar_criteria(criteria)
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    kind = _require_choice("kind", defect.get("kind"), BUS_BAR_DEFECT_KINDS)
    zone = _require_choice("zone", defect.get("zone"), BUS_BAR_ZONES)
    factor = zone_severity_factor(zone, criteria)
    reasons = []
    tolerated = kind not in NOT_TOLERATED_KINDS
    measurements = {}

    if kind == "solder-bridging":
        designed = defect.get("designed_gap_mm")
        spread = defect.get("solder_spread_mm")
        if designed is None or spread is None:
            raise ValueError(
                "a solder-bridging indication needs designed_gap_mm and "
                "solder_spread_mm to show what the gap became"
            )
        gap = residual_conductor_gap_mm(designed, spread)
        measurements["residual_gap_mm"] = gap
        measurements["min_isolation_gap_mm"] = criteria["min_isolation_gap_mm"]
        if is_bridged(designed, spread):
            disposition = REJECT
            reasons.append(
                "solder has closed the %.3f mm design gap between adjacent "
                "conductors; a bridge carries no size allowance" % designed
            )
        elif not _at_least(gap, criteria["min_isolation_gap_mm"]):
            disposition = REWORK
            tolerated = True
            reasons.append(
                "residual gap %.3f mm is under the %.3f mm isolation minimum; "
                "the solder is encroaching but has not bridged"
                % (gap, criteria["min_isolation_gap_mm"])
            )
        else:
            disposition = ACCEPT
            tolerated = True

    elif kind == "blocked-opening":
        nominal = defect.get("nominal_opening_area_mm2")
        obstructed = defect.get("obstructed_area_mm2")
        if nominal is None or obstructed is None:
            raise ValueError(
                "a blocked-opening indication needs nominal_opening_area_mm2 "
                "and obstructed_area_mm2 to show how much stayed clear"
            )
        clear = clear_opening_fraction(nominal, obstructed)
        measurements["clear_opening_fraction"] = clear
        if _at_least(clear, criteria["accept_clear_opening_fraction"]):
            disposition = ACCEPT
        elif _at_least(clear, criteria["rework_clear_opening_fraction"]):
            disposition = REWORK
            reasons.append(
                "only %.3f of the opening is clear against the %.3f accept "
                "fraction; the obstruction can still be drawn back off the land"
                % (clear, criteria["accept_clear_opening_fraction"])
            )
        else:
            disposition = REJECT
            tolerated = False
            reasons.append(
                "the opening is %.3f clear, below the %.3f rework fraction; "
                "clearing that much solder would put more heat into the bar "
                "than the surrounding joints survive"
                % (clear, criteria["rework_clear_opening_fraction"])
            )

    elif kind in NOT_TOLERATED_KINDS:
        disposition = REJECT
        reasons.append(
            "%s is on the not-tolerated list; presence alone decides and no "
            "measurement can bring it back" % kind
        )

    else:
        area = _require_non_negative("area_mm2", defect.get("area_mm2"))
        accept_area = criteria["accept_area_mm2"][kind] * factor
        rework_area = criteria["rework_area_mm2"][kind] * factor
        measurements["area_mm2"] = area
        measurements["accept_area_mm2"] = accept_area
        measurements["rework_area_mm2"] = rework_area
        if _at_most(area, accept_area):
            disposition = ACCEPT
        elif _at_most(area, rework_area):
            disposition = REWORK
            reasons.append(
                "area %.3f mm2 exceeds the %.3f mm2 accept limit for %s in the "
                "%s zone" % (area, accept_area, kind, zone)
            )
        else:
            disposition = REJECT
            reasons.append(
                "area %.3f mm2 exceeds the %.3f mm2 rework limit for %s in the "
                "%s zone" % (area, rework_area, kind, zone)
            )

    return {
        "id": defect.get("id"),
        "kind": kind,
        "zone": zone,
        "tolerated": tolerated,
        "disposition": disposition,
        "measurements": measurements,
        "reasons": reasons,
    }


def group_defects_by_kind(defects):
    """Group indications by kind and count the not-tolerated ones."""
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list, got %r" % (defects,))
    counts = dict((kind, 0) for kind in BUS_BAR_DEFECT_KINDS)
    for defect in defects:
        if not isinstance(defect, dict):
            raise ValueError("each defect must be a mapping, got %r" % (defect,))
        kind = _require_choice("kind", defect.get("kind"), BUS_BAR_DEFECT_KINDS)
        counts[kind] += 1
    not_tolerated = sum(counts[kind] for kind in NOT_TOLERATED_KINDS)
    return {"counts": counts, "not_tolerated_count": not_tolerated}


def inspect_bus_bar(bus_bar, criteria=DEFAULT_BUS_BAR_CRITERIA):
    """Full clause 5.5.3.2.11 bus bar screen with a bar-level verdict."""
    validate_bus_bar_criteria(criteria)
    if not isinstance(bus_bar, dict):
        raise ValueError("bus_bar must be a mapping, got %r" % (bus_bar,))
    bar_id = bus_bar.get("bus_bar_id")
    if not isinstance(bar_id, str) or not bar_id.strip():
        raise ValueError("bus_bar needs a non-empty bus_bar_id for traceability")
    defects = bus_bar.get("defects")
    if not isinstance(defects, (list, tuple)):
        raise ValueError("bus_bar defects must be a list, got %r" % (defects,))

    seen = set()
    assessed = []
    for defect in defects:
        result = assess_bus_bar_defect(defect, criteria)
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate defect id %r on bus bar %s; traceability to the "
                    "rework record would be lost" % (marker, bar_id)
                )
            seen.add(marker)
        assessed.append(result)

    grouping = group_defects_by_kind(list(defects))
    calls = [result["disposition"] for result in assessed]
    verdict = _worst(calls) if calls else ACCEPT
    findings = []
    if not assessed:
        findings.append(
            "no indications recorded; the bus bar is examined and clean, and "
            "the record still stands as the inspection evidence"
        )
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))
    blocking = [
        result["id"] for result in assessed if not result["tolerated"]
    ]
    if blocking:
        findings.append(
            "not-tolerated conditions on %s; the bar cannot be dispositioned "
            "by size" % ", ".join(str(marker) for marker in blocking)
        )
    return {
        "bus_bar_id": bar_id,
        "verdict": verdict,
        "defects": assessed,
        "reject_count": calls.count(REJECT),
        "rework_count": calls.count(REWORK),
        "accept_count": calls.count(ACCEPT),
        "not_tolerated_ids": blocking,
        "kind_counts": grouping["counts"],
        "reinspection_required": verdict == REWORK,
        "findings": findings,
    }
