#!/usr/bin/env python3
"""Electron-seeding general provisions (ECSS-E-ST-20-01C clause 6.5.1).

Deterministic, offline, stdlib-only decision logic for the general seeding
provisions of a multipaction test campaign.  Paraphrased engineering
procedure only -- no standard text is reproduced.

Decision chain implemented here:

1. Categorize the seed-electron access of a critical radio-frequency gap of
   the flight-representative article: an unobstructed line-of-sight path to
   the seed source, a coupling aperture large enough and shielded little
   enough for seed electrons to enter, or an enclosed gap beyond reach.
2. Pick the seeding route from that category: seed the article itself, or
   substitute a dedicated breadboard / development model that reproduces the
   gap and is open to the seed source.
3. When a substitute is used, score its representativeness attribute by
   attribute against the article gap (dimension, drive frequency, surface
   roughness, base material, surface coating, gap geometry).
4. Confirm the substitute is itself reachable by the seed source and that
   its seeding effectiveness was demonstrated.
5. Aggregate findings per gap and across the campaign; the provision is met
   only when no finding remains.
"""

import math

REL_TOL = 1e-9
ABS_TOL = 1e-12

MIN_APERTURE_MM2 = 1.0
MAX_SHIELD_ATTENUATION_DB = 20.0

ACCESS_DIRECT = "direct-seedable"
ACCESS_APERTURE = "aperture-seedable"
ACCESS_BLOCKED = "not-seedable"

ROUTE_ARTICLE = "seed-flight-article"
ROUTE_SUBSTITUTE = "dedicated-breadboard"

SEEDABLE = (ACCESS_DIRECT, ACCESS_APERTURE)

GAP_GEOMETRIES = (
    "parallel-plate",
    "coaxial-gap",
    "waveguide-iris",
    "microstrip-edge",
    "dielectric-loaded-gap",
)

SUBSTITUTE_MODEL_TYPES = (
    "breadboard",
    "development-model",
    "engineering-model",
    "dedicated-test-piece",
)

NUMERIC_ATTRIBUTES = (
    ("gap_height_mm", 0.02),
    ("drive_frequency_ghz", 0.05),
    ("surface_roughness_um", 0.30),
)

CATEGORICAL_ATTRIBUTES = ("base_material", "surface_coating", "gap_geometry")


# --------------------------------------------------------------------------
# numeric guards -- absorb representation error at a limit, never widen it
# --------------------------------------------------------------------------
def _at_least(value, limit):
    """True when value meets limit, tolerating float representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _at_most(value, limit):
    """True when value stays within limit, tolerating representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


# --------------------------------------------------------------------------
# input validation
# --------------------------------------------------------------------------
def _require_mapping(obj, label):
    if not isinstance(obj, dict):
        raise ValueError("%s must be a mapping, got %s" % (label, type(obj).__name__))
    return obj


def _number(mapping, key, label):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s field '%s' must be a real number" % (label, key))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s field '%s' must be finite" % (label, key))
    return value


def _non_negative(mapping, key, label):
    value = _number(mapping, key, label)
    if value < 0.0:
        raise ValueError("%s field '%s' cannot be negative" % (label, key))
    return value


def _positive(mapping, key, label):
    value = _number(mapping, key, label)
    if value <= 0.0:
        raise ValueError("%s field '%s' must be greater than zero" % (label, key))
    return value


def _flag(mapping, key, label):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    value = mapping[key]
    if not isinstance(value, bool):
        raise ValueError("%s field '%s' must be true or false" % (label, key))
    return value


