"""Pre-tailoring of the quality assurance requirement set by space product type.

Anchor: ECSS-Q-ST-20C clause 6 -- the pre-tailoring matrix, which states for
each space product type which of the clause 5 requirements apply as written,
which do not apply, and which apply in a modified form. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the pre-tailoring matrix: every requirement it covers carries a
   disposition for every declared product type, a modified disposition carries
   the modification it stands for, and no disposition falls outside the closed
   vocabulary.
2. Apply the matrix to the requirement set for one product type, producing the
   tailored set and naming every requirement the matrix does not cover.
3. Reconcile the project's own proposed disposition against the matrix,
   separating a relaxation, which needs justification and approval, from a
   tightening, which the project may always take on itself.
4. Compute the applicable fraction of the requirement set, since that is the
   number the pre-tailoring argument is actually about.
5. Return the tailored set, the findings and the verdict on whether the
   tailoring as proposed may be adopted.
"""

import math

__all__ = [
    "PRODUCT_TYPES",
    "DISPOSITIONS",
    "APPLIED_DISPOSITIONS",
    "FRACTION_TOLERANCE",
    "normalize_token",
    "validate_product_type",
    "validate_matrix",
    "apply_pretailoring",
    "deviation_findings",
    "applicable_fraction",
    "assess_pretailoring",
]

# The space product types the pre-tailoring matrix distinguishes.
PRODUCT_TYPES = (
    "first-flight-hardware",
    "recurrent-flight-hardware",
    "ground-support-equipment",
    "commercial-off-the-shelf-item",
    "software-product",
)

# What the matrix can say about a requirement for a given product type.
DISPOSITIONS = ("applicable", "modified", "not-applicable")

# Dispositions under which the requirement stays in the tailored set.
APPLIED_DISPOSITIONS = ("applicable", "modified")

# The applicable fraction is a ratio of two counts and can land a few ULPs
# short of a stated target.
FRACTION_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for a name."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def validate_product_type(product_type):
    """Return the validated space product type token."""
    token = normalize_token(product_type, "product_type")
    if token not in PRODUCT_TYPES:
        raise ValueError("product_type %r is not a space product type" % token)
    return token


def validate_matrix(matrix):
    """Return the validated pre-tailoring matrix keyed by requirement."""
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping of requirement to dispositions")
    validated = {}
    for requirement, row in matrix.items():
        rid = normalize_token(requirement, "matrix requirement")
        if rid in validated:
            raise ValueError("requirement %r appears twice in the matrix" % rid)
        if not isinstance(row, dict):
            raise ValueError("matrix[%r] must be a mapping of product type to disposition" % rid)
        entries = {}
        for product_type, disposition in row.items():
            ptype = validate_product_type(product_type)
            if isinstance(disposition, dict):
                state = normalize_token(
                    disposition.get("disposition", ""), "matrix[%r] disposition" % rid
                )
                note = disposition.get("modification")
            else:
                state = normalize_token(disposition, "matrix[%r] disposition" % rid)
                note = None
            if state not in DISPOSITIONS:
                raise ValueError("matrix[%r] disposition %r is unknown" % (rid, state))
            if state == "modified" and not note:
                raise ValueError(
                    "matrix[%r] is modified for %s with no modification stated" % (rid, ptype)
                )
            entries[ptype] = {"disposition": state, "modification": note}
        missing = [p for p in PRODUCT_TYPES if p not in entries]
        if missing:
            raise ValueError(
                "matrix[%r] says nothing about %s" % (rid, ", ".join(missing))
            )
        validated[rid] = entries
    return validated


def apply_pretailoring(requirements, matrix, product_type):
    """Return the tailored requirement set for one space product type."""
    rows = validate_matrix(matrix)
    ptype = validate_product_type(product_type)
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("requirements must be a non-empty sequence of identifiers")
    applied = []
    dropped = []
    findings = []
    seen = set()
    for requirement in requirements:
        rid = normalize_token(requirement, "requirement")
        if rid in seen:
            raise ValueError("requirement %r is listed twice" % rid)
        seen.add(rid)
        row = rows.get(rid)
        if row is None:
            findings.append("%s has no pre-tailoring entry for any product type" % rid)
            continue
        entry = row[ptype]
        if entry["disposition"] in APPLIED_DISPOSITIONS:
            applied.append(
                {
                    "id": rid,
                    "disposition": entry["disposition"],
                    "modification": entry["modification"],
                }
            )
        else:
            dropped.append(rid)
    return {
        "product_type": ptype,
        "applied": applied,
        "dropped": dropped,
        "findings": findings,
    }


def deviation_findings(proposed, matrix, product_type, justified=()):
    """Return the findings where the project's proposal departs from the matrix."""
    rows = validate_matrix(matrix)
    ptype = validate_product_type(product_type)
    if not isinstance(proposed, dict) or not proposed:
        raise ValueError("proposed must be a non-empty mapping of requirement to disposition")
    if not isinstance(justified, (list, tuple)):
        raise ValueError("justified must be a sequence of requirement identifiers")
    approved = {normalize_token(j, "justified requirement") for j in justified}
    findings = []
    tightenings = []
    for requirement, disposition in proposed.items():
        rid = normalize_token(requirement, "proposed requirement")
        state = normalize_token(disposition, "proposed[%r]" % rid)
        if state not in DISPOSITIONS:
            raise ValueError("proposed disposition %r for %s is unknown" % (state, rid))
        row = rows.get(rid)
        if row is None:
            findings.append("%s is proposed but the matrix does not cover it" % rid)
            continue
        baseline = row[ptype]["disposition"]
        if state == baseline:
            continue
        relaxed = DISPOSITIONS.index(state) > DISPOSITIONS.index(baseline)
        if relaxed:
            if rid not in approved:
                findings.append(
                    "%s is relaxed from %s to %s with no approved justification"
                    % (rid, baseline, state)
                )
        else:
            tightenings.append(
                "%s is tightened from %s to %s by the project" % (rid, baseline, state)
            )
    return {"findings": findings, "tightenings": tightenings}


def applicable_fraction(tailored, requirement_count):
    """Return the share of the requirement set that survives pre-tailoring."""
    if not isinstance(tailored, dict) or "applied" not in tailored:
        raise ValueError("tailored must be the mapping returned by apply_pretailoring")
    if not isinstance(requirement_count, int) or isinstance(requirement_count, bool):
        raise ValueError("requirement_count must be an integer, got %r" % (requirement_count,))
    if requirement_count <= 0:
        raise ValueError("requirement_count must be positive, got %r" % (requirement_count,))
    return len(tailored["applied"]) / float(requirement_count)


def assess_pretailoring(spec):
    """Run the full clause 6 pre-tailoring assessment.

    spec keys: requirements, matrix, product_type, proposed, justified.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("requirements", "matrix", "product_type", "proposed", "justified"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    tailored = apply_pretailoring(spec["requirements"], spec["matrix"], spec["product_type"])
    deviations = deviation_findings(
        spec["proposed"], spec["matrix"], spec["product_type"], spec["justified"]
    )
    fraction = applicable_fraction(tailored, len(spec["requirements"]))
    findings = list(tailored["findings"]) + list(deviations["findings"])
    everything_applies = math.isclose(
        fraction, 1.0, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )
    return {
        "product_type": tailored["product_type"],
        "applied": tailored["applied"],
        "dropped": tailored["dropped"],
        "tightenings": deviations["tightenings"],
        "applicable_fraction": fraction,
        "untailored": everything_applies,
        "findings": findings,
        "tailoring_adoptable": not findings,
    }
