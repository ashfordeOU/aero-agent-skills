"""Deliverable set the foundry supplies alongside an accepted wafer batch.

Anchor: ECSS-Q-ST-60-12C clause 10.2.6 (the items and the records that travel
with each accepted wafer batch when it is handed over).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the batch case: which batch, which revision the paperwork has to
   match, and the conditions that decide which deliverables the batch owes -
   whether it is handed over as die, whether it is a first lot, whether the
   process moved since the last lot, whether a radiation environment applies
   and whether deviations were raised.
2. Derive the required deliverable set from those conditions rather than from
   a fixed list, keeping the reason each item was required.
3. Validate what the foundry actually supplied: known items, known statuses,
   no item supplied twice.
4. Reconcile the two: an item is satisfied only when it is issued AND its
   revision matches the batch revision. A draft, an unsigned copy, a
   superseded issue and a right document at the wrong revision are each
   unusable, and each for a different reason the foundry can act on.
5. Report what is missing, what is unusable and what was supplied without
   being required, with the completeness fraction over the required set.
6. Decide whether the batch is accepted with its paperwork or withheld.
"""

__all__ = [
    "DELIVERABLE_KEYS",
    "SUPPLY_STATUSES",
    "USABLE_STATUS",
    "deliverable_titles",
    "validate_case",
    "required_deliverables",
    "validate_supplied",
    "reconcile_delivery",
    "completeness_fraction",
    "delivery_findings",
    "assess_wafer_deliverables",
]

SUPPLY_STATUSES = ("issued", "draft", "unsigned", "superseded", "absent")

# The one status that can satisfy a required deliverable. Everything else is a
# document that exists without being usable evidence.
USABLE_STATUS = "issued"

_STATUS_REASONS = {
    "draft": "supplied as a draft, which is not issued evidence",
    "unsigned": "supplied unsigned, so nobody has taken responsibility for it",
    "superseded": "supplied at a superseded issue",
    "absent": "listed but not actually supplied",
}


def _rule_always(case):
    return True, "every accepted batch hands this over"


def _rule_die_form(case):
    if case["delivered_as_die"]:
        return True, "the batch is handed over as separated die"
    return False, "the batch stays at wafer level, so the die-form item is not owed"


def _rule_wafer_map(case):
    if case["delivered_as_die"]:
        return True, "a die handover needs the map that locates the accepted dies"
    if case["map_requested"]:
        return True, "the map was requested on the order"
    return False, "no die handover and no map on the order"


def _rule_radiation(case):
    if case["radiation_environment"]:
        return True, "the dies are destined for a radiation environment"
    return False, "no radiation environment declared for this batch"


def _rule_first_lot(case):
    if case["first_lot"]:
        return True, "this is the first lot of this model from this line"
    return False, "not a first lot"


def _rule_process_change(case):
    if case["process_changed"]:
        return True, "the process moved since the previous lot"
    return False, "no process change declared since the previous lot"


def _rule_deviations(case):
    if case["deviations_raised"]:
        return True, "deviations were raised while the batch was running"
    return False, "no deviations raised on this batch"


# key, title, applicability rule.
_DELIVERABLE_REGISTRY = (
    ("certificate-of-conformity", "Certificate of conformity", _rule_always),
    ("wafer-lot-identification", "Wafer and lot identification list", _rule_always),
    ("acceptance-measurement-data", "Wafer acceptance measurement data", _rule_always),
    ("process-monitor-limits", "Process monitor parameter limits", _rule_always),
    ("visual-inspection-record", "Wafer visual inspection record", _rule_always),
    ("wafer-map", "Accepted die wafer map", _rule_wafer_map),
    (
        "storage-and-handling-instruction",
        "Bare die storage and handling instruction",
        _rule_die_form,
    ),
    ("radiation-evaluation-data", "Radiation evaluation data", _rule_radiation),
    ("process-change-notice", "Process change notice", _rule_process_change),
    (
        "first-lot-qualification-report",
        "First lot qualification report",
        _rule_first_lot,
    ),
    ("deviation-and-waiver-list", "Deviation and waiver list", _rule_deviations),
)

