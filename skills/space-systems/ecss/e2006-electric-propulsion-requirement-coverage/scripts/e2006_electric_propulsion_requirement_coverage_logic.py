#!/usr/bin/env python3
"""Electric-propulsion requirement ownership and coverage checking.

Anchor: ECSS-E-ST-20-06C clause 11.1.2 (paraphrased, not quoted).

Clause 11.1.2 explains how the electric-propulsion provisions of the
charging standard relate to the broader propulsion standard, which
covers performance, interfaces and verification. This module turns that
relationship into a deterministic allocation and coverage check:

* resolve each requirement topic to the standard that owns it
  (charging standard, propulsion standard, or jointly governed);
* confirm the declared owner matches the registry, and that a jointly
  governed topic carries an explicit cross-reference;
* validate the declared verification method;
* detect duplicate identifiers and conflicting ownership claims on the
  same topic;
* compute weighted coverage of the mandatory charging-interaction
  topics and grade it against an agreed threshold.

Standard library only, offline, deterministic.
"""

import math

CHARGING_STANDARD = "ecss-e-st-20-06"
PROPULSION_STANDARD = "ecss-e-st-35"
JOINT = "jointly-governed"

# Tolerance used only to absorb binary-floating-point representation
# error on an exact-threshold comparison. It never relaxes the
# engineering threshold itself.
REPRESENTATION_TOLERANCE = 1e-9

# Topic -> owning standard. Charging-interaction topics belong to the
# charging standard; performance, interface and verification topics
# belong to the propulsion standard; a few topics are governed by both
# and must carry a cross-reference in either direction.
TOPIC_OWNER = {
    "beam-neutralization-capacity": CHARGING_STANDARD,
    "plume-charge-exchange-backflow": CHARGING_STANDARD,
    "plume-sputter-erosion": CHARGING_STANDARD,
    "neutral-gas-discharge-triggering": CHARGING_STANDARD,
    "spacecraft-floating-potential": CHARGING_STANDARD,
    "differential-charging-mitigation": CHARGING_STANDARD,
    "thrust-performance": PROPULSION_STANDARD,
    "specific-impulse-performance": PROPULSION_STANDARD,
    "propellant-feed-architecture": PROPULSION_STANDARD,
    "thruster-mechanical-interface": PROPULSION_STANDARD,
    "propellant-throughput-life": PROPULSION_STANDARD,
    "propulsion-functional-verification": PROPULSION_STANDARD,
    "electrical-power-interface": JOINT,
    "plume-impingement-envelope": JOINT,
    "ground-facility-effect-correction": JOINT,
}

# Charging-interaction topics clause 11.1.2 expects the requirement set
# to cover, with the weight each carries in the coverage figure.
MANDATORY_TOPIC_WEIGHT = {
    "beam-neutralization-capacity": 0.3,
    "plume-charge-exchange-backflow": 0.2,
    "plume-sputter-erosion": 0.2,
    "neutral-gas-discharge-triggering": 0.1,
    "spacecraft-floating-potential": 0.1,
    "differential-charging-mitigation": 0.1,
}

VERIFICATION_METHODS = (
    "analysis",
    "inspection",
    "review-of-design",
    "similarity",
    "verification-by-testing",
)


