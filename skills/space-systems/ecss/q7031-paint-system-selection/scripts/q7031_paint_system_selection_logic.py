"""Selection of a primer and topcoat pairing for a substrate, environment and thermal role.

Anchor: ECSS-Q-ST-70-31C materials clause -- choosing which paint system goes
on a given item, given what it is made of, what it will fly through and what
thermo-optical job the finish has to do. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Screen every candidate system for hard incompatibility: a primer chemistry
   the substrate does not accept, a topcoat the primer does not accept, and an
   environment the system is not rated for. A screened-out candidate is named
   with its reason rather than scored low and quietly ranked last.
2. Degrade the beginning-of-life solar absorptance over the mission ultraviolet
   dose to an end-of-life value, because the thermal role has to hold at the
   end of life, not on the day the item is painted.
3. Score each surviving candidate on how close its end-of-life absorptance and
   its absorptance-to-emittance ratio sit to the thermal role's targets, with
   thermal-cycle and atomic-oxygen margin folded in.
4. Rank, break an exact tie deterministically on the candidate name, and return
   the selection with every rejection reason attached.
"""

import math

__all__ = [
    "SCORE_TOLERANCE",
    "SUBSTRATE_PRIMER_COMPATIBILITY",
    "PRIMER_TOPCOAT_COMPATIBILITY",
    "THERMAL_ROLES",
    "REJECTION_REASONS",
    "normalize_key",
    "primer_accepts_substrate",
    "topcoat_accepts_primer",
    "end_of_life_absorptance",
    "absorptance_emittance_ratio",
    "environment_findings",
    "thermal_role_targets",
    "score_candidate",
    "select_paint_system",
]

# Scores are sums of ratios; two genuinely equal candidates can differ by a few
# ULPs. Treat anything inside this as a tie and break it deterministically.
SCORE_TOLERANCE = 1e-12

# Which primer chemistries bond to which substrates.
SUBSTRATE_PRIMER_COMPATIBILITY = {
    "aluminium-alloy": ("epoxy-polyamide", "epoxy-polyamine", "silicate"),
    "titanium-alloy": ("epoxy-polyamide", "epoxy-polyamine"),
    "stainless-steel": ("epoxy-polyamide", "epoxy-polyamine", "silicate"),
    "magnesium-alloy": ("epoxy-polyamide",),
    "cfrp-laminate": ("epoxy-polyamine", "polyurethane-primer"),
    "gfrp-laminate": ("epoxy-polyamine", "polyurethane-primer"),
}

# Which topcoat chemistries are qualified over which primers.
PRIMER_TOPCOAT_COMPATIBILITY = {
    "epoxy-polyamide": ("polyurethane", "silicone", "inorganic-silicate"),
    "epoxy-polyamine": ("polyurethane", "silicone"),
    "silicate": ("inorganic-silicate", "silicone"),
    "polyurethane-primer": ("polyurethane",),
}

# Thermal roles and their (target absorptance, target absorptance/emittance).
THERMAL_ROLES = {
    "radiator-cold-surface": (0.15, 0.18),
    "solar-absorber-warm-surface": (0.90, 1.05),
    "internal-black-surface": (0.95, 1.00),
    "neutral-structural-finish": (0.45, 0.55),
}

REJECTION_REASONS = (
    "primer-not-compatible-with-substrate",
    "topcoat-not-qualified-over-primer",
    "atomic-oxygen-fluence-over-rating",
    "ultraviolet-dose-over-rating",
    "thermal-cycle-range-over-rating",
)


