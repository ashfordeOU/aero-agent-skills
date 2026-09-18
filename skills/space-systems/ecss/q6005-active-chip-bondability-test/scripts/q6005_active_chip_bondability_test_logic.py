#!/usr/bin/env python3
"""Active-chip bondability logic (ECSS-Q-ST-60-05 clause 8.3.2).

Deterministic, offline, stdlib-only helpers that grade the wire-attachment
evidence a die lot owes before its parts are released into assembly:

- interpolate the minimum individual pull force a wire diameter earns from
  the strength schedule,
- hold each recorded reading against that floor at the exact boundary,
- hold the lot mean against its own higher floor,
- disposition every recorded separation mode, so a separation at the pad
  interface fails the lot whatever force it took,
- confirm the tested bond count meets the sampling floor.

Anchor: ECSS-Q-ST-60-05 clause 8.3.2 (paraphrased procedure only).
"""

import math

# Minimum individual pull force (grams-force) earned by a bond wire of a
# given nominal diameter (micrometres). Between two anchors the floor is
# linearly interpolated; outside the tabulated span there is no schedule
# entry and the reading cannot be graded.
PULL_STRENGTH_SCHEDULE = (
    (18.0, 2.0),
    (25.0, 3.0),
    (33.0, 4.5),
    (50.0, 8.0),
)

# The lot mean carries a margin over the individual floor: a lot whose mean
# sits on the individual floor has half its population below it.
MEAN_MARGIN_FACTOR = 1.25

# Fewest bonds that can carry a bondability statement for a die lot.
MIN_BONDS_TESTED = 10

# Separation inside the wire itself: the attachment outlived the wire, so
# the reading grades the bond strength.
STRUCTURAL_MODES = frozenset(
    {"wire-break", "heel-break", "neck-break", "midspan-break"}
)

# Separation at or under the pad: the attachment or the die metallization
# gave way. The force reached is irrelevant, the interface is unsound.
INTERFACE_MODES = frozenset(
    {"bond-lift", "pad-lift", "cratering", "metallization-peel"}
)

# Pull forces and interpolated floors are floats; a reading that sits
# exactly on its floor can evaluate a few ULPs low. The tolerance absorbs
# that representation error only - the schedule floor is never relaxed.
REL_TOL = 1e-9
ABS_TOL = 1e-12


