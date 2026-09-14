#!/usr/bin/env python3
"""An external protection diode is bought against a drawing that has to state its limits.

Anchor: ECSS-E-ST-20-08C Annex E. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

An external protection diode sits outside the cell assembly and carries the
string when a cell stops doing so. It is bought against a source control
drawing, and that drawing is the only place the part's limits are written
down. A drawing that lists a part number and a package has bought a diode; it
has not bought a diode that survives the string it protects. This module reads
the drawing and answers four questions:

    content   does the drawing carry every heading the part is bought against
              -- construction, forward and reverse characteristics, current
              rating, thermal characteristics, terminals and mounting, ESD
              sensitivity, radiation, marking, packaging, screening and the
              source it may be bought from
    blocking  does the stated reverse breakdown stand far enough above the
              reverse working voltage the application applies to it
    derating  does the forward current the application applies stay inside the
              rated current once the declared derating factor is taken off
    thermal   does the junction temperature that follows from the dissipated
              power and the stated thermal resistance stay below the rated
              maximum with the required margin still in hand

The arms are ranked rather than merged. A heading that is absent outranks a
limit that is stated and not met, because an absent heading leaves nobody able
to compute anything, while a breached limit is a computation that came out
wrong and can be argued about with numbers.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_DIODE_SCD_CONTENT = (
    "drawing_identifier",
    "issue_and_date",
    "component_description",
    "diode_construction",
    "forward_characteristics",
    "reverse_characteristics",
    "current_rating",
    "thermal_characteristics",
    "terminal_and_mounting",
    "esd_sensitivity",
    "radiation_requirement",
    "marking_and_traceability",
    "packaging_and_handling",
    "screening_and_acceptance",
    "approved_source",
)

ESD_CATEGORIES = ("class-0", "class-1a", "class-1b", "class-1c", "class-2", "class-3")

BLOCKING_ADEQUATE = "reverse-blocking-adequate"
BLOCKING_MARGIN_THIN = "reverse-blocking-margin-thin"
BLOCKING_INVERTED = "reverse-blocking-inverted"

DERATING_MET = "forward-current-derating-met"
DERATING_EXCEEDED = "forward-current-derating-exceeded"

THERMAL_MARGIN_MET = "junction-thermal-margin-met"
THERMAL_MARGIN_EXCEEDED = "junction-thermal-margin-exceeded"

DIODE_SCD_RELEASABLE = "diode-scd-releasable"
DIODE_SCD_NOT_RELEASABLE = "diode-scd-not-releasable"

DEFAULT_DIODE_SCD_POLICY = {
    "min_reverse_blocking_margin": 2.0,
    "max_forward_current_utilisation": 1.0,
    "junction_temperature_margin_k": 10.0,
    "require_esd_category": True,
    "min_content_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    value = _require_number(name, value)
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def validate_diode_scd_policy(policy):
    """Check a diode drawing-review policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    margin = _require_number(
        "min_reverse_blocking_margin", policy.get("min_reverse_blocking_margin")
    )
    if margin < 1.0:
        raise ValueError(
            "min_reverse_blocking_margin must be at least 1, got %r" % (margin,)
        )
    _require_positive(
        "max_forward_current_utilisation",
        policy.get("max_forward_current_utilisation"),
    )
    _require_non_negative(
        "junction_temperature_margin_k",
        policy.get("junction_temperature_margin_k"),
    )
    _require_flag("require_esd_category", policy.get("require_esd_category"))
    _require_fraction("min_content_fraction", policy.get("min_content_fraction"))
    return policy


def required_diode_scd_content():
    """The headings an external protection diode is bought against."""
    return tuple(REQUIRED_DIODE_SCD_CONTENT)


def esd_categories():
    """The sensitivity categories a drawing may place the part in."""
    return tuple(ESD_CATEGORIES)


