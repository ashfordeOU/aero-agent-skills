#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.3.2 environments and design-and-test factors
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
system engineering general requirements standard calls for every
product to have its applicable natural and induced environments
defined across the mission phases it is exposed to, and for a
design-and-test factor to be derived for each applicable environment
from its engineering domain and the product's verification approach
(qualification test, protoflight test, acceptance test, analysis, or
similarity), so that a captured limit level can be converted into the
level actually applied during test. This module implements the
mission-phase-to-environment lookup, the environment-to-domain lookup,
the design-and-test factor lookup, the limit-to-test-level conversion,
and the per-product review that flags an applicable environment with
no captured limit level. The specific numeric factors below are
illustrative generic engineering margins for this module's checkable
logic -- they are not a reproduction of any standard's factor table
and a real project must substitute its own approved values.
"""

MISSION_PHASES = frozenset({"ground", "launch", "transfer_orbit", "on_station"})

# Environment types applicable during each mission phase. A product's
# overall applicable-environment set is the union across its declared
# phases.
PHASE_ENVIRONMENTS = {
    "ground": frozenset({"electromagnetic_susceptibility"}),
    "launch": frozenset(
        {
            "quasi_static_acceleration",
            "random_vibration",
            "acoustic",
            "shock",
            "electromagnetic_susceptibility",
        }
    ),
    "transfer_orbit": frozenset(
        {"thermal_cycling", "thermal_vacuum", "radiation_total_dose"}
    ),
    "on_station": frozenset(
        {
            "thermal_cycling",
            "thermal_vacuum",
            "radiation_total_dose",
            "electromagnetic_susceptibility",
        }
    ),
}

# Engineering domain each environment type belongs to, for the purpose
# of picking a design-and-test factor.
ENVIRONMENT_DOMAIN = {
    "quasi_static_acceleration": "mechanical",
    "random_vibration": "mechanical",
    "acoustic": "mechanical",
    "shock": "mechanical",
    "thermal_cycling": "thermal",
    "thermal_vacuum": "thermal",
    "radiation_total_dose": "radiation",
    "electromagnetic_susceptibility": "electromagnetic",
}

# Verification approaches that produce a physical test and therefore
# use a numeric design-and-test factor to convert a limit level into a
# test level. Analysis and similarity are documentation-based approaches
# that instead require a recorded margin-of-safety justification.
TEST_VERIFICATION_APPROACHES = frozenset(
    {"qualification_test", "protoflight_test", "acceptance_test"}
)
DOCUMENTED_VERIFICATION_APPROACHES = frozenset({"analysis", "similarity"})
VERIFICATION_APPROACHES = TEST_VERIFICATION_APPROACHES | DOCUMENTED_VERIFICATION_APPROACHES

# Illustrative design-and-test factor applied to a domain's limit level
# to obtain the level applied during test, keyed by (domain, approach).
DESIGN_TEST_FACTORS = {
    ("mechanical", "qualification_test"): 1.25,
    ("mechanical", "protoflight_test"): 1.25,
    ("mechanical", "acceptance_test"): 1.0,
    ("thermal", "qualification_test"): 1.15,
    ("thermal", "protoflight_test"): 1.10,
    ("thermal", "acceptance_test"): 1.0,
    ("radiation", "qualification_test"): 1.5,
    ("radiation", "protoflight_test"): 1.5,
    ("radiation", "acceptance_test"): 1.0,
    ("electromagnetic", "qualification_test"): 1.0,
    ("electromagnetic", "protoflight_test"): 1.0,
    ("electromagnetic", "acceptance_test"): 1.0,
}


def environment_domain(environment_type):
    """Engineering domain for an environment type. Raises ValueError
    for an environment type outside ENVIRONMENT_DOMAIN."""
    if environment_type not in ENVIRONMENT_DOMAIN:
        raise ValueError(
            "unrecognized environment type %r under E-ST-10C clause 5.3.2"
            % (environment_type,)
        )
    return ENVIRONMENT_DOMAIN[environment_type]


def applicable_environments(mission_phases):
    """Union of environment types applicable across the given mission
    phases. mission_phases: iterable of phase strings. Raises
    ValueError for an empty iterable or an unrecognized phase."""
    phases = list(mission_phases)
    if not phases:
        raise ValueError("a product must declare at least one mission phase")
    environments = set()
    for phase in phases:
        if phase not in PHASE_ENVIRONMENTS:
            raise ValueError(
                "unrecognized mission phase %r under E-ST-10C clause 5.3.2"
                % (phase,)
            )
        environments |= PHASE_ENVIRONMENTS[phase]
    return environments


def verification_requires_test(approach):
    """True when a verification approach produces a physical test and
    therefore uses a numeric design-and-test factor; False when the
    approach is documentation-based (analysis, similarity) and instead
    requires a recorded margin-of-safety justification. Raises
    ValueError for an unrecognized approach."""
    if approach not in VERIFICATION_APPROACHES:
        raise ValueError("unrecognized verification approach %r" % (approach,))
    return approach in TEST_VERIFICATION_APPROACHES


def design_test_factor(domain, approach):
    """Design-and-test factor for a domain/approach pair. Raises
    ValueError if the approach does not require a test (use a
    margin-of-safety check instead) or if the domain/approach pair is
    not in DESIGN_TEST_FACTORS."""
    if not verification_requires_test(approach):
        raise ValueError(
            "verification approach %r has no numeric design-and-test "
            "factor; record a margin-of-safety justification instead"
            % (approach,)
        )
    key = (domain, approach)
    if key not in DESIGN_TEST_FACTORS:
        raise ValueError("no design-and-test factor for domain/approach %r" % (key,))
    return DESIGN_TEST_FACTORS[key]


def compute_test_level(limit_level, environment_type, approach):
    """Test level for one environment: limit_level x the design-and-
    test factor for the environment's domain and the given approach.
    Raises ValueError for an unrecognized environment_type, an
    approach with no numeric factor, or a non-numeric limit_level."""
    if isinstance(limit_level, bool) or not isinstance(limit_level, (int, float)):
        raise ValueError("limit_level must be a number, got %r" % (limit_level,))
    domain = environment_domain(environment_type)
    factor = design_test_factor(domain, approach)
    return limit_level * factor


def environment_review(product):
    """Full clause 5.3.2 environment review for one product.

    product: {"product_id": str, "mission_phases": [str, ...],
    "verification_approach": str, "limit_levels": {environment_type:
    float, ...}}. "limit_levels" holds the levels the product owner has
    already captured; an applicable environment absent from it is
    flagged. Returns {"missing_limit_levels": [...], "test_levels":
    {environment_type: float}}: test_levels is populated only when the
    verification approach requires a test. Raises ValueError for an
    unrecognized product_id-less input, mission phase, or verification
    approach."""
    product_id = product["product_id"]
    approach = product["verification_approach"]
    requires_test = verification_requires_test(approach)
    applicable = applicable_environments(product["mission_phases"])
    limit_levels = product.get("limit_levels", {})
    missing = []
    test_levels = {}
    for environment_type in sorted(applicable):
        if environment_type not in limit_levels:
            missing.append(
                {
                    "issue": "missing_limit_level",
                    "product": product_id,
                    "environment": environment_type,
                }
            )
            continue
        if requires_test:
            test_levels[environment_type] = compute_test_level(
                limit_levels[environment_type], environment_type, approach
            )
    return {"missing_limit_levels": missing, "test_levels": test_levels}


def is_environment_design_compliant(review):
    """True when an environment_review result has no missing limit
    levels -- the product's applicable environments are all captured
    for this assessment."""
    return len(review["missing_limit_levels"]) == 0
