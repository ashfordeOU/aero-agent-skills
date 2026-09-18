"""End-to-end receiving-chain integrity check before an emission measurement.

Anchor: ECSS-E-ST-20-07C clause 5.2.11.2 (the complete receiving chain is
checked at the start of every emission measurement). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalize the receiving chain: a transducer at the head, the cables,
   attenuators, amplifiers and filters between, and the receiver at the tail,
   each carrying its gain in decibels (a loss is a negative gain).
2. Sum the element contributions into an end-to-end gain and predict what a
   reference signal of known level should indicate at the receiver.
3. Compare the indication actually obtained against that prediction and hold
   the deviation to the decibel allowance the campaign declared.
4. Confirm the injection exercised the whole chain: a reference applied part
   way down the chain leaves every element ahead of it unverified.
5. Confirm the check belongs to the run: it must precede the first measured
   point and must not be older than the staleness window, and one check record
   may not be reused to cover a second run.
6. Aggregate the runs into a conforming fraction and one finding per defect.
"""

import datetime
import math

__all__ = [
    "DEVIATION_TOLERANCE_DB",
    "TIME_TOLERANCE_MINUTES",
    "ELEMENT_KINDS",
    "HEAD_KIND",
    "TAIL_KIND",
    "validate_chain",
    "chain_gain_db",
    "expected_indication_dbuv",
    "deviation_db",
    "within_allowance",
    "bypassed_elements",
    "parse_timestamp",
    "check_timing",
    "assess_run",
    "assess_chain_integrity",
]

# Deviations are differences of decibel quantities: an exactly met allowance
# can land a few units in the last place outside it. Absorb the representation
# error here rather than by widening the allowance.
DEVIATION_TOLERANCE_DB = 1e-9
TIME_TOLERANCE_MINUTES = 1e-9

ELEMENT_KINDS = ("transducer", "cable", "attenuator", "preamplifier", "filter", "receiver")
HEAD_KIND = "transducer"
TAIL_KIND = "receiver"

_ELEMENT_KEYS = ("id", "kind", "gain_db")
_CHECK_KEYS = ("time", "injected_dbuv", "measured_dbuv", "injection_point")
_RUN_KEYS = ("id", "start_time", "check")


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-blank string" % label)
    return value.strip()


def validate_chain(elements):
    """Return the validated receiving chain, head to tail."""
    if isinstance(elements, dict) or not isinstance(elements, (list, tuple)):
        raise ValueError("chain must be a sequence of element records")
    if len(elements) < 2:
        raise ValueError("a receiving chain needs at least a transducer and a receiver")
    normalized = []
    seen = set()
    for index, item in enumerate(elements):
        if not isinstance(item, dict):
            raise ValueError("chain[%d] must be a mapping" % index)
        unknown = sorted(set(item) - set(_ELEMENT_KEYS))
        if unknown:
            raise ValueError("chain[%d] has unknown key(s): %s" % (index, ", ".join(unknown)))
        for key in _ELEMENT_KEYS:
            if key not in item:
                raise ValueError("chain[%d] missing required key '%s'" % (index, key))
        kind = item["kind"]
        if not isinstance(kind, str) or kind.strip().lower() not in ELEMENT_KINDS:
            raise ValueError(
                "chain[%d] kind must be one of %s, got %r"
                % (index, ", ".join(ELEMENT_KINDS), kind)
            )
        identifier = _identifier(item["id"], "chain[%d] id" % index)
        if identifier in seen:
            raise ValueError("duplicate chain element id %r" % identifier)
        seen.add(identifier)
        normalized.append({
            "id": identifier,
            "kind": kind.strip().lower(),
            "gain_db": _real(item["gain_db"], "chain[%d] gain_db" % index),
        })
    if normalized[0]["kind"] != HEAD_KIND:
        raise ValueError("the chain must start at the %s that senses the emission" % HEAD_KIND)
    if normalized[-1]["kind"] != TAIL_KIND:
        raise ValueError("the chain must end at the %s that indicates the level" % TAIL_KIND)
    for element in normalized[1:]:
        if element["kind"] == HEAD_KIND:
            raise ValueError("only the head element may be a %s" % HEAD_KIND)
    for element in normalized[:-1]:
        if element["kind"] == TAIL_KIND:
            raise ValueError("only the tail element may be a %s" % TAIL_KIND)
    return normalized


def chain_gain_db(elements):
    """Return the end-to-end gain of the chain in decibels."""
    validated = validate_chain(elements)
    return math.fsum(element["gain_db"] for element in validated)


def expected_indication_dbuv(injected_dbuv, elements):
    """Return the level the receiver should indicate for an injected reference."""
    level = _real(injected_dbuv, "injected_dbuv")
    return level + chain_gain_db(elements)


def deviation_db(measured_dbuv, expected_dbuv):
    """Return the signed deviation of the indication from its prediction."""
    return _real(measured_dbuv, "measured_dbuv") - _real(expected_dbuv, "expected_dbuv")


def within_allowance(deviation, allowance_db):
    """Return whether a deviation sits inside a two-sided decibel allowance."""
    value = _real(deviation, "deviation")
    allowance = _real(allowance_db, "allowance_db")
    if allowance < 0.0:
        raise ValueError("allowance_db must not be negative, got %g" % allowance)
    return abs(value) <= allowance + DEVIATION_TOLERANCE_DB


def bypassed_elements(elements, injection_point):
    """Return the ids of the elements ahead of the injection point."""
    validated = validate_chain(elements)
    target = _identifier(injection_point, "injection_point")
    ids = [element["id"] for element in validated]
    if target not in ids:
        raise ValueError("injection_point %r names no element of the chain" % target)
    return ids[: ids.index(target)]


