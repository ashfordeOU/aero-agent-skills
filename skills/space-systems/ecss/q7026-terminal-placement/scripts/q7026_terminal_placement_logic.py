#!/usr/bin/env python3
"""Terminal and contact placement on a prepared conductor, before crimping.

Anchor: ECSS-Q-ST-70-26 Preparation clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Placement is the last moment at which anything can be changed for free.
Once the die closes, every one of these is a cut-and-remake. Six things
decide whether the contact is where it has to be:

insulation gap   the distance between the insulation edge and the mouth
                 of the conductor barrel. Too small and insulation goes
                 under the conductor grip; too large and bare conductor
                 sits between the two grips with nothing supporting it.
bottoming        the conductor has to reach the back of the barrel bore.
                 A conductor short of it is crimped over a part-length
                 of strands whatever the height gauge later reads.
window fill      the inspection window exists so the conductor end can
                 be seen. A part-filled window is the only warning that
                 the bundle did not go all the way in.
stray strands    strands outside the barrel are conductor removed from
                 the joint and loose metal inside the assembly.
entrapment       insulation caught under the conductor grip prevents the
                 cold weld over the area it covers.
seating          the contact has to sit square in the die nest. An
                 off-axis contact is crimped off-axis.

Dispositions rank accept < reposition < reject. Reposition is available
while the wire end itself is sound; a wire end that cannot reach the
back of the barrel has to go back to preparation.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PLACEMENT_ACCEPT = "accept"
PLACEMENT_REPOSITION = "reposition"
PLACEMENT_REJECT = "reject"

_RANK = {
    PLACEMENT_ACCEPT: 0,
    PLACEMENT_REPOSITION: 1,
    PLACEMENT_REJECT: 2,
}

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
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_number(name, value)
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must sit between 0 and 1, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (name, value))
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


def _worst(dispositions):
    worst = PLACEMENT_ACCEPT
    for disposition in dispositions:
        if _RANK[disposition] > _RANK[worst]:
            worst = disposition
    return worst


def validate_contact_table(table):
    """Normalise the per-contact placement table and refuse an unusable one.

    A contact type is the unit here, not the wire alone: the barrel bore,
    the window and the gap band belong to the contact, and the strand
    count and stray allowance to the wire it accepts.
    """
    if not isinstance(table, dict) or not table:
        raise ValueError("contact table must be a non-empty mapping")
    normalised = {}
    for part, entry in table.items():
        if not isinstance(part, str) or not part.strip():
            raise ValueError("contact key must be a non-empty string, got %r" % (part,))
        if not isinstance(entry, dict):
            raise ValueError("contact %s entry must be a mapping" % part)
        gap_min = _require_non_negative(
            "contact %s gap_min_mm" % part, entry.get("gap_min_mm")
        )
        gap_max = _require_positive(
            "contact %s gap_max_mm" % part, entry.get("gap_max_mm")
        )
        if gap_max < gap_min:
            raise ValueError(
                "contact %s gap band is inverted: max %g below min %g"
                % (part, gap_max, gap_min)
            )
        depth = _require_positive(
            "contact %s barrel_depth_mm" % part, entry.get("barrel_depth_mm")
        )
        seat_tol = _require_non_negative(
            "contact %s bottoming_tolerance_mm" % part,
            entry.get("bottoming_tolerance_mm", 0.0),
        )
        if seat_tol >= depth:
            raise ValueError(
                "contact %s bottoming tolerance %g reaches the %g mm bore depth, "
                "so nothing could ever be short of the back" % (part, seat_tol, depth)
            )
        window_min = _require_fraction(
            "contact %s window_fill_min" % part, entry.get("window_fill_min", 1.0)
        )
        strands = _require_count(
            "contact %s strand_count" % part, entry.get("strand_count")
        )
        if strands <= 0:
            raise ValueError("contact %s strand_count must be positive" % part)
        stray = _require_count(
            "contact %s max_stray_strands" % part, entry.get("max_stray_strands", 0)
        )
        if stray >= strands:
            raise ValueError(
                "contact %s allows %d stray strands of %d; an allowance that "
                "reaches the strand count is not an allowance"
                % (part, stray, strands)
            )
        seat_angle = _require_non_negative(
            "contact %s max_seating_error_deg" % part,
            entry.get("max_seating_error_deg", 0.0),
        )
        normalised[part] = {
            "contact": part,
            "gap_min_mm": gap_min,
            "gap_max_mm": gap_max,
            "barrel_depth_mm": depth,
            "bottoming_tolerance_mm": seat_tol,
            "window_fill_min": window_min,
            "strand_count": strands,
            "max_stray_strands": stray,
            "max_seating_error_deg": seat_angle,
        }
    return normalised


def _looks_normalised(table):
    return (
        isinstance(table, dict)
        and bool(table)
        and all(
            isinstance(entry, dict) and "barrel_depth_mm" in entry and "contact" in entry
            for entry in table.values()
        )
    )


def lookup_contact(table, part):
    """Return the entry for one contact part; nothing is interpolated."""
    normalised = table if _looks_normalised(table) else validate_contact_table(table)
    if part not in normalised:
        raise ValueError(
            "contact %r is not tabulated (have %s); a placement band is not "
            "derived from a neighbouring part number"
            % (part, ", ".join(sorted(normalised)))
        )
    return normalised[part]


def evaluate_insulation_gap(gap_mm, entry):
    """Grade the insulation-to-barrel gap against the band for the contact."""
    gap = _require_non_negative("gap_mm", gap_mm)
    low = entry["gap_min_mm"]
    high = entry["gap_max_mm"]
    tight = not _at_least(gap, low)
    wide = not _at_most(gap, high)
    findings = []
    if tight:
        findings.append(
            "insulation gap %.2f mm is below the %.2f mm minimum; insulation will "
            "be driven under the conductor grip" % (gap, low)
        )
    if wide:
        findings.append(
            "insulation gap %.2f mm is above the %.2f mm maximum; bare conductor "
            "is left unsupported between the grips" % (gap, high)
        )
    span = high - low
    return {
        "gap_mm": gap,
        "band_min_mm": low,
        "band_max_mm": high,
        "below_minimum": tight,
        "above_maximum": wide,
        "band_position": (gap - low) / span if span > 0.0 else 0.0,
        "disposition": PLACEMENT_REPOSITION if (tight or wide) else PLACEMENT_ACCEPT,
        "findings": findings,
    }


def evaluate_bottoming(insertion_depth_mm, exposed_length_mm, entry):
    """Decide whether the conductor reached the back of the barrel bore.

    A conductor that is short of the back because it was pushed in short
    can be pushed further. A conductor whose exposed length is shorter
    than the bore can never reach it, so that end goes back to
    preparation rather than being nudged.
    """
    depth = _require_non_negative("insertion_depth_mm", insertion_depth_mm)
    exposed = _require_non_negative("exposed_length_mm", exposed_length_mm)
    bore = entry["barrel_depth_mm"]
    required = bore - entry["bottoming_tolerance_mm"]
    if depth > exposed and not math.isclose(
        depth, exposed, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        raise ValueError(
            "insertion depth %g mm exceeds the %g mm of conductor that was "
            "exposed; the record is inconsistent" % (depth, exposed)
        )
    bottomed = _at_least(depth, required)
    findings = []
    if bottomed:
        disposition = PLACEMENT_ACCEPT
    elif _at_least(exposed, required):
        disposition = PLACEMENT_REPOSITION
        findings.append(
            "conductor reached %.2f mm of the %.2f mm it has to, and enough "
            "conductor is exposed to push it home" % (depth, required)
        )
    else:
        disposition = PLACEMENT_REJECT
        findings.append(
            "only %.2f mm of conductor is exposed against the %.2f mm bore, so "
            "this end cannot bottom and goes back to preparation"
            % (exposed, required)
        )
    return {
        "insertion_depth_mm": depth,
        "required_depth_mm": required,
        "barrel_depth_mm": bore,
        "bottomed": bottomed,
        "shortfall_mm": max(0.0, required - depth),
        "disposition": disposition,
        "findings": findings,
    }


def evaluate_window_fill(fill_fraction, entry, window_present=True):
    """Grade how much of the inspection window the conductor fills."""
    window_present = _require_flag("window_present", window_present)
    findings = []
    if not window_present:
        return {
            "window_present": False,
            "fill_fraction": None,
            "required_fill": entry["window_fill_min"],
            "disposition": PLACEMENT_ACCEPT,
            "findings": [
                "contact has no inspection window; bottoming rests on the "
                "insertion measurement alone"
            ],
        }
    fill = _require_fraction("fill_fraction", fill_fraction)
    required = entry["window_fill_min"]
    filled = _at_least(fill, required)
    if not filled:
        findings.append(
            "inspection window is %.0f%% filled against the %.0f%% required; the "
            "bundle did not reach the window" % (fill * 100.0, required * 100.0)
        )
    return {
        "window_present": True,
        "fill_fraction": fill,
        "required_fill": required,
        "disposition": PLACEMENT_ACCEPT if filled else PLACEMENT_REPOSITION,
        "findings": findings,
    }


def evaluate_stray_strands(strands_in_barrel, strands_outside, entry):
    """Count the strands that missed the barrel against the allowance."""
    inside = _require_count("strands_in_barrel", strands_in_barrel)
    outside = _require_count("strands_outside", strands_outside)
    expected = entry["strand_count"]
    if inside + outside != expected:
        raise ValueError(
            "%d strands in the barrel plus %d outside it do not account for the "
            "%d the contact expects" % (inside, outside, expected)
        )
    allowance = entry["max_stray_strands"]
    findings = []
    if outside > allowance:
        disposition = PLACEMENT_REJECT
        findings.append(
            "%d strands sit outside the barrel against an allowance of %d; that "
            "is lost conductor and loose metal in the assembly"
            % (outside, allowance)
        )
    elif outside > 0:
        disposition = PLACEMENT_REPOSITION
        findings.append(
            "%d strand(s) outside the barrel, within the allowance of %d, but the "
            "bundle should be re-laid before the die closes" % (outside, allowance)
        )
    else:
        disposition = PLACEMENT_ACCEPT
    return {
        "strands_in_barrel": inside,
        "strands_outside": outside,
        "allowance": allowance,
        "captured_fraction": inside / expected,
        "disposition": disposition,
        "findings": findings,
    }


def evaluate_entrapment(insulation_under_conductor_grip=False, conductor_under_insulation_grip=True):
    """Check that insulation and conductor are each under their own grip."""
    trapped = _require_flag(
        "insulation_under_conductor_grip", insulation_under_conductor_grip
    )
    supported = _require_flag(
        "conductor_under_insulation_grip", conductor_under_insulation_grip
    )
    findings = []
    dispositions = [PLACEMENT_ACCEPT]
    if trapped:
        dispositions.append(PLACEMENT_REPOSITION)
        findings.append(
            "insulation is caught under the conductor grip and will block the "
            "cold weld over the area it covers"
        )
    if not supported:
        dispositions.append(PLACEMENT_REPOSITION)
        findings.append(
            "the insulation grip closes on bare conductor, so the strain relief "
            "loads the strands instead of the jacket"
        )
    return {
        "insulation_under_conductor_grip": trapped,
        "conductor_under_insulation_grip": supported,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def evaluate_seating(seating_error_deg, entry, seated_in_nest=True):
    """Grade how square the contact sits in the die nest."""
    seated = _require_flag("seated_in_nest", seated_in_nest)
    error = _require_non_negative("seating_error_deg", seating_error_deg)
    limit = entry["max_seating_error_deg"]
    findings = []
    dispositions = [PLACEMENT_ACCEPT]
    if not seated:
        dispositions.append(PLACEMENT_REPOSITION)
        findings.append(
            "contact is not seated against the nest locator, so the crimp lands "
            "at an unknown position along the barrel"
        )
    square = _at_most(error, limit)
    if not square:
        dispositions.append(PLACEMENT_REPOSITION)
        findings.append(
            "contact sits %.2f deg off axis against a %.2f deg limit; an off-axis "
            "contact is crimped off-axis" % (error, limit)
        )
    return {
        "seated_in_nest": seated,
        "seating_error_deg": error,
        "limit_deg": limit,
        "square": square,
        "disposition": _worst(dispositions),
        "findings": findings,
    }


def assess_placement(case, table):
    """Full placement disposition for one contact on one prepared wire."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    normalised = table if _looks_normalised(table) else validate_contact_table(table)
    entry = lookup_contact(normalised, case.get("contact"))
    gap = evaluate_insulation_gap(case.get("gap_mm"), entry)
    bottoming = evaluate_bottoming(
        case.get("insertion_depth_mm"), case.get("exposed_length_mm"), entry
    )
    window = evaluate_window_fill(
        case.get("window_fill"), entry, window_present=case.get("window_present", True)
    )
    strays = evaluate_stray_strands(
        case.get("strands_in_barrel"), case.get("strands_outside", 0), entry
    )
    entrapment = evaluate_entrapment(
        insulation_under_conductor_grip=case.get(
            "insulation_under_conductor_grip", False
        ),
        conductor_under_insulation_grip=case.get(
            "conductor_under_insulation_grip", True
        ),
    )
    seating = evaluate_seating(
        case.get("seating_error_deg", 0.0),
        entry,
        seated_in_nest=case.get("seated_in_nest", True),
    )
    parts = {
        "insulation_gap": gap,
        "bottoming": bottoming,
        "window_fill": window,
        "stray_strands": strays,
        "entrapment": entrapment,
        "seating": seating,
    }
    disposition = _worst(part["disposition"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _RANK[part["disposition"]] == _RANK[disposition]
        and disposition != PLACEMENT_ACCEPT
    )
    order = (
        "insulation_gap",
        "bottoming",
        "window_fill",
        "stray_strands",
        "entrapment",
        "seating",
    )
    findings = []
    for name in order:
        findings.extend("%s: %s" % (name, text) for text in parts[name]["findings"])
    return {
        "identifier": case.get("identifier", "unidentified"),
        "contact": entry["contact"],
        "disposition": disposition,
        "driving_checks": driving,
        "insulation_gap": gap,
        "bottoming": bottoming,
        "window_fill": window,
        "stray_strands": strays,
        "entrapment": entrapment,
        "seating": seating,
        "findings": findings,
    }


def assess_placement_batch(batch):
    """Roll a batch of placements up before any die is closed."""
    if not isinstance(batch, dict):
        raise ValueError("batch must be a mapping, got %r" % (batch,))
    table = validate_contact_table(batch.get("contact_table"))
    cases = batch.get("placements")
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("batch must carry a non-empty placements sequence")
    declared = _require_count(
        "declared_placement_count", batch.get("declared_placement_count", len(cases))
    )
    if declared < len(cases):
        raise ValueError(
            "%d placements were recorded against a declared population of %d"
            % (len(cases), declared)
        )
    results = [assess_placement(case, table) for case in cases]
    counts = {
        PLACEMENT_ACCEPT: 0,
        PLACEMENT_REPOSITION: 0,
        PLACEMENT_REJECT: 0,
    }
    for result in results:
        counts[result["disposition"]] += 1
    unrecorded = declared - len(results)
    return {
        "declared_placement_count": declared,
        "recorded_placement_count": len(results),
        "unrecorded_placement_count": unrecorded,
        "record_complete": unrecorded == 0,
        "accepted": counts[PLACEMENT_ACCEPT],
        "reposition": counts[PLACEMENT_REPOSITION],
        "rejected": counts[PLACEMENT_REJECT],
        "worst_disposition": _worst(r["disposition"] for r in results),
        "ready_to_crimp": counts[PLACEMENT_REPOSITION] == 0
        and counts[PLACEMENT_REJECT] == 0
        and unrecorded == 0,
        "not_accepted": [
            r["identifier"] for r in results if r["disposition"] != PLACEMENT_ACCEPT
        ],
        "placements": results,
    }
