#!/usr/bin/env python3
"""Material and construction restrictions for Class 3 commercial EEE.

Anchor: ECSS-Q-ST-60-13C clause 6.2.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Class 3 buys a commercial part largely as the maker built it, so the
one thing the buyer still controls is what the part is made of. A
commercial maker optimises finish and encapsulation for a benign
ground environment: a bare tin finish is cheap and solders well, a
cadmium or zinc plate stops rust in a warehouse, a plastic body costs a
fraction of a sealed one. Every one of those choices fails differently
in vacuum, in a thermal cycle, or after a year on a shelf.

Two screens are applied.

The construction screen grades each declared material or construction
against a restriction table. Each entry is one of

    accepted      no restriction on this construction
    conditional   restricted, and admissible only against one of the
                  named mitigations
    prohibited    no mitigation makes it admissible

The encapsulation screen is numeric: a non-hermetic plastic body
absorbs moisture, and the maker's moisture-sensitivity level sets a
floor life -- the hours the part may sit out of a sealed dry pack
before it has to be baked again. Exposure beyond that floor life is an
open action, not a silent pass, because the moisture boils inside the
package at reflow and lifts the die.

The governing item is the worst-graded one, and it is what a buyer has
to change; the rest of the declaration is noise until that is settled.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

RESTRICTION_ACCEPTED = "accepted-construction"
RESTRICTION_CONDITIONAL = "conditionally-acceptable-construction"
RESTRICTION_PROHIBITED = "prohibited-construction"

RESTRICTION_CATEGORIES = (
    RESTRICTION_ACCEPTED,
    RESTRICTION_CONDITIONAL,
    RESTRICTION_PROHIBITED,
)

ITEM_ACCEPTED = "construction-accepted"
ITEM_MITIGATED = "construction-mitigated"
ITEM_UNMITIGATED = "construction-unmitigated"
ITEM_PROHIBITED = "construction-prohibited"

ITEM_SEVERITY = {
    ITEM_ACCEPTED: 0,
    ITEM_MITIGATED: 1,
    ITEM_UNMITIGATED: 2,
    ITEM_PROHIBITED: 3,
}

SCREEN_ACCEPTED = "class-3-construction-accepted"
SCREEN_MITIGATED = "class-3-construction-accepted-with-mitigations"
SCREEN_REJECTED = "class-3-construction-rejected"

MOISTURE_ITEM = "plastic-encapsulation-moisture-exposure"

DEFAULT_RESTRICTION_TABLE = {
    "tin-lead-finish": {
        "category": RESTRICTION_ACCEPTED,
        "mechanism": "alloyed finish does not grow whiskers",
        "mitigations": (),
    },
    "gold-over-nickel-finish": {
        "category": RESTRICTION_ACCEPTED,
        "mechanism": "stable barrier finish",
        "mitigations": (),
    },
    "hermetic-ceramic-package": {
        "category": RESTRICTION_ACCEPTED,
        "mechanism": "sealed cavity keeps moisture out",
        "mitigations": (),
    },
    "pure-tin-finish": {
        "category": RESTRICTION_CONDITIONAL,
        "mechanism": "tin whisker growth shorts adjacent conductors",
        "mitigations": (
            "hot-solder-dip-lead-bearing",
            "reflow-with-lead-bearing-alloy",
            "tin-lead-refinish",
        ),
    },
    "pure-silver-external-finish": {
        "category": RESTRICTION_CONDITIONAL,
        "mechanism": "sulfide tarnish and silver migration across insulation",
        "mitigations": (
            "gold-over-nickel-refinish",
            "conformal-coating-over-finish",
        ),
    },
    "non-hermetic-plastic-encapsulation": {
        "category": RESTRICTION_CONDITIONAL,
        "mechanism": "moisture ingress, package cracking at reflow",
        "mitigations": (
            "dry-pack-and-bake-before-mounting",
            "conformal-coating-after-mounting",
        ),
    },
    "polyvinyl-chloride-insulation": {
        "category": RESTRICTION_CONDITIONAL,
        "mechanism": "outgassing and corrosive decomposition products",
        "mitigations": ("replace-with-fluoropolymer-insulation",),
    },
    "beryllium-oxide-package": {
        "category": RESTRICTION_CONDITIONAL,
        "mechanism": "toxic dust if the package body is broken",
        "mitigations": ("controlled-handling-and-disposal-procedure",),
    },
    "cadmium-plating": {
        "category": RESTRICTION_PROHIBITED,
        "mechanism": "sublimation in vacuum and whisker growth",
        "mitigations": (),
    },
    "zinc-plating": {
        "category": RESTRICTION_PROHIBITED,
        "mechanism": "sublimation in vacuum and whisker growth",
        "mitigations": (),
    },
    "mercury-wetted-contact": {
        "category": RESTRICTION_PROHIBITED,
        "mechanism": "liquid metal migrates and is orientation dependent",
        "mitigations": (),
    },
    "pure-magnesium-structure": {
        "category": RESTRICTION_PROHIBITED,
        "mechanism": "galvanic corrosion against every common finish",
        "mitigations": (),
    },
}

# Hours a part may sit outside a sealed dry pack before it must be
# baked again. None means the level carries no floor life at all.
MOISTURE_FLOOR_LIFE_HOURS = {
    "1": None,
    "2": 8760.0,
    "2a": 672.0,
    "3": 168.0,
    "4": 72.0,
    "5": 48.0,
    "5a": 24.0,
    "6": 0.0,
}

MOISTURE_WITHIN = "within-floor-life"
MOISTURE_ON_LIMIT = "on-floor-life"
MOISTURE_OVER = "over-floor-life"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    An exposure is accumulated from several open intervals while a floor
    life is a single declared number, so an exposure built to land
    exactly on the floor life can sit a few units in the last place
    above it. The floor life is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or _equal(value, limit)


def validate_restriction_table(table):
    """Check a restriction table is well formed before it is used."""
    if not isinstance(table, dict) or not table:
        raise ValueError("restriction table must be a non-empty mapping")
    for item, entry in table.items():
        if not isinstance(item, str) or not item:
            raise ValueError("restriction table key must be a non-empty string")
        if not isinstance(entry, dict):
            raise ValueError("restriction table entry for %s must be a mapping" % item)
        category = entry.get("category")
        if category not in RESTRICTION_CATEGORIES:
            raise ValueError(
                "restriction table entry for %s has an unknown category %r"
                % (item, category)
            )
        mitigations = entry.get("mitigations")
        if not isinstance(mitigations, (tuple, list)):
            raise ValueError(
                "restriction table entry for %s needs a mitigations sequence" % item
            )
        if category == RESTRICTION_CONDITIONAL and not mitigations:
            raise ValueError(
                "conditional entry %s names no mitigation, so nothing can clear it"
                % item
            )
        if category != RESTRICTION_CONDITIONAL and mitigations:
            raise ValueError(
                "entry %s is not conditional yet names mitigations" % item
            )
    return table


def restriction_for(item, table=DEFAULT_RESTRICTION_TABLE):
    """Look one declared material or construction up in the table."""
    validate_restriction_table(table)
    if item not in table:
        raise ValueError(
            "declared construction %r is not in the restriction table; add it "
            "rather than screening it silently" % (item,)
        )
    return table[item]


def accepted_mitigations(item, table=DEFAULT_RESTRICTION_TABLE):
    """Mitigations that clear one restricted construction."""
    return tuple(restriction_for(item, table)["mitigations"])


def assess_construction_item(item, mitigations=(), table=DEFAULT_RESTRICTION_TABLE):
    """Grade one declared material or construction."""
    entry = restriction_for(item, table)
    if isinstance(mitigations, str) or not isinstance(mitigations, (tuple, list, set)):
        raise ValueError(
            "mitigations for %s must be a sequence of names, got %r"
            % (item, mitigations)
        )
    applied = tuple(mitigations)
    allowed = tuple(entry["mitigations"])
    effective = tuple(name for name in applied if name in allowed)
    category = entry["category"]
    if category == RESTRICTION_PROHIBITED:
        verdict = ITEM_PROHIBITED
        detail = "prohibited construction: %s" % entry["mechanism"]
    elif category == RESTRICTION_ACCEPTED:
        verdict = ITEM_ACCEPTED
        detail = "accepted construction"
    elif effective:
        verdict = ITEM_MITIGATED
        detail = "restricted construction cleared by %s" % ", ".join(effective)
    else:
        verdict = ITEM_UNMITIGATED
        detail = (
            "restricted construction with no accepted mitigation applied: %s"
            % entry["mechanism"]
        )
    return {
        "item": item,
        "category": category,
        "verdict": verdict,
        "severity": ITEM_SEVERITY[verdict],
        "mechanism": entry["mechanism"],
        "applied_mitigations": applied,
        "effective_mitigations": effective,
        "accepted_mitigations": allowed,
        "compliant": verdict in (ITEM_ACCEPTED, ITEM_MITIGATED),
        "detail": detail,
    }


def moisture_floor_life_hours(moisture_level):
    """Hours out of a dry pack the maker's level leaves, or None."""
    if moisture_level not in MOISTURE_FLOOR_LIFE_HOURS:
        raise ValueError(
            "moisture_level must be one of %s, got %r"
            % (", ".join(sorted(MOISTURE_FLOOR_LIFE_HOURS)), moisture_level)
        )
    return MOISTURE_FLOOR_LIFE_HOURS[moisture_level]


