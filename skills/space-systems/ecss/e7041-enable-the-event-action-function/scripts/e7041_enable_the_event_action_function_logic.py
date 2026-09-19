"""Enabling the event-action function, and what that switch does not touch.

Anchor: ECSS-E-ST-70-41C clause 6.19.6.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

There are two switches in the event-action service and this clause is
about the outer one. The function as a whole can be enabled or
disabled, and separately each definition in the table carries its own
enable status. A binding releases its action only when both are on.

The three requirements here are small and the consequence is not. The
function can be enabled by request; enabling it makes it enabled;
and -- the part that gets implemented wrongly -- the per-definition
statuses are not touched by the function-level switch. Disabling the
function does not disarm the definitions, and enabling it does not arm
them. It gates them.

That is what makes the outer switch safe to use. An operator can shut
the whole function during a critical operation and restore it
afterwards, and the table comes back exactly as it was: the
definitions somebody deliberately disarmed are still disarmed, and the
armed ones are armed again without anybody re-issuing a request per
entry. An implementation that clears or sets the per-definition
statuses on a function toggle destroys that, and it destroys it
quietly -- the table is still full, the entries are still there, only
their statuses are now whatever the toggle wrote.

Definition-level requests are themselves independent of the function
switch. Arming a definition while the function is off is meaningful:
it takes effect the moment the function comes back, which is exactly
how an operation is staged.

Stdlib only, offline, deterministic.
"""

REQUEST_ENABLE_FUNCTION = "enable-function"
REQUEST_DISABLE_FUNCTION = "disable-function"
REQUEST_ENABLE_DEFINITION = "enable-definition"
REQUEST_DISABLE_DEFINITION = "disable-definition"
FUNCTION_REQUESTS = (REQUEST_ENABLE_FUNCTION, REQUEST_DISABLE_FUNCTION)
DEFINITION_REQUESTS = (REQUEST_ENABLE_DEFINITION, REQUEST_DISABLE_DEFINITION)
REQUESTS = FUNCTION_REQUESTS + DEFINITION_REQUESTS

FINDING_FUNCTION_ALREADY_ENABLED = "enable-request-on-an-already-enabled-function"
FINDING_FUNCTION_ALREADY_DISABLED = "disable-request-on-an-already-disabled-function"
FINDING_UNKNOWN_DEFINITION = "request-named-a-definition-the-table-does-not-hold"
FINDING_DEFINITION_UNCHANGED = "definition-request-left-the-status-as-it-was"
FINDING_STATUS_NOT_PRESERVED = "a-function-toggle-changed-a-per-definition-status"
FINDING_NOTHING_ARMED = "the-function-is-enabled-but-no-definition-is-armed"
FINDING_STAGED_WHILE_DISABLED = "definition-armed-while-the-function-was-disabled"

APID_MAX = 2047


def _key(value):
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("definition key %r is not an (apid, event id) pair" % (value,))
    apid, event_definition_id = value
    if isinstance(apid, bool) or not isinstance(apid, int):
        raise ValueError("application process id must be an integer, got %r" % (apid,))
    if apid < 0 or apid > APID_MAX:
        raise ValueError("application process id must be in [0, %d]" % APID_MAX)
    if isinstance(event_definition_id, bool) or not isinstance(event_definition_id, int):
        raise ValueError(
            "event definition id must be an integer, got %r" % (event_definition_id,)
        )
    if event_definition_id < 0:
        raise ValueError("event definition id must not be negative")
    return (apid, event_definition_id)


def new_function_state(definition_keys, function_enabled=False, armed_keys=None):
    """The two-level switch state: the function, and each definition's status."""
    if not isinstance(definition_keys, (list, tuple, set)):
        raise ValueError("definition_keys must be a collection of event keys")
    keys = [_key(k) for k in definition_keys]
    if len(set(keys)) != len(keys):
        raise ValueError("the definition table cannot hold one key twice")
    if not keys:
        raise ValueError("a function state needs at least one definition")
    armed = set()
    if armed_keys is not None:
        if not isinstance(armed_keys, (list, tuple, set)):
            raise ValueError("armed_keys must be a collection of event keys")
        for raw in armed_keys:
            key = _key(raw)
            if key not in keys:
                raise ValueError("armed key %s is not in the table" % (key,))
            armed.add(key)
    return {
        "function_enabled": bool(function_enabled),
        "definitions": dict((key, key in armed) for key in keys),
    }


def status_snapshot(state):
    """A copy of the per-definition statuses, independent of the state."""
    if not isinstance(state, dict) or "definitions" not in state:
        raise ValueError("state must be a new_function_state result")
    return dict(state["definitions"])


