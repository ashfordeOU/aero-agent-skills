"""
Structural interface definition and tolerance stack-up analysis.
Reference: ECSS-E-ST-32 clauses 4.3.9 and 4.4 (paraphrased — no verbatim standard text).
stdlib only; offline; deterministic.
"""

import math

# Recognized structural interface types (ECSS-E-ST-32 clause 4.3.9 taxonomy)
INTERFACE_TYPES = frozenset({
    "mechanical-fastened",
    "adhesive-bonded",
    "bearing-contact",
    "alignment-critical",
})

# Permitted tolerance stack-up computation methods (clause 4.4)
STACKUP_METHODS = frozenset({"worst-case", "rss"})

# Recognized tolerance feature types
TOLERANCE_TYPES = frozenset({"linear", "angular", "flatness", "perpendicularity"})


class InterfaceDefinitionError(ValueError):
    """Raised when an interface record is invalid or incomplete."""


class ToleranceStackupError(ValueError):
    """Raised when a tolerance stack-up computation cannot proceed."""


def categorize_interface(interface_type: str) -> str:
    """
    Categorize a structural interface by type.

    Returns the normalized type string on success.
    Raises InterfaceDefinitionError for unrecognized types.
    """
    normalized = interface_type.strip().lower()
    if normalized not in INTERFACE_TYPES:
        raise InterfaceDefinitionError(
            f"Unrecognized interface type '{interface_type}'. "
            f"Accepted: {sorted(INTERFACE_TYPES)}."
        )
    return normalized


def validate_interface_record(record: dict) -> list:
    """
    Validate a single interface record for required fields.

    Expected keys:
      id             – unique interface identifier (str)
      type           – interface type string (one of INTERFACE_TYPES)
      tolerances     – list of dicts, each with {type, value, unit}
      reference_frame – non-empty string naming the coordinate datum
      icd_reference  – non-empty string identifying the ICD

    Returns a list of finding strings; empty list means the record is complete.
    """
    findings = []
    iid = record.get("id", "<unknown>")

    if not record.get("reference_frame", "").strip():
        findings.append(f"Interface {iid}: missing coordinate reference frame.")

    if not record.get("icd_reference", "").strip():
        findings.append(f"Interface {iid}: no ICD reference on record.")

    itype = record.get("type", "")
    try:
        categorize_interface(itype)
    except InterfaceDefinitionError as exc:
        findings.append(f"Interface {iid}: {exc}")

    tolerances = record.get("tolerances", [])
    if not tolerances:
        findings.append(f"Interface {iid}: no tolerance features defined.")
    else:
        for idx, tol in enumerate(tolerances):
            if tol.get("type") not in TOLERANCE_TYPES:
                findings.append(
                    f"Interface {iid} tolerance[{idx}]: "
                    f"unrecognized type '{tol.get('type')}'."
                )
            val = tol.get("value")
            if val is None or (isinstance(val, (int, float)) and val < 0):
                findings.append(
                    f"Interface {iid} tolerance[{idx}]: "
                    f"value must be a non-negative number, got '{val}'."
                )

    return findings


def compute_tolerance_stackup(tolerances: list, method: str) -> float:
    """
    Compute the combined tolerance from individual tolerance feature values.

    method "worst-case" — arithmetic sum of all individual values (conservative).
    method "rss"        — square root of the sum of squares (statistical).

    All tolerance values must be non-negative floats/ints.
    Raises ToleranceStackupError for empty lists, bad values, or unknown methods.
    """
    if method not in STACKUP_METHODS:
        raise ToleranceStackupError(
            f"Unknown stack-up method '{method}'. "
            f"Must be one of: {sorted(STACKUP_METHODS)}."
        )
    if not tolerances:
        raise ToleranceStackupError("Tolerance list is empty; cannot compute stack-up.")

    values = []
    for tol in tolerances:
        val = tol.get("value")
        if val is None or not isinstance(val, (int, float)) or val < 0:
            raise ToleranceStackupError(
                f"Each tolerance value must be a non-negative number; got '{val}'."
            )
        values.append(float(val))

    if method == "worst-case":
        return sum(values)
    # rss
    return math.sqrt(sum(v * v for v in values))


def check_alignment_budget(stackup_value: float, budget: float) -> dict:
    """
    Compare a computed tolerance stack-up against an alignment budget.

    Returns:
      stackup   – the input stack-up value
      budget    – the input budget value
      margin    – budget minus stackup (positive → compliant)
      compliant – True when margin >= 0
      finding   – None when compliant, descriptive string when not
    """
    if not isinstance(budget, (int, float)) or budget <= 0:
        raise InterfaceDefinitionError(
            f"Alignment budget must be a positive number; got '{budget}'."
        )

    margin = budget - stackup_value
    compliant = margin >= 0.0
    finding = None
    if not compliant:
        finding = (
            f"Stack-up {stackup_value:.6g} exceeds budget {budget:.6g} "
            f"by {abs(margin):.6g} (same units)."
        )
    return {
        "stackup": stackup_value,
        "budget": budget,
        "margin": margin,
        "compliant": compliant,
        "finding": finding,
    }


def assess_interface_set(
    interfaces: list,
    alignment_budget: float,
    stackup_method: str,
) -> dict:
    """
    Full interface-and-tolerance assessment for a set of structural interfaces.

    For each interface record the function:
      1. Validates completeness (reference frame, ICD, type, tolerances).
      2. Computes the tolerance stack-up from valid tolerance features.
      3. Compares the stack-up against the global alignment budget.

    Returns:
      interface_findings – list of definition/validation finding strings
      budget_findings    – list of strings for interfaces that exceed the budget
      missing_icd        – list of interface IDs with no ICD reference
      compliant          – True iff all three lists are empty
    """
    interface_findings = []
    budget_findings = []
    missing_icd = []

    for record in interfaces:
        iid = record.get("id", "<unknown>")

        findings = validate_interface_record(record)
        interface_findings.extend(findings)

        if not record.get("icd_reference", "").strip():
            missing_icd.append(iid)

        valid_tols = [
            t for t in record.get("tolerances", [])
            if isinstance(t.get("value"), (int, float)) and t["value"] >= 0
        ]
        if valid_tols:
            try:
                su = compute_tolerance_stackup(valid_tols, stackup_method)
                result = check_alignment_budget(su, alignment_budget)
                if not result["compliant"]:
                    budget_findings.append(f"Interface {iid}: {result['finding']}")
            except (ToleranceStackupError, InterfaceDefinitionError) as exc:
                interface_findings.append(f"Interface {iid}: {exc}")

    compliant = not interface_findings and not budget_findings and not missing_icd
    return {
        "interface_findings": interface_findings,
        "budget_findings": budget_findings,
        "missing_icd": missing_icd,
        "compliant": compliant,
    }