def _at_least(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _as_float(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    return number


def minimum_pull_force_gf(wire_diameter_um):
    """Minimum individual pull force a wire of this diameter must reach.

    Exact at a tabulated anchor, linearly interpolated between two anchors.
    Raises ValueError outside the tabulated span - an untabulated diameter
    has no floor to grade against and must not silently borrow one.
    """
    diameter = _as_float(wire_diameter_um, "wire_diameter_um")
    if diameter <= 0.0:
        raise ValueError("wire_diameter_um must be > 0, got %r" % (wire_diameter_um,))
    low = PULL_STRENGTH_SCHEDULE[0][0]
    high = PULL_STRENGTH_SCHEDULE[-1][0]
    if diameter < low or diameter > high:
        raise ValueError(
            "wire diameter %.4f um is outside the schedule span %.4f-%.4f um"
            % (diameter, low, high)
        )
    for anchor_diameter, anchor_force in PULL_STRENGTH_SCHEDULE:
        if diameter == anchor_diameter:
            return anchor_force
    for index in range(len(PULL_STRENGTH_SCHEDULE) - 1):
        d0, f0 = PULL_STRENGTH_SCHEDULE[index]
        d1, f1 = PULL_STRENGTH_SCHEDULE[index + 1]
        if d0 < diameter < d1:
            fraction = (diameter - d0) / (d1 - d0)
            return f0 + fraction * (f1 - f0)
    raise ValueError("no schedule segment covers %.4f um" % (diameter,))


def categorize_failure_mode(mode):
    """Group a recorded separation mode as structural or interface.

    Raises ValueError on an unrecorded or unrecognised mode - a reading
    with no separation mode cannot be dispositioned at all.
    """
    if not isinstance(mode, str) or not mode.strip():
        raise ValueError("failure_mode must be a non-empty string, got %r" % (mode,))
    key = mode.strip().lower()
    if key in STRUCTURAL_MODES:
        return "structural"
    if key in INTERFACE_MODES:
        return "interface"
    raise ValueError("unrecognised separation mode %r" % (mode,))


def validate_bond_test(record):
    """Normalize one wire-pull record.

    record keys: pad_id, wire_diameter_um, pull_force_gf, failure_mode.
    Raises ValueError on any malformed field.
    """
    if not isinstance(record, dict):
        raise ValueError("bond-pull record must be a mapping, got %r" % (record,))
    pad_id = record.get("pad_id")
    if not isinstance(pad_id, str) or not pad_id.strip():
        raise ValueError("pad_id must be a non-empty string, got %r" % (pad_id,))
    diameter = _as_float(record.get("wire_diameter_um"), "wire_diameter_um")
    force = _as_float(record.get("pull_force_gf"), "pull_force_gf")
    if force < 0.0:
        raise ValueError("pull_force_gf must be >= 0, got %r" % (force,))
    group = categorize_failure_mode(record.get("failure_mode"))
    return {
        "pad_id": pad_id.strip(),
        "wire_diameter_um": diameter,
        "pull_force_gf": force,
        "failure_mode": record.get("failure_mode").strip().lower(),
        "mode_group": group,
    }


def normalize_bond_tests(records):
    """Validate a whole pull-test set, rejecting a duplicate pad record."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("bond-pull record set must be a non-empty list")
    normalized = []
    seen = set()
    for record in records:
        item = validate_bond_test(record)
        if item["pad_id"] in seen:
            raise ValueError("duplicate bond-pull record for pad %r" % (item["pad_id"],))
        seen.add(item["pad_id"])
        normalized.append(item)
    return normalized


def evaluate_bond_test(record):
    """Grade one normalized pull record against its own schedule floor."""
    required = minimum_pull_force_gf(record["wire_diameter_um"])
    force = record["pull_force_gf"]
    force_ok = _at_least(force, required)
    interface_failure = record["mode_group"] == "interface"
    reasons = []
    if not force_ok:
        reasons.append(
            "pull force %.4f gf short of the %.4f gf floor by %.4f gf"
            % (force, required, required - force)
        )
    if interface_failure:
        reasons.append(
            "separation at the pad interface (%s) regardless of the %.4f gf reached"
            % (record["failure_mode"], force)
        )
    return {
        "pad_id": record["pad_id"],
        "required_gf": required,
        "pull_force_gf": force,
        "margin_gf": force - required,
        "force_ok": force_ok,
        "mode_group": record["mode_group"],
        "conforming": force_ok and not interface_failure,
        "reasons": reasons,
    }


def sample_mean(values):
    """Arithmetic mean of a non-empty sequence of readings."""
    numbers = [_as_float(v, "reading") for v in values]
    if not numbers:
        raise ValueError("mean of an empty reading set is undefined")
    return math.fsum(numbers) / len(numbers)


def sample_standard_deviation(values):
    """Sample standard deviation (n-1) of a reading set of at least two."""
    numbers = [_as_float(v, "reading") for v in values]
    if len(numbers) < 2:
        raise ValueError("sample standard deviation needs at least two readings")
    mean = math.fsum(numbers) / len(numbers)
    variance = math.fsum((n - mean) * (n - mean) for n in numbers) / (len(numbers) - 1)
    return math.sqrt(variance)


def required_mean_pull_force_gf(evaluations):
    """Mean floor for the lot: the worst individual floor plus its margin."""
    if not evaluations:
        raise ValueError("mean floor is undefined for an empty evaluation set")
    return max(e["required_gf"] for e in evaluations) * MEAN_MARGIN_FACTOR


def assess_bondability(records, minimum_bonds=MIN_BONDS_TESTED):
    """Grade a whole clause 8.3.2 bondability demonstration for a die lot.

    Returns a report dict with per-pad evaluations, the lot statistics and
    the findings. bondable is True only when findings is empty.
    """
    floor_count = minimum_bonds
    if isinstance(floor_count, bool) or not isinstance(floor_count, int):
        raise ValueError("minimum_bonds must be an integer, got %r" % (minimum_bonds,))
    if floor_count < 1:
        raise ValueError("minimum_bonds must be >= 1, got %r" % (minimum_bonds,))
    normalized = normalize_bond_tests(records)
    evaluations = [evaluate_bond_test(item) for item in normalized]
    evaluations.sort(key=lambda e: e["pad_id"])
    forces = [e["pull_force_gf"] for e in evaluations]
    mean = sample_mean(forces)
    deviation = sample_standard_deviation(forces) if len(forces) > 1 else None
    required_mean = required_mean_pull_force_gf(evaluations)
    mean_ok = _at_least(mean, required_mean)
    findings = []
    if len(evaluations) < floor_count:
        findings.append(
            "only %d bonds tested, the sampling floor is %d"
            % (len(evaluations), floor_count)
        )
    for evaluation in evaluations:
        if not evaluation["conforming"]:
            findings.append(
                "pad %s not conforming: %s"
                % (evaluation["pad_id"], "; ".join(evaluation["reasons"]))
            )
    if not mean_ok:
        findings.append(
            "lot mean %.4f gf short of the %.4f gf mean floor by %.4f gf"
            % (mean, required_mean, required_mean - mean)
        )
    return {
        "bonds_tested": len(evaluations),
        "minimum_bonds": floor_count,
        "evaluations": evaluations,
        "mean_pull_force_gf": mean,
        "standard_deviation_gf": deviation,
        "required_mean_gf": required_mean,
        "mean_ok": mean_ok,
        "interface_failures": sorted(
            e["pad_id"] for e in evaluations if e["mode_group"] == "interface"
        ),
        "findings": findings,
        "bondable": not findings,
    }


def format_bondability_report(report):
    """Render a bondability assessment as deterministic plain-text lines."""
    deviation = report["standard_deviation_gf"]
    lines = [
        "active-chip bondability: %s"
        % ("BONDABLE" if report["bondable"] else "NOT BONDABLE"),
        "bonds=%d mean=%.3f gf sd=%s required-mean=%.3f gf"
        % (
            report["bonds_tested"],
            report["mean_pull_force_gf"],
            "n/a" if deviation is None else "%.3f gf" % deviation,
            report["required_mean_gf"],
        ),
    ]
    for item in report["evaluations"]:
        lines.append(
            "  %s force=%.3f gf floor=%.3f gf mode=%s conforming=%s"
            % (
                item["pad_id"],
                item["pull_force_gf"],
                item["required_gf"],
                item["mode_group"],
                "yes" if item["conforming"] else "no",
            )
        )
    for finding in report["findings"]:
        lines.append("  FINDING: %s" % finding)
    return "\n".join(lines)
