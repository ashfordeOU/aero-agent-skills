"""Step 2 of the hazard-analysis process: identify and assess hazards.

Anchor: ECSS-Q-ST-40-02C clause 5.2.2 (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Check that all four identification sources were worked, not one. A
   hazard list built from the generic library alone, or from the
   functional breakdown alone, is a list of the hazards that source
   happens to surface.
2. Validate each hazard entry: which source found it, the severity
   category it carries, the likelihood band, and whether the evidence
   behind each of those two is on record. An unsupported severity or
   likelihood is a finding in its own right, because the risk index is
   only as good as the pair it is read from.
3. Where a quantified probability is supplied, place it in a likelihood
   band rather than carrying the number forward. Band boundaries are
   inclusive at the upper band, and a small tolerance absorbs the
   representation error of a probability that was itself computed.
4. Read severity and likelihood into the project risk index, and group
   the index into the acceptability bands the project will act on.
5. Aggregate: which sources went untouched, which entries are
   unsupported, and the index distribution across the hazard list.

Stdlib only, offline, deterministic.
"""

# The four places a space-system hazard comes from. Working one of them
# and calling the list complete is the defect this step exists to catch.
IDENTIFICATION_SOURCES = (
    "generic-hazard-library",
    "system-functions",
    "planned-operations",
    "induced-and-natural-environments",
)

# Severity, worst first. The ordinal is the matrix row.
SEVERITY_CATEGORIES = ("catastrophic", "critical", "major", "minor")
SEVERITY_ORDINAL = {name: i for i, name in enumerate(SEVERITY_CATEGORIES)}

# Likelihood, most likely first. The ordinal is the matrix column.
LIKELIHOOD_BANDS = ("probable", "occasional", "remote", "improbable")
LIKELIHOOD_ORDINAL = {name: i for i, name in enumerate(LIKELIHOOD_BANDS)}

# Lower probability bound of each band, most likely band first. A
# probability at or above a bound sits in that band.
LIKELIHOOD_LOWER_BOUND = (
    ("probable", 1.0e-2),
    ("occasional", 1.0e-3),
    ("remote", 1.0e-5),
    ("improbable", 0.0),
)

# A supplied probability is usually itself a computed quotient, so a
# value meant to sit exactly on a boundary can land a few units in the
# last place under it. The tolerance absorbs that without moving the
# engineering boundary.
PROBABILITY_TOLERANCE = 1.0e-12

# Risk index by (severity ordinal, likelihood ordinal). 1 is the worst
# cell, 16 the mildest; the index is an integer so it is identical on
# every platform.
RISK_INDEX_MATRIX = (
    (1, 2, 4, 8),
    (3, 5, 7, 11),
    (6, 9, 12, 14),
    (10, 13, 15, 16),
)

# Acceptability grouping of the index. The boundaries are inclusive.
UNACCEPTABLE_MAX_INDEX = 5
UNDESIRABLE_MAX_INDEX = 9
ACCEPTABLE_WITH_REVIEW_MAX_INDEX = 14


