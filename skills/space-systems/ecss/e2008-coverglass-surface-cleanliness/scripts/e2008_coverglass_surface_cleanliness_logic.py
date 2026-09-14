#!/usr/bin/env python3
"""Surface cleanliness screen for delivered coverglasses.

Anchor: ECSS-E-ST-20-08C clause 8.7.1.3.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The requirement is short -- a delivered coverglass carries no soiling and
no contamination on either optical surface -- and almost every way a
campaign gets it wrong follows from reading it too quickly.

Both surfaces count. A coverglass has an outer optical surface that faces
the environment and an inner one that ends up in the bond line against the
cell, and the inner surface is the one that stops being inspectable the
moment the assembly is built. A record covering one surface answers half
the question, so an item with a single surface screened is held open no
matter how clean that surface was.

Soiling and contamination are not the same finding. Soiling comes off: a
particle, a handling film, a fingerprint. It is not a property of the
glass, it does not count toward any permanent-obscuration allowance, and
the item goes back for cleaning and a second look. Contamination is what
survives the clean -- an etched stain, a baked residue, a deposit bonded
into the coating -- and it stays in the optical path for the life of the
array.

Because soiling is curable, a cleaned item is not closed by the cleaning.
It is closed by the re-inspection after the cleaning, and a record that
shows a clean instruction with no post-clean result is an open item, not
a passing one.

Individually small permanent deposits still accumulate. A cumulative
obscured-area fraction per surface catches the coverglass that passed
every single-deposit limit and is nevertheless hazy, and an oversize
particle count catches the surface that is peppered rather than dirty.

The allowances below are declared policy, not physical constants: a
project substitutes the values its cell assembly control drawing fixes.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SURFACE_OUTER = "outer-optical"
SURFACE_INNER = "inner-optical"
REQUIRED_SURFACES = (SURFACE_OUTER, SURFACE_INNER)

DEPOSIT_PARTICULATE = "particulate"
DEPOSIT_FILM = "film"
DEPOSIT_FINGERPRINT = "fingerprint"
DEPOSIT_STAIN = "stain"
RECOGNISED_DEPOSIT_KINDS = (
    DEPOSIT_PARTICULATE,
    DEPOSIT_FILM,
    DEPOSIT_FINGERPRINT,
    DEPOSIT_STAIN,
)

ACCEPT = "accept"
CLEAN_AND_REINSPECT = "clean-and-reinspect"
REFER_FOR_REVIEW = "refer-for-review"
REJECT = "reject"

DISPOSITION_SEVERITY = {
    ACCEPT: 0,
    CLEAN_AND_REINSPECT: 1,
    REFER_FOR_REVIEW: 2,
    REJECT: 3,
}

LOT_ACCEPTED = "lot-cleanliness-accepted"
LOT_OUTSTANDING = "lot-cleanliness-outstanding"
LOT_RECORD_INCOMPLETE = "lot-record-incomplete"

DEFAULT_CLEANLINESS_POLICY = {
    "max_obscured_area_fraction": 0.005,
    "oversize_particle_diameter_mm": 0.10,
    "max_oversize_particle_count": 3,
    "max_single_deposit_area_mm2": 0.05,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-18


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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_cleanliness_policy(policy):
    """Check a cleanliness policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    fraction = _require_positive(
        "max_obscured_area_fraction", policy.get("max_obscured_area_fraction")
    )
    if fraction >= 1.0:
        raise ValueError(
            "max_obscured_area_fraction %g allows the whole optical surface to "
            "be obscured, which is not a cleanliness allowance" % fraction
        )
    _require_positive(
        "oversize_particle_diameter_mm",
        policy.get("oversize_particle_diameter_mm"),
    )
    count = policy.get("max_oversize_particle_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError(
            "max_oversize_particle_count must be a non-negative integer, got %r"
            % (count,)
        )
    _require_positive(
        "max_single_deposit_area_mm2", policy.get("max_single_deposit_area_mm2")
    )
    return policy


def deposit_area_mm2(deposit):
    """Obscured area of one deposit, from its diameter or its declared area."""
    if not isinstance(deposit, dict):
        raise ValueError("deposit must be a mapping, got %r" % (deposit,))
    kind = _require_label("deposit kind", deposit.get("kind"))
    if kind not in RECOGNISED_DEPOSIT_KINDS:
        raise ValueError(
            "unknown deposit kind %r; recognised kinds are %s"
            % (kind, ", ".join(RECOGNISED_DEPOSIT_KINDS))
        )
    if kind == DEPOSIT_PARTICULATE:
        diameter = _require_positive(
            "particle diameter_mm", deposit.get("diameter_mm")
        )
        return math.pi * 0.25 * diameter * diameter
    return _require_positive("deposit area_mm2", deposit.get("area_mm2"))


def deposit_is_removable(deposit):
    """True when the deposit is soiling that cleaning takes off."""
    if not isinstance(deposit, dict):
        raise ValueError("deposit must be a mapping, got %r" % (deposit,))
    return _require_flag("deposit removable", deposit.get("removable"))


