#!/usr/bin/env python3
"""Visual and dimensional inspection of a procured threaded fastener.

Anchor: ECSS-Q-ST-70-46 inspection clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Two questions are answered for every fastener pulled from a lot.

Visually: a surface discontinuity is judged by where it sits, not only
by how deep it is. The thread root, the head-to-shank fillet and the
bearing surface are where the load line turns and the stress
concentrates, so nothing is allowed there at all. Elsewhere a seam, lap,
tool mark, pit or plating void is allowed to a depth taken as a fraction
of the basic thread height, which scales the allowance with the pitch
instead of fixing one number for every size. A crack or a forging fold
is rejectable wherever it is found, at any depth.

Dimensionally: every measured feature is judged against its own nominal
and its own signed tolerance band, and the margin to the nearer limit is
reported so a feature that is inside but walking towards a limit can be
seen before the next lot.

Depth and tolerance comparisons carry a small absolute slack so a value
sitting exactly on its own computed limit reads the same on every
platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparisons against a computed limit are slackened by this much so a
# value that lands exactly on the limit is accepted identically wherever
# the check runs.
_SLACK_MM = 1e-12

ZONE_THREAD_ROOT = "thread-root"
ZONE_THREAD_FLANK = "thread-flank"
ZONE_THREAD_CREST = "thread-crest"
ZONE_HEAD_TO_SHANK_FILLET = "head-to-shank-fillet"
ZONE_BEARING_SURFACE = "bearing-surface"
ZONE_SHANK = "shank"
ZONE_HEAD_TOP = "head-top"

ZONES = (
    ZONE_THREAD_ROOT,
    ZONE_THREAD_FLANK,
    ZONE_THREAD_CREST,
    ZONE_HEAD_TO_SHANK_FILLET,
    ZONE_BEARING_SURFACE,
    ZONE_SHANK,
    ZONE_HEAD_TOP,
)

# Where the load line turns and the stress concentrates. No discontinuity
# is allowed in these zones whatever its depth.
STRESS_CONCENTRATING_ZONES = (
    ZONE_THREAD_ROOT,
    ZONE_HEAD_TO_SHANK_FILLET,
    ZONE_BEARING_SURFACE,
)

DISCONTINUITIES = (
    "crack",
    "forging-fold",
    "seam",
    "lap",
    "burr",
    "tool-mark",
    "corrosion-pit",
    "plating-void",
)

# Rejectable wherever they are found, at any depth.
ALWAYS_REJECTABLE = ("crack", "forging-fold")

# Allowance outside the stress-concentrating zones, as a fraction of the
# basic thread height, so the allowance scales with the pitch.
_DEPTH_FRACTION = {
    "seam": 0.25,
    "lap": 0.25,
    "tool-mark": 0.125,
    "corrosion-pit": 0.125,
    "burr": 0.5,
    "plating-void": 0.5,
}

FEATURES = (
    "major-diameter",
    "pitch-diameter",
    "minor-diameter",
    "head-height",
    "head-diameter",
    "shank-diameter",
    "grip-length",
    "fillet-radius",
    "thread-runout-length",
)

VERDICT_ACCEPT = "accept"
VERDICT_REJECT = "reject"


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_number(name, value, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %s, got %s" % (name, minimum, value))
    return float(value)


def basic_thread_height(pitch_mm):
    """Height of the fundamental ISO metric triangle for this pitch."""
    pitch = _require_number("pitch_mm", pitch_mm, minimum=0.0)
    if pitch <= 0.0:
        raise ValueError("pitch_mm must be greater than zero, got %s" % pitch_mm)
    return pitch * math.sqrt(3.0) / 2.0


def allowable_discontinuity_depth(zone, discontinuity, pitch_mm):
    """Depth this discontinuity may reach in this zone, in millimetres.

    Zero means the discontinuity is not permitted there at all rather
    than that a zero-depth indication would be acceptable.
    """
    _require_choice("zone", zone, ZONES)
    _require_choice("discontinuity", discontinuity, DISCONTINUITIES)
    height = basic_thread_height(pitch_mm)
    if discontinuity in ALWAYS_REJECTABLE:
        return 0.0
    if zone in STRESS_CONCENTRATING_ZONES:
        return 0.0
    return _DEPTH_FRACTION[discontinuity] * height


def assess_discontinuity(zone, discontinuity, depth_mm, pitch_mm):
    """Accept or reject one recorded surface discontinuity."""
    depth = _require_number("depth_mm", depth_mm, minimum=0.0)
    allowed = allowable_discontinuity_depth(zone, discontinuity, pitch_mm)
    if discontinuity in ALWAYS_REJECTABLE:
        return {
            "zone": zone,
            "discontinuity": discontinuity,
            "depth_mm": depth,
            "allowed_depth_mm": 0.0,
            "verdict": VERDICT_REJECT,
            "reason": "%s is rejectable at any depth wherever it is found"
            % discontinuity,
        }
    if allowed <= 0.0:
        return {
            "zone": zone,
            "discontinuity": discontinuity,
            "depth_mm": depth,
            "allowed_depth_mm": 0.0,
            "verdict": VERDICT_REJECT,
            "reason": "no discontinuity is permitted in the %s, where the load "
            "line turns and the stress concentrates" % zone,
        }
    if depth > allowed + _SLACK_MM:
        return {
            "zone": zone,
            "discontinuity": discontinuity,
            "depth_mm": depth,
            "allowed_depth_mm": allowed,
            "verdict": VERDICT_REJECT,
            "reason": "%s depth %.4f mm in the %s exceeds the %.4f mm allowed "
            "at this pitch" % (discontinuity, depth, zone, allowed),
        }
    return {
        "zone": zone,
        "discontinuity": discontinuity,
        "depth_mm": depth,
        "allowed_depth_mm": allowed,
        "verdict": VERDICT_ACCEPT,
        "reason": "",
    }


def assess_dimension(feature, measured_mm, nominal_mm, plus_tol_mm, minus_tol_mm):
    """Judge one measured feature against its own signed tolerance band.

    plus_tol_mm and minus_tol_mm are both given as magnitudes; the minus
    tolerance is subtracted from the nominal.
    """
    _require_choice("feature", feature, FEATURES)
    measured = _require_number("measured_mm", measured_mm, minimum=0.0)
    nominal = _require_number("nominal_mm", nominal_mm, minimum=0.0)
    plus_tol = _require_number("plus_tol_mm", plus_tol_mm, minimum=0.0)
    minus_tol = _require_number("minus_tol_mm", minus_tol_mm, minimum=0.0)
    if plus_tol == 0.0 and minus_tol == 0.0:
        raise ValueError(
            "feature %s has a zero-width tolerance band; no measurement can "
            "ever pass it" % feature
        )
    upper = nominal + plus_tol
    lower = nominal - minus_tol
    deviation = measured - nominal
    inside = (measured >= lower - _SLACK_MM) and (measured <= upper + _SLACK_MM)
    margin = min(upper - measured, measured - lower)
    return {
        "feature": feature,
        "measured_mm": measured,
        "nominal_mm": nominal,
        "upper_limit_mm": upper,
        "lower_limit_mm": lower,
        "deviation_mm": deviation,
        "margin_mm": margin,
        "verdict": VERDICT_ACCEPT if inside else VERDICT_REJECT,
    }


def assess_fastener(record):
    """Roll one fastener's visual and dimensional results into a verdict."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    identifier = record.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("record needs a non-empty string id, got %r" % (identifier,))
    pitch = _require_number("pitch_mm", record.get("pitch_mm"), minimum=0.0)
    if pitch <= 0.0:
        raise ValueError("pitch_mm must be greater than zero, got %s" % pitch)
    discontinuities = record.get("discontinuities", [])
    dimensions = record.get("dimensions", [])
    if not isinstance(discontinuities, (list, tuple)):
        raise ValueError("discontinuities must be a sequence")
    if not isinstance(dimensions, (list, tuple)):
        raise ValueError("dimensions must be a sequence")
    if not discontinuities and not dimensions:
        raise ValueError(
            "record %s carries neither a visual nor a dimensional result; an "
            "empty inspection is not a pass" % identifier
        )
    visual = []
    for entry in discontinuities:
        if not isinstance(entry, dict):
            raise ValueError("each discontinuity must be a mapping, got %r" % (entry,))
        visual.append(
            assess_discontinuity(
                entry.get("zone"),
                entry.get("discontinuity"),
                entry.get("depth_mm"),
                pitch,
            )
        )
    dimensional = []
    for entry in dimensions:
        if not isinstance(entry, dict):
            raise ValueError("each dimension must be a mapping, got %r" % (entry,))
        dimensional.append(
            assess_dimension(
                entry.get("feature"),
                entry.get("measured_mm"),
                entry.get("nominal_mm"),
                entry.get("plus_tol_mm"),
                entry.get("minus_tol_mm"),
            )
        )
    findings = [r["reason"] for r in visual if r["verdict"] == VERDICT_REJECT]
    for result in dimensional:
        if result["verdict"] == VERDICT_REJECT:
            findings.append(
                "%s measured %.4f mm, outside %.4f..%.4f mm"
                % (
                    result["feature"],
                    result["measured_mm"],
                    result["lower_limit_mm"],
                    result["upper_limit_mm"],
                )
            )
    verdict = VERDICT_REJECT if findings else VERDICT_ACCEPT
    return {
        "id": identifier,
        "pitch_mm": pitch,
        "visual": visual,
        "dimensional": dimensional,
        "findings": findings,
        "verdict": verdict,
    }


def summarize_inspection(records):
    """Group a bench run of fasteners and name what drove the rejects."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of mappings")
    if not records:
        raise ValueError("no fasteners were inspected; there is nothing to report")
    results = [assess_fastener(record) for record in records]
    seen = set()
    for result in results:
        if result["id"] in seen:
            raise ValueError("duplicate fastener id %r in the run" % result["id"])
        seen.add(result["id"])
    rejected = [r for r in results if r["verdict"] == VERDICT_REJECT]
    causes = {}
    for result in rejected:
        for entry in result["visual"]:
            if entry["verdict"] == VERDICT_REJECT:
                key = "%s/%s" % (entry["zone"], entry["discontinuity"])
                causes[key] = causes.get(key, 0) + 1
        for entry in result["dimensional"]:
            if entry["verdict"] == VERDICT_REJECT:
                causes[entry["feature"]] = causes.get(entry["feature"], 0) + 1
    inspected = len(results)
    return {
        "inspected": inspected,
        "accepted": inspected - len(rejected),
        "rejected": len(rejected),
        "rejected_ids": [r["id"] for r in rejected],
        "reject_rate_per_hundred": (len(rejected) * 100) // inspected,
        "grouped_causes": causes,
        "results": results,
    }
