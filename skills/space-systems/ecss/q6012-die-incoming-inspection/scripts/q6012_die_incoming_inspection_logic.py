"""Incoming inspection of an arriving bare die batch before production release.

Anchor: ECSS-Q-ST-60-12C clause 10.3 (what the buyer checks when a die batch
turns up at goods inwards, and what happens to the batch depending on what
those checks find).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the arrival record: the batch, the quantities from three
   independent places (what was ordered, what the packing list claims, what
   was counted), and the conditions that decide which checks apply.
2. Reconcile the three quantities against each other. A packing list that
   agrees with the count but not with the order is a different problem from a
   count that disagrees with the packing list, and they are reported apart.
3. Derive the applicable check set from the arrival conditions, keeping the
   reason each check applies and the severity a failure of it carries.
4. Take the inspector's outcomes for the judgement checks, but compute the
   quantity check's outcome here from the reconciliation, so the one check
   that can be arithmetic is not left to an assertion.
5. Refuse an incomplete inspection: a missing outcome for an applicable check
   is an error in the record, not a silent pass.
6. Apply the disposition ladder - a failed or skipped critical check rejects,
   a failed or skipped major check quarantines, a minor finding is a
   deviation, and only a wholly clean arrival is released to production.
"""

__all__ = [
    "SEVERITIES",
    "OUTCOMES",
    "CHECK_KEYS",
    "COMPUTED_CHECKS",
    "DISPOSITIONS",
    "check_titles",
    "check_severities",
    "validate_arrival",
    "quantity_reconciliation",
    "applicable_checks",
    "validate_results",
    "check_outcomes",
    "inspection_findings",
    "disposition_for",
    "assess_incoming_inspection",
]

# Ordered worst first; the ladder walks them in this order.
SEVERITIES = ("critical", "major", "minor")

OUTCOMES = ("pass", "fail", "not-performed")

DISPOSITIONS = (
    "reject",
    "quarantine",
    "accept-with-deviation",
    "accept",
)


def _rule_always(arrival):
    return True, "every arriving batch is checked for this"


def _rule_sealed(arrival):
    if arrival["arrived_sealed"]:
        return True, "the batch arrived in a sealed moisture barrier bag"
    return False, "the batch did not arrive sealed, so there is no seal to read"


def _rule_visual_sample(arrival):
    if arrival["visual_sample_required"]:
        return True, "a visual sample is called for on this batch"
    return False, "no visual sample called for on this batch"


def _rule_wafer_map(arrival):
    if arrival["wafer_map_supplied"]:
        return True, "a wafer map came with the batch and can be cross-checked"
    return False, "no wafer map supplied with the batch"


def _rule_radiation(arrival):
    if arrival["radiation_lot"]:
        return True, "the batch is drawn from a radiation evaluated lot"
    return False, "not a radiation evaluated lot"


# key, title, severity if it fails, applicability rule.
_CHECK_REGISTRY = (
    (
        "documentation-completeness",
        "Delivery documentation completeness",
        "critical",
        _rule_always,
    ),
    (
        "identity-and-lot-match",
        "Die identity and lot number match",
        "critical",
        _rule_always,
    ),
    ("packaging-integrity", "Carrier and outer packaging integrity", "critical",
     _rule_always),
    ("visual-sample-inspection", "Visual inspection of the sample", "critical",
     _rule_visual_sample),
    ("quantity-reconciliation", "Quantity reconciliation", "major", _rule_always),
    (
        "electrostatic-handling-evidence",
        "Electrostatic handling evidence in transit",
        "major",
        _rule_always,
    ),
    ("seal-and-desiccant-condition", "Seal and desiccant condition", "major",
     _rule_sealed),
    ("humidity-indicator-reading", "Humidity indicator card reading", "major",
     _rule_sealed),
    ("radiation-lot-identity", "Radiation evaluated lot identity", "major",
     _rule_radiation),
    ("wafer-map-cross-check", "Wafer map cross-check", "minor", _rule_wafer_map),
    ("transit-condition-record", "Transit condition record", "minor", _rule_always),
)

CHECK_KEYS = tuple(entry[0] for entry in _CHECK_REGISTRY)
_CHECK_INDEX = {key: i for i, key in enumerate(CHECK_KEYS)}

