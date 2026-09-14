#!/usr/bin/env python3
"""Visible defect rules applied to a secondary working standard.

Anchor: ECSS-E-ST-20-08C clause 10.2.2.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A secondary working standard is not given a defect catalogue of its own.
It is held to the visible defect rules already written for solar cells
and for cell assemblies, which means the first question is not "how big
is this mark" but "which of those rule families reaches a device built
like this one". A bare cell standard is not reached by the coverglass
rules; a coverglassed standard is reached by both the cell rules and the
coverglass rules; an interconnected standard adds the joint rules on top.
Deciding the applicable families first is what stops an inspector either
grading a device against rules that never governed it or, worse, passing
a device because the family that would have condemned it was never run.

The second thing that makes a working standard different from the cell
it is built from is the consequence of a defect. A cell that loses a
sliver of active area loses a sliver of its own output. A working
standard that loses the same sliver biases the short-circuit current it
reports, and that bias is inherited by every measurement later
transferred through it. The rollup therefore converts the accumulated
obscured area into the fractional current bias it implies, because that
number, not the defect count, is what decides whether the device can
still carry a calibration value.

Allowances are derived from the device's own active area and its own
edges rather than typed in as absolutes, so a physically smaller
standard tightens its own limits without anyone editing a table.

Dispositions are accept, refer-for-review and reject.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

BARE_CELL_STANDARD = "bare-cell-standard"
COVERGLASSED_STANDARD = "coverglassed-cell-standard"
INTERCONNECTED_STANDARD = "interconnected-assembly-standard"
ENCAPSULATED_STANDARD = "encapsulated-module-standard"
STANDARD_CONSTRUCTIONS = (
    BARE_CELL_STANDARD,
    COVERGLASSED_STANDARD,
    INTERCONNECTED_STANDARD,
    ENCAPSULATED_STANDARD,
)

CELL_RULES = "cell-surface-and-edge-rules"
COVERGLASS_RULES = "coverglass-and-adhesive-rules"
JOINT_RULES = "interconnect-and-joint-rules"
CARRIER_RULES = "carrier-and-wiring-rules"
RULE_FAMILIES = (CELL_RULES, COVERGLASS_RULES, JOINT_RULES, CARRIER_RULES)

_FAMILIES_BY_CONSTRUCTION = {
    BARE_CELL_STANDARD: (CELL_RULES,),
    COVERGLASSED_STANDARD: (CELL_RULES, COVERGLASS_RULES),
    INTERCONNECTED_STANDARD: (CELL_RULES, COVERGLASS_RULES, JOINT_RULES),
    ENCAPSULATED_STANDARD: (
        CELL_RULES,
        COVERGLASS_RULES,
        JOINT_RULES,
        CARRIER_RULES,
    ),
}

_FAMILY_BY_DEFECT = {
    "cell-edge-chip": CELL_RULES,
    "cell-surface-nick": CELL_RULES,
    "cell-crack": CELL_RULES,
    "antireflection-coating-blemish": CELL_RULES,
    "contact-area-defect": CELL_RULES,
    "coverglass-chip": COVERGLASS_RULES,
    "coverglass-crack": COVERGLASS_RULES,
    "adhesive-void": COVERGLASS_RULES,
    "adhesive-discolouration": COVERGLASS_RULES,
    "interconnect-weld-defect": JOINT_RULES,
    "interconnect-deformation": JOINT_RULES,
    "wiring-defect": CARRIER_RULES,
    "carrier-surface-mark": CARRIER_RULES,
}
DEFECT_CATEGORIES = tuple(sorted(_FAMILY_BY_DEFECT))

# Defects that remove or shade collecting area bias the reported current;
# a weld or a wiring mark does not, however serious it is for handling.
_OBSCURING_FAMILIES = (CELL_RULES, COVERGLASS_RULES)
_CRACK_CATEGORIES = ("cell-crack", "coverglass-crack")

ACCEPT = "accept"
REFER = "refer-for-review"
REJECT = "reject"
DEFECT_DISPOSITIONS = (ACCEPT, REFER, REJECT)

_SEVERITY_ORDER = {ACCEPT: 0, REFER: 1, REJECT: 2}

STANDARD_FIT = "working-standard-fit-for-transfer"
STANDARD_REFERRED = "working-standard-referred"
STANDARD_UNFIT = "working-standard-not-fit-for-transfer"

_VERDICT_BY_SEVERITY = {
    ACCEPT: STANDARD_FIT,
    REFER: STANDARD_REFERRED,
    REJECT: STANDARD_UNFIT,
}

DEFAULT_VISUAL_CRITERIA = {
    # one defect, as a share of the device's own active area
    "max_defect_area_fraction": 0.0020,
    "defect_area_review_factor": 2.0,
    # everything that shades or removes collecting area, added up
    "max_cumulative_obscuration_fraction": 0.0050,
    # a crack, as a share of the shorter edge it runs across
    "max_crack_length_fraction": 0.05,
    "crack_length_review_factor": 2.0,
    # a mark this close to a contact undercuts the pad
    "min_contact_clearance_mm": 0.30,
    # how many findings one rule family may carry before the device is
    # referred even though each finding passed on its own
    "max_defects_per_family": 3,
    # the bias a transfer through this device would inherit
    "max_implied_current_bias_fraction": 0.0100,
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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    Every limit here is a product of a criteria share and a measured
    dimension, so a measurement sitting exactly on the limit can evaluate
    a few units in the last place above it. The limit is never raised;
    only the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_visual_criteria(criteria):
    """Check a defect criteria set is complete and self-consistent."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    for key in (
        "max_defect_area_fraction",
        "max_cumulative_obscuration_fraction",
        "max_crack_length_fraction",
        "max_implied_current_bias_fraction",
    ):
        fraction = _require_positive("criteria %s" % key, criteria.get(key))
        if fraction > 1.0:
            raise ValueError(
                "criteria %s is a share of a measured quantity and cannot "
                "exceed one, got %r" % (key, fraction)
            )
    _require_non_negative(
        "criteria min_contact_clearance_mm", criteria.get("min_contact_clearance_mm")
    )
    for key in ("defect_area_review_factor", "crack_length_review_factor"):
        factor = _require_positive("criteria %s" % key, criteria.get(key))
        if factor < 1.0:
            raise ValueError(
                "criteria %s must be at least one; a review band cannot be "
                "tighter than the accept band, got %r" % (key, factor)
            )
    _require_count(
        "criteria max_defects_per_family", criteria.get("max_defects_per_family")
    )
    if not _at_most(
        criteria["max_defect_area_fraction"],
        criteria["max_cumulative_obscuration_fraction"],
    ):
        raise ValueError(
            "one defect may not be allowed more area than every defect "
            "together: %r against %r"
            % (
                criteria["max_defect_area_fraction"],
                criteria["max_cumulative_obscuration_fraction"],
            )
        )
    if not _at_most(
        criteria["max_cumulative_obscuration_fraction"],
        criteria["max_implied_current_bias_fraction"],
    ):
        raise ValueError(
            "the referral band on accumulated obscuration cannot sit above "
            "the current bias a working standard may carry: %r against %r"
            % (
                criteria["max_cumulative_obscuration_fraction"],
                criteria["max_implied_current_bias_fraction"],
            )
        )
    return criteria


