"""Acceptability of a source of bare semiconductor and passive chips.

Anchor: ECSS-Q-ST-60-05C clause 8.1.2 (the basis on which a source of bare
chips is judged acceptable for a space hybrid). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the source record: who the source is, how many intermediaries sit
   between the wafer line and the buyer, and the evidence it carries.
2. Categorize the source from the supply chain itself -- the die manufacturer
   that ran the wafer line, a distributor working under a franchise agreement
   with that manufacturer, or an independent reseller holding stock whose
   origin it did not itself produce.
3. Apply the veto criteria. These are the conditions no amount of commercial
   merit can outrank: an unapproved quality system, a die that cannot be traced
   back to the wafer lot that produced it, an audit that has aged out of its
   validity window, a chain deeper than the buyer can audit through, and an
   independent reseller offering no upscreening evidence of its own.
4. Only when no veto fires, score the remaining desirable attributes -- source
   category, process-change-notification commitment and the ability to deliver
   the whole quantity from one wafer lot -- and compare with the acceptance
   threshold.
5. Return one of three dispositions with every failing criterion named, so a
   refused source can be told what would change the answer.
"""

import math

__all__ = [
    "SCORE_TOLERANCE",
    "SOURCE_ORIGINAL",
    "SOURCE_FRANCHISED",
    "SOURCE_INDEPENDENT",
    "CATEGORY_WEIGHT",
    "DEFAULT_AUDIT_VALIDITY_MONTHS",
    "DEFAULT_MAX_CHAIN_DEPTH",
    "DEFAULT_ACCEPT_THRESHOLD",
    "validate_source_record",
    "chain_depth",
    "categorize_source",
    "audit_is_current",
    "veto_findings",
    "weighted_score",
    "outstanding_conditions",
    "assess_source_acceptability",
]

# A weighted sum of decimal fractions is not exact in binary: 0.4 + 0.3 + 0.3
# lands a couple of ULP above one. Comparisons against a threshold absorb that
# representation error here rather than by moving the engineering threshold.
SCORE_TOLERANCE = 1e-9

SOURCE_ORIGINAL = "original-manufacturer"
SOURCE_FRANCHISED = "franchised-distributor"
SOURCE_INDEPENDENT = "independent-reseller"

# How much confidence the supply route itself carries, before any evidence.
CATEGORY_WEIGHT = {
    SOURCE_ORIGINAL: 0.40,
    SOURCE_FRANCHISED: 0.25,
    SOURCE_INDEPENDENT: 0.10,
}

WEIGHT_PCN_COMMITMENT = 0.30
WEIGHT_SINGLE_WAFER_LOT = 0.30

DEFAULT_AUDIT_VALIDITY_MONTHS = 36.0
DEFAULT_MAX_CHAIN_DEPTH = 2
DEFAULT_ACCEPT_THRESHOLD = 0.75

_BOOL_FIELDS = (
    "quality_system_approved",
    "traceable_to_wafer_lot",
    "franchise_agreement",
    "pcn_commitment",
    "supplies_single_wafer_lot",
    "upscreening_evidence",
)


def _require_real(value, label, allow_zero=True):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return number


def validate_source_record(record):
    """Return a normalised source record, raising on any malformed field.

    Required keys: name, chain (sequence of intermediary names, possibly
    empty), audit_age_months, plus the boolean evidence fields.
    """
    if not isinstance(record, dict):
        raise ValueError("source record must be a mapping")
    name = record.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("source record needs a non-empty 'name'")
    if "chain" not in record:
        raise ValueError("source record needs a 'chain' sequence (empty when direct)")
    chain = record["chain"]
    if isinstance(chain, str) or not isinstance(chain, (list, tuple)):
        raise ValueError("'chain' must be a sequence of intermediary names")
    normalised_chain = []
    for index, link in enumerate(chain):
        if not isinstance(link, str) or not link.strip():
            raise ValueError("chain[%d] must be a non-empty name" % index)
        normalised_chain.append(link.strip())
    if "audit_age_months" not in record:
        raise ValueError("source record needs 'audit_age_months'")
    audit_age = _require_real(record["audit_age_months"], "audit_age_months")
    normalised = {
        "name": name.strip(),
        "chain": tuple(normalised_chain),
        "audit_age_months": audit_age,
    }
    for field in _BOOL_FIELDS:
        value = record.get(field, False)
        if not isinstance(value, bool):
            raise ValueError("'%s' must be a boolean, got %r" % (field, value))
        normalised[field] = value
    return normalised


def chain_depth(record):
    """Return the number of intermediaries between the wafer line and the buyer."""
    return len(validate_source_record(record)["chain"])


def categorize_source(record):
    """Return the supply-route category of the source.

    A direct source is the manufacturer that ran the wafer line. An
    intermediary holding a franchise agreement with that manufacturer is a
    franchised distributor; any other intermediary is an independent reseller.
    """
    normalised = validate_source_record(record)
    if not normalised["chain"]:
        return SOURCE_ORIGINAL
    if normalised["franchise_agreement"]:
        return SOURCE_FRANCHISED
    return SOURCE_INDEPENDENT