def _string(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def likelihood_band(probability):
    """Place a per-mission probability in a likelihood band."""
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise ValueError("probability must be numeric, got %r" % (probability,))
    value = float(probability)
    if value < 0.0 or value > 1.0:
        raise ValueError("probability must lie in [0, 1], got %r" % (probability,))
    for name, bound in LIKELIHOOD_LOWER_BOUND:
        if value >= bound - PROBABILITY_TOLERANCE:
            return name
    return LIKELIHOOD_BANDS[-1]


def risk_index(severity, likelihood):
    """Project risk index for a severity and likelihood pair."""
    if severity not in SEVERITY_ORDINAL:
        raise ValueError(
            "unknown severity %r (expected one of %s)"
            % (severity, ", ".join(SEVERITY_CATEGORIES))
        )
    if likelihood not in LIKELIHOOD_ORDINAL:
        raise ValueError(
            "unknown likelihood %r (expected one of %s)"
            % (likelihood, ", ".join(LIKELIHOOD_BANDS))
        )
    return RISK_INDEX_MATRIX[SEVERITY_ORDINAL[severity]][LIKELIHOOD_ORDINAL[likelihood]]


def risk_acceptability(index):
    """Group a risk index into the band the project acts on."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError("risk index must be an int, got %r" % (index,))
    if index < 1 or index > 16:
        raise ValueError("risk index must lie in 1..16, got %r" % (index,))
    if index <= UNACCEPTABLE_MAX_INDEX:
        return "unacceptable"
    if index <= UNDESIRABLE_MAX_INDEX:
        return "undesirable"
    if index <= ACCEPTABLE_WITH_REVIEW_MAX_INDEX:
        return "acceptable-with-review"
    return "acceptable"


def validate_hazard(hazard):
    """Validate one hazard entry and return a normalized copy."""
    if not isinstance(hazard, dict):
        raise ValueError("hazard must be a mapping")
    hazard_id = _string("hazard id", hazard.get("id"))
    source = hazard.get("source")
    if source not in IDENTIFICATION_SOURCES:
        raise ValueError(
            "hazard %s has unknown source %r (expected one of %s)"
            % (hazard_id, source, ", ".join(IDENTIFICATION_SOURCES))
        )
    severity = hazard.get("severity")
    if severity not in SEVERITY_ORDINAL:
        raise ValueError("hazard %s has unknown severity %r" % (hazard_id, severity))
    likelihood = hazard.get("likelihood")
    probability = hazard.get("probability")
    if probability is not None:
        likelihood = likelihood_band(probability)
    if likelihood not in LIKELIHOOD_ORDINAL:
        raise ValueError(
            "hazard %s has unknown likelihood %r and no probability"
            % (hazard_id, hazard.get("likelihood"))
        )
    return {
        "id": hazard_id,
        "source": source,
        "severity": severity,
        "likelihood": likelihood,
        "probability": None if probability is None else float(probability),
        "severity_evidence": _boolean(
            "hazard %s severity_evidence" % hazard_id,
            hazard.get("severity_evidence", False),
        ),
        "likelihood_evidence": _boolean(
            "hazard %s likelihood_evidence" % hazard_id,
            hazard.get("likelihood_evidence", False),
        ),
    }


def assess_hazard(hazard):
    """Assess one hazard entry: index, grouping and support findings."""
    norm = validate_hazard(hazard)
    index = risk_index(norm["severity"], norm["likelihood"])
    findings = []
    if not norm["severity_evidence"]:
        findings.append("severity-not-supported-by-evidence")
    if not norm["likelihood_evidence"]:
        findings.append("likelihood-not-supported-by-evidence")
    return {
        "id": norm["id"],
        "source": norm["source"],
        "severity": norm["severity"],
        "likelihood": norm["likelihood"],
        "risk_index": index,
        "acceptability": risk_acceptability(index),
        "findings": findings,
        "supported": not findings,
    }


def source_coverage(hazards):
    """Which identification sources the hazard list actually used."""
    if not isinstance(hazards, list):
        raise ValueError("hazards must be a list")
    used = set()
    for hazard in hazards:
        used.add(validate_hazard(hazard)["source"])
    untouched = [s for s in IDENTIFICATION_SOURCES if s not in used]
    fraction = float(len(IDENTIFICATION_SOURCES) - len(untouched)) / float(
        len(IDENTIFICATION_SOURCES)
    )
    return {
        "used": [s for s in IDENTIFICATION_SOURCES if s in used],
        "untouched": untouched,
        "coverage_fraction": fraction,
    }


def assess_identification_and_assessment(hazards):
    """Run the full clause 5.2.2 step-2 assessment over a hazard list."""
    if not isinstance(hazards, list) or not hazards:
        raise ValueError("hazards must be a non-empty list")
    results = []
    seen = set()
    for hazard in hazards:
        result = assess_hazard(hazard)
        if result["id"] in seen:
            raise ValueError("duplicate hazard id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    coverage = source_coverage(hazards)
    findings = []
    for source in coverage["untouched"]:
        findings.append("identification-source-not-worked:%s" % source)
    for result in results:
        for finding in result["findings"]:
            findings.append("%s:%s" % (finding, result["id"]))
    distribution = {}
    for result in results:
        key = result["acceptability"]
        distribution[key] = distribution.get(key, 0) + 1
    return {
        "hazards": results,
        "source_coverage": coverage,
        "acceptability_distribution": distribution,
        "unacceptable_ids": [
            r["id"] for r in results if r["acceptability"] == "unacceptable"
        ],
        "findings": findings,
        "complete": not findings,
    }
