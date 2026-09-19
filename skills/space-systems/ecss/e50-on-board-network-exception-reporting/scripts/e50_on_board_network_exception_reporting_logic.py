"""Exception reporting on an on-board network.

Anchor: ECSS-E-ST-50C clause 5.7.2.6 -- on-board network exception reporting.
Paraphrased into an implementable procedure; no standard text is reproduced.

The clause carries two normative items. The first is that the exceptions the
network can raise are detected and reported rather than absorbed. The second
is that a report carries what somebody needs to act on it: which exception it
is, where it came from, and when it happened.

They fail as a ladder, and a report that gives one verdict for the clause
loses which rung a given exception is on. An exception nobody detects is an
instrumentation gap. One that is detected and never leaves the node is a
plumbing gap. One that arrives without a source is a content gap. One that
arrives too late to act on is a timing gap. The four have different owners and
different fixes.

The assessment therefore walks a declared catalogue against a required
exception set and a required field set, reports the worst rung each exception
sits on with the reasons underneath, and keeps the two clause items separate
so a content gap is never reported as full coverage.
"""

import math

__all__ = [
    "REPORTED",
    "DEFICIENT",
    "UNREPORTED",
    "UNDETECTED",
    "DEFAULT_FIELDS",
    "REL_TOL",
    "validate_name",
    "validate_names",
    "validate_latency",
    "normalise_entry",
    "missing_fields",
    "assess_exception",
    "assess_exception_reporting",
]

REPORTED = "reported"
DEFICIENT = "deficient"
UNREPORTED = "unreported"
UNDETECTED = "undetected"

# What a report has to carry before anyone can act on it. Override where a
# programme owes more; shortening the set turns a content gap into a pass.
DEFAULT_FIELDS = ("exception-id", "source", "time")

# Relative tolerance for the report-latency comparison, so a report landing
# exactly on its bound is timely on every platform.
REL_TOL = 1e-9


def validate_name(value, name="name"):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def validate_names(value, name="names"):
    """Return an ordered tuple of distinct identifier strings."""
    if isinstance(value, str):
        raise ValueError("%s must be a list of names, not a single string" % name)
    if not isinstance(value, (list, tuple)):
        raise ValueError("%s must be a list of names, got %r" % (name, type(value).__name__))
    out = []
    for index, item in enumerate(value):
        entry = validate_name(item, "%s[%d]" % (name, index))
        if entry in out:
            raise ValueError("%s repeats %r" % (name, entry))
        out.append(entry)
    return tuple(out)


