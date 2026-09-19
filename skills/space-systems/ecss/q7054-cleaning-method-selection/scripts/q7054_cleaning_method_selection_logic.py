#!/usr/bin/env python3
"""Choosing an ultracleaning method for one part.

Anchor: ECSS-Q-ST-70-54C methods clause. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Six routes are in general use for ultraclean work — precision solvent
applied by wipe or by immersion, aqueous detergent with ultrasonic
agitation, carbon-dioxide snow, plasma, and ultraviolet-ozone — and they
are not interchangeable. Each is good at one family of contaminant, each
damages some substrates, and each reaches only the geometry its transport
mechanism can reach.

The choice runs as hard screens first, then a score:

    screens   substrate compatibility, geometry reach, whether the route
              removes the contaminant at all, and whether it can hold the
              particulate level and the residue allowance asked for. A
              route that fails any screen is out with the reason, not
              carried forward with a low score.

    score     removal effectiveness for the contaminant actually present,
              plus the margin the route has on each ladder, minus a
              penalty for aggressiveness so an over-capable route does
              not win a job a gentler one closes.

The rejected list matters as much as the ranking: it is what stops the
same unsuitable route being proposed again at the next review.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CONTAMINANT_TYPES = (
    "particulate",
    "thin-organic-film",
    "heavy-organic-soil",
    "ionic-residue",
    "adsorbed-hydrocarbon",
)

GEOMETRIES = ("open-surface", "blind-hole", "internal-passage", "complex-assembly")

SUBSTRATES = (
    "aluminium-alloy",
    "stainless-steel",
    "titanium-alloy",
    "magnesium-alloy",
    "polymer-composite",
    "optical-glass",
    "silver-coating",
    "gold-coating",
)

METHOD_CATALOGUE = {
    "precision-solvent-wipe": {
        "removal": {
            "particulate": 0.50,
            "thin-organic-film": 0.80,
            "heavy-organic-soil": 0.60,
            "ionic-residue": 0.20,
            "adsorbed-hydrocarbon": 0.50,
        },
        "reaches": frozenset({"open-surface"}),
        "incompatible_substrates": frozenset(),
        "achievable_particulate_level_um": 300.0,
        "achievable_nvr_mg_per_01m2": 1.00,
        "aggressiveness": 1,
    },
    "carbon-dioxide-snow": {
        "removal": {
            "particulate": 0.90,
            "thin-organic-film": 0.60,
            "heavy-organic-soil": 0.20,
            "ionic-residue": 0.00,
            "adsorbed-hydrocarbon": 0.40,
        },
        "reaches": frozenset({"open-surface"}),
        "incompatible_substrates": frozenset({"polymer-composite"}),
        "achievable_particulate_level_um": 100.0,
        "achievable_nvr_mg_per_01m2": 0.50,
        "aggressiveness": 2,
    },
    "ultraviolet-ozone": {
        "removal": {
            "particulate": 0.00,
            "thin-organic-film": 0.95,
            "heavy-organic-soil": 0.10,
            "ionic-residue": 0.00,
            "adsorbed-hydrocarbon": 0.90,
        },
        "reaches": frozenset({"open-surface"}),
        "incompatible_substrates": frozenset({"silver-coating", "magnesium-alloy"}),
        "achievable_particulate_level_um": 500.0,
        "achievable_nvr_mg_per_01m2": 0.02,
        "aggressiveness": 2,
    },
    "aqueous-detergent-ultrasonic": {
        "removal": {
            "particulate": 0.95,
            "thin-organic-film": 0.70,
            "heavy-organic-soil": 0.85,
            "ionic-residue": 0.95,
            "adsorbed-hydrocarbon": 0.50,
        },
        "reaches": frozenset(
            {"open-surface", "blind-hole", "internal-passage", "complex-assembly"}
        ),
        "incompatible_substrates": frozenset(
            {"magnesium-alloy", "optical-glass", "silver-coating"}
        ),
        "achievable_particulate_level_um": 50.0,
        "achievable_nvr_mg_per_01m2": 0.10,
        "aggressiveness": 3,
    },
    "precision-solvent-immersion": {
        "removal": {
            "particulate": 0.70,
            "thin-organic-film": 0.90,
            "heavy-organic-soil": 0.90,
            "ionic-residue": 0.30,
            "adsorbed-hydrocarbon": 0.70,
        },
        "reaches": frozenset(
            {"open-surface", "blind-hole", "internal-passage", "complex-assembly"}
        ),
        "incompatible_substrates": frozenset({"polymer-composite"}),
        "achievable_particulate_level_um": 25.0,
        "achievable_nvr_mg_per_01m2": 0.05,
        "aggressiveness": 4,
    },
    "plasma": {
        "removal": {
            "particulate": 0.10,
            "thin-organic-film": 0.98,
            "heavy-organic-soil": 0.30,
            "ionic-residue": 0.00,
            "adsorbed-hydrocarbon": 0.95,
        },
        "reaches": frozenset({"open-surface", "blind-hole", "complex-assembly"}),
        "incompatible_substrates": frozenset({"polymer-composite", "silver-coating"}),
        "achievable_particulate_level_um": 100.0,
        "achievable_nvr_mg_per_01m2": 0.01,
        "aggressiveness": 5,
    },
}

WEIGHT_REMOVAL = 6.0
WEIGHT_PARTICULATE_MARGIN = 1.5
WEIGHT_RESIDUE_MARGIN = 1.5
WEIGHT_AGGRESSIVENESS = 0.4
MARGIN_DECADE_CAP = 2.0

REJECT_INCOMPATIBLE = "substrate-incompatible"
REJECT_UNREACHABLE = "geometry-unreachable"
REJECT_INEFFECTIVE = "contaminant-not-removed"
REJECT_LEVEL = "particulate-level-unreachable"
REJECT_RESIDUE = "residue-allowance-unreachable"

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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(sorted(allowed)), value)
        )
    return value


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _clamp(value, low, high):
    return max(low, min(high, value))


def validate_request(request):
    """Check a method-selection request describes one real cleaning job."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping, got %r" % (request,))
    contaminant = _require_choice(
        "contaminant", request.get("contaminant"), CONTAMINANT_TYPES
    )
    substrate = _require_choice("substrate", request.get("substrate"), SUBSTRATES)
    geometry = _require_choice("geometry", request.get("geometry"), GEOMETRIES)
    level = _require_positive(
        "required_particulate_level_um", request.get("required_particulate_level_um")
    )
    residue = _require_positive(
        "required_nvr_mg_per_01m2", request.get("required_nvr_mg_per_01m2")
    )
    return {
        "contaminant": contaminant,
        "substrate": substrate,
        "geometry": geometry,
        "required_particulate_level_um": level,
        "required_nvr_mg_per_01m2": residue,
    }