def assess_moisture_exposure(moisture_level, exposure_hours):
    """Grade time out of a dry pack against the maker's floor life."""
    floor = moisture_floor_life_hours(moisture_level)
    exposure = _require_non_negative("exposure_hours", exposure_hours)
    if floor is None:
        return {
            "item": MOISTURE_ITEM,
            "moisture_level": moisture_level,
            "floor_life_hours": None,
            "exposure_hours": exposure,
            "remaining_hours": None,
            "verdict": MOISTURE_WITHIN,
            "compliant": True,
            "detail": "level carries no floor life; exposure is unrestricted",
        }
    if _equal(exposure, floor):
        verdict = MOISTURE_ON_LIMIT
        detail = "exposure sits exactly on the floor life"
    elif _at_most(exposure, floor):
        verdict = MOISTURE_WITHIN
        detail = "exposure is inside the floor life"
    else:
        verdict = MOISTURE_OVER
        detail = (
            "exposure of %.2f h is past the %.2f h floor life; bake and reseal "
            "before mounting" % (exposure, floor)
        )
    return {
        "item": MOISTURE_ITEM,
        "moisture_level": moisture_level,
        "floor_life_hours": floor,
        "exposure_hours": exposure,
        "remaining_hours": floor - exposure,
        "verdict": verdict,
        "compliant": verdict != MOISTURE_OVER,
        "detail": detail,
    }