DELIVERABLE_KEYS = tuple(entry[0] for entry in _DELIVERABLE_REGISTRY)
_DELIVERABLE_INDEX = {key: i for i, key in enumerate(DELIVERABLE_KEYS)}

_REQUIRED_CASE_KEYS = ("batch_id", "batch_revision")

_OPTIONAL_CASE_DEFAULTS = {
    "delivered_as_die": True,
    "map_requested": False,
    "radiation_environment": False,
    "first_lot": False,
    "process_changed": False,
    "deviations_raised": False,
}


def deliverable_titles():
    """Return the deliverable registry as an ordered key to title mapping."""
    return {entry[0]: entry[1] for entry in _DELIVERABLE_REGISTRY}


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string" % label)
    token = value.strip()
    if not token:
        raise ValueError("%s must not be empty" % label)
    return token


def validate_case(spec):
    """Return the normalised batch case built from spec.

    Unknown keys are refused rather than ignored: a misspelt condition flag
    would silently drop a whole deliverable out of the required set.
    """
    if not isinstance(spec, dict):
        raise ValueError("batch case must be a mapping")
    for key in _REQUIRED_CASE_KEYS:
        if key not in spec:
            raise ValueError("batch case missing required key '%s'" % key)
    allowed = set(_REQUIRED_CASE_KEYS) | set(_OPTIONAL_CASE_DEFAULTS)
    for key in spec:
        if key not in allowed:
            raise ValueError("batch case carries unknown key '%s'" % key)
    case = {
        "batch_id": _identifier(spec["batch_id"], "batch_id"),
        "batch_revision": _identifier(spec["batch_revision"], "batch_revision"),
    }
    for key, default in _OPTIONAL_CASE_DEFAULTS.items():
        value = spec.get(key, default)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean" % key)
        case[key] = value
    return case


def _require_case(case):
    if not isinstance(case, dict):
        raise ValueError("case must be a normalised batch case mapping")
    for key in list(_REQUIRED_CASE_KEYS) + list(_OPTIONAL_CASE_DEFAULTS):
        if key not in case:
            raise ValueError("case is not normalised: missing '%s'" % key)
    return case


def required_deliverables(case):
    """Return the deliverables this batch owes, each with the reason it is owed."""
    _require_case(case)
    titles = deliverable_titles()
    required = []
    for key, _title, rule in _DELIVERABLE_REGISTRY:
        owed, reason = rule(case)
        if owed:
            required.append({"item": key, "title": titles[key], "reason": reason})
    return required


def validate_supplied(raw):
    """Return the normalised list of what the foundry actually handed over."""
    if not isinstance(raw, (list, tuple)):
        raise ValueError("supplied must be a sequence of supplied item records")
    supplied = []
    seen = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("each supplied item must be a mapping")
        for field in entry:
            if field not in ("item", "status", "revision"):
                raise ValueError("supplied item carries unknown field '%s'" % field)
        for field in ("item", "status"):
            if field not in entry:
                raise ValueError("supplied item missing field '%s'" % field)
        item = _identifier(entry["item"], "supplied item").lower()
        if item not in _DELIVERABLE_INDEX:
            raise ValueError("unknown deliverable '%s'" % item)
        if item in seen:
            raise ValueError("deliverable '%s' is supplied more than once" % item)
        seen.add(item)
        status = _identifier(entry["status"], "supplied status").lower()
        if status not in SUPPLY_STATUSES:
            raise ValueError(
                "status '%s' is not one of %s" % (status, ", ".join(SUPPLY_STATUSES))
            )
        revision = entry.get("revision", "")
        if not isinstance(revision, str):
            raise ValueError("supplied revision must be a string")
        supplied.append(
            {"item": item, "status": status, "revision": revision.strip()}
        )
    supplied.sort(key=lambda s: _DELIVERABLE_INDEX[s["item"]])
    return supplied