def validate_standard_geometry(geometry):
    """Check the outline the working standard's own allowances come from."""
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be a mapping, got %r" % (geometry,))
    length = _require_positive("length_mm", geometry.get("length_mm"))
    width = _require_positive("width_mm", geometry.get("width_mm"))
    border = _require_positive(
        "inactive_border_mm", geometry.get("inactive_border_mm")
    )
    if 2.0 * border >= min(length, width):
        raise ValueError(
            "an inactive border of %.3f mm leaves no active area on a %.3f by "
            "%.3f mm standard" % (border, length, width)
        )
    active_length = length - 2.0 * border
    active_width = width - 2.0 * border
    return {
        "length_mm": length,
        "width_mm": width,
        "inactive_border_mm": border,
        "shortest_edge_mm": min(length, width),
        "outline_area_mm2": length * width,
        "active_area_mm2": active_length * active_width,
    }


def applicable_rule_families(construction):
    """Rule families the cell and assembly defect rules give this build."""
    _require_choice("construction", construction, STANDARD_CONSTRUCTIONS)
    return _FAMILIES_BY_CONSTRUCTION[construction]


def defect_rule_family(category):
    """The rule family one observed defect category belongs to."""
    _require_choice("category", category, DEFECT_CATEGORIES)
    return _FAMILY_BY_DEFECT[category]


