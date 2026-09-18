"""Shortened hybrid-circuit approval route justified by documented likeness.

Anchor: ECSS-Q-ST-60-05C clause 7.3.3 (approval of a hybrid circuit by
similarity to a circuit that already carries an approval, and the reduced
programme that likeness buys).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A candidate hybrid is compared against one named reference hybrid that is
  already approved. Every design and process attribute of the pair is rated
  identical, minor-variant, major-variant or incompatible.
* Attributes are not equal in weight. Substrate technology, package family,
  sealing method, die attach, wire bonding and the manufacturing line decide
  whether the reference says anything at all about the candidate; layout,
  element counts, design rules and dissipation shade the answer.
* The route is refused outright when the reference is not itself approved,
  when its approval has aged past the validity window, when it was built on a
  different line, when it carries a less demanding quality level than the
  candidate asks for, when any decisive attribute is incompatible, or when
  too many decisive attributes are major variants at once.
* When the route survives, the attributes that moved decide the delta test
  groups: the parts of the approval programme that still have to be run on
  the candidate. Identical attributes contribute nothing, and the sample
  size grows with the number of major variants.
* A weighted divergence index summarises the pair on a nought-to-one scale so
  two candidates against the same reference can be ranked.
"""

from __future__ import annotations

import math

# Decisive attributes carry the heavier weight: without them the reference
# tells you nothing about the candidate.
ATTRIBUTE_CRITICALITY = {
    "substrate-technology": "decisive",
    "package-family": "decisive",
    "sealing-method": "decisive",
    "die-attach-process": "decisive",
    "wire-bond-process": "decisive",
    "manufacturing-line": "decisive",
    "design-rule-set": "supporting",
    "thermal-dissipation-class": "supporting",
    "active-element-count": "supporting",
    "passive-element-count": "supporting",
    "internal-layout-topology": "supporting",
}

CRITICALITY_WEIGHTS = {
    "decisive": 3.0,
    "supporting": 1.0,
}

DIVERGENCE_RANKS = {
    "identical": 0,
    "minor-variant": 1,
    "major-variant": 2,
    "incompatible": 3,
}

MAX_DIVERGENCE_RANK = 3

# Quality levels ordered by how demanding they are; a reference approved at a
# less demanding level cannot carry a candidate asking for a harder one.
QUALITY_LEVEL_DEMAND = {
    "level-3": 1,
    "level-2": 2,
    "level-1": 3,
}

DELTA_TEST_GROUPS = {
    "substrate-technology": ("construction-analysis", "thermal-cycling-endurance"),
    "package-family": ("hermeticity-and-seal", "mechanical-shock-and-vibration"),
    "sealing-method": ("hermeticity-and-seal", "residual-gas-and-moisture"),
    "die-attach-process": ("die-shear-strength", "thermal-cycling-endurance"),
    "wire-bond-process": ("bond-pull-strength", "operating-life-endurance"),
    "manufacturing-line": ("construction-analysis", "operating-life-endurance"),
    "design-rule-set": ("electrical-characterization",),
    "thermal-dissipation-class": ("thermal-cycling-endurance",),
    "active-element-count": ("electrical-characterization",),
    "passive-element-count": ("electrical-characterization",),
    "internal-layout-topology": ("construction-analysis",),
}

ROUTE_FULL = "full-approval-required"
ROUTE_PARTIAL = "similarity-partial-programme"
ROUTE_FULL_CREDIT = "similarity-full-credit"

MAX_MAJOR_VARIANT_ATTRIBUTES = 2
REFERENCE_VALIDITY_MONTHS = 24
BASE_DELTA_SAMPLE = 5
SAMPLE_PER_MAJOR_VARIANT = 3

# The divergence index is a ratio of sums of exactly representable terms, but
# it is still compared against typed-in thresholds, so equality is absorbed.
INDEX_TOLERANCE = 1e-9


def attribute_weight(attribute):
    """Weight carried by one comparison attribute; unknown names are rejected."""
    if attribute not in ATTRIBUTE_CRITICALITY:
        raise ValueError(
            "unknown comparison attribute %r (known: %s)"
            % (attribute, ", ".join(sorted(ATTRIBUTE_CRITICALITY)))
        )
    return CRITICALITY_WEIGHTS[ATTRIBUTE_CRITICALITY[attribute]]


