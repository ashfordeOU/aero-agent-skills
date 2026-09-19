"""Execution and documentation ledger for device validation.

Anchor: ECSS-E-ST-20-40C clause 5.8.2 (validation, qualification and
acceptance phase -- running and documenting the validation activities that
prove the device meets its intended purpose). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the execution ledger: one record per planned validation case,
   carrying its state, outcome, the device configuration it ran on, and the
   reference to the evidence it produced.
2. Measure how much of the plan has actually been run, and of that, how much
   passed.
3. Find the evidence that does not exist: a case reported run with no
   evidence reference documents nothing.
4. Find the evidence that proves the wrong article: a case run on a
   configuration other than the delivered one.
5. Propagate retest. A failed case invalidates every case that depends on
   it, transitively, so the retest set is a closure over the dependency
   graph and not just the failure list.
6. Combine execution, outcome and documentation into a completeness index
   and decide whether validation can be declared complete.
"""

import math

__all__ = [
    "COMPLETENESS_TOLERANCE",
    "EXECUTION_STATES",
    "PASSING_RESULTS",
    "RESULTS",
    "WEIGHT_DOCUMENTATION",
    "WEIGHT_EXECUTION",
    "WEIGHT_OUTCOME",
    "validate_execution_record",
    "validate_ledger",
    "execution_coverage",
    "outcome_split",
    "evidence_gaps",
    "configuration_mismatches",
    "retest_closure",
    "completeness_index",
    "assess_validation_execution",
]

# The completeness index is a weighted sum of integer ratios; an exact unity
# can land a few ULP either side, so absorb representation error here rather
# than lowering what "validation complete" means.
COMPLETENESS_TOLERANCE = 1e-9

EXECUTION_STATES = ("not-run", "run", "aborted")
RESULTS = ("pass", "pass-with-deviation", "fail")
PASSING_RESULTS = ("pass", "pass-with-deviation")

WEIGHT_EXECUTION = 0.4
WEIGHT_OUTCOME = 0.4
WEIGHT_DOCUMENTATION = 0.2


def _text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    stripped = value.strip()
    if not stripped:
        raise ValueError("%s must not be empty" % label)
    return stripped


def validate_execution_record(record):
    """Return a normalised validation-case execution record."""
    if not isinstance(record, dict):
        raise ValueError("execution record must be a mapping, got %r" % (record,))
    cid = _text(record.get("id"), "case id")
    state = _text(record.get("state"), "case %s state" % cid).lower()
    if state not in EXECUTION_STATES:
        raise ValueError(
            "case %s state %r is not one of %s" % (cid, state, ", ".join(EXECUTION_STATES))
        )
    result = record.get("result")
    if result is not None:
        result = _text(result, "case %s result" % cid).lower()
        if result not in RESULTS:
            raise ValueError(
                "case %s result %r is not one of %s" % (cid, result, ", ".join(RESULTS))
            )
    if state == "run" and result is None:
        raise ValueError("case %s is reported run but carries no result" % cid)
    if state != "run" and result is not None:
        raise ValueError(
            "case %s is not reported run but carries the result %r" % (cid, result)
        )
    configuration = record.get("configuration_id")
    if configuration is not None:
        configuration = _text(configuration, "case %s configuration_id" % cid)
    if state == "run" and configuration is None:
        raise ValueError("case %s is reported run but names no device configuration" % cid)
    evidence = record.get("evidence_ref")
    if evidence is not None:
        evidence = _text(evidence, "case %s evidence_ref" % cid)
    depends = record.get("depends_on", [])
    if isinstance(depends, str) or not isinstance(depends, (list, tuple)):
        raise ValueError("case %s depends_on must be a list of case ids" % cid)
    dependencies = [_text(item, "case %s dependency" % cid) for item in depends]
    if len(set(dependencies)) != len(dependencies):
        raise ValueError("case %s lists the same dependency twice" % cid)
    if cid in dependencies:
        raise ValueError("case %s depends on itself" % cid)
    return {
        "id": cid,
        "state": state,
        "result": result,
        "configuration_id": configuration,
        "evidence_ref": evidence,
        "depends_on": dependencies,
    }


