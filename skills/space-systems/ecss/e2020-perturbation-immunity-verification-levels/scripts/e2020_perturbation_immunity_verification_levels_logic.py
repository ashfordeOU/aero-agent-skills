#!/usr/bin/env python3
"""Splitting power-bus perturbation immunity checks across verification levels.

Anchor: ECSS-E-ST-20-20C clause 5.2.16.2.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protection device has to stay immune to the perturbations that live on
the power bus it sits on. Showing that is not one campaign but two, and
the clause is about deciding which requirement is discharged where:

    unit level        the device alone on a bench, driven by a
                      laboratory source through a laboratory harness
    spacecraft level  the device in its flight position, fed by the real
                      bus through the real harness, with every other
                      user of that bus connected and running

The split is not a preference. Some perturbations only exist once the
flight harness inductance, the real source impedance of the bus and the
switching of the other users are all present at once; a bench cannot
manufacture them, so those requirements belong at spacecraft level
whatever the schedule says. Everything else belongs at the earliest
level that is representative, because a spacecraft-level slot arrives
late, is shared with the whole programme and cannot be repeated.

Two failure shapes are worth separating:

    1. A requirement no level can reproduce. Its amplitude or its upper
       frequency is beyond both the bench and the spacecraft-level
       facility, so it is not allocated at all and saying so is the
       point of running this.
    2. A slice of the specified frequency band that no allocated
       requirement covers. Each requirement carries its own band; the
       union of the allocated bands is what has actually been verified,
       and the difference against the specified band is a gap nobody
       planned to close.

The bench and facility capabilities, the advisory ceiling on how many
items may land at spacecraft level and the unit-level share floor are a
declared project policy, not physical constants; a project substitutes
its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIREMENT_FIELDS = (
    "id",
    "perturbation",
    "amplitude",
    "frequency_low_hz",
    "frequency_high_hz",
    "needs_flight_harness",
    "needs_bus_source_impedance",
    "needs_cross_user_coupling",
)

FLAG_FIELDS = (
    "needs_flight_harness",
    "needs_bus_source_impedance",
    "needs_cross_user_coupling",
)

LEVEL_UNIT = "unit-level-test"
LEVEL_SPACECRAFT = "spacecraft-level-test"
LEVEL_NONE = "no-adequate-level"

VERDICT_COMPLETE = "immunity-allocation-complete"
VERDICT_INCOMPLETE = "immunity-allocation-incomplete"

REASON_HARNESS = "flight-harness-not-representable-on-the-bench"
REASON_SOURCE_Z = "bus-source-impedance-not-representable-on-the-bench"
REASON_COUPLING = "cross-user-coupling-not-representable-on-the-bench"
REASON_AMPLITUDE = "amplitude-beyond-unit-bench-capability"
REASON_FREQUENCY = "frequency-beyond-unit-bench-capability"

FINDING_NO_LEVEL = "no-level-can-reproduce-the-perturbation"
FINDING_BAND_GAP = "specified-band-slice-not-verified"

ADVISORY_SPACECRAFT_LOAD = "spacecraft-level-count-above-advisory-ceiling"
ADVISORY_UNIT_SHARE = "unit-level-share-below-advisory-floor"

DEFAULT_ALLOCATION_POLICY = {
    "unit_bench_amplitude_limit": 8.0,
    "unit_bench_frequency_high_hz": 5.0e6,
    "facility_amplitude_limit": 40.0,
    "facility_frequency_high_hz": 1.0e8,
    "spacecraft_level_advisory_ceiling": 4,
    "unit_level_share_floor": 0.5,
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


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A bench capability and a stimulus amplitude are usually carried in
    different units and scaled on the way in, so a case meant to sit
    exactly on the capability can land a few units in the last place
    above it. The capability is never widened; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _same(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def validate_allocation_policy(policy):
    """Check the bench, facility and advisory figures are usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    bench_amp = _require_positive(
        "unit_bench_amplitude_limit", policy.get("unit_bench_amplitude_limit")
    )
    bench_f = _require_positive(
        "unit_bench_frequency_high_hz", policy.get("unit_bench_frequency_high_hz")
    )
    fac_amp = _require_positive(
        "facility_amplitude_limit", policy.get("facility_amplitude_limit")
    )
    fac_f = _require_positive(
        "facility_frequency_high_hz", policy.get("facility_frequency_high_hz")
    )
    if fac_amp < bench_amp:
        raise ValueError(
            "facility_amplitude_limit %g is below the bench limit %g; a level "
            "that reproduces less than the bench is not a fallback"
            % (fac_amp, bench_amp)
        )
    if fac_f < bench_f:
        raise ValueError(
            "facility_frequency_high_hz %g is below the bench ceiling %g; a "
            "level that reproduces less than the bench is not a fallback"
            % (fac_f, bench_f)
        )
    ceiling = policy.get("spacecraft_level_advisory_ceiling")
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling < 0:
        raise ValueError(
            "spacecraft_level_advisory_ceiling must be a non-negative integer, "
            "got %r" % (ceiling,)
        )
    floor = policy.get("unit_level_share_floor")
    if not _is_finite_number(floor) or floor < 0.0 or floor > 1.0:
        raise ValueError(
            "unit_level_share_floor must sit between zero and one, got %r" % (floor,)
        )
    return policy


