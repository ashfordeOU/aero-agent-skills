"""Lot traceability record coverage at the intermediate assurance class.

Anchor: ECSS-Q-ST-60-13C clause 5.5.4 (keeping a traceability record for a
commercial EEE lot across the handling steps it passes through). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the traceability policy: the handling steps that must carry a
   record, their fixed order, the plain and credited coverage floors, the
   credit a record held by another party earns, and the retention floor in
   whole years.
2. Validate every record: a non-blank identifier, a recognised handling step,
   a lot code, a holder, a retention period and a day index.
3. Bridge identity. A record naming the lot under investigation is on the
   chain; a record naming a different lot is on the chain only where it
   carries a cross-reference back, and is an identity break otherwise.
4. Dispose each required step as held by the project, held by another party
   under a recorded access undertaking, held with no undertaking, or missing.
5. Take the plain coverage over the required steps and the credited coverage
   with the external credit applied, and compare both with their floors.
6. Read the chain's order: the records that survive must run forward in the
   declared step order, and the first step must be the earliest one recorded.
7. Return one verdict in precedence order: chain not established, an identity
   break, a record held outside with no access undertaking, step coverage
   short, a retention period below the floor, records out of order, or lot
   traceability that meets the intermediate class.
"""

__all__ = [
    "COVERAGE_TOLERANCE",
    "HANDLING_STEP_ORDER",
    "HELD_BY_PROJECT",
    "HELD_EXTERNALLY",
    "DEFAULT_TRACEABILITY_POLICY",
    "CHAIN_NOT_ESTABLISHED",
    "LOT_IDENTITY_BROKEN",
    "ACCESS_UNDERTAKING_MISSING",
    "STEP_COVERAGE_SHORT",
    "RETENTION_BELOW_FLOOR",
    "RECORDS_OUT_OF_ORDER",
    "TRACEABILITY_MEETS_CLASS_TWO",
    "validate_traceability_policy",
    "validate_record",
    "validate_records",
    "step_rank",
    "resolve_identity",
    "dispose_steps",
    "step_coverage",
    "retention_shortfalls",
    "order_breaks",
    "assess_lot_traceability",
]

# Coverage is a ratio of small integer counts turned into a float, so a value
# landing exactly on its floor has to read as met. Every comparison runs
# through this tolerance rather than as a bare inequality.
COVERAGE_TOLERANCE = 1e-9

# The handling steps a commercial EEE lot passes through, in the only order
# they can occur in. The rank of a step is its position in this tuple.
HANDLING_STEP_ORDER = (
    "receipt",
    "incoming-inspection",
    "storage",
    "kitting",
    "assembly",
    "delivery",
)

HELD_BY_PROJECT = "project"
HELD_EXTERNALLY = "external"

CHAIN_NOT_ESTABLISHED = "chain-not-established"
LOT_IDENTITY_BROKEN = "lot-identity-broken"
ACCESS_UNDERTAKING_MISSING = "access-undertaking-missing"
STEP_COVERAGE_SHORT = "step-coverage-short"
RETENTION_BELOW_FLOOR = "retention-below-floor"
RECORDS_OUT_OF_ORDER = "records-out-of-order"
TRACEABILITY_MEETS_CLASS_TWO = "traceability-meets-class-two"

DEFAULT_TRACEABILITY_POLICY = {
    # Steps that must carry a traceability record for the lot.
    "required_steps": list(HANDLING_STEP_ORDER),
    # Share of required steps that must carry a record at all.
    "min_step_coverage": 1.0,
    # Share once a record held by another party is weighed below one held here.
    "min_credited_step_coverage": 0.75,
    # What a record held by another party is worth against one held here.
    "external_record_credit": 0.5,
    # Whole years a traceability record must be kept for.
    "min_retention_years": 10,
    # Whether a record held by another party needs a recorded access
    # undertaking before it counts at all.
    "require_access_undertaking": True,
    # Whether a record naming a different lot may be bridged by a
    # cross-reference back to the lot under investigation.
    "allow_cross_reference_bridge": True,
}