# Checks whose outcome this module computes rather than accepts from the
# inspector's report.
COMPUTED_CHECKS = ("quantity-reconciliation",)

_REQUIRED_ARRIVAL_KEYS = (
    "batch_id",
    "ordered_quantity",
    "packing_list_quantity",
    "counted_quantity",
)

_OPTIONAL_ARRIVAL_DEFAULTS = {
    "arrived_sealed": True,
    "visual_sample_required": True,
    "wafer_map_supplied": True,
    "radiation_lot": False,
}


def check_titles():
    """Return the check registry as an ordered key to title mapping."""
    return {entry[0]: entry[1] for entry in _CHECK_REGISTRY}


def check_severities():
    """Return the severity a failure of each check carries."""
    return {entry[0]: entry[2] for entry in _CHECK_REGISTRY}


def _count(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number of dies" % label)
    if value < 0:
        raise ValueError("%s must not be negative" % label)
    return value


def validate_arrival(spec):
    """Return the normalised arrival record built from spec."""
    if not isinstance(spec, dict):
        raise ValueError("arrival record must be a mapping")
    for key in _REQUIRED_ARRIVAL_KEYS:
        if key not in spec:
            raise ValueError("arrival record missing required key '%s'" % key)
    allowed = set(_REQUIRED_ARRIVAL_KEYS) | set(_OPTIONAL_ARRIVAL_DEFAULTS)
    for key in spec:
        if key not in allowed:
            raise ValueError("arrival record carries unknown key '%s'" % key)
    batch_id = spec["batch_id"]
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string")
    arrival = {"batch_id": batch_id.strip()}
    for key in (
        "ordered_quantity",
        "packing_list_quantity",
        "counted_quantity",
    ):
        arrival[key] = _count(spec[key], key)
    if arrival["ordered_quantity"] < 1:
        raise ValueError("ordered_quantity must be at least 1")
    for key, default in _OPTIONAL_ARRIVAL_DEFAULTS.items():
        value = spec.get(key, default)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % key)
        arrival[key] = value
    return arrival


def _require_arrival(arrival):
    if not isinstance(arrival, dict):
        raise ValueError("arrival must be a normalised arrival record")
    for key in list(_REQUIRED_ARRIVAL_KEYS) + list(_OPTIONAL_ARRIVAL_DEFAULTS):
        if key not in arrival:
            raise ValueError("arrival is not normalised: missing '%s'" % key)
    return arrival


def quantity_reconciliation(arrival):
    """Reconcile counted, packing list and ordered quantities against each other."""
    _require_arrival(arrival)
    counted = arrival["counted_quantity"]
    listed = arrival["packing_list_quantity"]
    ordered = arrival["ordered_quantity"]
    packing_delta = counted - listed
    order_delta = counted - ordered
    if packing_delta != 0:
        status = "packing-list-mismatch"
    elif order_delta < 0:
        status = "short-shipped"
    elif order_delta > 0:
        status = "over-shipped"
    else:
        status = "matched"
    return {
        "counted": counted,
        "packing_list": listed,
        "ordered": ordered,
        "packing_delta": packing_delta,
        "order_delta": order_delta,
        "status": status,
    }


def applicable_checks(arrival):
    """Return the checks this arrival calls for, in registry order, with reasons."""
    _require_arrival(arrival)
    titles = check_titles()
    severities = check_severities()
    records = []
    for key, _title, _severity, rule in _CHECK_REGISTRY:
        applies, reason = rule(arrival)
        if applies:
            records.append(
                {
                    "check": key,
                    "title": titles[key],
                    "severity": severities[key],
                    "reason": reason,
                    "computed": key in COMPUTED_CHECKS,
                }
            )
    return records