def validate_latency(value, name="report_latency_s"):
    """Return a non-negative report latency in seconds, or None when unstated."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number or None" % name)
    seconds = float(value)
    if math.isnan(seconds) or math.isinf(seconds):
        raise ValueError("%s must be finite" % name)
    if seconds < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return seconds


def normalise_entry(entry):
    """Return a validated copy of one declared exception catalogue entry."""
    if not isinstance(entry, dict):
        raise ValueError("catalogue entry must be a mapping, got %r" % type(entry).__name__)
    detected = entry.get("detected", False)
    reported = entry.get("reported", False)
    if not isinstance(detected, bool):
        raise ValueError("entry 'detected' must be a boolean, got %r" % (detected,))
    if not isinstance(reported, bool):
        raise ValueError("entry 'reported' must be a boolean, got %r" % (reported,))
    if reported and not detected:
        raise ValueError(
            "entry %r claims a report for an exception it does not detect"
            % entry.get("name")
        )
    return {
        "name": validate_name(entry.get("name"), "exception name"),
        "detected": detected,
        "reported": reported,
        "fields": validate_names(entry.get("fields", []), "fields"),
        "report_latency_s": validate_latency(entry.get("report_latency_s")),
    }


def missing_fields(entry, required=DEFAULT_FIELDS):
    """Return the required report fields this entry does not carry."""
    entry = normalise_entry(entry)
    required = validate_names(required, "required_fields")
    return tuple(field for field in required if field not in entry["fields"])


def assess_exception(entry, required_fields=DEFAULT_FIELDS, latency_bound_s=None):
    """Place one catalogue entry on the detect-report-content-timing ladder."""
    entry = normalise_entry(entry)
    required_fields = validate_names(required_fields, "required_fields")
    bound = validate_latency(latency_bound_s, "latency_bound_s")
    reasons = []
    if not entry["detected"]:
        return {
            "exception": entry["name"],
            "verdict": UNDETECTED,
            "missing_fields": list(required_fields),
            "report_latency_s": entry["report_latency_s"],
            "late": False,
            "reasons": ["%s is not detected by the network" % entry["name"]],
        }
    if not entry["reported"]:
        return {
            "exception": entry["name"],
            "verdict": UNREPORTED,
            "missing_fields": list(required_fields),
            "report_latency_s": entry["report_latency_s"],
            "late": False,
            "reasons": ["%s is detected but never reported off the node" % entry["name"]],
        }
    gaps = missing_fields(entry, required_fields)
    if gaps:
        reasons.append(
            "the report for %s carries no %s" % (entry["name"], ", ".join(gaps))
        )
    late = False
    if bound is not None:
        latency = entry["report_latency_s"]
        if latency is None:
            late = True
            reasons.append(
                "%s declares no report latency against a %.6g s bound" % (entry["name"], bound)
            )
        else:
            tolerance = REL_TOL * max(latency, bound, 1.0)
            late = latency > bound + tolerance
            if late:
                reasons.append(
                    "%s is reported after %.6g s against a %.6g s bound"
                    % (entry["name"], latency, bound)
                )
    return {
        "exception": entry["name"],
        "verdict": DEFICIENT if reasons else REPORTED,
        "missing_fields": list(gaps),
        "report_latency_s": entry["report_latency_s"],
        "late": late,
        "reasons": reasons,
    }


def assess_exception_reporting(
    required_exceptions,
    catalogue,
    required_fields=DEFAULT_FIELDS,
    latency_bound_s=None,
):
    """Assess a declared exception catalogue against what the network owes."""
    required = validate_names(required_exceptions, "required_exceptions")
    if not required:
        raise ValueError("at least one required exception must be declared")
    if not isinstance(catalogue, (list, tuple)):
        raise ValueError("catalogue must be a list")
    entries = [normalise_entry(e) for e in catalogue]
    names = [e["name"] for e in entries]
    if len(set(names)) != len(names):
        raise ValueError("duplicate exception name in the catalogue")
    by_name = dict((e["name"], e) for e in entries)
    per_exception = []
    for name in required:
        entry = by_name.get(name)
        if entry is None:
            entry = {"name": name, "detected": False, "reported": False, "fields": []}
        per_exception.append(assess_exception(entry, required_fields, latency_bound_s))
    undetected = [r["exception"] for r in per_exception if r["verdict"] == UNDETECTED]
    unreported = [r["exception"] for r in per_exception if r["verdict"] == UNREPORTED]
    deficient = [r["exception"] for r in per_exception if r["verdict"] == DEFICIENT]
    late = [r["exception"] for r in per_exception if r["late"]]
    extras = sorted(set(names) - set(required))
    findings = []
    if undetected or unreported:
        findings.append(
            "clause item 1 not met: %s"
            % ", ".join(sorted(undetected + unreported))
        )
    if deficient:
        findings.append(
            "clause item 2 not met: the report for %s does not carry what an "
            "operator needs" % ", ".join(sorted(deficient))
        )
    if extras:
        findings.append(
            "catalogue declares %s, which the required set does not ask for"
            % ", ".join(extras)
        )
    return {
        "required": list(required),
        "catalogue": names,
        "per_exception": per_exception,
        "undetected": undetected,
        "unreported": unreported,
        "deficient": deficient,
        "late": late,
        "extras": extras,
        "detection_ratio": (len(required) - len(undetected)) / float(len(required)),
        "reporting_met": not undetected and not unreported,
        "content_met": not deficient,
        "compliant": not undetected and not unreported and not deficient,
        "findings": findings,
    }
