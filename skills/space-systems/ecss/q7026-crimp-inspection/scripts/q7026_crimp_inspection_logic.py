#!/usr/bin/env python3
"""Dimensional and visual acceptance of a finished crimp.

Anchor: ECSS-Q-ST-70-26 Quality clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A finished crimp cannot be adjusted, so inspection is not a chance to
improve it: it decides whether the joint stays in the harness. Six
characteristics are read, and each of them can also be unreadable,
which is a third outcome and not a pass:

crimp height   the compression measurement, two-sided. Under the band
               the barrel cut the strands; over it the barrel never
               closed.
crimp width    the same closure seen across the die. A height inside
               the band with a width outside it means the barrel rolled
               in the nest rather than closing.
flash          material extruded at the die parting line. Excess flash
               is metal that left the joint and a sharp edge inside the
               assembly.
bell mouth     the flare at the barrel mouth that stops the strands
               turning on a sheared edge. Absent it is a finding; too
               long and the barrel is short of grip.
visibility     the strands have to be countable where the design lets
               them be seen, at the conductor end or at the inspection
               window.
grip           the insulation grip has to close on insulation, so the
               bending load stays off the strands.

Dispositions rank accept < review < reject. Review is what an
unmeasured characteristic earns: an unknown reading is not a passing
one, and a crimp carrying one is not accepted until it is read.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INSPECTION_ACCEPT = "accept"
INSPECTION_REVIEW = "review"
INSPECTION_REJECT = "reject"

_RANK = {
    INSPECTION_ACCEPT: 0,
    INSPECTION_REVIEW: 1,
    INSPECTION_REJECT: 2,
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
    worst = INSPECTION_ACCEPT
    for disposition in dispositions:
        if _RANK[disposition] > _RANK[worst]:
            worst = disposition
    return worst


def _band(name, entry, low_key, high_key):
    low = _require_positive("%s %s" % (name, low_key), entry.get(low_key))
    high = _require_positive("%s %s" % (name, high_key), entry.get(high_key))
    if high < low:
        raise ValueError(
            "%s band %s..%s is inverted: %g below %g"
            % (name, low_key, high_key, high, low)
        )
    return low, high


def validate_limits_table(table):
    """Normalise the per-contact acceptance limits and refuse an unusable set."""
    if not isinstance(table, dict) or not table:
        raise ValueError("limits table must be a non-empty mapping")
    normalised = {}
    for part, entry in table.items():
        if not isinstance(part, str) or not part.strip():
            raise ValueError("contact key must be a non-empty string, got %r" % (part,))
        if not isinstance(entry, dict):
            raise ValueError("contact %s entry must be a mapping" % part)
        h_low, h_high = _band("contact %s height" % part, entry, "height_min_mm", "height_max_mm")
        w_low, w_high = _band("contact %s width" % part, entry, "width_min_mm", "width_max_mm")
        flash = _require_non_negative(
            "contact %s max_flash_mm" % part, entry.get("max_flash_mm")
        )
        bell_required = _require_flag(
            "contact %s bell_mouth_required" % part,
            entry.get("bell_mouth_required", True),
        )
        b_low, b_high = _band(
            "contact %s bell mouth" % part, entry, "bell_mouth_min_mm", "bell_mouth_max_mm"
        )
        strands = _require_count(
            "contact %s strand_count" % part, entry.get("strand_count")
        )
        if strands <= 0:
            raise ValueError("contact %s strand_count must be positive" % part)
        normalised[part] = {
            "contact": part,
            "height_min_mm": h_low,
            "height_max_mm": h_high,
            "width_min_mm": w_low,
            "width_max_mm": w_high,
            "max_flash_mm": flash,
            "bell_mouth_required": bell_required,
            "bell_mouth_min_mm": b_low,
            "bell_mouth_max_mm": b_high,
            "strand_count": strands,
        }
    return normalised


def _looks_normalised(table):
    return (
        isinstance(table, dict)
        and bool(table)
        and all(
            isinstance(entry, dict) and "height_min_mm" in entry and "contact" in entry
            for entry in table.values()
        )
    )


def lookup_limits(table, part):
    """Return the acceptance limits for one contact; nothing is interpolated."""
    normalised = table if _looks_normalised(table) else validate_limits_table(table)
    if part not in normalised:
        raise ValueError(
            "contact %r is not tabulated (have %s); acceptance limits are not "
            "derived from a neighbouring part"
            % (part, ", ".join(sorted(normalised)))
        )
    return normalised[part]


def _grade_two_sided(label, value, low, high, unmeasured_text, low_text, high_text):
    if value is None:
        return {
            "value_mm": None,
            "band_min_mm": low,
            "band_max_mm": high,
            "measured": False,
            "read": False,
            "below_minimum": None,
            "above_maximum": None,
            "disposition": INSPECTION_REVIEW,
            "findings": [unmeasured_text],
        }
    measured = _require_positive(label, value)
    below = not _at_least(measured, low)
    above = not _at_most(measured, high)
    findings = []
    if below:
        findings.append(low_text % (measured, low))
    if above:
        findings.append(high_text % (measured, high))
    span = high - low
    return {
        "value_mm": measured,
        "band_min_mm": low,
        "band_max_mm": high,
        "measured": True,
        "read": True,
        "below_minimum": below,
        "above_maximum": above,
        "band_position": (measured - low) / span if span > 0.0 else 0.0,
        "disposition": INSPECTION_REJECT if (below or above) else INSPECTION_ACCEPT,
        "findings": findings,
    }


def evaluate_crimp_height(height_mm, entry):
    """Grade the crimp height against its two-sided band, or report it unread."""
    return _grade_two_sided(
        "height_mm",
        height_mm,
        entry["height_min_mm"],
        entry["height_max_mm"],
        "crimp height was not measured; an unread compression is not a passing one",
        "crimp height %.3f mm is below the %.3f mm floor; the barrel was driven "
        "into the strands",
        "crimp height %.3f mm is above the %.3f mm ceiling; the barrel never "
        "closed on the bundle",
    )


def evaluate_crimp_width(width_mm, entry):
    """Grade the crimp width across the die, or report it unread."""
    return _grade_two_sided(
        "width_mm",
        width_mm,
        entry["width_min_mm"],
        entry["width_max_mm"],
        "crimp width was not measured; height alone cannot show a barrel that "
        "rolled in the nest",
        "crimp width %.3f mm is below the %.3f mm floor; the barrel was squeezed "
        "narrow rather than closed",
        "crimp width %.3f mm is above the %.3f mm ceiling; the barrel spread "
        "under the die instead of compressing",
    )


def evaluate_flash(flash_mm, entry):
    """Grade the material extruded at the die parting line."""
    if flash_mm is None:
        return {
            "flash_mm": None,
            "limit_mm": entry["max_flash_mm"],
            "measured": False,
            "read": False,
            "disposition": INSPECTION_REVIEW,
            "findings": [
                "die flash was not measured; extruded material is both lost "
                "section and a sharp edge, so it is not assumed absent"
            ],
        }
    flash = _require_non_negative("flash_mm", flash_mm)
    limit = entry["max_flash_mm"]
    within = _at_most(flash, limit)
    findings = []
    if not within:
        findings.append(
            "die flash %.3f mm exceeds the %.3f mm limit; that is material driven "
            "out of the joint and left as an edge" % (flash, limit)
        )
    return {
        "flash_mm": flash,
        "limit_mm": limit,
        "measured": True,
        "read": True,
        "disposition": INSPECTION_ACCEPT if within else INSPECTION_REJECT,
        "findings": findings,
    }


def evaluate_bell_mouth(entry, present=None, length_mm=None):
    """Grade the flare at the barrel mouth, where the contact calls for one."""
    if not entry["bell_mouth_required"]:
        return {
            "required": False,
            "read": True,
            "present": present,
            "length_mm": length_mm,
            "disposition": INSPECTION_ACCEPT,
            "findings": [
                "this contact carries no bell mouth requirement, so the mouth is "
                "not graded against a length band"
            ],
        }
    if present is None:
        return {
            "required": True,
            "read": False,
            "present": None,
            "length_mm": None,
            "disposition": INSPECTION_REVIEW,
            "findings": [
                "the bell mouth was not read; it carries the strain relief that "
                "no dimension shows"
            ],
        }
    present = _require_flag("present", present)
    if not present:
        return {
            "required": True,
            "read": True,
            "present": False,
            "length_mm": None,
            "disposition": INSPECTION_REJECT,
            "findings": [
                "no bell mouth is formed, so the strands turn on a sheared barrel "
                "edge under vibration"
            ],
        }
    if length_mm is None:
        return {
            "required": True,
            "read": False,
            "present": True,
            "length_mm": None,
            "disposition": INSPECTION_REVIEW,
            "findings": [
                "a bell mouth is present but its length was not measured against "
                "the band"
            ],
        }
    length = _require_non_negative("length_mm", length_mm)
    low = entry["bell_mouth_min_mm"]
    high = entry["bell_mouth_max_mm"]
    short = not _at_least(length, low)
    long_ = not _at_most(length, high)
    findings = []
    if short:
        findings.append(
            "bell mouth %.3f mm is below the %.3f mm minimum; the flare is too "
            "small to keep the strands off the edge" % (length, low)
        )
    if long_:
        findings.append(
            "bell mouth %.3f mm is above the %.3f mm maximum; the flare has eaten "
            "into the gripped length of the barrel" % (length, high)
        )
    return {
        "required": True,
        "read": True,
        "present": True,
        "length_mm": length,
        "band_min_mm": low,
        "band_max_mm": high,
        "disposition": INSPECTION_REJECT if (short or long_) else INSPECTION_ACCEPT,
        "findings": findings,
    }


def evaluate_strand_visibility(entry, strands_visible=None, window_present=True):
    """Count the strands that can be seen where the design lets them be seen."""
    window_present = _require_flag("window_present", window_present)
    expected = entry["strand_count"]
    if strands_visible is None:
        return {
            "expected": expected,
            "visible": None,
            "read": False,
            "window_present": window_present,
            "disposition": INSPECTION_REVIEW,
            "findings": [
                "strand visibility was not read; the strands that never reached "
                "the barrel cannot be inferred from the outside of it"
            ],
        }
    visible = _require_count("strands_visible", strands_visible)
    if visible > expected:
        raise ValueError(
            "%d strands were counted where the contact carries %d"
            % (visible, expected)
        )
    findings = []
    if visible == expected:
        disposition = INSPECTION_ACCEPT
    elif window_present:
        disposition = INSPECTION_REJECT
        findings.append(
            "%d of %d strands are visible; the missing strands are conductor the "
            "joint never received" % (visible, expected)
        )
    else:
        disposition = INSPECTION_REVIEW
        findings.append(
            "%d of %d strands are visible on a contact with no inspection window, "
            "so the shortfall cannot be resolved from the outside"
            % (visible, expected)
        )
    return {
        "expected": expected,
        "visible": visible,
        "read": True,
        "missing": expected - visible,
        "visible_fraction": visible / expected,
        "window_present": window_present,
        "disposition": disposition,
        "findings": findings,
    }


def evaluate_insulation_grip(closed_on_insulation=None):
    """Check that the insulation grip closed on the jacket, not on conductor."""
    if closed_on_insulation is None:
        return {
            "closed_on_insulation": None,
            "read": False,
            "disposition": INSPECTION_REVIEW,
            "findings": [
                "the insulation grip was not read; it carries the bending load "
                "that no crimp dimension sees"
            ],
        }
    closed = _require_flag("closed_on_insulation", closed_on_insulation)
    findings = []
    if not closed:
        findings.append(
            "the insulation grip did not close on the jacket, so flexing loads "
            "the strands at the barrel edge"
        )
    return {
        "closed_on_insulation": closed,
        "read": True,
        "disposition": INSPECTION_ACCEPT if closed else INSPECTION_REJECT,
        "findings": findings,
    }


_CHECK_ORDER = (
    "crimp_height",
    "crimp_width",
    "flash",
    "bell_mouth",
    "strand_visibility",
    "insulation_grip",
)


def inspect_crimp(case, table):
    """Full acceptance disposition for one finished crimp."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    entry = lookup_limits(table, case.get("contact"))
    parts = {
        "crimp_height": evaluate_crimp_height(case.get("height_mm"), entry),
        "crimp_width": evaluate_crimp_width(case.get("width_mm"), entry),
        "flash": evaluate_flash(case.get("flash_mm"), entry),
        "bell_mouth": evaluate_bell_mouth(
            entry,
            present=case.get("bell_mouth_present"),
            length_mm=case.get("bell_mouth_mm"),
        ),
        "strand_visibility": evaluate_strand_visibility(
            entry,
            strands_visible=case.get("strands_visible"),
            window_present=case.get("window_present", True),
        ),
        "insulation_grip": evaluate_insulation_grip(
            case.get("insulation_grip_closed")
        ),
    }
    disposition = _worst(part["disposition"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _RANK[part["disposition"]] == _RANK[disposition]
        and disposition != INSPECTION_ACCEPT
    )
    unread = sorted(
        name for name, part in parts.items() if not part["read"]
    )
    findings = []
    for name in _CHECK_ORDER:
        findings.extend("%s: %s" % (name, text) for text in parts[name]["findings"])
    result = {
        "identifier": case.get("identifier", "unidentified"),
        "contact": entry["contact"],
        "disposition": disposition,
        "driving_checks": driving,
        "unread_characteristics": unread,
        "findings": findings,
    }
    result.update(parts)
    return result


def summarize_inspection(lot):
    """Roll an inspected population up, keeping the unread ones visible."""
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    table = validate_limits_table(lot.get("limits_table"))
    cases = lot.get("crimps")
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("lot must carry a non-empty crimps sequence")
    declared = _require_count(
        "declared_crimp_count", lot.get("declared_crimp_count", len(cases))
    )
    if declared < len(cases):
        raise ValueError(
            "%d crimps were inspected against a declared population of %d"
            % (len(cases), declared)
        )
    results = [inspect_crimp(case, table) for case in cases]
    counts = {INSPECTION_ACCEPT: 0, INSPECTION_REVIEW: 0, INSPECTION_REJECT: 0}
    for result in results:
        counts[result["disposition"]] += 1
    uninspected = declared - len(results)
    return {
        "declared_crimp_count": declared,
        "inspected_crimp_count": len(results),
        "uninspected_crimp_count": uninspected,
        "record_complete": uninspected == 0,
        "accepted": counts[INSPECTION_ACCEPT],
        "review": counts[INSPECTION_REVIEW],
        "rejected": counts[INSPECTION_REJECT],
        "worst_disposition": _worst(r["disposition"] for r in results),
        "with_unread_characteristics": [
            r["identifier"] for r in results if r["unread_characteristics"]
        ],
        "not_accepted": [
            r["identifier"] for r in results if r["disposition"] != INSPECTION_ACCEPT
        ],
        "crimps": results,
    }