def normalize_token(value, label):
    """Lowercase and strip a required string token."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def topic_owner(topic):
    """Return the standard that owns a requirement topic."""
    key = normalize_token(topic, "topic")
    if key not in TOPIC_OWNER:
        raise ValueError("uncategorized requirement topic: %r" % (topic,))
    return TOPIC_OWNER[key]


def delegation_chain(topic):
    """Return (primary, supporting) standards for a topic.

    A charging topic is written here and supported by the propulsion
    standard's performance and interface data; a propulsion topic is
    the reverse; a jointly governed topic names both as primary.
    """
    owner = topic_owner(topic)
    if owner == CHARGING_STANDARD:
        return (CHARGING_STANDARD, PROPULSION_STANDARD)
    if owner == PROPULSION_STANDARD:
        return (PROPULSION_STANDARD, CHARGING_STANDARD)
    return (CHARGING_STANDARD, PROPULSION_STANDARD)


def validate_verification_method(method):
    """Validate a declared verification method token."""
    key = normalize_token(method, "verification method")
    if key not in VERIFICATION_METHODS:
        raise ValueError("unrecognised verification method: %r" % (method,))
    return key


def validate_requirement(req):
    """Normalise and validate one requirement record.

    Required keys: ``id``, ``topic``, ``owner``, ``verification_method``.
    Optional: ``cross_reference`` (the other standard, for a jointly
    governed topic).
    """
    if not isinstance(req, dict):
        raise ValueError("requirement must be a mapping")
    for key in ("id", "topic", "owner", "verification_method"):
        if key not in req:
            raise ValueError("requirement missing required key %r" % (key,))
    out = {
        "id": normalize_token(req["id"], "requirement id"),
        "topic": normalize_token(req["topic"], "topic"),
        "declared_owner": normalize_token(req["owner"], "owner"),
        "verification_method": validate_verification_method(
            req["verification_method"]),
    }
    out["registry_owner"] = topic_owner(out["topic"])
    cross = req.get("cross_reference")
    out["cross_reference"] = (normalize_token(cross, "cross reference")
                              if cross is not None else None)
    if out["declared_owner"] not in (CHARGING_STANDARD, PROPULSION_STANDARD,
                                     JOINT):
        raise ValueError("unrecognised declared owner: %r" % (req["owner"],))
    return out


def ownership_findings(req):
    """Findings raised by the ownership rules for one requirement."""
    checked = validate_requirement(req)
    findings = []
    if checked["declared_owner"] != checked["registry_owner"]:
        findings.append(
            "misallocated-ownership: %s declares %s, registry says %s"
            % (checked["id"], checked["declared_owner"],
               checked["registry_owner"]))
    if checked["registry_owner"] == JOINT:
        if checked["cross_reference"] is None:
            findings.append(
                "missing-cross-reference: %s covers a jointly-governed topic"
                % checked["id"])
        elif checked["cross_reference"] not in (CHARGING_STANDARD,
                                                PROPULSION_STANDARD):
            findings.append(
                "cross-reference-not-a-governing-standard: %s" % checked["id"])
    if (checked["registry_owner"] == CHARGING_STANDARD
            and checked["verification_method"] == "similarity"):
        findings.append(
            "similarity-not-acceptable-for-charging-topic: %s" % checked["id"])
    return checked, findings


def weighted_coverage(topics):
    """Weighted share of the mandatory charging topics that are covered."""
    if not isinstance(topics, (list, tuple, set, frozenset)):
        raise ValueError("topics must be a list, tuple or set")
    covered = set()
    for topic in topics:
        key = normalize_token(topic, "topic")
        if key in MANDATORY_TOPIC_WEIGHT:
            covered.add(key)
    # Summation order is fixed (sorted keys) so the ratio is bit-for-bit
    # reproducible from run to run, not dependent on set iteration order.
    total = sum(MANDATORY_TOPIC_WEIGHT[k] for k in sorted(MANDATORY_TOPIC_WEIGHT))
    if total <= 0:
        raise ValueError("mandatory topic weights must sum above zero")
    got = sum(MANDATORY_TOPIC_WEIGHT[k] for k in sorted(covered))
    return got / total


def missing_mandatory_topics(topics):
    """Mandatory charging topics not present in the requirement set."""
    present = set()
    for topic in topics:
        present.add(normalize_token(topic, "topic"))
    return tuple(sorted(set(MANDATORY_TOPIC_WEIGHT) - present))


def meets_threshold(ratio, threshold):
    """True when a coverage ratio reaches an agreed threshold.

    The ratio is a sum of weights divided by a sum of weights, so an
    exactly-compliant set can land a few units in the last place under
    the threshold. The comparison absorbs that representation error; it
    does not lower the threshold.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must lie in [0, 1]")
    if ratio < 0.0:
        raise ValueError("coverage ratio must not be negative")
    return ratio >= threshold or math.isclose(
        ratio, threshold, rel_tol=0.0, abs_tol=REPRESENTATION_TOLERANCE)


def assess_requirement_coverage(requirements, threshold=1.0):
    """Assess a whole electric-propulsion requirement set.

    Returns the per-requirement records, the weighted coverage of the
    mandatory charging topics, the missing topics, the method tally and
    the aggregated findings. The set is coverage-compliant only when no
    finding stands and the coverage reaches the threshold.
    """
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("requirement set must be a list")
    if not requirements:
        raise ValueError("requirement set must contain at least one entry")
    records = []
    findings = []
    seen_ids = set()
    topic_claims = {}
    methods = {}
    for req in requirements:
        checked, found = ownership_findings(req)
        if checked["id"] in seen_ids:
            raise ValueError("duplicate requirement id %r" % (checked["id"],))
        seen_ids.add(checked["id"])
        claim = topic_claims.setdefault(checked["topic"], set())
        claim.add(checked["declared_owner"])
        if len(claim) > 1:
            findings.append(
                "conflicting-ownership-claim: topic %s claimed by %s"
                % (checked["topic"], ", ".join(sorted(claim))))
        methods[checked["verification_method"]] = methods.get(
            checked["verification_method"], 0) + 1
        records.append(checked)
        findings.extend(found)
    topics = [r["topic"] for r in records]
    ratio = weighted_coverage(topics)
    missing = missing_mandatory_topics(topics)
    reaches = meets_threshold(ratio, threshold)
    if not reaches:
        findings.append(
            "coverage-below-threshold: %.3f against %.3f" % (ratio, threshold))
    return {
        "requirements": records,
        "coverage_ratio": ratio,
        "missing_topics": missing,
        "verification_methods": methods,
        "findings": findings,
        "coverage_compliant": not findings and reaches,
    }