def _text(mapping, key, label, allowed=None):
    _require_mapping(mapping, label)
    if key not in mapping:
        raise ValueError("%s is missing required field '%s'" % (label, key))
    value = mapping[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s field '%s' must be a non-empty string" % (label, key))
    value = value.strip().lower()
    if allowed is not None and value not in allowed:
        raise ValueError("%s field '%s' holds an unrecognised value '%s'" % (label, key, value))
    return value


# --------------------------------------------------------------------------
# step 1 -- seed-electron access of a gap
# --------------------------------------------------------------------------
def categorize_seed_access(gap, label="gap"):
    """Return the seed-electron access category of one radio-frequency gap.

    A gap with an unobstructed view of the source is directly seedable.  A
    shielded gap is still seedable through a coupling aperture when the open
    area meets MIN_APERTURE_MM2 and the intervening structure attenuates the
    seed flux by no more than MAX_SHIELD_ATTENUATION_DB.  Anything else is
    enclosed beyond the reach of the source.
    """
    _require_mapping(gap, label)
    line_of_sight = _flag(gap, "line_of_sight", label)
    aperture = _non_negative(gap, "aperture_area_mm2", label)
    attenuation = _non_negative(gap, "shield_attenuation_db", label)
    if line_of_sight:
        return ACCESS_DIRECT
    if _at_least(aperture, MIN_APERTURE_MM2) and _at_most(
        attenuation, MAX_SHIELD_ATTENUATION_DB
    ):
        return ACCESS_APERTURE
    return ACCESS_BLOCKED


def seeding_route(access_category):
    """Map an access category onto the seeding route it obliges."""
    if not isinstance(access_category, str) or not access_category.strip():
        raise ValueError("access category must be a non-empty string")
    category = access_category.strip().lower()
    if category in SEEDABLE:
        return ROUTE_ARTICLE
    if category == ACCESS_BLOCKED:
        return ROUTE_SUBSTITUTE
    raise ValueError("unknown seed-access category '%s'" % category)


# --------------------------------------------------------------------------
# step 2 -- representativeness of a substitute model
# --------------------------------------------------------------------------
def relative_deviation(reference, candidate):
    """Fractional deviation of a candidate value from a reference value."""
    for name, value in (("reference", reference), ("candidate", candidate)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % name)
        if math.isnan(float(value)) or math.isinf(float(value)):
            raise ValueError("%s must be finite" % name)
    reference = float(reference)
    candidate = float(candidate)
    if reference <= 0.0:
        raise ValueError("reference value must be greater than zero")
    if candidate <= 0.0:
        raise ValueError("candidate value must be greater than zero")
    return abs(candidate - reference) / reference


def _resolve_tolerances(overrides):
    limits = dict(NUMERIC_ATTRIBUTES)
    if overrides is None:
        return limits
    _require_mapping(overrides, "tolerance overrides")
    for key, value in overrides.items():
        if key not in limits:
            raise ValueError("tolerance override names unknown attribute '%s'" % key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("tolerance for '%s' must be a real number" % key)
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            raise ValueError("tolerance for '%s' must be finite" % key)
        if value <= 0.0:
            raise ValueError("tolerance for '%s' must be greater than zero" % key)
        limits[key] = value
    return limits


def evaluate_representativeness(article_gap, substitute_gap, tolerances=None):
    """Compare a substitute gap against the article gap, attribute by attribute."""
    _require_mapping(article_gap, "article gap")
    _require_mapping(substitute_gap, "substitute gap")
    limits = _resolve_tolerances(tolerances)
    records = []
    mismatches = []
    for key, _default in NUMERIC_ATTRIBUTES:
        reference = _positive(article_gap, key, "article gap")
        candidate = _positive(substitute_gap, key, "substitute gap")
        deviation = relative_deviation(reference, candidate)
        within = _at_most(deviation, limits[key])
        records.append(
            {
                "attribute": key,
                "kind": "numeric",
                "article": reference,
                "substitute": candidate,
                "deviation": deviation,
                "tolerance": limits[key],
                "within": within,
            }
        )
        if not within:
            mismatches.append(key)
    for key in CATEGORICAL_ATTRIBUTES:
        allowed = GAP_GEOMETRIES if key == "gap_geometry" else None
        reference = _text(article_gap, key, "article gap", allowed)
        candidate = _text(substitute_gap, key, "substitute gap", allowed)
        within = reference == candidate
        records.append(
            {
                "attribute": key,
                "kind": "categorical",
                "article": reference,
                "substitute": candidate,
                "within": within,
            }
        )
        if not within:
            mismatches.append(key)
    return {
        "attributes": records,
        "mismatches": mismatches,
        "representative": not mismatches,
    }


# --------------------------------------------------------------------------
# step 3 -- the substitute must itself be open to the seed source
# --------------------------------------------------------------------------
def assess_substitute_seedability(substitute, label="substitute"):
    """Check that a substitute model can be seeded and was shown to be seeded."""
    _require_mapping(substitute, label)
    model_type = _text(substitute, "model_type", label, SUBSTITUTE_MODEL_TYPES)
    gap = substitute.get("gap")
    _require_mapping(gap, label + " gap")
    access = categorize_seed_access(gap, label + " gap")
    verified = _flag(substitute, "seeding_effectiveness_verified", label)
    findings = []
    if access == ACCESS_BLOCKED:
        findings.append("substitute-not-seedable")
    if not verified:
        findings.append("substitute-seeding-effectiveness-unverified")
    return {
        "model_type": model_type,
        "access": access,
        "effectiveness_verified": verified,
        "findings": findings,
    }


# --------------------------------------------------------------------------
# step 4 -- per-gap provision assessment
# --------------------------------------------------------------------------
def assess_seeding_provisions(case, tolerances=None):
    """Decide how the seeding provision is discharged for one critical gap."""
    _require_mapping(case, "case")
    gap_id = _text(case, "gap_id", "case")
    article_gap = case.get("article_gap")
    _require_mapping(article_gap, "article gap")
    access = categorize_seed_access(article_gap, "article gap")
    route = seeding_route(access)
    substitute = case.get("substitute")
    findings = []
    representativeness = None
    substitute_report = None
    if route == ROUTE_ARTICLE:
        if substitute is not None:
            findings.append("substitute-substitution-unjustified")
    else:
        if substitute is None:
            findings.append("no-seeded-path-to-critical-gap")
        else:
            substitute_report = assess_substitute_seedability(substitute)
            findings.extend(substitute_report["findings"])
            representativeness = evaluate_representativeness(
                article_gap, substitute["gap"], tolerances
            )
            for attribute in representativeness["mismatches"]:
                findings.append("substitute-not-representative:%s" % attribute)
    return {
        "gap_id": gap_id,
        "access": access,
        "route": route,
        "substitute": substitute_report,
        "representativeness": representativeness,
        "findings": findings,
        "compliant": not findings,
    }


def summarize_campaign(cases, tolerances=None):
    """Roll per-gap provision assessments up to a campaign verdict."""
    if not isinstance(cases, (list, tuple)):
        raise ValueError("cases must be a list of gap assessments")
    if not cases:
        raise ValueError("cases must contain at least one critical gap")
    results = [assess_seeding_provisions(case, tolerances) for case in cases]
    seen = set()
    for result in results:
        if result["gap_id"] in seen:
            raise ValueError("duplicate gap identifier '%s'" % result["gap_id"])
        seen.add(result["gap_id"])
    open_findings = [
        "%s:%s" % (r["gap_id"], f) for r in results for f in r["findings"]
    ]
    return {
        "results": results,
        "gap_count": len(results),
        "substitute_count": sum(1 for r in results if r["route"] == ROUTE_SUBSTITUTE),
        "open_findings": open_findings,
        "compliant": not open_findings,
    }
