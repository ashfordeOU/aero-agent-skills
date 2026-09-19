"""Initiating the action bound to an on-board event, occurrence by occurrence.

Anchor: ECSS-E-ST-70-41C clause 6.19.5.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

This clause is the moment of decision, not the table. The table says
which request an event is bound to; this says what happens when the
event actually occurs. Two requirements govern it: the event-action
function releases the bound request when the event occurs and the
binding is armed, and it releases the request the definition holds --
not a request assembled at that moment.

Arming is two-level and the levels are checked in order. The function
itself can be off, and an individual definition can be off. A
detection meets the function switch first: with the function off
nothing is released whatever the individual definitions say, and the
individual statuses are not consulted, not changed, and not reported
as the reason.

Every occurrence is its own decision. Two detections of the same event
release the action twice; the clause does not coalesce them, because
the second detection is a second piece of evidence that the condition
is still there. That is correct and it is also how a misbehaving
sensor turns one binding into a command storm, so the count and the
peak release rate are worth computing even though neither changes the
decision.

A disposition is recorded for every occurrence, released or not. An
occurrence with no definition at all and one whose definition is
disarmed both release nothing, and they are entirely different
findings: the first is a gap in the table, the second is a deliberate
state somebody set.

Stdlib only, offline, deterministic.
"""

DISPOSITION_RELEASED = "action-released"
DISPOSITION_FUNCTION_DISABLED = "no-release-the-function-is-disabled"
DISPOSITION_NO_DEFINITION = "no-release-no-definition-covers-this-event"
DISPOSITION_DEFINITION_DISABLED = "no-release-this-definition-is-disabled"
DISPOSITIONS = (
    DISPOSITION_RELEASED,
    DISPOSITION_FUNCTION_DISABLED,
    DISPOSITION_NO_DEFINITION,
    DISPOSITION_DEFINITION_DISABLED,
)

FINDING_REPEAT_RELEASE = "one-event-released-its-action-more-than-once"
FINDING_RELEASE_RATE_EXCEEDED = "peak-release-rate-exceeds-the-stated-limit"
FINDING_OCCURRENCE_OUT_OF_ORDER = "event-occurrence-times-are-not-non-decreasing"
FINDING_UNCOVERED_EVENT_SEEN = "an-event-with-no-definition-was-detected"

APID_MAX = 2047