def audit_diode_scd_content(drawing, policy=DEFAULT_DIODE_SCD_POLICY):
    """Which required headings the diode drawing does not actually carry."""
    validate_diode_scd_policy(policy)
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    content = drawing.get("content")
    if not isinstance(content, dict):
        raise ValueError("drawing content must be a mapping, got %r" % (content,))
    missing = []
    for heading in REQUIRED_DIODE_SCD_CONTENT:
        value = content.get(heading)
        if value is None:
            missing.append(heading)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(heading)
            continue
        if isinstance(value, (list, tuple, dict)) and not value:
            missing.append(heading)
    return sorted(missing)


def categorize_esd_sensitivity(entry):
    """Place the stated ESD sensitivity in one of the drawing's categories."""
    category = _require_text("esd_sensitivity", entry).lower()
    if category not in ESD_CATEGORIES:
        raise ValueError(
            "esd_sensitivity must be one of %s, got %r"
            % (", ".join(ESD_CATEGORIES), category)
        )
    return category


def assess_reverse_blocking(entry, policy=DEFAULT_DIODE_SCD_POLICY):
    """Does the stated breakdown stand far enough above the applied reverse volts."""
    validate_diode_scd_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("reverse characteristics must be a mapping, got %r" % (entry,))
    breakdown = _require_positive(
        "reverse_breakdown_v", entry.get("reverse_breakdown_v")
    )
    working = _require_positive(
        "reverse_working_v", entry.get("reverse_working_v")
    )
    leakage = _require_non_negative(
        "reverse_leakage_a", entry.get("reverse_leakage_a")
    )
    margin = breakdown / working
    required = float(policy["min_reverse_blocking_margin"])
    if not _at_least(breakdown, working) or _close(breakdown, working):
        verdict = BLOCKING_INVERTED
    elif not _at_least(margin, required):
        verdict = BLOCKING_MARGIN_THIN
    else:
        verdict = BLOCKING_ADEQUATE
    return {
        "reverse_breakdown_v": breakdown,
        "reverse_working_v": working,
        "reverse_leakage_a": leakage,
        "blocking_margin": margin,
        "required_margin": required,
        "verdict": verdict,
        "adequate": verdict == BLOCKING_ADEQUATE,
    }


def assess_forward_current_derating(entry, policy=DEFAULT_DIODE_SCD_POLICY):
    """Does the applied forward current stay inside the derated rating."""
    validate_diode_scd_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("current rating must be a mapping, got %r" % (entry,))
    rated = _require_positive("rated_forward_a", entry.get("rated_forward_a"))
    applied = _require_non_negative("applied_forward_a", entry.get("applied_forward_a"))
    factor = _require_fraction("derating_factor", entry.get("derating_factor"))
    if factor <= 0.0:
        raise ValueError("derating_factor must be greater than 0, got %r" % (factor,))
    allowed = rated * factor
    utilisation = applied / allowed
    ceiling = float(policy["max_forward_current_utilisation"])
    met = _at_most(utilisation, ceiling)
    return {
        "rated_forward_a": rated,
        "applied_forward_a": applied,
        "derating_factor": factor,
        "derated_allowance_a": allowed,
        "utilisation": utilisation,
        "utilisation_ceiling": ceiling,
        "verdict": DERATING_MET if met else DERATING_EXCEEDED,
        "met": met,
    }


def junction_temperature(forward, thermal):
    """Junction temperature that follows from the dissipation and the stated path."""
    if not isinstance(forward, dict):
        raise ValueError("forward characteristics must be a mapping, got %r" % (forward,))
    if not isinstance(thermal, dict):
        raise ValueError("thermal characteristics must be a mapping, got %r" % (thermal,))
    forward_v = _require_positive("forward_drop_v", forward.get("forward_drop_v"))
    forward_a = _require_non_negative(
        "forward_current_a", forward.get("forward_current_a")
    )
    resistance = _require_non_negative(
        "junction_to_case_k_per_w", thermal.get("junction_to_case_k_per_w")
    )
    case_c = _require_number("case_temperature_c", thermal.get("case_temperature_c"))
    dissipation = forward_v * forward_a
    rise = dissipation * resistance
    return {
        "dissipation_w": dissipation,
        "temperature_rise_k": rise,
        "case_temperature_c": case_c,
        "junction_temperature_c": case_c + rise,
    }


