"""Verification of safety-critical functions: activities, failure tests, closure.

Anchor: ECSS-Q-ST-40C clause on the verification of safety-critical functions --
validation, qualification, failure testing, verification of design and
operational characteristics, and safety verification testing. Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. A safety-critical function's criticality category fixes WHICH verification
   activities it owes. The set grows as criticality rises; it is never chosen
   by the team.
2. An owed activity is discharged only by a passed record with an evidence
   reference. Not-run is an omission, failed is a stop, and a waiver is a
   narrow escape hatch: it needs its own reference and it is not available at
   the top category at all.
3. Failure testing is graded by coverage of the function's declared failure
   modes, not by whether any failure test happened. The required fraction
   rises with criticality.
4. Activities the category does not owe are reported as supplementary rather
   than silently dropped, because they are still evidence.
5. Close the function: verified, verified with open actions, or not verified,
   and say which activity or which uncovered failure mode did it.
"""

__all__ = [
    "ACTIVITIES",
    "CRITICALITY_CATEGORIES",
    "STATUSES",
    "REQUIRED_ACTIVITIES",
    "REQUIRED_FAILURE_COVERAGE",
    "WAIVABLE_CATEGORIES",
    "COVERAGE_TOLERANCE",
    "validate_function",
    "required_activities",
    "activity_index",
    "outstanding_activities",
    "supplementary_activities",
    "failure_test_coverage",
    "failure_coverage_met",
    "verify_critical_function",
    "verify_function_set",
]

ACTIVITIES = (
    "validation",
    "qualification",
    "failure-test",
    "design-characteristic-verification",
    "operational-characteristic-verification",
    "safety-verification-test",
)

CRITICALITY_CATEGORIES = ("catastrophic", "critical", "major")

STATUSES = ("passed", "failed", "not-run", "waived")

# What each category owes. The set only ever grows with criticality.
REQUIRED_ACTIVITIES = {
    "catastrophic": ACTIVITIES,
    "critical": (
        "validation",
        "qualification",
        "failure-test",
        "design-characteristic-verification",
        "safety-verification-test",
    ),
    "major": (
        "validation",
        "qualification",
        "design-characteristic-verification",
    ),
}

# Fraction of the declared failure modes that failure testing has to reach.
REQUIRED_FAILURE_COVERAGE = {
    "catastrophic": 1.0,
    "critical": 0.8,
    "major": 0.5,
}

# A waiver cannot stand in for an owed activity at the top category.
WAIVABLE_CATEGORIES = ("critical", "major")

# Coverage is an int/int division compared against a stored fraction; the
# comparison carries this slack so a value that should sit on the bound is
# not pushed under it by the last bit of the division.
COVERAGE_TOLERANCE = 1e-9


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _member(value, label, allowed):
    token = _text(value, label).lower()
    if token not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(allowed), value)
        )
    return token


def _unique_tokens(values, label, allowed=None):
    if not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a sequence, got %r" % (label, values))
    out = []
    for value in values:
        token = _text(value, "%s entry" % label).lower()
        if allowed is not None and token not in allowed:
            raise ValueError(
                "%s entry must be one of %s, got %r" % (label, ", ".join(allowed), value)
            )
        if token in out:
            raise ValueError("%s repeats %r" % (label, token))
        out.append(token)
    return out


def validate_function(record):
    """Return a normalised safety-critical-function verification record."""
    if not isinstance(record, dict):
        raise ValueError("function record must be a mapping")
    category = _member(
        record.get("criticality"), "criticality", CRITICALITY_CATEGORIES
    )
    failure_modes = _unique_tokens(record.get("failure_modes", []), "failure_modes")

    raw_activities = record.get("activities", [])
    if not isinstance(raw_activities, (list, tuple)):
        raise ValueError("activities must be a sequence")
    activities = []
    seen = set()
    for entry in raw_activities:
        if not isinstance(entry, dict):
            raise ValueError("each activity must be a mapping, got %r" % (entry,))
        name = _member(entry.get("name"), "activity name", ACTIVITIES)
        if name in seen:
            raise ValueError("activity %r is recorded twice" % name)
        seen.add(name)
        status = _member(entry.get("status"), "activity status", STATUSES)
        evidence = entry.get("evidence_ref")
        if evidence is not None:
            evidence = _text(evidence, "evidence_ref")
        waiver = entry.get("waiver_ref")
        if waiver is not None:
            waiver = _text(waiver, "waiver_ref")
        covered = _unique_tokens(
            entry.get("failure_modes_covered", []), "failure_modes_covered"
        )
        unknown = [mode for mode in covered if mode not in failure_modes]
        if unknown:
            raise ValueError(
                "failure_modes_covered names modes not declared on the function: %s"
                % ", ".join(unknown)
            )
        activities.append(
            {
                "name": name,
                "status": status,
                "evidence_ref": evidence,
                "waiver_ref": waiver,
                "failure_modes_covered": covered,
            }
        )

    return {
        "id": _text(record.get("id"), "id"),
        "criticality": category,
        "failure_modes": failure_modes,
        "activities": activities,
    }