def audit_is_current(audit_age_months, validity_months=DEFAULT_AUDIT_VALIDITY_MONTHS):
    """Return True while the source audit is still inside its validity window."""
    age = _require_real(audit_age_months, "audit_age_months")
    validity = _require_real(validity_months, "validity_months", allow_zero=False)
    return age < validity or math.isclose(age, validity, rel_tol=0.0, abs_tol=SCORE_TOLERANCE)


def veto_findings(record, validity_months=DEFAULT_AUDIT_VALIDITY_MONTHS,
                  max_chain_depth=DEFAULT_MAX_CHAIN_DEPTH):
    """Return the ordered list of veto criteria this source fails."""
    normalised = validate_source_record(record)
    if not isinstance(max_chain_depth, int) or isinstance(max_chain_depth, bool):
        raise ValueError("max_chain_depth must be an integer")
    if max_chain_depth < 0:
        raise ValueError("max_chain_depth must be non-negative, got %d" % max_chain_depth)
    category = categorize_source(normalised)
    depth = len(normalised["chain"])
    findings = []
    if not normalised["quality_system_approved"]:
        findings.append("quality system of the source is not approved")
    if not normalised["traceable_to_wafer_lot"]:
        findings.append("die cannot be traced back to the wafer lot that produced it")
    if not audit_is_current(normalised["audit_age_months"], validity_months):
        findings.append(
            "source audit is %.1f months old, past its %.1f month validity"
            % (normalised["audit_age_months"], float(validity_months))
        )
    if depth > max_chain_depth:
        findings.append(
            "supply chain is %d intermediaries deep, beyond the auditable limit of %d"
            % (depth, max_chain_depth)
        )
    if category == SOURCE_INDEPENDENT and not normalised["upscreening_evidence"]:
        findings.append(
            "independent reseller offers no upscreening evidence of its own"
        )
    return findings


def weighted_score(record):
    """Return the 0..1 merit score of a source that no veto criterion refused."""
    normalised = validate_source_record(record)
    category = categorize_source(normalised)
    score = CATEGORY_WEIGHT[category]
    if normalised["pcn_commitment"]:
        score += WEIGHT_PCN_COMMITMENT
    if normalised["supplies_single_wafer_lot"]:
        score += WEIGHT_SINGLE_WAFER_LOT
    # The weights are chosen to total one; binary addition can overshoot by a
    # couple of ULP, so pin the top of the range instead of reporting 1.0000002.
    if score > 1.0:
        score = 1.0
    return score


def outstanding_conditions(record):
    """Return the ordered attributes a conditionally acceptable source still owes."""
    normalised = validate_source_record(record)
    conditions = []
    if not normalised["pcn_commitment"]:
        conditions.append("obtain a process-change-notification commitment")
    if not normalised["supplies_single_wafer_lot"]:
        conditions.append("confirm the whole quantity can come from one wafer lot")
    if categorize_source(normalised) != SOURCE_ORIGINAL:
        conditions.append(
            "obtain the die manufacturer's own conformity evidence through the chain"
        )
    return conditions


def assess_source_acceptability(spec):
    """Run the full clause 8.1.2 source-acceptability assessment.

    spec keys: source (the record), optional audit_validity_months,
    max_chain_depth and accept_threshold.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "source" not in spec:
        raise ValueError("spec missing required key 'source'")
    record = validate_source_record(spec["source"])
    validity = _require_real(
        spec.get("audit_validity_months", DEFAULT_AUDIT_VALIDITY_MONTHS),
        "audit_validity_months",
        allow_zero=False,
    )
    max_depth = spec.get("max_chain_depth", DEFAULT_MAX_CHAIN_DEPTH)
    threshold = _require_real(
        spec.get("accept_threshold", DEFAULT_ACCEPT_THRESHOLD), "accept_threshold"
    )
    if threshold > 1.0:
        raise ValueError("accept_threshold must not exceed 1.0, got %r" % (threshold,))
    category = categorize_source(record)
    vetoes = veto_findings(record, validity, max_depth)
    score = weighted_score(record)
    if vetoes:
        decision = "refused"
        conditions = []
    elif score > threshold or math.isclose(
        score, threshold, rel_tol=0.0, abs_tol=SCORE_TOLERANCE
    ):
        decision = "acceptable"
        conditions = []
    else:
        decision = "acceptable-with-conditions"
        conditions = outstanding_conditions(record)
    return {
        "source": record["name"],
        "category": category,
        "chain_depth": len(record["chain"]),
        "audit_current": audit_is_current(record["audit_age_months"], validity),
        "score": score,
        "threshold": threshold,
        "decision": decision,
        "vetoes": vetoes,
        "conditions": conditions,
        "acceptable": decision != "refused",
    }