def validate_requirement(item):
    """Check one immunity requirement carries everything the split needs."""
    if not isinstance(item, dict):
        raise ValueError("requirement must be a mapping, got %r" % (item,))
    missing = [f for f in REQUIREMENT_FIELDS if f not in item]
    if missing:
        raise ValueError(
            "requirement is missing fields: %s" % ", ".join(sorted(missing))
        )
    ident = item["id"]
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("requirement id must be a non-empty string, got %r" % (ident,))
    perturbation = item["perturbation"]
    if not isinstance(perturbation, str) or not perturbation.strip():
        raise ValueError(
            "requirement %s must name its perturbation, got %r" % (ident, perturbation)
        )
    low = _require_positive("frequency_low_hz", item["frequency_low_hz"])
    high = _require_positive("frequency_high_hz", item["frequency_high_hz"])
    if high < low:
        raise ValueError(
            "requirement %s has an inverted frequency band (%g Hz .. %g Hz)"
            % (ident, low, high)
        )
    row = {
        "id": ident,
        "perturbation": perturbation,
        "amplitude": _require_positive("amplitude", item["amplitude"]),
        "frequency_low_hz": low,
        "frequency_high_hz": high,
    }
    for flag in FLAG_FIELDS:
        row[flag] = _require_flag(flag, item[flag])
    return row


def validate_requirement_set(items):
    """Normalise a requirement list and refuse a repeated identifier."""
    if isinstance(items, dict) or not hasattr(items, "__iter__"):
        raise ValueError("requirement set must be a sequence of requirements")
    rows = [validate_requirement(i) for i in items]
    if not rows:
        raise ValueError("requirement set is empty; there is nothing to allocate")
    seen = set()
    for row in rows:
        if row["id"] in seen:
            raise ValueError("requirement set repeats the id %r" % (row["id"],))
        seen.add(row["id"])
    return tuple(rows)


def bench_representativeness_blockers(item, policy=DEFAULT_ALLOCATION_POLICY):
    """Every reason this requirement cannot be discharged on a bench."""
    validate_allocation_policy(policy)
    row = validate_requirement(item)
    reasons = []
    if row["needs_flight_harness"]:
        reasons.append(REASON_HARNESS)
    if row["needs_bus_source_impedance"]:
        reasons.append(REASON_SOURCE_Z)
    if row["needs_cross_user_coupling"]:
        reasons.append(REASON_COUPLING)
    if not _at_most(row["amplitude"], float(policy["unit_bench_amplitude_limit"])):
        reasons.append(REASON_AMPLITUDE)
    if not _at_most(
        row["frequency_high_hz"], float(policy["unit_bench_frequency_high_hz"])
    ):
        reasons.append(REASON_FREQUENCY)
    return tuple(reasons)


def facility_can_reproduce(item, policy=DEFAULT_ALLOCATION_POLICY):
    """Whether the spacecraft-level facility can raise this stimulus at all."""
    validate_allocation_policy(policy)
    row = validate_requirement(item)
    return _at_most(
        row["amplitude"], float(policy["facility_amplitude_limit"])
    ) and _at_most(
        row["frequency_high_hz"], float(policy["facility_frequency_high_hz"])
    )


def allocate_requirement(item, policy=DEFAULT_ALLOCATION_POLICY):
    """Place one requirement at the earliest level that is representative."""
    row = validate_requirement(item)
    blockers = bench_representativeness_blockers(row, policy)
    if not blockers:
        return {
            "id": row["id"],
            "perturbation": row["perturbation"],
            "level": LEVEL_UNIT,
            "reasons": (),
            "frequency_low_hz": row["frequency_low_hz"],
            "frequency_high_hz": row["frequency_high_hz"],
            "verified": True,
            "findings": [],
        }
    if facility_can_reproduce(row, policy):
        return {
            "id": row["id"],
            "perturbation": row["perturbation"],
            "level": LEVEL_SPACECRAFT,
            "reasons": blockers,
            "frequency_low_hz": row["frequency_low_hz"],
            "frequency_high_hz": row["frequency_high_hz"],
            "verified": True,
            "findings": [],
        }
    return {
        "id": row["id"],
        "perturbation": row["perturbation"],
        "level": LEVEL_NONE,
        "reasons": blockers,
        "frequency_low_hz": row["frequency_low_hz"],
        "frequency_high_hz": row["frequency_high_hz"],
        "verified": False,
        "findings": [
            "%s: %s at %.4g over %.4g Hz .. %.4g Hz is beyond the bench and "
            "beyond the spacecraft-level facility"
            % (
                FINDING_NO_LEVEL,
                row["id"],
                row["amplitude"],
                row["frequency_low_hz"],
                row["frequency_high_hz"],
            )
        ],
    }


