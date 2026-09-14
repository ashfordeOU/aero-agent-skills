"""Alert monitoring and response assessment at the intermediate assurance class.

Anchor: ECSS-Q-ST-60-13C clause 5.5.3 (watching the manufacturer alert channels
that serve commercial EEE parts, and answering what arrives on them).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the monitoring policy: the required source categories, the sweep
   interval that keeps a source live, the plain and credited coverage floors,
   the credit a delegated subscription earns, the forwarding lag it may carry
   and the two response deadlines in working days.
2. Validate every declared alert source. A source is watched directly by the
   project or through a subscription delegated to another party; a delegated
   source is only a source where the delegation is recorded and its forwarding
   lag stays inside the bound.
3. Discount a source whose last confirmed sweep is older than the monitoring
   interval. A stale subscription is not a covered category; it is a category
   nobody has looked at recently.
4. Take the plain coverage over the required categories and the credited
   coverage with the delegation credit applied, and compare both with floors.
5. Dispose every alert on the desk: an applicable alert needs an action, a
   not-applicable alert needs a recorded rationale, and an alert with neither
   is undisposed.
6. Count acknowledgement and disposition working days from receipt, letting an
   open step accrue to the assessment day, and compare them with the deadlines.
7. Return one verdict in precedence order: monitoring not established, a
   delegation nobody recorded, coverage short of its floor, a disposition with
   no rationale behind it, a response past its deadline, or alert handling that
   meets the intermediate class.
"""

__all__ = [
    "DAYS_PER_WEEK",
    "COVERAGE_TOLERANCE",
    "RECOGNISED_SOURCE_CATEGORIES",
    "DIRECT",
    "DELEGATED",
    "APPLICABLE",
    "NOT_APPLICABLE",
    "DEFAULT_MONITORING_POLICY",
    "MONITORING_NOT_ESTABLISHED",
    "DELEGATION_NOT_RECORDED",
    "SOURCE_COVERAGE_SHORT",
    "DISPOSITION_UNJUSTIFIED",
    "RESPONSE_OVERDUE",
    "ALERT_HANDLING_MEETS_CLASS_TWO",
    "validate_monitoring_policy",
    "working_days_between",
    "validate_source",
    "validate_sources",
    "source_is_live",
    "effective_sources",
    "category_coverage",
    "validate_alert",
    "validate_alerts",
    "alert_response_timing",
    "assess_alert_handling",
]

DAYS_PER_WEEK = 7

# Coverage figures are ratios of small integer counts turned into floats. A
# coverage that lands exactly on its floor must read as met, so every
# comparison runs through this tolerance rather than as a bare inequality.
COVERAGE_TOLERANCE = 1e-9

DIRECT = "direct"
DELEGATED = "delegated"

APPLICABLE = "applicable"
NOT_APPLICABLE = "not-applicable"

RECOGNISED_SOURCE_CATEGORIES = (
    "manufacturer-notice",
    "distributor-notice",
    "agency-alert-service",
    "industry-alert-exchange",
)

MONITORING_NOT_ESTABLISHED = "monitoring-not-established"
DELEGATION_NOT_RECORDED = "delegation-not-recorded"
SOURCE_COVERAGE_SHORT = "source-coverage-short"
DISPOSITION_UNJUSTIFIED = "disposition-unjustified"
RESPONSE_OVERDUE = "response-overdue"
ALERT_HANDLING_MEETS_CLASS_TWO = "alert-handling-meets-class-two"

DEFAULT_MONITORING_POLICY = {
    # Categories the intermediate class expects somebody to be watching.
    "required_source_categories": list(RECOGNISED_SOURCE_CATEGORIES),
    # A source not swept inside this many days is stale, not covered.
    "monitoring_interval_days": 30,
    # Share of required categories that must be covered at all.
    "min_source_coverage": 0.75,
    # Share once a delegated subscription is weighed below a direct one.
    "min_credited_source_coverage": 0.5,
    # What a delegated subscription is worth against a direct one.
    "delegated_source_credit": 0.5,
    # Longest forwarding lag a delegated subscription may carry, in days.
    "max_forwarding_days": 5,
    # Response deadlines, in working days from receipt of the alert.
    "acknowledgement_working_days": 5,
    "disposition_working_days": 20,
    # Whether a not-applicable disposition has to carry a written rationale.
    "require_rationale_for_not_applicable": True,
}