def assess_standard_defect(defect, geometry, construction, criteria=DEFAULT_VISUAL_CRITERIA):
    """Disposition one observed defect on a working standard.

    A defect whose family does not reach this construction is referred,
    never accepted. It is a real observation that these rules do not
    govern, and silently passing it is how a device leaves inspection
    with an unjudged mark on it.
    """
    validate_visual_criteria(criteria)
    resolved = validate_standard_geometry(geometry)
    families = applicable_rule_families(construction)
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    category = _require_choice(
        "category", defect.get("category"), DEFECT_CATEGORIES
    )
    family = defect_rule_family(category)
    area = _require_positive("area_mm2", defect.get("area_mm2"))
    if not _at_most(area, resolved["outline_area_mm2"]):
        raise ValueError(
            "a defect of %.4f mm2 does not fit on a %.4f mm2 standard"
            % (area, resolved["outline_area_mm2"])
        )
    clearance = _require_non_negative(
        "contact_clearance_mm", defect.get("contact_clearance_mm", 0.0)
    )
    length = _require_non_negative("length_mm", defect.get("length_mm", 0.0))

    reasons = []
    dispositions = []
    governed = family in families
    obscuring = family in _OBSCURING_FAMILIES and governed
    area_fraction = area / resolved["active_area_mm2"]
    if not governed:
        return {
            "id": defect.get("id"),
            "category": category,
            "rule_family": family,
            "governed": False,
            "area_mm2": area,
            "area_fraction_of_active": area_fraction,
            "length_mm": length,
            "contact_clearance_mm": clearance,
            "obscures_active_area": False,
            "obscured_area_mm2": 0.0,
            "disposition": REFER,
            "reasons": [
                "a %s finding belongs to the %s, which a %s is not built to "
                "carry; the observation stands and these rules do not "
                "dispose of it" % (category, family, construction)
            ],
        }

    limit = criteria["max_defect_area_fraction"]
    review_limit = limit * criteria["defect_area_review_factor"]
    if _at_most(area_fraction, limit):
        dispositions.append(ACCEPT)
    elif _at_most(area_fraction, review_limit):
        dispositions.append(REFER)
        reasons.append(
            "takes %.5f of the active area, past the %.5f allowance"
            % (area_fraction, limit)
        )
    else:
        dispositions.append(REJECT)
        reasons.append(
            "takes %.5f of the active area, past the %.5f review limit"
            % (area_fraction, review_limit)
        )

    if category in _CRACK_CATEGORIES:
        run = _require_positive("length_mm", defect.get("length_mm"))
        crack_limit = resolved["shortest_edge_mm"] * criteria["max_crack_length_fraction"]
        crack_review = crack_limit * criteria["crack_length_review_factor"]
        if _at_most(run, crack_limit):
            dispositions.append(ACCEPT)
        elif _at_most(run, crack_review):
            dispositions.append(REFER)
            reasons.append(
                "runs %.3f mm across a %.3f mm edge, past the %.3f mm allowance"
                % (run, resolved["shortest_edge_mm"], crack_limit)
            )
        else:
            dispositions.append(REJECT)
            reasons.append(
                "runs %.3f mm, past the %.3f mm review limit; a crack that long "
                "propagates under thermal cycling and the device stops holding "
                "one value" % (run, crack_review)
            )

    if _at_most(criteria["min_contact_clearance_mm"], clearance):
        dispositions.append(ACCEPT)
    else:
        dispositions.append(REJECT)
        reasons.append(
            "sits %.3f mm from a contact, inside the %.3f mm clearance, so it "
            "undercuts the pad the transfer measurement is taken through"
            % (clearance, criteria["min_contact_clearance_mm"])
        )

    return {
        "id": defect.get("id"),
        "category": category,
        "rule_family": family,
        "governed": governed,
        "area_mm2": area,
        "area_fraction_of_active": area_fraction,
        "length_mm": length,
        "contact_clearance_mm": clearance,
        "obscures_active_area": obscuring,
        "obscured_area_mm2": area if obscuring else 0.0,
        "disposition": _worst(dispositions),
        "reasons": reasons,
    }


