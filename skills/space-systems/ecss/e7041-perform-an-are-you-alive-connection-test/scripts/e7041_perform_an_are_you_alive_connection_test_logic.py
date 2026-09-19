"""Are-you-alive connection test execution and grading.

Anchor: ECSS-E-ST-70-41C clause 6.17.3 (perform an are-you-alive connection
test). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the connection-test request: a destination application process
   that exists in the identifier space, an empty application data field, and
   a positive finite timeout.
2. Filter the observed responses to those that arrived after the request and
   grade the rest by their own failure reason (wrong report type, foreign
   source).
3. Decide the verdict from the matching set: none, one, or more than one.
4. For a single match, compute the round-trip and compare it against the
   timeout through a named tolerance, so an arrival landing exactly on the
   budget is in time.
5. Census a campaign of tests into an availability fraction, the worst
   round-trip among the alive tests, and the targets that never answered.
"""

import math

__all__ = [
    "APID_MIN",
    "APID_MAX",
    "APID_IDLE",
    "ARE_YOU_ALIVE_REPORT",
    "TIMEOUT_TOLERANCE_S",
    "VERDICTS",
    "WHAT_A_PASS_COVERS",
    "validate_application_process_id",
    "validate_timeout",
    "validate_request",
    "validate_response",
    "candidate_responses",
    "round_trip_s",
    "within_timeout",
    "evaluate_connection_test",
    "census_campaign",
    "assess_are_you_alive_connection_test",
]

APID_MIN = 0
APID_MAX = 2046
APID_IDLE = 2047

ARE_YOU_ALIVE_REPORT = "are-you-alive-connection-test-report"

# An arrival landing exactly on the timeout budget is in time. The equality is
# a float-representation question, absorbed here rather than by widening the
# operational budget.
TIMEOUT_TOLERANCE_S = 1e-9

VERDICTS = (
    "alive",
    "no-response",
    "late-response",
    "duplicate-response",
)

WHAT_A_PASS_COVERS = (
    "the request reached the test service of the addressed application "
    "process, was recognised, and one report came back; no other service and "
    "no other application process is covered"
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
        raise ValueError(
            "%s %d is the reserved idle identifier" % (label, value)
        )
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
    """Return a normalised are-you-alive connection-test request."""
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping, got %r" % (request,))
    for key in ("destination_application_process_id", "timeout_s"):
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)
    apid = validate_application_process_id(
        request["destination_application_process_id"],
        "destination_application_process_id",
    )
    timeout = validate_timeout(request["timeout_s"])
    data = request.get("application_data", b"")
    if not isinstance(data, (bytes, bytearray, str, list, tuple)):
        raise ValueError("application_data must be a sized value, got %r" % (data,))
    if len(data) != 0:
        raise ValueError(
            "the are-you-alive request carries no application data; %d unit(s) "
            "were supplied" % len(data)
        )
    issued = _require_number(request.get("issued_at_s", 0.0), "issued_at_s")
    if issued < 0.0:
        raise ValueError("issued_at_s must not be negative, got %r" % (issued,))
    return {
        "destination_application_process_id": apid,
        "timeout_s": timeout,
        "issued_at_s": issued,
    }


def validate_response(response):
    """Return a normalised observed response record."""
    if not isinstance(response, dict):
        raise ValueError("response must be a mapping, got %r" % (response,))
    for key in ("report_type", "source_application_process_id", "received_at_s"):
        if key not in response:
            raise ValueError("response missing required key '%s'" % key)
    report_type = response["report_type"]
    if not isinstance(report_type, str) or not report_type.strip():
        raise ValueError("report_type must be a non-empty string")
    source = validate_application_process_id(
        response["source_application_process_id"],
        "source_application_process_id",
    )
    received = _require_number(response["received_at_s"], "received_at_s")
    if received < 0.0:
        raise ValueError("received_at_s must not be negative, got %r" % (received,))
    data = response.get("application_data", b"")
    if not isinstance(data, (bytes, bytearray, str, list, tuple)):
        raise ValueError("application_data must be a sized value, got %r" % (data,))
    return {
        "report_type": report_type.strip(),
        "source_application_process_id": source,
        "received_at_s": received,
        "data_units": len(data),
    }