def validate_results(raw, applicable):
    """Return the inspector's outcomes, refusing an incomplete inspection record."""
    if not isinstance(raw, dict):
        raise ValueError("results must be a mapping of check key to outcome")
    if not isinstance(applicable, (list, tuple)):
        raise ValueError("applicable must come from applicable_checks")
    expected = set()
    for record in applicable:
        if not isinstance(record, dict) or "check" not in record:
            raise ValueError("each applicable record must carry 'check'")
        if record["check"] not in COMPUTED_CHECKS:
            expected.add(record["check"])
    results = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ValueError("check key must be a string")
        token = key.strip().lower()
        if token not in _CHECK_INDEX:
            raise ValueError("unknown check '%s'" % key)
        if token in COMPUTED_CHECKS:
            raise ValueError(
                "check '%s' is computed from the arrival record and must not be "
                "reported" % token
            )
        if token not in expected:
            raise ValueError(
                "check '%s' is reported but does not apply to this arrival" % token
            )
        if not isinstance(value, str):
            raise ValueError("outcome for '%s' must be a string" % token)
        outcome = value.strip().lower()
        if outcome not in OUTCOMES:
            raise ValueError(
                "outcome '%s' for '%s' is not one of %s"
                % (value, token, ", ".join(OUTCOMES))
            )
        results[token] = outcome
    for key in sorted(expected, key=lambda k: _CHECK_INDEX[k]):
        if key not in results:
            raise ValueError(
                "inspection record has no outcome for applicable check '%s'" % key
            )
    return results


def check_outcomes(arrival, results):
    """Return one outcome record per applicable check, computed where possible."""
    _require_arrival(arrival)
    reconciliation = quantity_reconciliation(arrival)
    records = []
    for record in applicable_checks(arrival):
        entry = dict(record)
        if record["check"] in COMPUTED_CHECKS:
            entry["outcome"] = (
                "pass" if reconciliation["status"] == "matched" else "fail"
            )
            entry["detail"] = reconciliation["status"]
        else:
            if record["check"] not in results:
                raise ValueError(
                    "no outcome supplied for applicable check '%s'" % record["check"]
                )
            entry["outcome"] = results[record["check"]]
            entry["detail"] = ""
        records.append(entry)
    return records


def inspection_findings(outcomes):
    """Return a finding for every check that did not cleanly pass."""
    if not isinstance(outcomes, (list, tuple)):
        raise ValueError("outcomes must come from check_outcomes")
    findings = []
    for severity in SEVERITIES:
        for record in outcomes:
            if not isinstance(record, dict) or "outcome" not in record:
                raise ValueError("each outcome record must carry 'outcome'")
            if record["severity"] != severity:
                continue
            if record["outcome"] == "fail":
                detail = " (%s)" % record["detail"] if record.get("detail") else ""
                findings.append(
                    "%s check failed: %s%s" % (severity, record["title"], detail)
                )
            elif record["outcome"] == "not-performed":
                findings.append(
                    "%s check was not performed: %s; an unperformed check is not a "
                    "pass" % (severity, record["title"])
                )
    return findings


def disposition_for(outcomes):
    """Return the batch disposition the outcome set drives."""
    if not isinstance(outcomes, (list, tuple)) or not outcomes:
        raise ValueError("outcomes must be a non-empty sequence from check_outcomes")
    unclean = {"fail", "not-performed"}
    worst = None
    for record in outcomes:
        if not isinstance(record, dict) or "severity" not in record:
            raise ValueError("each outcome record must carry 'severity'")
        if record["severity"] not in SEVERITIES:
            raise ValueError("unknown severity '%s'" % (record["severity"],))
        if record["outcome"] in unclean:
            rank = SEVERITIES.index(record["severity"])
            if worst is None or rank < worst:
                worst = rank
    if worst is None:
        return "accept"
    if SEVERITIES[worst] == "critical":
        return "reject"
    if SEVERITIES[worst] == "major":
        return "quarantine"
    return "accept-with-deviation"


def assess_incoming_inspection(spec):
    """Run the full clause 10.3 incoming inspection of an arriving die batch."""
    if not isinstance(spec, dict):
        raise ValueError("inspection spec must be a mapping")
    if "results" not in spec:
        raise ValueError("inspection spec missing required key 'results'")
    arrival = validate_arrival({k: v for k, v in spec.items() if k != "results"})
    applicable = applicable_checks(arrival)
    results = validate_results(spec["results"], applicable)
    outcomes = check_outcomes(arrival, results)
    findings = inspection_findings(outcomes)
    disposition = disposition_for(outcomes)
    passed = sum(1 for record in outcomes if record["outcome"] == "pass")
    return {
        "arrival": arrival,
        "quantities": quantity_reconciliation(arrival),
        "applicable_checks": applicable,
        "outcomes": outcomes,
        "passed_checks": passed,
        "pass_fraction": passed / float(len(outcomes)),
        "findings": findings,
        "disposition": disposition,
        "release_to_production": disposition == "accept",
    }