def merge_frequency_intervals(intervals):
    """Union of frequency intervals, joined where they touch or overlap."""
    if isinstance(intervals, dict) or not hasattr(intervals, "__iter__"):
        raise ValueError("intervals must be a sequence of (low, high) pairs")
    pairs = []
    for interval in intervals:
        if isinstance(interval, (str, bytes)) or not hasattr(interval, "__iter__"):
            raise ValueError("interval must be a (low, high) pair, got %r" % (interval,))
        parts = list(interval)
        if len(parts) != 2:
            raise ValueError("interval must hold exactly two values, got %r" % (parts,))
        low = _require_positive("interval low", parts[0])
        high = _require_positive("interval high", parts[1])
        if high < low:
            raise ValueError("interval is inverted (%g .. %g)" % (low, high))
        pairs.append((low, high))
    if not pairs:
        return ()
    pairs.sort()
    merged = [pairs[0]]
    for low, high in pairs[1:]:
        last_low, last_high = merged[-1]
        if low <= last_high or _same(low, last_high):
            merged[-1] = (last_low, max(last_high, high))
        else:
            merged.append((low, high))
    return tuple(merged)


def uncovered_band_slices(intervals, band_low_hz, band_high_hz):
    """Slices of the specified band that no supplied interval reaches."""
    low = _require_positive("band_low_hz", band_low_hz)
    high = _require_positive("band_high_hz", band_high_hz)
    if high <= low or _same(low, high):
        raise ValueError(
            "specified band must ascend, got %g Hz .. %g Hz" % (low, high)
        )
    merged = merge_frequency_intervals(intervals)
    gaps = []
    cursor = low
    for start, stop in merged:
        if stop <= cursor or _same(stop, cursor):
            continue
        if start > cursor and not _same(start, cursor):
            gaps.append((cursor, min(start, high)))
        cursor = max(cursor, stop)
        if cursor >= high or _same(cursor, high):
            break
    if cursor < high and not _same(cursor, high):
        gaps.append((cursor, high))
    return tuple((a, b) for a, b in gaps if b > a and not _same(a, b))


def allocate_immunity_verification(
    items, band_low_hz, band_high_hz, policy=DEFAULT_ALLOCATION_POLICY
):
    """Full clause 5.2.16.2.1 split with a coverage verdict.

    Every requirement is placed at the earliest representative level, the
    bands actually verified are merged, and the difference against the
    specified band is reported as a gap rather than assumed closed.
    """
    validate_allocation_policy(policy)
    rows = validate_requirement_set(items)
    allocations = [allocate_requirement(r, policy) for r in rows]

    unit = [a for a in allocations if a["level"] == LEVEL_UNIT]
    spacecraft = [a for a in allocations if a["level"] == LEVEL_SPACECRAFT]
    unplaced = [a for a in allocations if a["level"] == LEVEL_NONE]

    covered = [
        (a["frequency_low_hz"], a["frequency_high_hz"])
        for a in allocations
        if a["verified"]
    ]
    gaps = uncovered_band_slices(covered, band_low_hz, band_high_hz)

    findings = []
    for a in unplaced:
        findings.extend(a["findings"])
    for start, stop in gaps:
        findings.append(
            "%s: %.6g Hz .. %.6g Hz is inside the specified band and no "
            "allocated requirement reaches it" % (FINDING_BAND_GAP, start, stop)
        )

    placed = len(unit) + len(spacecraft)
    unit_share = (len(unit) / placed) if placed else 0.0

    advisories = []
    if len(spacecraft) > int(policy["spacecraft_level_advisory_ceiling"]):
        advisories.append(
            "%s: %d requirements need the spacecraft-level slot against an "
            "advisory ceiling of %d"
            % (
                ADVISORY_SPACECRAFT_LOAD,
                len(spacecraft),
                int(policy["spacecraft_level_advisory_ceiling"]),
            )
        )
    if placed and unit_share < float(policy["unit_level_share_floor"]) and not _same(
        unit_share, float(policy["unit_level_share_floor"])
    ):
        advisories.append(
            "%s: unit-level share %.3f sits under the advisory floor %.3f"
            % (ADVISORY_UNIT_SHARE, unit_share, float(policy["unit_level_share_floor"]))
        )

    return {
        "verdict": VERDICT_COMPLETE if not findings else VERDICT_INCOMPLETE,
        "allocations": allocations,
        "unit_level": [a["id"] for a in unit],
        "spacecraft_level": [a["id"] for a in spacecraft],
        "unplaced": [a["id"] for a in unplaced],
        "unit_level_share": unit_share,
        "verified_intervals": merge_frequency_intervals(covered),
        "band_gaps": gaps,
        "findings": findings,
        "advisories": advisories,
    }