def validate_ledger(records):
    """Return the normalised ledger, checking identifiers and dependencies."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("the execution ledger must be a non-empty sequence")
    checked = [validate_execution_record(item) for item in records]
    ids = [r["id"] for r in checked]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate case id in the execution ledger")
    known = set(ids)
    for record in checked:
        for dependency in record["depends_on"]:
            if dependency not in known:
                raise ValueError(
                    "case %s depends on %s, which is not in the ledger"
                    % (record["id"], dependency)
                )
    return checked


def execution_coverage(ledger):
    """Return how much of the planned validation has been run."""
    records = validate_ledger(ledger)
    run = [r for r in records if r["state"] == "run"]
    aborted = sorted(r["id"] for r in records if r["state"] == "aborted")
    not_run = sorted(r["id"] for r in records if r["state"] == "not-run")
    return {
        "planned_count": len(records),
        "run_count": len(run),
        "aborted_case_ids": aborted,
        "not_run_case_ids": not_run,
        "execution_fraction": len(run) / float(len(records)),
    }


def outcome_split(ledger):
    """Return the pass and fail split over the cases actually run."""
    records = validate_ledger(ledger)
    run = [r for r in records if r["state"] == "run"]
    if not run:
        return {
            "run_count": 0,
            "passed_case_ids": [],
            "failed_case_ids": [],
            "deviation_case_ids": [],
            "pass_fraction": 0.0,
        }
    passed = sorted(r["id"] for r in run if r["result"] in PASSING_RESULTS)
    failed = sorted(r["id"] for r in run if r["result"] == "fail")
    deviations = sorted(r["id"] for r in run if r["result"] == "pass-with-deviation")
    return {
        "run_count": len(run),
        "passed_case_ids": passed,
        "failed_case_ids": failed,
        "deviation_case_ids": deviations,
        "pass_fraction": len(passed) / float(len(run)),
    }


def evidence_gaps(ledger):
    """Return the cases reported run that document nothing."""
    records = validate_ledger(ledger)
    run = [r for r in records if r["state"] == "run"]
    undocumented = sorted(r["id"] for r in run if not r["evidence_ref"])
    if not run:
        return {"undocumented_case_ids": [], "documentation_fraction": 0.0}
    return {
        "undocumented_case_ids": undocumented,
        "documentation_fraction": (len(run) - len(undocumented)) / float(len(run)),
    }


def configuration_mismatches(ledger, delivered_configuration_id):
    """Return the run cases whose evidence was gathered on the wrong article."""
    delivered = _text(delivered_configuration_id, "delivered_configuration_id")
    records = validate_ledger(ledger)
    return sorted(
        r["id"]
        for r in records
        if r["state"] == "run" and r["configuration_id"] != delivered
    )


def retest_closure(ledger):
    """Return every case invalidated by a failure, transitively.

    A failed case invalidates itself and every case that depends on it, and
    every case depending on those, so the answer is a closure over the
    dependency graph. A dependency cycle is refused: it makes the closure
    meaningless and is a ledger defect in its own right.
    """
    records = validate_ledger(ledger)
    by_id = {r["id"]: r for r in records}

    # Refuse a cycle before walking the graph.
    state = {}

    def visit(node, stack):
        mark = state.get(node)
        if mark == "done":
            return
        if mark == "active":
            cycle = " -> ".join(stack[stack.index(node):] + [node])
            raise ValueError("dependency cycle in the execution ledger: %s" % cycle)
        state[node] = "active"
        for dependency in by_id[node]["depends_on"]:
            visit(dependency, stack + [node])
        state[node] = "done"

    for record in records:
        visit(record["id"], [])

    dependents = {r["id"]: [] for r in records}
    for record in records:
        for dependency in record["depends_on"]:
            dependents[dependency].append(record["id"])

    invalidated = set()
    frontier = [r["id"] for r in records if r["result"] == "fail"]
    while frontier:
        node = frontier.pop()
        if node in invalidated:
            continue
        invalidated.add(node)
        frontier.extend(dependents[node])
    return sorted(invalidated)


def completeness_index(execution_fraction, pass_fraction, documentation_fraction):
    """Combine the three measures into a single completeness index in [0, 1]."""
    for label, value in (
        ("execution_fraction", execution_fraction),
        ("pass_fraction", pass_fraction),
        ("documentation_fraction", documentation_fraction),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        v = float(value)
        if not math.isfinite(v) or v < 0.0 or v > 1.0:
            raise ValueError("%s must lie in [0, 1], got %r" % (label, value))
    return (
        WEIGHT_EXECUTION * float(execution_fraction)
        + WEIGHT_OUTCOME * float(pass_fraction)
        + WEIGHT_DOCUMENTATION * float(documentation_fraction)
    )


def assess_validation_execution(spec):
    """Run the full clause 5.8.2 validation execution assessment.

    spec keys: ledger (sequence of execution records),
    delivered_configuration_id (string).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("ledger", "delivered_configuration_id"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    ledger = validate_ledger(spec["ledger"])
    coverage = execution_coverage(ledger)
    outcome = outcome_split(ledger)
    documentation = evidence_gaps(ledger)
    mismatched = configuration_mismatches(ledger, spec["delivered_configuration_id"])
    retest = retest_closure(ledger)
    index = completeness_index(
        coverage["execution_fraction"],
        outcome["pass_fraction"],
        documentation["documentation_fraction"],
    )

    findings = []
    if coverage["not_run_case_ids"]:
        findings.append(
            "planned case(s) never run: %s" % ", ".join(coverage["not_run_case_ids"])
        )
    if coverage["aborted_case_ids"]:
        findings.append(
            "case(s) aborted without a result: %s" % ", ".join(coverage["aborted_case_ids"])
        )
    if outcome["failed_case_ids"]:
        findings.append("case(s) failed: %s" % ", ".join(outcome["failed_case_ids"]))
    if outcome["deviation_case_ids"]:
        findings.append(
            "case(s) passed only with a recorded deviation: %s"
            % ", ".join(outcome["deviation_case_ids"])
        )
    if documentation["undocumented_case_ids"]:
        findings.append(
            "case(s) run with no evidence reference: %s"
            % ", ".join(documentation["undocumented_case_ids"])
        )
    if mismatched:
        findings.append(
            "case(s) run on an article other than the delivered configuration %s: %s"
            % (spec["delivered_configuration_id"], ", ".join(mismatched))
        )
    if retest:
        findings.append(
            "case(s) invalidated by a failure and owing a rerun: %s" % ", ".join(retest)
        )

    complete = math.isclose(index, 1.0, rel_tol=0.0, abs_tol=COMPLETENESS_TOLERANCE)
    return {
        "execution_fraction": coverage["execution_fraction"],
        "pass_fraction": outcome["pass_fraction"],
        "documentation_fraction": documentation["documentation_fraction"],
        "completeness_index": index,
        "not_run_case_ids": coverage["not_run_case_ids"],
        "failed_case_ids": outcome["failed_case_ids"],
        "undocumented_case_ids": documentation["undocumented_case_ids"],
        "wrong_configuration_case_ids": mismatched,
        "retest_case_ids": retest,
        "findings": findings,
        "validation_complete": complete and not findings,
    }