def required_activities(criticality):
    """Return the activities a criticality category owes."""
    return REQUIRED_ACTIVITIES[
        _member(criticality, "criticality", CRITICALITY_CATEGORIES)
    ]


def activity_index(record):
    """Return the function's activities keyed by activity name."""
    return dict((item["name"], item) for item in validate_function(record)["activities"])


def outstanding_activities(record):
    """Return one finding per owed activity that is not properly discharged."""
    norm = validate_function(record)
    index = activity_index(norm)
    findings = []
    for name in required_activities(norm["criticality"]):
        item = index.get(name)
        if item is None:
            findings.append(
                {"activity": name, "reason": "owed activity has no record at all"}
            )
            continue
        if item["status"] == "failed":
            findings.append({"activity": name, "reason": "activity record is a failure"})
        elif item["status"] == "not-run":
            findings.append({"activity": name, "reason": "activity has not been run"})
        elif item["status"] == "waived":
            if norm["criticality"] not in WAIVABLE_CATEGORIES:
                findings.append(
                    {
                        "activity": name,
                        "reason": "a waiver cannot discharge this activity at %s"
                        % norm["criticality"],
                    }
                )
            elif item["waiver_ref"] is None:
                findings.append(
                    {"activity": name, "reason": "waived with no waiver reference"}
                )
        elif item["evidence_ref"] is None:
            findings.append(
                {"activity": name, "reason": "passed with no evidence reference"}
            )
    return findings


def supplementary_activities(record):
    """Return recorded activities the category does not owe."""
    norm = validate_function(record)
    owed = required_activities(norm["criticality"])
    return [item["name"] for item in norm["activities"] if item["name"] not in owed]


def failure_test_coverage(record):
    """Return the fraction of declared failure modes reached by failure testing."""
    norm = validate_function(record)
    if not norm["failure_modes"]:
        raise ValueError("the function declares no failure modes to cover")
    covered = set()
    for item in norm["activities"]:
        if item["name"] == "failure-test" and item["status"] == "passed":
            covered.update(item["failure_modes_covered"])
    return len(covered) / float(len(norm["failure_modes"]))


def failure_coverage_met(record):
    """Return whether failure testing reaches the fraction the category demands."""
    norm = validate_function(record)
    if "failure-test" not in required_activities(norm["criticality"]):
        return True
    needed = REQUIRED_FAILURE_COVERAGE[norm["criticality"]]
    return failure_test_coverage(norm) + COVERAGE_TOLERANCE >= needed


def verify_critical_function(record):
    """Return the verification disposition for one safety-critical function."""
    norm = validate_function(record)
    outstanding = outstanding_activities(norm)
    findings = [
        "%s: %s" % (item["activity"], item["reason"]) for item in outstanding
    ]

    coverage = None
    needed = REQUIRED_FAILURE_COVERAGE[norm["criticality"]]
    if "failure-test" in required_activities(norm["criticality"]):
        coverage = failure_test_coverage(norm)
        if not failure_coverage_met(norm):
            findings.append(
                "failure testing reaches %d of %d declared failure modes, below the"
                " fraction a %s function owes"
                % (
                    int(round(coverage * len(norm["failure_modes"]))),
                    len(norm["failure_modes"]),
                    norm["criticality"],
                )
            )

    # A missing evidence reference on an otherwise passed activity is an
    # administrative gap; every other outstanding reason means the activity
    # was not actually discharged, and those stop the function.
    blocking = [
        item
        for item in outstanding
        if item["reason"] != "passed with no evidence reference"
    ]
    if blocking or (coverage is not None and not failure_coverage_met(norm)):
        disposition = "function-not-verified"
    elif findings:
        disposition = "function-verified-with-open-actions"
    else:
        disposition = "function-verified"

    return {
        "id": norm["id"],
        "criticality": norm["criticality"],
        "required_activities": list(required_activities(norm["criticality"])),
        "outstanding_activities": outstanding,
        "supplementary_activities": supplementary_activities(norm),
        "failure_test_coverage": coverage,
        "required_failure_coverage": needed,
        "findings": findings,
        "verified": disposition == "function-verified",
        "disposition": disposition,
    }


def verify_function_set(records):
    """Return the verification rollup across a set of safety-critical functions."""
    items = list(records)
    if not items:
        raise ValueError("at least one safety-critical function is needed")
    reports = [verify_critical_function(item) for item in items]
    seen = set()
    for report in reports:
        if report["id"] in seen:
            raise ValueError("duplicate function id %r" % report["id"])
        seen.add(report["id"])
    unverified = [r["id"] for r in reports if r["disposition"] == "function-not-verified"]
    open_actions = [
        r["id"] for r in reports if r["disposition"] == "function-verified-with-open-actions"
    ]
    verified_ratio = sum(1 for r in reports if r["verified"]) / float(len(reports))
    if unverified:
        disposition = "set-not-verified"
    elif open_actions:
        disposition = "set-verified-with-open-actions"
    else:
        disposition = "set-verified"
    return {
        "functions": reports,
        "unverified_ids": unverified,
        "open_action_ids": open_actions,
        "verified_ratio": verified_ratio,
        "disposition": disposition,
    }