_INTEGER_POLICY_KEYS = (
    "monitoring_interval_days",
    "max_forwarding_days",
    "acknowledgement_working_days",
    "disposition_working_days",
)

_RATIO_POLICY_KEYS = (
    "min_source_coverage",
    "min_credited_source_coverage",
    "delegated_source_credit",
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _clean_text(value):
    return value.strip() if isinstance(value, str) else ""


def validate_monitoring_policy(policy=None):
    """Return a complete monitoring policy, defaults filled in."""
    if policy is None:
        return {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in DEFAULT_MONITORING_POLICY.items()
        }
    if not isinstance(policy, dict):
        raise ValueError("monitoring policy must be a mapping")
    merged = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in DEFAULT_MONITORING_POLICY.items()
    }
    for key, value in policy.items():
        if key not in DEFAULT_MONITORING_POLICY:
            raise ValueError("unknown monitoring policy key %r" % (key,))
        merged[key] = list(value) if isinstance(value, (list, tuple)) else value
    categories = merged["required_source_categories"]
    if not isinstance(categories, list) or not categories:
        raise ValueError("required_source_categories must be a non-empty list")
    seen = set()
    for category in categories:
        name = _clean_text(category)
        if not name:
            raise ValueError("a required source category must not be blank")
        if name not in RECOGNISED_SOURCE_CATEGORIES:
            raise ValueError("unrecognised source category %r" % (category,))
        if name in seen:
            raise ValueError("duplicate required source category %r" % (name,))
        seen.add(name)
    merged["required_source_categories"] = [_clean_text(c) for c in categories]
    for key in _INTEGER_POLICY_KEYS:
        if not _is_int(merged[key]):
            raise ValueError("%s must be an integer, got %r" % (key, merged[key]))
        if merged[key] < 0:
            raise ValueError("%s must not be negative" % key)
    for key in _RATIO_POLICY_KEYS:
        value = merged[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a number, got %r" % (key, value))
        if not 0.0 < float(value) <= 1.0:
            raise ValueError("%s must lie in (0, 1]" % key)
        merged[key] = float(value)
    if merged["min_credited_source_coverage"] > merged["min_source_coverage"]:
        raise ValueError(
            "the credited coverage floor must not sit above the plain floor; a "
            "delegated subscription is worth less, never more"
        )
    if not isinstance(merged["require_rationale_for_not_applicable"], bool):
        raise ValueError("require_rationale_for_not_applicable must be a boolean")
    return merged


def working_days_between(start_day, end_day):
    """Return elapsed working days between two day indices, weekends removed.

    Day indices are whole days on one project calendar whose day 0 is a Monday.
    The count is exact integer arithmetic, so the same pair of dates yields the
    same answer on any machine.
    """
    if not _is_int(start_day) or not _is_int(end_day):
        raise ValueError("day indices must be integers")
    if start_day < 0 or end_day < 0:
        raise ValueError("day indices must not be negative")
    if end_day < start_day:
        raise ValueError("the later day must not precede the earlier one")
    whole_weeks, remainder = divmod(end_day - start_day, DAYS_PER_WEEK)
    count = whole_weeks * 5
    weekday = start_day % DAYS_PER_WEEK
    for offset in range(remainder):
        if (weekday + offset) % DAYS_PER_WEEK < 5:
            count += 1
    return count


def validate_source(source):
    """Return a normalised alert source record."""
    if not isinstance(source, dict):
        raise ValueError("each source must be a mapping, got %r" % (type(source).__name__,))
    identifier = _clean_text(source.get("id"))
    if not identifier:
        raise ValueError("each alert source needs a non-empty 'id'")
    category = _clean_text(source.get("category"))
    if category not in RECOGNISED_SOURCE_CATEGORIES:
        raise ValueError(
            "source %s carries an unrecognised category %r" % (identifier, source.get("category"))
        )
    mode = _clean_text(source.get("mode")) or DIRECT
    if mode not in (DIRECT, DELEGATED):
        raise ValueError("source %s has an unknown mode %r" % (identifier, source.get("mode")))
    last_sweep = source.get("last_sweep_day")
    if not _is_int(last_sweep) or last_sweep < 0:
        raise ValueError("source %s needs a non-negative integer 'last_sweep_day'" % identifier)
    record = {
        "id": identifier,
        "category": category,
        "mode": mode,
        "last_sweep_day": last_sweep,
        "delegation_record": _clean_text(source.get("delegation_record")),
        "forwarding_days": 0,
    }
    if mode == DELEGATED:
        forwarding = source.get("forwarding_days")
        if not _is_int(forwarding) or forwarding < 0:
            raise ValueError(
                "delegated source %s needs a non-negative integer 'forwarding_days'" % identifier
            )
        record["forwarding_days"] = forwarding
    elif source.get("delegation_record"):
        raise ValueError(
            "source %s is watched directly, so it must not carry a delegation record" % identifier
        )
    return record


def validate_sources(sources):
    """Return the validated list of declared alert sources."""
    if not isinstance(sources, (list, tuple)):
        raise ValueError("sources must be a sequence of source records")
    records = []
    seen = set()
    for source in sources:
        record = validate_source(source)
        if record["id"] in seen:
            raise ValueError("duplicate alert source id %r" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    return records


def source_is_live(record, as_of_day, policy=None):
    """Return whether a source was swept recently enough to count as watched."""
    settings = validate_monitoring_policy(policy)
    if not _is_int(as_of_day) or as_of_day < 0:
        raise ValueError("as_of_day must be a non-negative integer")
    if record["last_sweep_day"] > as_of_day:
        raise ValueError(
            "source %s reports a sweep after the assessment day" % (record["id"],)
        )
    return as_of_day - record["last_sweep_day"] <= settings["monitoring_interval_days"]


def effective_sources(records, as_of_day, policy=None):
    """Split declared sources into those that count and the reasons the rest do not."""
    settings = validate_monitoring_policy(policy)
    counted = []
    stale = []
    unrecorded = []
    slow = []
    for record in records:
        if record["mode"] == DELEGATED and not record["delegation_record"]:
            unrecorded.append(record["id"])
            continue
        if record["mode"] == DELEGATED and record["forwarding_days"] > settings["max_forwarding_days"]:
            slow.append(record["id"])
            continue
        if not source_is_live(record, as_of_day, settings):
            stale.append(record["id"])
            continue
        counted.append(record)
    return {
        "counted": counted,
        "stale": sorted(stale),
        "unrecorded_delegations": sorted(unrecorded),
        "slow_forwarding": sorted(slow),
    }


def category_coverage(counted, policy=None):
    """Return plain and credited coverage of the required source categories."""
    settings = validate_monitoring_policy(policy)
    required = settings["required_source_categories"]
    credit = settings["delegated_source_credit"]
    best = {}
    for record in counted:
        if record["category"] not in required:
            continue
        weight = 1.0 if record["mode"] == DIRECT else credit
        if weight > best.get(record["category"], 0.0):
            best[record["category"]] = weight
    total = len(required)
    plain = float(len(best)) / float(total)
    credited = sum(best.values()) / float(total)
    uncovered = sorted(c for c in required if c not in best)
    return {
        "plain": plain,
        "credited": credited,
        "covered_categories": sorted(best),
        "uncovered_categories": uncovered,
        "required_categories": list(required),
    }


def validate_alert(alert):
    """Return a normalised alert record from the project's alert desk."""
    if not isinstance(alert, dict):
        raise ValueError("each alert must be a mapping, got %r" % (type(alert).__name__,))
    identifier = _clean_text(alert.get("id"))
    if not identifier:
        raise ValueError("each alert needs a non-empty 'id'")
    received = alert.get("received_day")
    if not _is_int(received) or received < 0:
        raise ValueError("alert %s needs a non-negative integer 'received_day'" % identifier)
    record = {
        "id": identifier,
        "received_day": received,
        "acknowledged_day": None,
        "disposition": None,
        "disposition_day": None,
        "rationale": _clean_text(alert.get("rationale")),
        "action": _clean_text(alert.get("action")),
    }
    acknowledged = alert.get("acknowledged_day")
    if acknowledged is not None:
        if not _is_int(acknowledged) or acknowledged < received:
            raise ValueError(
                "alert %s was acknowledged before it was received" % identifier
            )
        record["acknowledged_day"] = acknowledged
    disposition = alert.get("disposition")
    if disposition is not None:
        name = _clean_text(disposition)
        if name not in (APPLICABLE, NOT_APPLICABLE):
            raise ValueError("alert %s has an unknown disposition %r" % (identifier, disposition))
        record["disposition"] = name
        day = alert.get("disposition_day")
        if not _is_int(day) or day < received:
            raise ValueError(
                "alert %s needs a 'disposition_day' at or after receipt" % identifier
            )
        record["disposition_day"] = day
    return record


def validate_alerts(alerts):
    """Return the validated list of alerts sitting on the desk."""
    if alerts is None:
        return []
    if not isinstance(alerts, (list, tuple)):
        raise ValueError("alerts must be a sequence of alert records")
    records = []
    seen = set()
    for alert in alerts:
        record = validate_alert(alert)
        if record["id"] in seen:
            raise ValueError("duplicate alert id %r" % (record["id"],))
        seen.add(record["id"])
        records.append(record)
    return records


def alert_response_timing(record, as_of_day, policy=None):
    """Return the two working-day counts an alert has accrued, and their breaches."""
    settings = validate_monitoring_policy(policy)
    if not _is_int(as_of_day) or as_of_day < 0:
        raise ValueError("as_of_day must be a non-negative integer")
    if record["received_day"] > as_of_day:
        raise ValueError("alert %s was received after the assessment day" % (record["id"],))
    for key in ("acknowledged_day", "disposition_day"):
        if record[key] is not None and record[key] > as_of_day:
            raise ValueError(
                "alert %s records a %s after the assessment day" % (record["id"], key)
            )
    # An open step keeps accruing: with nothing recorded the clock runs to the
    # day the assessment is taken, never stopping quietly at receipt.
    ack_end = record["acknowledged_day"] if record["acknowledged_day"] is not None else as_of_day
    disp_end = record["disposition_day"] if record["disposition_day"] is not None else as_of_day
    ack_days = working_days_between(record["received_day"], ack_end)
    disp_days = working_days_between(record["received_day"], disp_end)
    breaches = []
    if ack_days > settings["acknowledgement_working_days"]:
        breaches.append(
            "alert %s took %d working days to acknowledge against a limit of %d"
            % (record["id"], ack_days, settings["acknowledgement_working_days"])
        )
    if disp_days > settings["disposition_working_days"]:
        breaches.append(
            "alert %s has run %d working days to disposition against a limit of %d"
            % (record["id"], disp_days, settings["disposition_working_days"])
        )
    return {
        "id": record["id"],
        "acknowledgement_working_days": ack_days,
        "disposition_working_days": disp_days,
        "acknowledged": record["acknowledged_day"] is not None,
        "dispositioned": record["disposition"] is not None,
        "breaches": breaches,
    }


def assess_alert_handling(case):
    """Run the clause 5.5.3 alert monitoring and response assessment.

    case keys: sources (sequence of declared alert sources), as_of_day (the
    integer day the assessment is taken on), optional alerts, optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("sources", "as_of_day"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    settings = validate_monitoring_policy(case.get("policy"))
    as_of_day = case["as_of_day"]
    if not _is_int(as_of_day) or as_of_day < 0:
        raise ValueError("as_of_day must be a non-negative integer")
    sources = validate_sources(case["sources"])
    alerts = validate_alerts(case.get("alerts"))

    findings = []
    if not sources:
        return {
            "verdict": MONITORING_NOT_ESTABLISHED,
            "plain_source_coverage": 0.0,
            "credited_source_coverage": 0.0,
            "covered_categories": [],
            "uncovered_categories": list(settings["required_source_categories"]),
            "stale_sources": [],
            "unrecorded_delegations": [],
            "slow_forwarding_sources": [],
            "alert_timing": [],
            "undisposed_alerts": [],
            "unjustified_alerts": [],
            "monitoring_established": False,
            "findings": ["no alert source is declared, so nothing is being watched"],
        }

    split = effective_sources(sources, as_of_day, settings)
    coverage = category_coverage(split["counted"], settings)

    for identifier in split["unrecorded_delegations"]:
        findings.append(
            "source %s is watched under a delegation nobody recorded, so it covers nothing"
            % identifier
        )
    for identifier in split["slow_forwarding"]:
        findings.append(
            "source %s forwards later than the %d day bound the class admits"
            % (identifier, settings["max_forwarding_days"])
        )
    for identifier in split["stale"]:
        findings.append(
            "source %s was last swept more than %d days ago and is not a live source"
            % (identifier, settings["monitoring_interval_days"])
        )
    for category in coverage["uncovered_categories"]:
        findings.append("no live source covers the %s category" % category)

    plain_short = coverage["plain"] + COVERAGE_TOLERANCE < settings["min_source_coverage"]
    credited_short = (
        coverage["credited"] + COVERAGE_TOLERANCE < settings["min_credited_source_coverage"]
    )
    if plain_short:
        findings.append(
            "plain source coverage %.3f sits below the %.3f floor"
            % (coverage["plain"], settings["min_source_coverage"])
        )
    if credited_short:
        findings.append(
            "credited source coverage %.3f sits below the %.3f floor"
            % (coverage["credited"], settings["min_credited_source_coverage"])
        )

    timing = []
    undisposed = []
    unjustified = []
    overdue = []
    for record in alerts:
        entry = alert_response_timing(record, as_of_day, settings)
        timing.append(entry)
        if entry["breaches"]:
            overdue.append(record["id"])
            findings.extend(entry["breaches"])
        if record["disposition"] is None:
            undisposed.append(record["id"])
            findings.append("alert %s carries no disposition at all" % record["id"])
        elif record["disposition"] == NOT_APPLICABLE:
            if settings["require_rationale_for_not_applicable"] and not record["rationale"]:
                unjustified.append(record["id"])
                findings.append(
                    "alert %s was set aside as not applicable with no rationale recorded"
                    % record["id"]
                )
        elif not record["action"]:
            undisposed.append(record["id"])
            findings.append(
                "alert %s is applicable but names no action" % record["id"]
            )

    if not split["counted"]:
        verdict = MONITORING_NOT_ESTABLISHED
    elif split["unrecorded_delegations"]:
        verdict = DELEGATION_NOT_RECORDED
    elif plain_short or credited_short:
        verdict = SOURCE_COVERAGE_SHORT
    elif unjustified or undisposed:
        verdict = DISPOSITION_UNJUSTIFIED
    elif overdue:
        verdict = RESPONSE_OVERDUE
    else:
        verdict = ALERT_HANDLING_MEETS_CLASS_TWO

    return {
        "verdict": verdict,
        "plain_source_coverage": coverage["plain"],
        "credited_source_coverage": coverage["credited"],
        "covered_categories": coverage["covered_categories"],
        "uncovered_categories": coverage["uncovered_categories"],
        "stale_sources": split["stale"],
        "unrecorded_delegations": split["unrecorded_delegations"],
        "slow_forwarding_sources": split["slow_forwarding"],
        "alert_timing": timing,
        "undisposed_alerts": sorted(set(undisposed)),
        "unjustified_alerts": sorted(set(unjustified)),
        "overdue_alerts": sorted(set(overdue)),
        "monitoring_established": bool(split["counted"]),
        "findings": findings,
    }