def reconcile_delivery(case, supplied):
    """Return what is satisfied, missing, unusable and surplus for this batch."""
    _require_case(case)
    if not isinstance(supplied, (list, tuple)):
        raise ValueError("supplied must be the output of validate_supplied")
    titles = deliverable_titles()
    required = required_deliverables(case)
    required_keys = [entry["item"] for entry in required]
    by_item = {}
    for entry in supplied:
        if not isinstance(entry, dict) or "item" not in entry or "status" not in entry:
            raise ValueError("each supplied record must carry 'item' and 'status'")
        if entry["item"] not in _DELIVERABLE_INDEX:
            raise ValueError("unknown deliverable '%s'" % (entry["item"],))
        by_item[entry["item"]] = entry

    satisfied = []
    missing = []
    unusable = []
    for key in required_keys:
        entry = by_item.get(key)
        if entry is None:
            missing.append({"item": key, "title": titles[key],
                            "reason": "not supplied with the batch"})
            continue
        if entry["status"] != USABLE_STATUS:
            unusable.append(
                {
                    "item": key,
                    "title": titles[key],
                    "reason": _STATUS_REASONS.get(
                        entry["status"], "supplied in an unusable state"
                    ),
                }
            )
            continue
        if entry["revision"] != case["batch_revision"]:
            unusable.append(
                {
                    "item": key,
                    "title": titles[key],
                    "reason": "issued at revision '%s' but the batch is revision '%s'"
                    % (entry["revision"] or "(none)", case["batch_revision"]),
                }
            )
            continue
        satisfied.append({"item": key, "title": titles[key]})

    surplus = [
        {"item": entry["item"], "title": titles[entry["item"]]}
        for entry in supplied
        if entry["item"] not in set(required_keys)
    ]
    return {
        "required": required,
        "satisfied": satisfied,
        "missing": missing,
        "unusable": unusable,
        "surplus": surplus,
    }


def completeness_fraction(reconciliation):
    """Return the fraction of the required set that is satisfied."""
    if not isinstance(reconciliation, dict) or "required" not in reconciliation:
        raise ValueError("reconciliation must come from reconcile_delivery")
    required = reconciliation["required"]
    if not required:
        raise ValueError("a batch with no required deliverables is not a valid case")
    return len(reconciliation["satisfied"]) / float(len(required))


def delivery_findings(reconciliation):
    """Return the findings the handover raises, blocking ones first."""
    if not isinstance(reconciliation, dict) or "missing" not in reconciliation:
        raise ValueError("reconciliation must come from reconcile_delivery")
    findings = []
    for entry in reconciliation["missing"]:
        findings.append("'%s' is required and %s" % (entry["title"], entry["reason"]))
    for entry in reconciliation["unusable"]:
        findings.append("'%s' is %s" % (entry["title"], entry["reason"]))
    for entry in reconciliation["surplus"]:
        findings.append(
            "'%s' was supplied but this batch does not owe it; confirm it belongs "
            "to this batch" % entry["title"]
        )
    return findings


def assess_wafer_deliverables(spec):
    """Run the full clause 10.2.6 wafer batch deliverable handover assessment."""
    if not isinstance(spec, dict):
        raise ValueError("handover spec must be a mapping")
    if "supplied" not in spec:
        raise ValueError("handover spec missing required key 'supplied'")
    case_spec = {k: v for k, v in spec.items() if k != "supplied"}
    case = validate_case(case_spec)
    supplied = validate_supplied(spec["supplied"])
    reconciliation = reconcile_delivery(case, supplied)
    findings = delivery_findings(reconciliation)
    blocking = reconciliation["missing"] + reconciliation["unusable"]
    return {
        "case": case,
        "supplied": supplied,
        "required": reconciliation["required"],
        "satisfied": reconciliation["satisfied"],
        "missing": reconciliation["missing"],
        "unusable": reconciliation["unusable"],
        "surplus": reconciliation["surplus"],
        "completeness_fraction": completeness_fraction(reconciliation),
        "findings": findings,
        "accepted": not blocking,
        "disposition": "withhold-batch" if blocking else "accept-batch",
    }