def disposition_deposit(deposit, policy=DEFAULT_CLEANLINESS_POLICY):
    """Disposition one deposit, with the reason when it leaves the accept band."""
    validate_cleanliness_policy(policy)
    area = deposit_area_mm2(deposit)
    kind = _require_label("deposit kind", deposit.get("kind"))
    if deposit_is_removable(deposit):
        return (
            CLEAN_AND_REINSPECT,
            "%s soiling of %.4g mm2 comes off; the item is cleaned and looked "
            "at again rather than dispositioned on this record" % (kind, area),
        )
    limit = float(policy["max_single_deposit_area_mm2"])
    if _at_most(area, limit):
        return (
            REFER_FOR_REVIEW,
            "%s contamination of %.4g mm2 survives cleaning and stays in the "
            "optical path, inside the %.4g mm2 single-deposit allowance"
            % (kind, area, limit),
        )
    return (
        REJECT,
        "%s contamination of %.4g mm2 survives cleaning and is above the %.4g "
        "mm2 single-deposit allowance" % (kind, area, limit),
    )


def permanent_obscured_area_mm2(deposits):
    """Obscured area that cleaning will not recover, over one surface."""
    if not isinstance(deposits, (list, tuple)):
        raise ValueError("deposits must be a sequence of deposit records")
    total = 0.0
    for deposit in deposits:
        if not deposit_is_removable(deposit):
            total += deposit_area_mm2(deposit)
    return total


def obscured_area_fraction(deposits, surface_area_mm2):
    """Permanent obscuration as a fraction of the optical surface."""
    area = _require_positive("surface_area_mm2", surface_area_mm2)
    return permanent_obscured_area_mm2(deposits) / area


def oversize_particle_count(deposits, policy=DEFAULT_CLEANLINESS_POLICY):
    """Permanent particles at or above the oversize diameter."""
    validate_cleanliness_policy(policy)
    if not isinstance(deposits, (list, tuple)):
        raise ValueError("deposits must be a sequence of deposit records")
    limit = float(policy["oversize_particle_diameter_mm"])
    count = 0
    for deposit in deposits:
        kind = _require_label("deposit kind", deposit.get("kind"))
        if kind != DEPOSIT_PARTICULATE or deposit_is_removable(deposit):
            continue
        diameter = _require_positive(
            "particle diameter_mm", deposit.get("diameter_mm")
        )
        if _at_least(diameter, limit):
            count += 1
    return count


def worst_disposition(dispositions):
    """The governing disposition of a set: the most severe one present."""
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    worst = ACCEPT
    for disposition in dispositions:
        name = _require_label("disposition", disposition)
        if name not in DISPOSITION_SEVERITY:
            raise ValueError("unknown disposition %r" % (disposition,))
        if DISPOSITION_SEVERITY[name] > DISPOSITION_SEVERITY[worst]:
            worst = name
    return worst


def post_clean_state(surface):
    """What the post-clean re-inspection of one surface says, if it happened."""
    record = surface.get("post_clean_reinspection")
    if record is None:
        return None
    if not isinstance(record, dict):
        raise ValueError(
            "post_clean_reinspection must be a mapping, got %r" % (record,)
        )
    performed = _require_flag(
        "post_clean_reinspection performed", record.get("performed")
    )
    if not performed:
        return None
    return _require_flag(
        "post_clean_reinspection surface_free_of_residue",
        record.get("surface_free_of_residue"),
    )


def assess_surface(surface, policy=DEFAULT_CLEANLINESS_POLICY):
    """Screen one optical surface of one coverglass."""
    validate_cleanliness_policy(policy)
    if not isinstance(surface, dict):
        raise ValueError("surface must be a mapping, got %r" % (surface,))
    name = _require_label("surface", surface.get("surface"))
    if name not in REQUIRED_SURFACES:
        raise ValueError(
            "unknown optical surface %r; the screen covers %s"
            % (name, " and ".join(REQUIRED_SURFACES))
        )
    surface_area = _require_positive(
        "surface_area_mm2", surface.get("surface_area_mm2")
    )
    deposits = surface.get("deposits", ())
    if not isinstance(deposits, (list, tuple)):
        raise ValueError("deposits must be a sequence of deposit records")

    findings = []
    dispositions = []
    removable_seen = False
    for index, deposit in enumerate(deposits, start=1):
        disposition, reason = disposition_deposit(deposit, policy)
        if deposit_is_removable(deposit):
            removable_seen = True
        else:
            dispositions.append(disposition)
            if disposition != ACCEPT:
                findings.append("deposit %d: %s" % (index, reason))

    fraction = obscured_area_fraction(deposits, surface_area)
    allowance = float(policy["max_obscured_area_fraction"])
    if not _at_most(fraction, allowance):
        dispositions.append(REJECT)
        findings.append(
            "permanent obscuration is %.4g per cent of the %s surface, above "
            "the %.4g per cent allowance; every deposit can be inside its own "
            "limit and the surface still be hazy"
            % (fraction * 100.0, name, allowance * 100.0)
        )

    oversize = oversize_particle_count(deposits, policy)
    max_oversize = int(policy["max_oversize_particle_count"])
    if oversize > max_oversize:
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "%d permanent particles reach the oversize diameter against an "
            "allowance of %d on the %s surface" % (oversize, max_oversize, name)
        )

    residue_free = post_clean_state(surface)
    if removable_seen:
        if residue_free is None:
            dispositions.append(CLEAN_AND_REINSPECT)
            findings.append(
                "the %s surface carries removable soiling and no post-clean "
                "re-inspection result; cleaning does not close the item, the "
                "second look does" % name
            )
        elif not residue_free:
            dispositions.append(REFER_FOR_REVIEW)
            findings.append(
                "residue survived the clean on the %s surface, so what was "
                "recorded as soiling is contamination" % name
            )
    elif residue_free is False:
        dispositions.append(REFER_FOR_REVIEW)
        findings.append(
            "the post-clean re-inspection of the %s surface reports residue "
            "that the deposit record does not list" % name
        )

    return {
        "surface": name,
        "surface_area_mm2": surface_area,
        "deposit_count": len(deposits),
        "permanent_obscured_area_mm2": permanent_obscured_area_mm2(deposits),
        "obscured_area_fraction": fraction,
        "oversize_particle_count": oversize,
        "removable_soiling_present": removable_seen,
        "post_clean_residue_free": residue_free,
        "disposition": worst_disposition(dispositions),
        "findings": findings,
    }