def implied_current_bias_fraction(obscured_area_mm2, active_area_mm2):
    """Fractional short-circuit-current bias a shaded area implies.

    Short-circuit current tracks collecting area under a fixed
    irradiance, so area lost from the active face is the share of the
    reported current the device no longer produces, and every value
    transferred through it carries that share as an error.
    """
    obscured = _require_non_negative("obscured_area_mm2", obscured_area_mm2)
    active = _require_positive("active_area_mm2", active_area_mm2)
    if not _at_most(obscured, active):
        raise ValueError(
            "%.4f mm2 obscured exceeds the %.4f mm2 active area" % (obscured, active)
        )
    return obscured / active


def assess_working_standard_visual(standard, criteria=DEFAULT_VISUAL_CRITERIA):
    """Clause 10.2.2.3.1 visual screen of one secondary working standard."""
    validate_visual_criteria(criteria)
    if not isinstance(standard, dict):
        raise ValueError("standard must be a mapping, got %r" % (standard,))
    standard_id = standard.get("standard_id")
    if not isinstance(standard_id, str) or not standard_id.strip():
        raise ValueError("each working standard needs a non-empty standard_id")
    construction = _require_choice(
        "construction", standard.get("construction"), STANDARD_CONSTRUCTIONS
    )
    geometry = validate_standard_geometry(standard.get("geometry"))
    families = applicable_rule_families(construction)

    defects = standard.get("defects", [])
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a list")
    inspected = standard.get("inspected_families", families)
    if not isinstance(inspected, (list, tuple)):
        raise ValueError("inspected_families must be a list")
    for family in inspected:
        _require_choice("inspected family", family, RULE_FAMILIES)

    seen = set()
    assessed = []
    for defect in defects:
        result = assess_standard_defect(
            defect, standard.get("geometry"), construction, criteria
        )
        marker = result["id"]
        if marker is not None:
            if marker in seen:
                raise ValueError(
                    "duplicate defect id %r on standard %s" % (marker, standard_id)
                )
            seen.add(marker)
        assessed.append(result)

    findings = []
    for result in assessed:
        for reason in result["reasons"]:
            findings.append("%s: %s" % (result["id"], reason))

    verdict = _worst([result["disposition"] for result in assessed])

    obscured = sum(result["obscured_area_mm2"] for result in assessed)
    bias = implied_current_bias_fraction(obscured, geometry["active_area_mm2"])
    if not _at_most(bias, criteria["max_cumulative_obscuration_fraction"]):
        verdict = _worst((verdict, REFER))
        findings.append(
            "shaded and missing area together take %.5f of the active face, "
            "past the %.5f allowance, even though no single defect did"
            % (bias, criteria["max_cumulative_obscuration_fraction"])
        )
    if not _at_most(bias, criteria["max_implied_current_bias_fraction"]):
        verdict = _worst((verdict, REJECT))
        findings.append(
            "a transfer through this device would inherit a %.5f current bias, "
            "past the %.5f a working standard may carry"
            % (bias, criteria["max_implied_current_bias_fraction"])
        )

    per_family = {}
    for result in assessed:
        per_family[result["rule_family"]] = per_family.get(result["rule_family"], 0) + 1
    for family in sorted(per_family):
        if per_family[family] > criteria["max_defects_per_family"]:
            verdict = _worst((verdict, REFER))
            findings.append(
                "%d findings under the %s exceed the %d allowed on one device"
                % (per_family[family], family, criteria["max_defects_per_family"])
            )

    uninspected = [family for family in families if family not in inspected]
    for family in uninspected:
        verdict = _worst((verdict, REFER))
        findings.append(
            "the %s reaches a %s and was not run; a clean report from the "
            "families that were run does not cover it"
            % (family, construction)
        )

    ungoverned = [result["id"] for result in assessed if not result["governed"]]

    return {
        "standard_id": standard_id,
        "construction": construction,
        "applicable_families": list(families),
        "inspected_families": [f for f in inspected],
        "uninspected_families": uninspected,
        "verdict": _VERDICT_BY_SEVERITY[verdict],
        "disposition": verdict,
        "defects": assessed,
        "findings_per_family": per_family,
        "obscured_area_mm2": obscured,
        "active_area_mm2": geometry["active_area_mm2"],
        "implied_current_bias_fraction": bias,
        "ungoverned_observation_ids": ungoverned,
        "not_accepted_ids": [
            result["id"] for result in assessed if result["disposition"] != ACCEPT
        ],
        "findings": findings,
    }