def parse_timestamp(value, label="timestamp"):
    """Return a timestamp from a datetime or an ISO 8601 string."""
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("%s must not be blank" % label)
        try:
            return datetime.datetime.fromisoformat(text)
        except ValueError:
            raise ValueError("%s must be an ISO 8601 timestamp, got %r" % (label, value))
    raise ValueError("%s must be a datetime or an ISO 8601 string, got %r" % (label, value))


def check_timing(check_time, run_start, max_age_minutes):
    """Return the ordering and staleness of a check against the run it covers."""
    checked = parse_timestamp(check_time, "check time")
    started = parse_timestamp(run_start, "run start_time")
    if (checked.tzinfo is None) != (started.tzinfo is None):
        raise ValueError("check time and run start_time must both carry a time zone or neither")
    window = _real(max_age_minutes, "max_age_minutes")
    if window <= 0.0:
        raise ValueError("max_age_minutes must be positive, got %g" % window)
    age = (started - checked).total_seconds() / 60.0
    return {
        "age_minutes": age,
        "precedes_run": age >= -TIME_TOLERANCE_MINUTES,
        "stale": age > window + TIME_TOLERANCE_MINUTES,
    }


def assess_run(run, chain, allowance_db, max_age_minutes):
    """Grade one emission run against its own chain-integrity check."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    unknown = sorted(set(run) - set(_RUN_KEYS))
    if unknown:
        raise ValueError("run has unknown key(s): %s" % ", ".join(unknown))
    for key in ("id", "start_time"):
        if key not in run:
            raise ValueError("run missing required key '%s'" % key)
    identifier = _identifier(run["id"], "run id")
    started = parse_timestamp(run["start_time"], "run start_time")
    validated = validate_chain(chain)
    findings = []
    check = run.get("check")
    if check is None:
        findings.append("run %s recorded no chain-integrity check" % identifier)
        return {
            "id": identifier,
            "start_time": started,
            "checked": False,
            "findings": findings,
            "conforming": False,
        }
    if not isinstance(check, dict):
        raise ValueError("run check must be a mapping")
    unknown = sorted(set(check) - set(_CHECK_KEYS))
    if unknown:
        raise ValueError("run check has unknown key(s): %s" % ", ".join(unknown))
    for key in _CHECK_KEYS:
        if key not in check:
            raise ValueError("run check missing required key '%s'" % key)
    expected = expected_indication_dbuv(check["injected_dbuv"], validated)
    deviation = deviation_db(check["measured_dbuv"], expected)
    conforming_level = within_allowance(deviation, allowance_db)
    bypassed = bypassed_elements(validated, check["injection_point"])
    timing = check_timing(check["time"], started, max_age_minutes)
    if not conforming_level:
        findings.append(
            "run %s: the chain indicated %.3f dB from its prediction, outside the "
            "%.3f dB allowance" % (identifier, deviation, float(allowance_db))
        )
    if bypassed:
        findings.append(
            "run %s: the reference was injected past %s, leaving %s unverified"
            % (identifier, check["injection_point"], ", ".join(bypassed))
        )
    if not timing["precedes_run"]:
        findings.append(
            "run %s: the chain check was performed %.1f minutes after the run began"
            % (identifier, -timing["age_minutes"])
        )
    elif timing["stale"]:
        findings.append(
            "run %s: the chain check is %.1f minutes old, beyond the %.1f minute window"
            % (identifier, timing["age_minutes"], float(max_age_minutes))
        )
    return {
        "id": identifier,
        "start_time": started,
        "checked": True,
        "chain_gain_db": chain_gain_db(validated),
        "expected_dbuv": expected,
        "measured_dbuv": _real(check["measured_dbuv"], "measured_dbuv"),
        "deviation_db": deviation,
        "bypassed": bypassed,
        "age_minutes": timing["age_minutes"],
        "findings": findings,
        "conforming": not findings,
    }


def assess_chain_integrity(spec):
    """Run the full clause 5.2.11.2 assessment over a campaign of emission runs.

    spec keys: chain, runs, allowance_db, optional max_age_minutes.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("chain", "runs", "allowance_db"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    runs = spec["runs"]
    if isinstance(runs, dict) or not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("runs must be a non-empty sequence of run records")
    max_age = spec.get("max_age_minutes", 60.0)
    gradings = [assess_run(run, spec["chain"], spec["allowance_db"], max_age) for run in runs]
    identifiers = [grading["id"] for grading in gradings]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate run id in the campaign")
    signatures = {}
    for run, grading in zip(runs, gradings):
        check = run.get("check")
        if not isinstance(check, dict):
            continue
        signature = (
            str(parse_timestamp(check["time"], "check time")),
            _identifier(check["injection_point"], "injection_point"),
            _real(check["injected_dbuv"], "injected_dbuv"),
            _real(check["measured_dbuv"], "measured_dbuv"),
        )
        signatures.setdefault(signature, []).append(grading)
    for shared in signatures.values():
        if len(shared) > 1:
            names = ", ".join(grading["id"] for grading in shared)
            for grading in shared:
                grading["findings"].append(
                    "run %s: one chain-integrity check record is being reused across "
                    "runs %s; each emission measurement begins with its own"
                    % (grading["id"], names)
                )
                grading["conforming"] = False
    findings = []
    for grading in gradings:
        findings.extend(grading["findings"])
    conforming = [grading for grading in gradings if grading["conforming"]]
    return {
        "runs": gradings,
        "run_count": len(gradings),
        "conforming_count": len(conforming),
        "conforming_fraction": len(conforming) / float(len(gradings)),
        "findings": findings,
        "compliant": not findings,
    }