def assess_coverglass(item, policy=DEFAULT_CLEANLINESS_POLICY):
    """Screen one delivered coverglass across both of its optical surfaces."""
    validate_cleanliness_policy(policy)
    if not isinstance(item, dict):
        raise ValueError("coverglass item must be a mapping, got %r" % (item,))
    identifier = _require_label("coverglass id", item.get("id"))
    if not identifier:
        raise ValueError("coverglass id must not be blank")
    surfaces = item.get("surfaces")
    if not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError(
            "coverglass %s records no optical surface; the screen needs both"
            % identifier
        )

    findings = []
    results = {}
    for surface in surfaces:
        result = assess_surface(surface, policy)
        if result["surface"] in results:
            raise ValueError(
                "coverglass %s records the %s surface twice"
                % (identifier, result["surface"])
            )
        results[result["surface"]] = result
        for finding in result["findings"]:
            findings.append("%s: %s" % (identifier, finding))

    missing = [name for name in REQUIRED_SURFACES if name not in results]
    complete = not missing
    if missing:
        findings.append(
            "%s: no record for the %s surface; the inner surface disappears "
            "into the bond line once the assembly is built, so a one-sided "
            "screen cannot be completed later"
            % (identifier, " and ".join(missing))
        )

    dispositions = [result["disposition"] for result in results.values()]
    return {
        "id": identifier,
        "surfaces": results,
        "surfaces_screened": tuple(sorted(results)),
        "missing_surfaces": tuple(missing),
        "record_complete": complete,
        "disposition": worst_disposition(dispositions),
        "findings": findings,
    }


def assess_surface_cleanliness(case, policy=DEFAULT_CLEANLINESS_POLICY):
    """Full clause 8.7.1.3.7 cleanliness decision for one delivery lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_cleanliness_policy(policy)

    declared = case.get("declared_coverglass_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_coverglass_count must be a positive integer, got %r"
            % (declared,)
        )
    items = case.get("coverglasses")
    if not isinstance(items, (list, tuple)):
        raise ValueError("case is missing a coverglasses record")
    if not items:
        raise ValueError(
            "no coverglass was screened, so there is no cleanliness evidence"
        )
    if len(items) > declared:
        raise ValueError(
            "%d coverglass records against a declared count of %d; the record "
            "set cannot be larger than the lot" % (len(items), declared)
        )

    findings = []
    results = []
    seen = set()
    for item in items:
        result = assess_coverglass(item, policy)
        if result["id"] in seen:
            raise ValueError("duplicate coverglass id %r in the lot" % result["id"])
        seen.add(result["id"])
        results.append(result)
        findings.extend(result["findings"])

    complete = len(results) == declared and all(r["record_complete"] for r in results)
    if len(results) < declared:
        findings.append(
            "%d of %d declared coverglasses carry a cleanliness record; the "
            "shortfall leaves the lot open however clean the screened items were"
            % (len(results), declared)
        )

    outstanding = tuple(r["id"] for r in results if r["disposition"] != ACCEPT)
    worst = worst_disposition([r["disposition"] for r in results])

    result = {
        "declared_coverglass_count": declared,
        "recorded_coverglass_count": len(results),
        "surfaces_screened": sum(len(r["surfaces"]) for r in results),
        "coverglasses": results,
        "outstanding_ids": outstanding,
        "worst_disposition": worst,
        "record_complete": complete,
        "findings": findings,
    }

    if not complete:
        result["verdict"] = LOT_RECORD_INCOMPLETE
    elif outstanding:
        result["verdict"] = LOT_OUTSTANDING
    else:
        result["verdict"] = LOT_ACCEPTED
    return result
