"""On-board connection test execution and grading.

Anchor: ECSS-E-ST-70-41C clause 6.17.4.2 (perform an on-board connection
test). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate a request that names a target application process, carries no
   application data and declares a positive timeout.
2. Refuse, before anything is transmitted, a target the test service was not
   declared able to reach; that refusal is a statement about the declaration
   and not about the target.
3. Filter the observed responses, keeping the reason for every discard.
4. Settle identity before timing: a report naming another target is a
   mismatch whatever its arrival time.
5. Grade the surviving matches: none, one inside or outside the budget, or
   more than one.
6. Sweep several targets into reached, refused and silent groups.
"""

import math

__all__ = [
    "APID_MIN",
    "APID_MAX",
    "APID_IDLE",
    "ON_BOARD_CONNECTION_TEST_REPORT",
    "TIMEOUT_TOLERANCE_S",
    "VERDICTS",
    "validate_application_process_id",
    "validate_timeout",
    "validate_request",
    "validate_response",
    "validate_accessible_targets",
    "target_is_accessible",
    "filter_responses",
    "round_trip_s",
    "within_timeout",
    "evaluate_on_board_connection_test",
    "sweep_targets",
    "assess_on_board_connection_test",
]

APID_MIN = 0
APID_MAX = 2046
APID_IDLE = 2047

ON_BOARD_CONNECTION_TEST_REPORT = "on-board-connection-test-report"

# An arrival landing exactly on the timeout budget is in time; the equality is
# absorbed here rather than by widening the operational budget.
TIMEOUT_TOLERANCE_S = 1e-9

VERDICTS = (
    "reached",
    "target-not-accessible",
    "no-response",
    "late-response",
    "target-identifier-mismatch",
    "duplicate-response",
)


def _require_number(value, label):
    """Return value as a finite float, refusing bools and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return result


def validate_application_process_id(value, label="application_process_id"):
    """Return a validated application process identifier."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value == APID_IDLE:
        raise ValueError("%s %d is the reserved idle identifier" % (label, value))
    if value < APID_MIN or value > APID_MAX:
        raise ValueError(
            "%s %d is outside the range [%d, %d]" % (label, value, APID_MIN, APID_MAX)
        )
    return int(value)


def validate_timeout(value):
    """Return a validated timeout in seconds."""
    timeout = _require_number(value, "timeout_s")
    if timeout <= 0.0:
        raise ValueError("timeout_s must be positive, got %r" % (value,))
    return timeout