def divergence_rank(state):
    """Rank of one divergence state, 0 for identical up to 3 for incompatible."""
    if state not in DIVERGENCE_RANKS:
        raise ValueError(
            "unknown divergence state %r (known: %s)"
            % (state, ", ".join(sorted(DIVERGENCE_RANKS)))
        )
    return DIVERGENCE_RANKS[state]


def quality_demand(level):
    """How demanding a quality level is; the higher number is the harder level."""
    if level not in QUALITY_LEVEL_DEMAND:
        raise ValueError(
            "unknown quality level %r (known: %s)"
            % (level, ", ".join(sorted(QUALITY_LEVEL_DEMAND)))
        )
    return QUALITY_LEVEL_DEMAND[level]


def decisive_attributes():
    """The attributes whose divergence can refuse the shortened route."""
    return tuple(
        sorted(a for a, c in ATTRIBUTE_CRITICALITY.items() if c == "decisive")
    )


def normalize_dossier(raw):
    """Validate one candidate-versus-reference likeness dossier."""
    if not isinstance(raw, dict):
        raise ValueError("dossier must be a mapping, got %r" % (type(raw).__name__,))
    candidate_id = raw.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError(
            "dossier needs a non-empty candidate_id, got %r" % (candidate_id,)
        )
    reference_id = raw.get("reference_id")
    if not isinstance(reference_id, str) or not reference_id.strip():
        raise ValueError(
            "dossier of %r needs a non-empty reference_id, got %r"
            % (candidate_id, reference_id)
        )
    if candidate_id == reference_id:
        raise ValueError(
            "candidate %r cannot be its own likeness reference" % (candidate_id,)
        )
    approved = raw.get("reference_approved")
    if not isinstance(approved, bool):
        raise ValueError(
            "reference_approved of %r must be a boolean, got %r"
            % (candidate_id, approved)
        )
    age = raw.get("reference_approval_age_months")
    if isinstance(age, bool) or not isinstance(age, (int, float)):
        raise ValueError(
            "reference_approval_age_months of %r must be a real number, got %r"
            % (candidate_id, age)
        )
    age = float(age)
    if not math.isfinite(age) or age < 0.0:
        raise ValueError(
            "reference_approval_age_months of %r must be finite and not negative"
            % (candidate_id,)
        )
    candidate_level = raw.get("candidate_quality_level")
    quality_demand(candidate_level)
    reference_level = raw.get("reference_quality_level")
    quality_demand(reference_level)
    attributes = raw.get("attributes")
    if not isinstance(attributes, dict):
        raise ValueError(
            "attributes of %r must be a mapping of attribute to divergence state"
            % (candidate_id,)
        )
    for attribute, state in attributes.items():
        attribute_weight(attribute)  # validation only
        divergence_rank(state)  # validation only
    missing = [a for a in decisive_attributes() if a not in attributes]
    if missing:
        raise ValueError(
            "dossier of %r does not rate the decisive attributes: %s"
            % (candidate_id, ", ".join(missing))
        )
    return {
        "candidate_id": candidate_id,
        "reference_id": reference_id,
        "reference_approved": approved,
        "reference_approval_age_months": age,
        "candidate_quality_level": candidate_level,
        "reference_quality_level": reference_level,
        "attributes": dict(attributes),
    }


def divergence_index(attributes):
    """Weighted likeness index: 0.0 when every rated attribute is identical."""
    if not isinstance(attributes, dict) or not attributes:
        raise ValueError("attributes must be a non-empty mapping")
    weighted = 0.0
    total = 0.0
    for attribute, state in attributes.items():
        weight = attribute_weight(attribute)
        weighted += weight * float(divergence_rank(state))
        total += weight * float(MAX_DIVERGENCE_RANK)
    return weighted / total


def delta_test_groups(attributes):
    """Test groups the candidate still owes, from the attributes that moved."""
    if not isinstance(attributes, dict) or not attributes:
        raise ValueError("attributes must be a non-empty mapping")
    groups = set()
    for attribute, state in attributes.items():
        if divergence_rank(state) >= 1:
            groups.update(DELTA_TEST_GROUPS[attribute])
    return tuple(sorted(groups))


