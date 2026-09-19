"""Operator go and no-go checks on a crimp tool, and the tool logbook.

Anchor: ECSS-Q-ST-70-26C, the tooling clause covering the check an
operator performs before using a crimp tool and the logbook that records
it (paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. The gauge check is two observations, not one. The go pin has to
   enter the closed die and the no-go pin has to be refused by it. Only
   that pair is a pass; each single failure names a different wear
   direction, and both failing at once is a gauge set nobody can trust
   rather than a very bad tool.
2. A check that was not recorded did not happen. The logbook entry
   carries the tool, the operator, when, which gauge set, and the crimp
   counter reading at the moment of the check, and a missing field is
   reported by name so the person who has it can supply it.
3. Release is the conjunction. A passing gauge with an incomplete entry
   releases nothing, because the evidence that would bound a later
   problem does not exist.
4. The counter reading is what makes a failed check actionable. The
   suspect crimps are the ones made since the last passing check, not
   the ones made since the shift began, and the two differ by however
   long the tool ran well that morning.
5. With no earlier passing check in the log, the span is open at the
   bottom and has to be reported as such rather than quietly measured
   from the first entry.

Stdlib only, offline, deterministic.
"""

import datetime

GAUGE_PASS = "gauge-check-pass"
GAUGE_UNDERSIZE = "gauge-check-fail-die-closes-undersize"
GAUGE_OVERSIZE = "gauge-check-fail-die-worn-oversize"
GAUGE_INVALID = "gauge-check-invalid-gauge-set"

RELEASED = "tool-released-for-the-shift"
HELD = "tool-held-pending-action"

REQUIRED_LOG_FIELDS = (
    "tool_id",
    "operator_id",
    "check_datetime",
    "gauge_set_id",
    "crimp_count_at_check",
)

BOUNDED_BY_LAST_PASS = "bounded-by-the-last-passing-check"
BOUNDED_OPEN = "open-no-earlier-passing-check"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _count(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def parse_check_datetime(value):
    """Parse an ISO timestamp, raising on anything else."""
    if isinstance(value, datetime.datetime):
        return value
    text = _text("check_datetime", value)
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        raise ValueError("check_datetime %r is not an ISO timestamp" % (value,))


def gauge_verdict(go_pin_enters, no_go_pin_enters):
    """Read a go and no-go pin pair into a single verdict."""
    went_in = _flag("go_pin_enters", go_pin_enters)
    no_go_went_in = _flag("no_go_pin_enters", no_go_pin_enters)
    if not went_in and no_go_went_in:
        return GAUGE_INVALID
    if not went_in:
        return GAUGE_UNDERSIZE
    if no_go_went_in:
        return GAUGE_OVERSIZE
    return GAUGE_PASS


def logbook_gaps(entry):
    """Name every required logbook field that is missing or unusable."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    gaps = []
    for field in REQUIRED_LOG_FIELDS:
        value = entry.get(field)
        if value is None:
            gaps.append("missing-%s" % field)
            continue
        try:
            if field == "crimp_count_at_check":
                _count(field, value, 0)
            elif field == "check_datetime":
                parse_check_datetime(value)
            else:
                _text(field, value)
        except ValueError:
            gaps.append("unusable-%s" % field)
    return gaps


def validate_check(entry):
    """Validate one logbook entry and normalize it."""
    gaps = logbook_gaps(entry)
    if gaps:
        raise ValueError("logbook entry is incomplete: %s" % ", ".join(gaps))
    return {
        "tool_id": _text("tool_id", entry.get("tool_id")),
        "operator_id": _text("operator_id", entry.get("operator_id")),
        "check_datetime": parse_check_datetime(entry.get("check_datetime")),
        "gauge_set_id": _text("gauge_set_id", entry.get("gauge_set_id")),
        "crimp_count_at_check": _count(
            "crimp_count_at_check", entry.get("crimp_count_at_check"), 0
        ),
        "verdict": gauge_verdict(
            entry.get("go_pin_enters"), entry.get("no_go_pin_enters")
        ),
        "tool_on_hold": _flag("tool_on_hold", entry.get("tool_on_hold", False)),
    }


def release_decision(entry):
    """May the operator use this tool on the strength of this check?"""
    gaps = logbook_gaps(entry)
    reasons = list(gaps)
    if gaps:
        verdict = None
    else:
        checked = validate_check(entry)
        verdict = checked["verdict"]
        if verdict != GAUGE_PASS:
            reasons.append(verdict)
        if checked["tool_on_hold"]:
            reasons.append("tool-already-on-hold")
    return {
        "decision": HELD if reasons else RELEASED,
        "verdict": verdict,
        "reasons": reasons,
    }


def validate_log(entries):
    """Validate an ordered run of logbook entries for one tool."""
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries must be a non-empty list")
    checked = [validate_check(e) for e in entries]
    tools = {c["tool_id"] for c in checked}
    if len(tools) > 1:
        raise ValueError("a logbook run covers one tool, got %d" % len(tools))
    previous = None
    for current in checked:
        if previous is not None:
            if current["check_datetime"] < previous["check_datetime"]:
                raise ValueError("logbook entries are out of time order")
            if current["crimp_count_at_check"] < previous["crimp_count_at_check"]:
                raise ValueError("the crimp counter went backwards")
        previous = current
    return checked


def quarantine_span(entries, failed_index):
    """Bound the crimps a failed check puts in doubt."""
    checked = validate_log(entries)
    index = _count("failed_index", failed_index, 0)
    if index >= len(checked):
        raise ValueError("failed_index %d is past the end of the log" % index)
    failing = checked[index]
    if failing["verdict"] == GAUGE_PASS:
        raise ValueError("entry %d is a passing check and quarantines nothing" % index)
    lower = None
    for earlier in reversed(checked[:index]):
        if earlier["verdict"] == GAUGE_PASS:
            lower = earlier
            break
    if lower is None:
        return {
            "from_count": checked[0]["crimp_count_at_check"],
            "to_count": failing["crimp_count_at_check"],
            "crimps_affected": failing["crimp_count_at_check"]
            - checked[0]["crimp_count_at_check"],
            "bounded_by": BOUNDED_OPEN,
        }
    return {
        "from_count": lower["crimp_count_at_check"],
        "to_count": failing["crimp_count_at_check"],
        "crimps_affected": failing["crimp_count_at_check"]
        - lower["crimp_count_at_check"],
        "bounded_by": BOUNDED_BY_LAST_PASS,
    }


def assess_shift(entries):
    """Roll a run of operator checks up into releases and quarantines."""
    checked = validate_log(entries)
    decisions = [release_decision(e) for e in entries]
    quarantines = []
    affected = 0
    for index, current in enumerate(checked):
        if current["verdict"] != GAUGE_PASS:
            span = quarantine_span(entries, index)
            span["at_index"] = index
            quarantines.append(span)
            affected += span["crimps_affected"]
    produced = (
        checked[-1]["crimp_count_at_check"] - checked[0]["crimp_count_at_check"]
    )
    fraction = 0.0 if produced == 0 else affected / produced
    return {
        "tool_id": checked[0]["tool_id"],
        "decisions": decisions,
        "released_count": sum(1 for d in decisions if d["decision"] == RELEASED),
        "held_count": sum(1 for d in decisions if d["decision"] == HELD),
        "quarantines": quarantines,
        "crimps_affected": affected,
        "crimps_produced": produced,
        "quarantine_fraction": fraction,
        "clean": not quarantines,
    }