def screen_construction(declaration, table=DEFAULT_RESTRICTION_TABLE):
    """Full clause 6.2.2.2 construction screen for one commercial part."""
    validate_restriction_table(table)
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping, got %r" % (declaration,))
    items = declaration.get("items")
    if not isinstance(items, (tuple, list)) or not items:
        raise ValueError("declaration items must be a non-empty sequence")
    mitigations = declaration.get("mitigations", {})
    if not isinstance(mitigations, dict):
        raise ValueError("declaration mitigations must be a mapping of item to names")
    unknown_keys = set(mitigations) - set(items)
    if unknown_keys:
        raise ValueError(
            "mitigations name constructions that were never declared: %s"
            % ", ".join(sorted(unknown_keys))
        )

    graded = [
        assess_construction_item(item, mitigations.get(item, ()), table)
        for item in items
    ]

    moisture = None
    level = declaration.get("moisture_level")
    exposure = declaration.get("exposure_hours")
    if level is not None and exposure is not None:
        moisture = assess_moisture_exposure(level, exposure)
    elif level is not None or exposure is not None:
        raise ValueError(
            "a moisture screen needs both moisture_level and exposure_hours"
        )

    conditional = [g for g in graded if g["category"] == RESTRICTION_CONDITIONAL]
    cleared = [g for g in conditional if g["verdict"] == ITEM_MITIGATED]
    coverage = 1.0 if not conditional else len(cleared) / len(conditional)

    worst = max(g["severity"] for g in graded)
    governing = next(g for g in graded if g["severity"] == worst)

    findings = [
        "%s: %s" % (g["item"], g["detail"]) for g in graded if not g["compliant"]
    ]
    if moisture is not None and not moisture["compliant"]:
        findings.append("%s: %s" % (moisture["item"], moisture["detail"]))

    moisture_ok = moisture is None or moisture["compliant"]
    if worst >= 2 or not moisture_ok:
        verdict = SCREEN_REJECTED
    elif worst == 1:
        verdict = SCREEN_MITIGATED
    else:
        verdict = SCREEN_ACCEPTED

    if not moisture_ok and worst < 2:
        governing_item = MOISTURE_ITEM
        governing_detail = moisture["detail"]
    else:
        governing_item = governing["item"]
        governing_detail = governing["detail"]

    return {
        "verdict": verdict,
        "acceptable": verdict != SCREEN_REJECTED,
        "items": graded,
        "moisture": moisture,
        "restricted_count": len(conditional),
        "prohibited_count": sum(
            1 for g in graded if g["verdict"] == ITEM_PROHIBITED
        ),
        "mitigation_coverage": coverage,
        "governing_item": governing_item,
        "governing_detail": governing_detail,
        "findings": findings,
    }