def assess_junction_thermal_margin(
    forward, thermal, policy=DEFAULT_DIODE_SCD_POLICY
):
    """Does the computed junction temperature sit below the rated maximum."""
    validate_diode_scd_policy(policy)
    computed = junction_temperature(forward, thermal)
    rated_max = _require_number(
        "rated_junction_max_c", thermal.get("rated_junction_max_c")
    )
    margin = float(policy["junction_temperature_margin_k"])
    limit = rated_max - margin
    met = _at_most(computed["junction_temperature_c"], limit)
    result = dict(computed)
    result.update(
        {
            "rated_junction_max_c": rated_max,
            "applied_margin_k": margin,
            "junction_limit_c": limit,
            "headroom_k": limit - computed["junction_temperature_c"],
            "verdict": THERMAL_MARGIN_MET if met else THERMAL_MARGIN_EXCEEDED,
            "met": met,
        }
    )
    return result


def assess_external_diode_scd(drawing, policy=DEFAULT_DIODE_SCD_POLICY):
    """Full Annex E sweep over an external protection diode source control drawing."""
    validate_diode_scd_policy(policy)
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    drawing_id = _require_text("drawing_id", drawing.get("drawing_id"))
    content = drawing.get("content")
    if not isinstance(content, dict) or not content:
        raise ValueError("drawing content must be a non-empty mapping")

    missing = audit_diode_scd_content(drawing, policy)
    findings = [
        "drawing %s states nothing under %s, so the part carries no stated limit "
        "there" % (drawing_id, heading)
        for heading in missing
    ]

    blocking = None
    if "reverse_characteristics" not in missing:
        blocking = assess_reverse_blocking(content["reverse_characteristics"], policy)
        if not blocking["adequate"]:
            findings.append(
                "drawing %s leaves reverse blocking %s at a margin of %.3f against "
                "%.3f" % (
                    drawing_id,
                    blocking["verdict"],
                    blocking["blocking_margin"],
                    blocking["required_margin"],
                )
            )

    derating = None
    if "current_rating" not in missing:
        derating = assess_forward_current_derating(content["current_rating"], policy)
        if not derating["met"]:
            findings.append(
                "drawing %s applies %.4f A against a derated allowance of %.4f A"
                % (
                    drawing_id,
                    derating["applied_forward_a"],
                    derating["derated_allowance_a"],
                )
            )

    thermal = None
    if (
        "forward_characteristics" not in missing
        and "thermal_characteristics" not in missing
    ):
        thermal = assess_junction_thermal_margin(
            content["forward_characteristics"], content["thermal_characteristics"], policy
        )
        if not thermal["met"]:
            findings.append(
                "drawing %s reaches a junction temperature of %.3f C against a "
                "limit of %.3f C"
                % (
                    drawing_id,
                    thermal["junction_temperature_c"],
                    thermal["junction_limit_c"],
                )
            )

    esd_category = None
    if "esd_sensitivity" not in missing and policy["require_esd_category"]:
        esd_category = categorize_esd_sensitivity(content["esd_sensitivity"])

    total = len(REQUIRED_DIODE_SCD_CONTENT)
    stated = total - len(missing)
    content_fraction = stated / float(total)
    minimum = float(policy["min_content_fraction"])
    content_ok = _at_least(content_fraction, minimum)
    if not content_ok:
        findings.append(
            "drawing %s states %d of %d required headings against a required "
            "share of %.3f" % (drawing_id, stated, total, minimum)
        )

    releasable = (
        content_ok
        and not missing
        and (blocking is None or blocking["adequate"])
        and (derating is None or derating["met"])
        and (thermal is None or thermal["met"])
    )
    return {
        "verdict": DIODE_SCD_RELEASABLE if releasable else DIODE_SCD_NOT_RELEASABLE,
        "drawing_id": drawing_id,
        "missing_content": missing,
        "stated_content_fraction": content_fraction,
        "required_content_fraction": minimum,
        "reverse_blocking": blocking,
        "forward_current_derating": derating,
        "junction_thermal_margin": thermal,
        "esd_category": esd_category,
        "every_heading_stated": not missing,
        "findings": findings,
    }