def normalize_key(value, label):
    """Return a trimmed lower-case key, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def _unit_fraction(value, label):
    v = _non_negative(value, label)
    if v > 1.0:
        raise ValueError("%s must not exceed 1.0, got %g" % (label, v))
    return v


def primer_accepts_substrate(primer, substrate):
    """Return True when the primer chemistry bonds to the substrate."""
    p = normalize_key(primer, "primer")
    s = normalize_key(substrate, "substrate")
    if s not in SUBSTRATE_PRIMER_COMPATIBILITY:
        raise ValueError("substrate '%s' has no compatibility data" % s)
    return p in SUBSTRATE_PRIMER_COMPATIBILITY[s]


def topcoat_accepts_primer(topcoat, primer):
    """Return True when the topcoat is qualified over that primer."""
    t = normalize_key(topcoat, "topcoat")
    p = normalize_key(primer, "primer")
    if p not in PRIMER_TOPCOAT_COMPATIBILITY:
        raise ValueError("primer '%s' has no compatibility data" % p)
    return t in PRIMER_TOPCOAT_COMPATIBILITY[p]


def end_of_life_absorptance(alpha_bol, degradation_per_1000_esh, equivalent_sun_hours):
    """Return the ultraviolet-degraded solar absorptance at end of life."""
    alpha = _unit_fraction(alpha_bol, "alpha_bol")
    rate = _non_negative(degradation_per_1000_esh, "degradation_per_1000_esh")
    esh = _non_negative(equivalent_sun_hours, "equivalent_sun_hours")
    grown = alpha + rate * (esh / 1000.0)
    return grown if grown < 1.0 else 1.0


def absorptance_emittance_ratio(alpha, epsilon):
    """Return the absorptance-to-emittance ratio of a finish."""
    a = _unit_fraction(alpha, "alpha")
    e = _positive(epsilon, "epsilon")
    if e > 1.0:
        raise ValueError("epsilon must not exceed 1.0, got %g" % e)
    return a / e


def environment_findings(candidate, environment):
    """Return the environment ratings the candidate does not meet."""
    if not isinstance(candidate, dict) or not isinstance(environment, dict):
        raise ValueError("candidate and environment must both be mappings")
    findings = []
    pairs = (
        ("atomic_oxygen_fluence", "atomic_oxygen_rating", "atomic-oxygen-fluence-over-rating"),
        ("equivalent_sun_hours", "ultraviolet_rating_esh", "ultraviolet-dose-over-rating"),
        ("thermal_cycle_range_k", "thermal_cycle_rating_k", "thermal-cycle-range-over-rating"),
    )
    for env_key, cand_key, reason in pairs:
        if env_key not in environment or cand_key not in candidate:
            continue
        demand = _non_negative(environment[env_key], env_key)
        rating = _non_negative(candidate[cand_key], cand_key)
        if demand > rating and not math.isclose(demand, rating, rel_tol=1e-12, abs_tol=0.0):
            findings.append(reason)
    return findings


def thermal_role_targets(role):
    """Return the (target absorptance, target alpha/epsilon) of a thermal role."""
    key = normalize_key(role, "thermal role")
    if key not in THERMAL_ROLES:
        raise ValueError("thermal role '%s' is not one of %s"
                         % (key, sorted(THERMAL_ROLES)))
    return THERMAL_ROLES[key]


def score_candidate(candidate, requirement):
    """Return the scored record of one candidate, or its rejection reasons."""
    if not isinstance(candidate, dict) or not isinstance(requirement, dict):
        raise ValueError("candidate and requirement must both be mappings")
    for key in ("name", "primer", "topcoat", "alpha_bol", "epsilon"):
        if key not in candidate:
            raise ValueError("candidate missing required key '%s'" % key)
    for key in ("substrate", "thermal_role"):
        if key not in requirement:
            raise ValueError("requirement missing required key '%s'" % key)
    name = normalize_key(candidate["name"], "candidate name")
    reasons = []
    if not primer_accepts_substrate(candidate["primer"], requirement["substrate"]):
        reasons.append("primer-not-compatible-with-substrate")
    if not topcoat_accepts_primer(candidate["topcoat"], candidate["primer"]):
        reasons.append("topcoat-not-qualified-over-primer")
    reasons.extend(environment_findings(candidate, requirement.get("environment", {})))
    alpha_eol = end_of_life_absorptance(
        candidate["alpha_bol"],
        candidate.get("uv_degradation_per_1000_esh", 0.0),
        requirement.get("environment", {}).get("equivalent_sun_hours", 0.0),
    )
    ratio = absorptance_emittance_ratio(alpha_eol, candidate["epsilon"])
    target_alpha, target_ratio = thermal_role_targets(requirement["thermal_role"])
    score = abs(alpha_eol - target_alpha) + abs(ratio - target_ratio)
    return {
        "name": name,
        "alpha_eol": alpha_eol,
        "ratio": ratio,
        "score": score,
        "rejected": bool(reasons),
        "reasons": reasons,
    }


def select_paint_system(candidates, requirement):
    """Return the ranked selection for a requirement, with every rejection named."""
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("at least one candidate paint system is needed")
    scored = [score_candidate(c, requirement) for c in candidates]
    names = [rec["name"] for rec in scored]
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be unique")
    viable = [rec for rec in scored if not rec["rejected"]]
    rejected = [rec for rec in scored if rec["rejected"]]
    viable.sort(key=lambda rec: (round(rec["score"], 12), rec["name"]))
    return {
        "selected": viable[0]["name"] if viable else None,
        "ranked": viable,
        "rejected": rejected,
    }