def validate_request(request):
    """Return a normalised on-board connection-test request."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping, got %r" % (request,))
    for key in ("target_application_process_id", "timeout_s"):
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)
    target = validate_application_process_id(
        request["target_application_process_id"], "target_application_process_id"
    )
    timeout = validate_timeout(request["timeout_s"])
    data = request.get("application_data", b"")
    if not isinstance(data, (bytes, bytearray, str, list, tuple)):
        raise ValueError("application_data must be a sized value, got %r" % (data,))
    if len(data) != 0:
        raise ValueError(
            "the on-board connection-test request carries only the target "
            "identifier; %d extra data unit(s) were supplied" % len(data)
        )
    issued = _require_number(request.get("issued_at_s", 0.0), "issued_at_s")
    if issued < 0.0:
        raise ValueError("issued_at_s must not be negative, got %r" % (issued,))
    return {
        "target_application_process_id": target,
        "timeout_s": timeout,
        "issued_at_s": issued,
    }


def validate_response(response):
    """Return a normalised observed response record."""
    if not isinstance(response, dict):
        raise ValueError("response must be a mapping, got %r" % (response,))
    for key in ("report_type", "target_application_process_id", "received_at_s"):
        if key not in response:
            raise ValueError("response missing required key '%s'" % key)
    report_type = response["report_type"]
    if not isinstance(report_type, str) or not report_type.strip():
        raise ValueError("report_type must be a non-empty string")
    target = validate_application_process_id(
        response["target_application_process_id"],
        "reported target_application_process_id",
    )
    received = _require_number(response["received_at_s"], "received_at_s")
    if received < 0.0:
        raise ValueError("received_at_s must not be negative, got %r" % (received,))
    return {
        "report_type": report_type.strip(),
        "target_application_process_id": target,
        "received_at_s": received,
    }


def validate_accessible_targets(targets):
    """Return the sorted declared-accessible target set of the test service."""
    if not isinstance(targets, (list, tuple, set)):
        raise ValueError("accessible targets must be a sequence")
    seen = []
    for target in targets:
        value = validate_application_process_id(target, "accessible target")
        if value in seen:
            raise ValueError("target %d is declared accessible twice" % value)
        seen.append(value)
    return sorted(seen)


def target_is_accessible(accessible_targets, target_application_process_id):
    """Return True when the test service was declared able to reach the target."""
    targets = validate_accessible_targets(accessible_targets)
    target = validate_application_process_id(target_application_process_id)
    return target in targets


def filter_responses(request, responses):
    """Split responses into matches, mismatches and graded discards."""
    norm_request = validate_request(request)
    if not isinstance(responses, (list, tuple)):
        raise ValueError("responses must be a sequence")
    matches = []
    mismatches = []
    discards = []
    for response in responses:
        norm = validate_response(response)
        if norm["received_at_s"] < norm_request["issued_at_s"]:
            discards.append(dict(norm, reason="arrived-before-the-request"))
            continue
        if norm["report_type"] != ON_BOARD_CONNECTION_TEST_REPORT:
            discards.append(dict(norm, reason="wrong-report-type"))
            continue
        if (
            norm["target_application_process_id"]
            != norm_request["target_application_process_id"]
        ):
            mismatches.append(norm)
            continue
        matches.append(norm)
    matches.sort(key=lambda r: r["received_at_s"])
    mismatches.sort(key=lambda r: r["received_at_s"])
    return (matches, mismatches, discards)


def round_trip_s(request, response):
    """Return the round-trip time in seconds for one response."""
    norm_request = validate_request(request)
    norm_response = validate_response(response)
    delta = norm_response["received_at_s"] - norm_request["issued_at_s"]
    if delta < 0.0:
        raise ValueError("the response predates the request")
    return delta


def within_timeout(round_trip, timeout_s):
    """Return True when the round-trip is inside the budget, equality included."""
    rtt = _require_number(round_trip, "round_trip")
    if rtt < 0.0:
        raise ValueError("round_trip must not be negative, got %r" % (round_trip,))
    budget = validate_timeout(timeout_s)
    return rtt <= budget + TIMEOUT_TOLERANCE_S


def evaluate_on_board_connection_test(request, responses, accessible_targets):
    """Return the verdict of one on-board connection test against a target."""
    norm_request = validate_request(request)
    target = norm_request["target_application_process_id"]
    result = {
        "target_application_process_id": target,
        "timeout_s": norm_request["timeout_s"],
        "round_trip_s": None,
        "transmitted": False,
        "reached": False,
        "discarded": [],
        "findings": [],
    }
    if not target_is_accessible(accessible_targets, target):
        result["verdict"] = "target-not-accessible"
        result["findings"].append(
            "target application process %d is not declared accessible from this "
            "test service; nothing was transmitted and nothing was learned about "
            "the target" % target
        )
        return result
    result["transmitted"] = True
    matches, mismatches, discards = filter_responses(norm_request, responses)
    result["discarded"] = discards
    for item in discards:
        result["findings"].append(
            "response at %.6f s discarded: %s" % (item["received_at_s"], item["reason"])
        )
    if mismatches:
        result["verdict"] = "target-identifier-mismatch"
        result["reported_target_application_process_ids"] = [
            m["target_application_process_id"] for m in mismatches
        ]
        result["round_trip_s"] = round_trip_s(norm_request, mismatches[0])
        result["findings"].append(
            "a report answered about application process %d while %d was asked "
            "about; the addressing is defective whatever the timing says"
            % (mismatches[0]["target_application_process_id"], target)
        )
        return result
    if not matches:
        result["verdict"] = "no-response"
        result["findings"].append(
            "no on-board connection-test report about application process %d "
            "inside %.6f s" % (target, norm_request["timeout_s"])
        )
        return result
    if len(matches) > 1:
        result["verdict"] = "duplicate-response"
        result["round_trip_s"] = round_trip_s(norm_request, matches[0])
        result["duplicate_arrival_times_s"] = [m["received_at_s"] for m in matches]
        result["findings"].append(
            "%d reports answered one request about application process %d; a "
            "duplicated request or a second responder is indicated"
            % (len(matches), target)
        )
        return result
    rtt = round_trip_s(norm_request, matches[0])
    result["round_trip_s"] = rtt
    if within_timeout(rtt, norm_request["timeout_s"]):
        result["verdict"] = "reached"
        result["reached"] = True
    else:
        result["verdict"] = "late-response"
        result["findings"].append(
            "the report about application process %d arrived at %.6f s, past the "
            "%.6f s budget" % (target, rtt, norm_request["timeout_s"])
        )
    return result


def sweep_targets(results):
    """Group a sweep of test results into reached, refused and silent targets."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    reached = []
    refused = []
    silent = []
    defective = []
    round_trips = []
    for result in results:
        if not isinstance(result, dict) or "verdict" not in result:
            raise ValueError("each result must be a mapping carrying 'verdict'")
        verdict = result["verdict"]
        if verdict not in VERDICTS:
            raise ValueError("unknown verdict %r" % (verdict,))
        target = result["target_application_process_id"]
        if verdict == "reached":
            reached.append(target)
            round_trips.append(result["round_trip_s"])
        elif verdict == "target-not-accessible":
            refused.append(target)
        elif verdict == "no-response":
            silent.append(target)
        else:
            defective.append(target)
    asked = len(results) - len(refused)
    return {
        "target_count": len(results),
        "asked_count": asked,
        "reached_application_process_ids": sorted(reached),
        "refused_application_process_ids": sorted(refused),
        "silent_application_process_ids": sorted(silent),
        "defective_application_process_ids": sorted(defective),
        "reached_fraction_of_asked": (len(reached) / float(asked)) if asked else None,
        "worst_reached_round_trip_s": max(round_trips) if round_trips else None,
    }


def assess_on_board_connection_test(spec):
    """Run a clause 6.17.4.2 sweep and group its outcome.

    spec keys: accessible_targets, tests (a sequence of {request, responses}).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("accessible_targets", "tests"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    accessible = validate_accessible_targets(spec["accessible_targets"])
    tests = spec["tests"]
    if not isinstance(tests, (list, tuple)) or not tests:
        raise ValueError("spec['tests'] must be a non-empty sequence")
    results = []
    for test in tests:
        if not isinstance(test, dict) or "request" not in test:
            raise ValueError("each test must be a mapping carrying 'request'")
        results.append(
            evaluate_on_board_connection_test(
                test["request"], test.get("responses", []), accessible
            )
        )
    sweep = sweep_targets(results)
    findings = []
    for result in results:
        findings.extend(result["findings"])
    return {
        "results": results,
        "sweep": sweep,
        "findings": findings,
        "all_asked_targets_reached": (
            sweep["asked_count"] > 0
            and len(sweep["reached_application_process_ids"]) == sweep["asked_count"]
        ),
    }