def screen_method(name, request):
    """Hard screens for one route: None when it survives, else the reason."""
    if name not in METHOD_CATALOGUE:
        raise ValueError("unknown method %r" % (name,))
    checked = validate_request(request)
    spec = METHOD_CATALOGUE[name]
    if checked["substrate"] in spec["incompatible_substrates"]:
        return REJECT_INCOMPATIBLE
    if checked["geometry"] not in spec["reaches"]:
        return REJECT_UNREACHABLE
    if spec["removal"][checked["contaminant"]] <= 0.0:
        return REJECT_INEFFECTIVE
    if not _at_most(
        spec["achievable_particulate_level_um"],
        checked["required_particulate_level_um"],
    ):
        return REJECT_LEVEL
    if not _at_most(
        spec["achievable_nvr_mg_per_01m2"], checked["required_nvr_mg_per_01m2"]
    ):
        return REJECT_RESIDUE
    return None


def method_score(name, request):
    """Score a route that has already survived the screens."""
    reason = screen_method(name, request)
    if reason is not None:
        raise ValueError("method %s does not survive the screens: %s" % (name, reason))
    checked = validate_request(request)
    spec = METHOD_CATALOGUE[name]
    removal = spec["removal"][checked["contaminant"]]
    level_margin = _clamp(
        math.log10(
            checked["required_particulate_level_um"]
            / spec["achievable_particulate_level_um"]
        ),
        0.0,
        MARGIN_DECADE_CAP,
    )
    residue_margin = _clamp(
        math.log10(
            checked["required_nvr_mg_per_01m2"] / spec["achievable_nvr_mg_per_01m2"]
        ),
        0.0,
        MARGIN_DECADE_CAP,
    )
    return (
        WEIGHT_REMOVAL * removal
        + WEIGHT_PARTICULATE_MARGIN * level_margin
        + WEIGHT_RESIDUE_MARGIN * residue_margin
        - WEIGHT_AGGRESSIVENESS * spec["aggressiveness"]
    )


def rank_cleaning_methods(request):
    """Ranked survivors and, just as usefully, why each route was dropped."""
    checked = validate_request(request)
    ranked = []
    rejected = []
    for name in sorted(METHOD_CATALOGUE):
        reason = screen_method(name, checked)
        if reason is not None:
            rejected.append({"method": name, "reason": reason})
            continue
        spec = METHOD_CATALOGUE[name]
        ranked.append(
            {
                "method": name,
                "score": method_score(name, checked),
                "removal_effectiveness": spec["removal"][checked["contaminant"]],
                "aggressiveness": spec["aggressiveness"],
            }
        )
    ranked.sort(key=lambda entry: (-entry["score"], entry["method"]))
    findings = []
    if not ranked:
        findings.append(
            "no catalogued route survives the screens for %s on %s in a %s; "
            "relax the geometry by disassembly, change the substrate finish, or "
            "qualify a route outside the catalogue"
            % (checked["contaminant"], checked["substrate"], checked["geometry"])
        )
    elif len(ranked) == 1:
        findings.append(
            "only %s survives; there is no fallback route if it is withdrawn "
            "or its agent supply changes" % ranked[0]["method"]
        )
    if ranked and ranked[0]["removal_effectiveness"] < 0.5:
        findings.append(
            "the leading route removes %s only weakly; a preceding step against "
            "that contaminant is likely to be needed"
            % checked["contaminant"]
        )
    return {
        "request": checked,
        "ranked": ranked,
        "rejected": rejected,
        "recommended": ranked[0]["method"] if ranked else None,
        "findings": findings,
    }