def effective_armed(state):
    """The definitions that would actually release: both switches on."""
    if not isinstance(state, dict) or "definitions" not in state:
        raise ValueError("state must be a new_function_state result")
    if not state["function_enabled"]:
        return []
    return sorted(key for key, armed in state["definitions"].items() if armed)


def _normalise_request(raw, index):
    if not isinstance(raw, dict):
        raise ValueError("request %d must be a mapping, got %r" % (index, raw))
    name = raw.get("request")
    if name not in REQUESTS:
        raise ValueError(
            "request %d is %r, expected one of %s" % (index, name, ", ".join(REQUESTS))
        )
    key = raw.get("key")
    if name in DEFINITION_REQUESTS:
        if not isinstance(key, (list, tuple)):
            raise ValueError(
                "request %d must name a definition as an (apid, event id) pair" % index
            )
        key = _key(tuple(key))
    elif key is not None:
        raise ValueError("function-level request %d must not name a definition" % index)
    return {"request": name, "key": key}


def apply_request(state, raw, index=0):
    """Apply one enable or disable request and report what it did."""
    if not isinstance(state, dict) or "definitions" not in state:
        raise ValueError("state must be a new_function_state result")
    request = _normalise_request(raw, index)
    name = request["request"]
    findings = []
    if name in FUNCTION_REQUESTS:
        before = status_snapshot(state)
        wanted = name == REQUEST_ENABLE_FUNCTION
        if state["function_enabled"] == wanted:
            findings.append(
                {
                    "finding": FINDING_FUNCTION_ALREADY_ENABLED
                    if wanted
                    else FINDING_FUNCTION_ALREADY_DISABLED
                }
            )
        state["function_enabled"] = wanted
        # The outer switch gates the definitions; it never writes them.
        findings.extend(check_statuses_preserved(before, status_snapshot(state)))
        return findings
    key = request["key"]
    if key not in state["definitions"]:
        findings.append({"finding": FINDING_UNKNOWN_DEFINITION, "key": key})
        return findings
    wanted = name == REQUEST_ENABLE_DEFINITION
    if state["definitions"][key] == wanted:
        findings.append({"finding": FINDING_DEFINITION_UNCHANGED, "key": key})
    state["definitions"][key] = wanted
    if wanted and not state["function_enabled"]:
        findings.append({"finding": FINDING_STAGED_WHILE_DISABLED, "key": key})
    return findings


def check_statuses_preserved(before, after):
    """Findings for every per-definition status a function toggle changed."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("both snapshots must be status mappings")
    findings = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            findings.append(
                {
                    "finding": FINDING_STATUS_NOT_PRESERVED,
                    "key": key,
                    "before": before.get(key),
                    "after": after.get(key),
                }
            )
    return findings


def run_requests(state, requests):
    """Apply a sequence of requests, collecting every finding in order."""
    if not isinstance(requests, (list, tuple)):
        raise ValueError("requests must be a list")
    findings = []
    for index, raw in enumerate(requests):
        for finding in apply_request(state, raw, index):
            entry = dict(finding)
            entry["index"] = index
            findings.append(entry)
    return findings


def function_toggle_round_trip(state):
    """Disable then enable the function and prove the statuses came back."""
    before = status_snapshot(state)
    started_enabled = state["function_enabled"]
    findings = []
    findings.extend(apply_request(state, {"request": REQUEST_DISABLE_FUNCTION}))
    findings.extend(apply_request(state, {"request": REQUEST_ENABLE_FUNCTION}))
    if not started_enabled:
        apply_request(state, {"request": REQUEST_DISABLE_FUNCTION})
    after = status_snapshot(state)
    breaches = check_statuses_preserved(before, after)
    return {
        "preserved": not breaches,
        "breaches": breaches,
        "incidental_findings": [
            f
            for f in findings
            if f["finding"] != FINDING_STATUS_NOT_PRESERVED
        ],
    }


def assess_function_enabling(definition_keys, requests, function_enabled=False,
                             armed_keys=None):
    """Replay a switching sequence and grade the two-level arming state."""
    state = new_function_state(
        definition_keys, function_enabled=function_enabled, armed_keys=armed_keys
    )
    findings = run_requests(state, requests)
    round_trip = function_toggle_round_trip(state)
    findings.extend(round_trip["breaches"])
    armed = effective_armed(state)
    if state["function_enabled"] and not armed:
        findings.append({"finding": FINDING_NOTHING_ARMED})
    return {
        "function_enabled": state["function_enabled"],
        "definition_statuses": status_snapshot(state),
        "armed": armed,
        "armed_count": len(armed),
        "definition_count": len(state["definitions"]),
        "statuses_survive_a_function_toggle": round_trip["preserved"],
        "findings": findings,
        "sequence_clean": not findings,
    }
