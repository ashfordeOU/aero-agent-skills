#!/usr/bin/env python3
"""Part removal, depowdering and cleaning verification for additive builds.

Anchor: ECSS-Q-ST-70-80 post-process clause on removing parts from the build
plate, freeing them of unfused powder and cleaning them, internal passages
included. The procedure below is a paraphrase into implementable steps; no
standard text is reproduced.

What the clause actually decides
--------------------------------
Unfused powder that stays inside a part is mass, it is a contamination
source, and in a fluid passage it is a blockage that no later inspection of
the outside will find. The decision is made on four things:

mass balance   the difference between the as-removed mass and the nominal
               solid mass is trapped powder. It is the only measurement
               that sees powder the borescope cannot reach.
passages       a channel frees itself only if its bore is large against the
               powder it has to pass, its length is short against that bore,
               and there is more than one opening for powder to leave by.
removal        the cut that frees the part from the plate consumes material,
               and the part moves when the plate constraint goes. Both come
               out of the same declared allowance.
cleanliness    what is left after depowdering is graded per unit area, not
               as a bare mass, because the same residue on a small part and
               a large one are different results.

The verdict is the worst of the four and the driving characteristic is
named, so the reviewer knows whether to change the design of the passage,
the depowdering recipe or the cut.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REMOVAL_METHODS = ("wire-edm", "band-saw", "milling", "abrasive-cut-off")

# Kerf consumed by the cut that frees the part, in millimetres. A saw takes
# an order more material than a wire, so the same declared allowance is
# generous for one method and absent for another.
METHOD_KERF_MM = {
    "wire-edm": 0.35,
    "band-saw": 1.60,
    "milling": 2.00,
    "abrasive-cut-off": 2.50,
}

VERDICT_ACCEPT = "accept"
VERDICT_REVIEW = "review"
VERDICT_REJECT = "reject"

_VERDICT_RANK = {VERDICT_ACCEPT: 0, VERDICT_REVIEW: 1, VERDICT_REJECT: 2}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

# A bore narrower than this many powder diameters bridges rather than flows.
DEFAULT_MIN_BORE_RATIO = 10.0
# Beyond this length-to-bore ratio a passage stops self-draining.
DEFAULT_MAX_ASPECT_RATIO = 20.0
# A shortfall smaller than this fraction of the nominal mass is weighing
# scatter; anything larger says the mass record and the model disagree.
DEFAULT_MASS_SCATTER_FRACTION = 0.005


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
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (name, value))
    return value


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


def _worst(verdicts):
    worst = VERDICT_ACCEPT
    for verdict in verdicts:
        if _VERDICT_RANK[verdict] > _VERDICT_RANK[worst]:
            worst = verdict
    return worst


def trapped_powder(as_removed_mass_g, nominal_solid_mass_g,
                   allowance_fraction=0.0,
                   scatter_fraction=DEFAULT_MASS_SCATTER_FRACTION):
    """Mass balance of a depowdered part against its nominal solid mass.

    The excess over the nominal mass is powder that never left the part. A
    part lighter than nominal by more than the weighing scatter is not a
    clean part, it is an inconsistent record: either the mass or the solid
    model is wrong, and neither can be graded.
    """
    as_removed = _require_positive("as_removed_mass_g", as_removed_mass_g)
    nominal = _require_positive("nominal_solid_mass_g", nominal_solid_mass_g)
    allowance = _require_non_negative("allowance_fraction", allowance_fraction)
    scatter = _require_non_negative("scatter_fraction", scatter_fraction)
    if allowance > 1.0:
        raise ValueError("allowance_fraction must not exceed 1.0")
    shortfall = nominal - as_removed
    if shortfall > 0.0 and not _at_most(shortfall, nominal * scatter):
        raise ValueError(
            "as-removed mass %.3f g is %.3f g under the %.3f g nominal solid "
            "mass, beyond weighing scatter; the mass record and the solid "
            "model disagree" % (as_removed, shortfall, nominal)
        )
    residue = max(as_removed - nominal, 0.0)
    fraction = residue / nominal
    acceptable = _at_most(fraction, allowance)
    findings = []
    if not acceptable:
        findings.append(
            "%.3f g of trapped powder is %.4f of the nominal mass, above the "
            "%.4f allowance" % (residue, fraction, allowance)
        )
    return {
        "residual_powder_g": residue,
        "residual_fraction": fraction,
        "verdict": VERDICT_ACCEPT if acceptable else VERDICT_REJECT,
        "findings": findings,
    }


def passage_depowdering(channel, min_bore_ratio=DEFAULT_MIN_BORE_RATIO,
                        max_aspect_ratio=DEFAULT_MAX_ASPECT_RATIO):
    """Grade one internal passage on bore, length and the exits it has.

    channel keys: id, bore_mm, length_mm, particle_d90_um, open_port_count.
    """
    if not isinstance(channel, dict):
        raise ValueError("channel must be a mapping, got %r" % (channel,))
    identifier = channel.get("id", "passage")
    bore = _require_positive("bore_mm", channel.get("bore_mm"))
    length = _require_positive("length_mm", channel.get("length_mm"))
    d90 = _require_positive("particle_d90_um", channel.get("particle_d90_um"))
    ports = _require_count("open_port_count", channel.get("open_port_count"))
    min_ratio = _require_positive("min_bore_ratio", min_bore_ratio)
    max_aspect = _require_positive("max_aspect_ratio", max_aspect_ratio)

    bore_ratio = (bore * 1000.0) / d90
    aspect_ratio = length / bore

    findings = []
    verdicts = [VERDICT_ACCEPT]

    if not _at_least(bore_ratio, min_ratio):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%s bore is %.1f powder diameters wide against the %.1f needed; "
            "powder bridges instead of flowing"
            % (identifier, bore_ratio, min_ratio)
        )

    if ports == 0:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%s has no open port; a blind passage has no path for the powder "
            "to leave by" % identifier
        )
    elif ports == 1:
        if not _at_most(aspect_ratio, max_aspect * 0.5):
            verdicts.append(VERDICT_REVIEW)
            findings.append(
                "%s is %.1f bores long with a single opening; powder has to "
                "travel back out the way it came" % (identifier, aspect_ratio)
            )

    if not _at_most(aspect_ratio, max_aspect):
        if ports >= 2:
            verdicts.append(VERDICT_REVIEW)
            findings.append(
                "%s is %.1f bores long, past the %.1f self-draining limit, "
                "and needs a declared flushing route between its ports"
                % (identifier, aspect_ratio, max_aspect)
            )
        else:
            verdicts.append(VERDICT_REJECT)
            findings.append(
                "%s is %.1f bores long, past the %.1f limit, with no second "
                "opening to flush through" % (identifier, aspect_ratio, max_aspect)
            )

    return {
        "id": identifier,
        "bore_ratio": bore_ratio,
        "aspect_ratio": aspect_ratio,
        "open_port_count": ports,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def removal_allowance(method, declared_allowance_mm, distortion_mm=0.0,
                      datum_uncertainty_mm=0.0, stress_relief_done=True):
    """Grade the material budget of the cut that frees the part."""
    method = _require_choice("method", method, REMOVAL_METHODS)
    declared = _require_non_negative("declared_allowance_mm", declared_allowance_mm)
    distortion = _require_non_negative("distortion_mm", distortion_mm)
    datum = _require_non_negative("datum_uncertainty_mm", datum_uncertainty_mm)
    if not isinstance(stress_relief_done, bool):
        raise ValueError("stress_relief_done must be True or False")
    kerf = METHOD_KERF_MM[method]
    required = kerf + distortion + datum
    findings = []
    verdicts = [VERDICT_ACCEPT]
    if not _at_least(declared, required):
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "%s needs %.2f mm (kerf %.2f, distortion %.2f, datum %.2f) but "
            "only %.2f mm was left on the part"
            % (method, required, kerf, distortion, datum, declared)
        )
    if not stress_relief_done:
        verdicts.append(VERDICT_REJECT)
        findings.append(
            "the part was cut from the plate before stress relief, so the "
            "as-built residual stress was released as distortion"
        )
    return {
        "method": method,
        "kerf_mm": kerf,
        "required_allowance_mm": required,
        "declared_allowance_mm": declared,
        "verdict": _worst(verdicts),
        "findings": findings,
    }


def cleanliness(residue_mg, area_cm2, limit_mg_per_cm2, review_fraction=0.8):
    """Grade cleaning residue per unit of cleaned area, not as a bare mass."""
    residue = _require_non_negative("residue_mg", residue_mg)
    area = _require_positive("area_cm2", area_cm2)
    limit = _require_positive("limit_mg_per_cm2", limit_mg_per_cm2)
    fraction = _require_positive("review_fraction", review_fraction)
    if fraction > 1.0:
        raise ValueError("review_fraction must not exceed 1.0")
    level = residue / area
    findings = []
    if not _at_most(level, limit):
        verdict = VERDICT_REJECT
        findings.append(
            "residue %.4f mg/cm2 over %.1f cm2 exceeds the %.4f mg/cm2 limit"
            % (level, area, limit)
        )
    elif _at_least(level, limit * fraction):
        verdict = VERDICT_REVIEW
        findings.append(
            "residue %.4f mg/cm2 sits inside the top %.0f%% of the limit; the "
            "cleaning recipe has no margin left"
            % (level, (1.0 - fraction) * 100.0)
        )
    else:
        verdict = VERDICT_ACCEPT
    return {
        "residue_mg_per_cm2": level,
        "limit_mg_per_cm2": limit,
        "verdict": verdict,
        "findings": findings,
    }


def assess_removal_and_cleaning(case):
    """Full removal, depowdering and cleaning verdict for one part."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    mass = trapped_powder(
        case.get("as_removed_mass_g"),
        case.get("nominal_solid_mass_g"),
        case.get("powder_allowance_fraction", 0.0),
    )
    channels = case.get("channels", [])
    if not isinstance(channels, (list, tuple)):
        raise ValueError("case['channels'] must be a sequence of passages")
    passages = [
        passage_depowdering(
            channel,
            case.get("min_bore_ratio", DEFAULT_MIN_BORE_RATIO),
            case.get("max_aspect_ratio", DEFAULT_MAX_ASPECT_RATIO),
        )
        for channel in channels
    ]
    removal = removal_allowance(
        case.get("removal_method"),
        case.get("declared_allowance_mm"),
        case.get("distortion_mm", 0.0),
        case.get("datum_uncertainty_mm", 0.0),
        case.get("stress_relief_done", True),
    )
    clean = cleanliness(
        case.get("residue_mg"),
        case.get("cleaned_area_cm2"),
        case.get("residue_limit_mg_per_cm2"),
    )
    passage_verdict = _worst([record["verdict"] for record in passages])
    parts = {
        "mass-balance": mass,
        "passages": {"verdict": passage_verdict},
        "removal": removal,
        "cleanliness": clean,
    }
    verdict = _worst(part["verdict"] for part in parts.values())
    driving = sorted(
        name
        for name, part in parts.items()
        if _VERDICT_RANK[part["verdict"]] == _VERDICT_RANK[verdict]
        and verdict != VERDICT_ACCEPT
    )
    worst_passages = [
        record["id"]
        for record in passages
        if _VERDICT_RANK[record["verdict"]] == _VERDICT_RANK[passage_verdict]
        and passage_verdict != VERDICT_ACCEPT
    ]
    findings = []
    findings.extend("mass-balance: %s" % text for text in mass["findings"])
    for record in passages:
        findings.extend("passage %s: %s" % (record["id"], text)
                        for text in record["findings"])
    findings.extend("removal: %s" % text for text in removal["findings"])
    findings.extend("cleanliness: %s" % text for text in clean["findings"])
    return {
        "verdict": verdict,
        "driving_characteristics": driving,
        "mass_balance": mass,
        "passages": passages,
        "passage_verdict": passage_verdict,
        "driving_passages": worst_passages,
        "removal": removal,
        "cleanliness": clean,
        "findings": findings,
    }