def candidate_responses(request, responses):
    """Split the observed responses into matches and graded discards."""
    norm_request = validate_request(request)
    if not isinstance(responses, (list, tuple)):
        raise ValueError("responses must be a sequence")
    matches = []
    discards = []
    for response in responses:
        norm = validate_response(response)
        if norm["received_at_s"] < norm_request["issued_at_s"]:
            discards.append(dict(norm, reason="arrived-before-the-request"))
            continue
        if norm["report_type"] != ARE_YOU_ALIVE_REPORT:
            discards.append(dict(norm, reason="wrong-report-type"))
            continue
        if (
            norm["source_application_process_id"]
            != norm_request["destination_application_process_id"]
        ):
            discards.append(dict(norm, reason="foreign-source-application-process"))
            continue
        if norm["data_units"] != 0:
            discards.append(dict(norm, reason="report-carries-application-data"))
            continue
        matches.append(norm)
    matches.sort(key=lambda r: r["received_at_s"])
    return (matches, discards)


def round_trip_s(request, response):
    """Return the round-trip time in seconds for one matched response."""
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


def evaluate_connection_test(request, responses):
    """Return the verdict of one are-you-alive connection test."""
    norm_request = validate_request(request)
    matches, discards = candidate_responses(norm_request, responses)
    result = {
        "destination_application_process_id":
            norm_request["destination_application_process_id"],
        "timeout_s": norm_request["timeout_s"],
        "round_trip_s": None,
        "discarded": discards,
        "covers": WHAT_A_PASS_COVERS,
        "findings": [],
    }
    for item in discards:
        result["findings"].append(
            "response at %.6f s discarded: %s" % (item["received_at_s"], item["reason"])
        )
    if not matches:
        result["verdict"] = "no-response"
        result["alive"] = False
        result["findings"].append(
            "no are-you-alive report from application process %d inside %.6f s"
            % (norm_request["destination_application_process_id"],
               norm_request["timeout_s"])
        )
        return result
    if len(matches) > 1:
        result["verdict"] = "duplicate-response"
        result["alive"] = False
        result["round_trip_s"] = round_trip_s(norm_request, matches[0])
        result["duplicate_arrival_times_s"] = [m["received_at_s"] for m in matches]
        result["findings"].append(
            "%d are-you-alive reports answered one request; a duplicated uplink "
            "or a second responder is indicated" % len(matches)
        )
        return result
    rtt = round_trip_s(norm_request, matches[0])
    result["round_trip_s"] = rtt
    if within_timeout(rtt, norm_request["timeout_s"]):
        result["verdict"] = "alive"
        result["alive"] = True
    else:
        result["verdict"] = "late-response"
        result["alive"] = False
        result["findings"].append(
            "the report arrived at %.6f s, past the %.6f s budget; the path works "
            "and the budget or the responder load does not"
            % (rtt, norm_request["timeout_s"])
        )
    return result


def census_campaign(results):
    """Census a set of connection-test results into availability figures."""
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    counts = {}
    alive_round_trips = []
    silent = []
    for result in results:
        if not isinstance(result, dict) or "verdict" not in result:
            raise ValueError("each result must be a mapping carrying 'verdict'")
        verdict = result["verdict"]
        if verdict not in VERDICTS:
            raise ValueError("unknown verdict %r" % (verdict,))
        counts[verdict] = counts.get(verdict, 0) + 1
        if verdict == "alive":
            alive_round_trips.append(result["round_trip_s"])
        if verdict == "no-response":
            silent.append(result["destination_application_process_id"])
    alive = counts.get("alive", 0)
    return {
        "test_count": len(results),
        "verdict_counts": counts,
        "alive_count": alive,
        "availability": alive / float(len(results)),
        "worst_alive_round_trip_s": max(alive_round_trips) if alive_round_trips else None,
        "silent_application_process_ids": sorted(set(silent)),
    }


def assess_are_you_alive_connection_test(spec):
    """Run a campaign of clause 6.17.3 connection tests and census the outcome.

    spec key: tests, a sequence of {request, responses} mappings.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    tests = spec.get("tests")
    if not isinstance(tests, (list, tuple)) or not tests:
        raise ValueError("spec['tests'] must be a non-empty sequence")
    results = []
    for test in tests:
        if not isinstance(test, dict) or "request" not in test:
            raise ValueError("each test must be a mapping carrying 'request'")
        results.append(
            evaluate_connection_test(test["request"], test.get("responses", []))
        )
    census = census_campaign(results)
    findings = []
    for result in results:
        findings.extend(result["findings"])
    return {
        "results": results,
        "census": census,
        "findings": findings,
        "all_alive": census["alive_count"] == census["test_count"],
    }