_RATIO_POLICY_KEYS = (
    "min_step_coverage",
    "min_credited_step_coverage",
    "external_record_credit",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _clean_text(value):
    return value.strip() if isinstance(value, str) else ""


def validate_traceability_policy(policy=None):
    """Return a complete traceability policy, defaults filled in."""
    if policy is None:
        return {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in DEFAULT_TRACEABILITY_POLICY.items()
        }
    if not isinstance(policy, dict):
        raise ValueError("traceability policy must be a mapping")
    merged = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in DEFAULT_TRACEABILITY_POLICY.items()
    }
    for key, value in policy.items():
        if key not in DEFAULT_TRACEABILITY_POLICY:
            raise ValueError("unknown traceability policy key %r" % (key,))
        merged[key] = list(value) if isinstance(value, (list, tuple)) else value
    steps = merged["required_steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError("required_steps must be a non-empty list")
    seen = set()
    for step in steps:
        name = _clean_text(step)
        if name not in HANDLING_STEP_ORDER:
            raise ValueError("unrecognised handling step %r" % (step,))
        if name in seen:
            raise ValueError("duplicate required step %r" % (name,))
        seen.add(name)
    if HANDLING_STEP_ORDER[0] not in seen:
        raise ValueError(
            "the receipt step must be required; without it the chain has no start"
        )
    merged["required_steps"] = sorted((_clean_text(s) for s in steps), key=step_rank)
    for key in _RATIO_POLICY_KEYS:
        value = merged[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number, got %r" % (key, value))
        if not 0.0 < float(value) <= 1.0:
            raise ValueError("%s must lie in (0, 1]" % key)
        merged[key] = float(value)
    if merged["min_credited_step_coverage"] > merged["min_step_coverage"]:
        raise ValueError(
            "the credited coverage floor must not sit above the plain floor; an "
            "externally held record is worth less, never more"
        )
    if not _is_int(merged["min_retention_years"]) or merged["min_retention_years"] <= 0:
        raise ValueError("min_retention_years must be a positive integer")
    for key in ("require_access_undertaking", "allow_cross_reference_bridge"):
        if not isinstance(merged[key], bool):
            raise ValueError("%s must be a boolean" % key)
    return merged


def step_rank(step):
    """Return the position of a handling step in the only order it can occur in."""
    name = _clean_text(step)
    if name not in HANDLING_STEP_ORDER:
        raise ValueError("unrecognised handling step %r" % (step,))
    return HANDLING_STEP_ORDER.index(name)


def validate_record(record):
    """Return a normalised traceability record for one handling step."""
    if not isinstance(record, dict):
        raise ValueError("each record must be a mapping, got %r" % (type(record).__name__,))
    identifier = _clean_text(record.get("id"))
    if not identifier:
        raise ValueError("each traceability record needs a non-empty 'id'")
    step = _clean_text(record.get("step"))
    if step not in HANDLING_STEP_ORDER:
        raise ValueError("record %s names an unrecognised step %r" % (identifier, record.get("step")))
    lot_code = _clean_text(record.get("lot_code"))
    if not lot_code:
        raise ValueError(
            "record %s carries no lot code; a record that names no lot traces nothing"
            % identifier
        )
    holder = _clean_text(record.get("holder")) or HELD_BY_PROJECT
    if holder not in (HELD_BY_PROJECT, HELD_EXTERNALLY):
        raise ValueError("record %s has an unknown holder %r" % (identifier, record.get("holder")))
    retention = record.get("retention_years")
    if not _is_int(retention) or retention < 0:
        raise ValueError(
            "record %s needs a non-negative integer 'retention_years'" % identifier
        )
    day = record.get("recorded_day")
    if not _is_int(day) or day < 0:
        raise ValueError("record %s needs a non-negative integer 'recorded_day'" % identifier)
    normalised = {
        "id": identifier,
        "step": step,
        "rank": step_rank(step),
        "lot_code": lot_code,
        "holder": holder,
        "retention_years": retention,
        "recorded_day": day,
        "cross_reference": _clean_text(record.get("cross_reference")),
        "access_undertaking": _clean_text(record.get("access_undertaking")),
    }
    if holder == HELD_BY_PROJECT and normalised["access_undertaking"]:
        raise ValueError(
            "record %s is held here, so it must not carry an access undertaking" % identifier
        )
    return normalised


def validate_records(records):
    """Return the validated list of traceability records for the lot."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a sequence of traceability records")
    normalised = []
    seen = set()
    for record in records:
        entry = validate_record(record)
        if entry["id"] in seen:
            raise ValueError("duplicate traceability record id %r" % (entry["id"],))
        seen.add(entry["id"])
        normalised.append(entry)
    return normalised


def resolve_identity(records, lot_code, policy=None):
    """Split records into those that speak for the lot and the identity breaks."""
    settings = validate_traceability_policy(policy)
    target = _clean_text(lot_code)
    if not target:
        raise ValueError("the lot under investigation needs a non-empty lot code")
    on_chain = []
    breaks = []
    bridged = []
    for record in records:
        if record["lot_code"] == target:
            on_chain.append(record)
            continue
        if settings["allow_cross_reference_bridge"] and record["cross_reference"] == target:
            bridged.append(record["id"])
            on_chain.append(record)
            continue
        breaks.append(record["id"])
    return {"on_chain": on_chain, "identity_breaks": sorted(breaks), "bridged": sorted(bridged)}


def dispose_steps(on_chain, policy=None):
    """Return how each required step is held, and the records behind it."""
    settings = validate_traceability_policy(policy)
    disposition = {}
    unprotected = []
    for step in settings["required_steps"]:
        candidates = [r for r in on_chain if r["step"] == step]
        if not candidates:
            disposition[step] = {"state": "missing", "records": [], "weight": 0.0}
            continue
        usable = []
        for record in candidates:
            if record["holder"] == HELD_EXTERNALLY:
                if settings["require_access_undertaking"] and not record["access_undertaking"]:
                    unprotected.append(record["id"])
                    continue
            usable.append(record)
        if not usable:
            disposition[step] = {"state": "unprotected", "records": [], "weight": 0.0}
            continue
        held_here = any(r["holder"] == HELD_BY_PROJECT for r in usable)
        weight = 1.0 if held_here else settings["external_record_credit"]
        state = "held-here" if held_here else "held-externally"
        disposition[step] = {
            "state": state,
            "records": sorted(r["id"] for r in usable),
            "weight": weight,
        }
    return {"steps": disposition, "unprotected_records": sorted(unprotected)}


def step_coverage(disposition, policy=None):
    """Return plain and credited coverage of the required handling steps."""
    settings = validate_traceability_policy(policy)
    required = settings["required_steps"]
    total = float(len(required))
    covered = [s for s in required if disposition[s]["weight"] > 0.0]
    plain = float(len(covered)) / total
    credited = sum(disposition[s]["weight"] for s in required) / total
    return {
        "plain": plain,
        "credited": credited,
        "covered_steps": covered,
        "uncovered_steps": [s for s in required if disposition[s]["weight"] <= 0.0],
    }


def retention_shortfalls(on_chain, policy=None):
    """Return the records kept for fewer whole years than the floor requires."""
    settings = validate_traceability_policy(policy)
    floor = settings["min_retention_years"]
    return sorted(r["id"] for r in on_chain if r["retention_years"] < floor)


def order_breaks(on_chain):
    """Return the records whose day contradicts the order of their handling step."""
    ordered = sorted(on_chain, key=lambda r: (r["rank"], r["id"]))
    breaks = []
    highest_day = None
    highest_id = None
    for record in ordered:
        if highest_day is not None and record["recorded_day"] < highest_day:
            breaks.append(
                "record %s for the %s step is dated before record %s from an earlier step"
                % (record["id"], record["step"], highest_id)
            )
        if highest_day is None or record["recorded_day"] > highest_day:
            highest_day = record["recorded_day"]
            highest_id = record["id"]
    return breaks


def assess_lot_traceability(case):
    """Run the clause 5.5.4 traceability assessment over one commercial lot.

    case keys: lot_code (the lot under investigation), records (sequence of
    traceability records), optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("lot_code", "records"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    settings = validate_traceability_policy(case.get("policy"))
    records = validate_records(case["records"])
    identity = resolve_identity(records, case["lot_code"], settings)
    on_chain = identity["on_chain"]

    findings = []
    for identifier in identity["identity_breaks"]:
        findings.append(
            "record %s names another lot with no cross-reference back; the identity "
            "does not carry through it" % identifier
        )

    disposition = dispose_steps(on_chain, settings)
    for identifier in disposition["unprotected_records"]:
        findings.append(
            "record %s is held by another party with no access undertaking recorded"
            % identifier
        )

    coverage = step_coverage(disposition["steps"], settings)
    for step in coverage["uncovered_steps"]:
        findings.append("the %s step carries no usable traceability record" % step)

    plain_short = coverage["plain"] + COVERAGE_TOLERANCE < settings["min_step_coverage"]
    credited_short = (
        coverage["credited"] + COVERAGE_TOLERANCE < settings["min_credited_step_coverage"]
    )
    if plain_short:
        findings.append(
            "plain step coverage %.3f sits below the %.3f floor"
            % (coverage["plain"], settings["min_step_coverage"])
        )
    if credited_short:
        findings.append(
            "credited step coverage %.3f sits below the %.3f floor"
            % (coverage["credited"], settings["min_credited_step_coverage"])
        )

    short_retention = retention_shortfalls(on_chain, settings)
    for identifier in short_retention:
        findings.append(
            "record %s is kept for fewer than the %d years the class requires"
            % (identifier, settings["min_retention_years"])
        )

    out_of_order = order_breaks(on_chain)
    findings.extend(out_of_order)

    first_step = settings["required_steps"][0]
    established = disposition["steps"][first_step]["weight"] > 0.0

    if not on_chain or not established:
        verdict = CHAIN_NOT_ESTABLISHED
        if not on_chain:
            findings.append("no record on file speaks for this lot at all")
        elif first_step not in coverage["uncovered_steps"]:
            findings.append("the %s step is not established for this lot" % first_step)
    elif identity["identity_breaks"]:
        verdict = LOT_IDENTITY_BROKEN
    elif disposition["unprotected_records"]:
        verdict = ACCESS_UNDERTAKING_MISSING
    elif plain_short or credited_short:
        verdict = STEP_COVERAGE_SHORT
    elif short_retention:
        verdict = RETENTION_BELOW_FLOOR
    elif out_of_order:
        verdict = RECORDS_OUT_OF_ORDER
    else:
        verdict = TRACEABILITY_MEETS_CLASS_TWO

    return {
        "verdict": verdict,
        "lot_code": _clean_text(case["lot_code"]),
        "plain_step_coverage": coverage["plain"],
        "credited_step_coverage": coverage["credited"],
        "covered_steps": coverage["covered_steps"],
        "uncovered_steps": coverage["uncovered_steps"],
        "step_disposition": {s: d["state"] for s, d in disposition["steps"].items()},
        "identity_breaks": identity["identity_breaks"],
        "bridged_records": identity["bridged"],
        "unprotected_records": disposition["unprotected_records"],
        "retention_shortfalls": short_retention,
        "order_breaks": out_of_order,
        "chain_established": bool(on_chain) and established,
        "traceable": verdict == TRACEABILITY_MEETS_CLASS_TWO,
        "findings": findings,
    }