def delta_sample_size(attributes):
    """Sample size for the delta programme; it grows with the major variants."""
    if not isinstance(attributes, dict) or not attributes:
        raise ValueError("attributes must be a non-empty mapping")
    majors = sum(1 for s in attributes.values() if divergence_rank(s) == 2)
    if not delta_test_groups(attributes):
        return 0
    return BASE_DELTA_SAMPLE + SAMPLE_PER_MAJOR_VARIANT * majors


def blocking_findings(dossier):
    """Every reason the shortened route cannot be granted, in a stable order."""
    record = normalize_dossier(dossier)
    findings = []
    if not record["reference_approved"]:
        findings.append("reference-circuit-not-approved")
    if record["reference_approval_age_months"] > REFERENCE_VALIDITY_MONTHS:
        findings.append("reference-approval-outside-validity-window")
    if quality_demand(record["candidate_quality_level"]) > quality_demand(
        record["reference_quality_level"]
    ):
        findings.append("reference-quality-level-below-candidate")
    attributes = record["attributes"]
    incompatible = sorted(
        a
        for a, s in attributes.items()
        if divergence_rank(s) == 3 and ATTRIBUTE_CRITICALITY[a] == "decisive"
    )
    if incompatible:
        findings.append("decisive-attribute-incompatible")
    majors = sorted(
        a
        for a, s in attributes.items()
        if divergence_rank(s) == 2 and ATTRIBUTE_CRITICALITY[a] == "decisive"
    )
    if len(majors) > MAX_MAJOR_VARIANT_ATTRIBUTES:
        findings.append("too-many-decisive-major-variants")
    return findings


def governing_attribute(attributes):
    """The rated attribute that most constrains the route, weight then rank."""
    if not isinstance(attributes, dict) or not attributes:
        raise ValueError("attributes must be a non-empty mapping")
    return max(
        sorted(attributes),
        key=lambda a: (
            divergence_rank(attributes[a]) * attribute_weight(a),
            divergence_rank(attributes[a]),
            a,
        ),
    )


def assess_similarity(dossier):
    """Decide the approval route for one candidate and size what remains."""
    record = normalize_dossier(dossier)
    attributes = record["attributes"]
    findings = blocking_findings(record)
    index = divergence_index(attributes)
    groups = delta_test_groups(attributes)
    if findings:
        route = ROUTE_FULL
        granted_groups = ()
        sample = 0
    elif not groups:
        route = ROUTE_FULL_CREDIT
        granted_groups = ()
        sample = 0
    else:
        route = ROUTE_PARTIAL
        granted_groups = groups
        sample = delta_sample_size(attributes)
    result = dict(record)
    result.update(
        {
            "route": route,
            "divergence_index": index,
            "delta_test_groups": granted_groups,
            "delta_sample_size": sample,
            "governing_attribute": governing_attribute(attributes),
            "findings": findings,
            "route_granted": route != ROUTE_FULL,
        }
    )
    return result


def rank_candidates(dossiers):
    """Assess a set of dossiers and rank the granted ones by their likeness.

    The return carries one record per dossier, the granted candidate ids
    ordered from most alike to least, the refused ones with their reasons,
    and the union of delta test groups the campaign has to cover.
    """
    if not isinstance(dossiers, (list, tuple)):
        raise ValueError(
            "dossiers must be a list or tuple, got %r" % (type(dossiers).__name__,)
        )
    if len(dossiers) == 0:
        raise ValueError("at least one dossier is required")
    records = [assess_similarity(d) for d in dossiers]
    seen = set()
    for record in records:
        if record["candidate_id"] in seen:
            raise ValueError("duplicate candidate_id %r" % (record["candidate_id"],))
        seen.add(record["candidate_id"])
    granted = [r for r in records if r["route_granted"]]
    refused = [r for r in records if not r["route_granted"]]
    granted.sort(key=lambda r: (r["divergence_index"], r["candidate_id"]))
    campaign_groups = set()
    for record in granted:
        campaign_groups.update(record["delta_test_groups"])
    return {
        "records": records,
        "granted_order": [r["candidate_id"] for r in granted],
        "refused": [
            {"candidate_id": r["candidate_id"], "findings": r["findings"]}
            for r in sorted(refused, key=lambda r: r["candidate_id"])
        ],
        "campaign_delta_groups": tuple(sorted(campaign_groups)),
        "all_granted": len(refused) == 0,
    }