def _apid(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("application process id must be an integer, got %r" % (value,))
    if value < 0 or value > APID_MAX:
        raise ValueError("application process id must be in [0, %d]" % APID_MAX)
    return value


def _event_definition_id(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("event definition id must be an integer, got %r" % (value,))
    if value < 0:
        raise ValueError("event definition id must not be negative")
    return value


def _time(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be before the epoch" % label)
    return float(value)


def normalise_occurrence(raw, index):
    """Validate one detected event occurrence."""
    if not isinstance(raw, dict):
        raise ValueError("occurrence %d must be a mapping" % index)
    return {
        "index": index,
        "key": (_apid(raw.get("apid")), _event_definition_id(raw.get("event_definition_id"))),
        "time_s": _time("occurrence %d time" % index, raw.get("time_s", 0.0)),
    }


def normalise_bindings(bindings):
    """Validate the armed-or-not table the decision is taken against."""
    if not isinstance(bindings, dict):
        raise ValueError("bindings must be a mapping of event keys to entries")
    normalised = {}
    for key, entry in bindings.items():
        if not isinstance(key, tuple) or len(key) != 2:
            raise ValueError("binding key %r is not an (apid, event id) pair" % (key,))
        _apid(key[0])
        _event_definition_id(key[1])
        if not isinstance(entry, dict):
            raise ValueError("binding %r must be a mapping" % (key,))
        action = entry.get("action")
        if not isinstance(action, dict) or not action:
            raise ValueError("binding %r holds no action to release" % (key,))
        normalised[key] = {"enabled": bool(entry.get("enabled", False)), "action": action}
    return normalised


def decide_release(function_enabled, bindings, key):
    """The disposition of one detection, with the switches read in order."""
    if not function_enabled:
        return DISPOSITION_FUNCTION_DISABLED
    entry = bindings.get(key)
    if entry is None:
        return DISPOSITION_NO_DEFINITION
    if not entry["enabled"]:
        return DISPOSITION_DEFINITION_DISABLED
    return DISPOSITION_RELEASED


def peak_release_rate(release_times_s, window_s):
    """Highest number of releases per second over any window of that width."""
    if not isinstance(release_times_s, (list, tuple)):
        raise ValueError("release times must be a list")
    window = _time("rate window", window_s)
    if window <= 0:
        raise ValueError("rate window must be positive, got %r" % (window_s,))
    if not release_times_s:
        return 0.0
    times = sorted(_time("release time", t) for t in release_times_s)
    best = 0
    for start_index, start in enumerate(times):
        count = 0
        for later in times[start_index:]:
            if later - start <= window:
                count += 1
            else:
                break
        if count > best:
            best = count
    return best / window


def initiate_actions(function_enabled, bindings, occurrences):
    """Decide every occurrence in order and collect what was released."""
    table = normalise_bindings(bindings)
    if not isinstance(occurrences, (list, tuple)) or not occurrences:
        raise ValueError("there must be at least one event occurrence to decide")
    decisions = []
    releases = []
    findings = []
    previous_time = None
    for index, raw in enumerate(occurrences):
        occurrence = normalise_occurrence(raw, index)
        if previous_time is not None and occurrence["time_s"] < previous_time:
            findings.append(
                {
                    "finding": FINDING_OCCURRENCE_OUT_OF_ORDER,
                    "index": index,
                    "key": occurrence["key"],
                }
            )
        previous_time = occurrence["time_s"]
        disposition = decide_release(function_enabled, table, occurrence["key"])
        record = {
            "index": index,
            "key": occurrence["key"],
            "time_s": occurrence["time_s"],
            "disposition": disposition,
            "action": None,
        }
        if disposition == DISPOSITION_RELEASED:
            record["action"] = dict(table[occurrence["key"]]["action"])
            releases.append(record)
        decisions.append(record)
    return {"decisions": decisions, "releases": releases, "findings": findings}


def releases_per_event(releases):
    """How many times each event released its action."""
    if not isinstance(releases, (list, tuple)):
        raise ValueError("releases must be a list")
    counts = {}
    for record in releases:
        counts[record["key"]] = counts.get(record["key"], 0) + 1
    return counts


def assess_action_initiation(
    function_enabled, bindings, occurrences, rate_limit_per_s=None, window_s=1.0
):
    """Grade a run of detections against the two-level arming state."""
    outcome = initiate_actions(function_enabled, bindings, occurrences)
    findings = list(outcome["findings"])
    counts = releases_per_event(outcome["releases"])
    for key, count in sorted(counts.items()):
        if count > 1:
            findings.append(
                {"finding": FINDING_REPEAT_RELEASE, "key": key, "releases": count}
            )
    uncovered = sorted(
        {
            d["key"]
            for d in outcome["decisions"]
            if d["disposition"] == DISPOSITION_NO_DEFINITION
        }
    )
    for key in uncovered:
        findings.append({"finding": FINDING_UNCOVERED_EVENT_SEEN, "key": key})
    rate = peak_release_rate([r["time_s"] for r in outcome["releases"]], window_s)
    if rate_limit_per_s is not None:
        limit = _time("rate limit", rate_limit_per_s)
        if limit <= 0:
            raise ValueError("rate limit must be positive, got %r" % (rate_limit_per_s,))
        if rate > limit:
            findings.append(
                {
                    "finding": FINDING_RELEASE_RATE_EXCEEDED,
                    "peak_per_s": rate,
                    "limit_per_s": limit,
                }
            )
    tally = dict((d, 0) for d in DISPOSITIONS)
    for decision in outcome["decisions"]:
        tally[decision["disposition"]] += 1
    return {
        "decisions": outcome["decisions"],
        "releases": outcome["releases"],
        "release_count": len(outcome["releases"]),
        "releases_per_event": counts,
        "disposition_counts": tally,
        "peak_release_rate_per_s": rate,
        "findings": findings,
        "run_clean": not findings,
    }
