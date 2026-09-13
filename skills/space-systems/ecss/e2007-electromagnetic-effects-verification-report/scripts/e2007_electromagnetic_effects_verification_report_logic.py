#!/usr/bin/env python3
"""Electromagnetic effects verification report logic (ECSS-E-ST-20-07C, 5.1.3).

Offline, deterministic, standard-library only. The module supports the
report that captures the analyses, measured results and outcomes of the
electromagnetic compatibility verification campaign:

* correction of an indicated receiver reading into a corrected level,
* emission margin against the applicable limit and the margin required by
  the criticality of the function,
* consistency between the recorded outcome and the measured margin,
* evidence-reference form per verification-method,
* nonconformance capture and disposition for every non-nominal outcome,
* traceability of the reported entries back to the planned activities,
* campaign closure status.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math
from datetime import date

__all__ = [
    "REL_TOL",
    "RESULT_STATES",
    "VERIFICATION_METHODS",
    "EVIDENCE_PREFIX",
    "CRITICALITY_MARGIN_DB",
    "DISPOSITIONS",
    "normalize_method",
    "normalize_result",
    "normalize_criticality",
    "normalize_disposition",
    "parse_report_date",
    "compute_corrected_level_db",
    "compute_margin_db",
    "required_margin_db",
    "margin_verdict",
    "evidence_reference_valid",
    "validate_report_entry",
    "evaluate_entry",
    "check_traceability",
    "summarize_campaign",
    "assess_verification_report",
]

# Absorbs binary-representation error when a corrected level built from a
# sum of decibel terms lands a few ULPs on the wrong side of an exactly
# satisfied margin. It never relaxes the required margin itself.
REL_TOL = 1e-9

RESULT_STATES = ("pass", "pass-with-deviation", "fail", "not-run")

_RESULT_SYNONYMS = {
    "p": "pass",
    "passed": "pass",
    "compliant": "pass",
    "f": "fail",
    "failed": "fail",
    "non-compliant": "fail",
    "pwd": "pass-with-deviation",
    "pass with deviation": "pass-with-deviation",
    "deviation": "pass-with-deviation",
    "open": "not-run",
    "not run": "not-run",
    "nr": "not-run",
}

VERIFICATION_METHODS = ("test", "analysis", "review-of-design", "inspection", "similarity")

_METHOD_SYNONYMS = {
    "t": "test",
    "a": "analysis",
    "r": "review-of-design",
    "rod": "review-of-design",
    "review of design": "review-of-design",
    "i": "inspection",
    "s": "similarity",
    "heritage": "similarity",
}

# Evidence carried by each method has its own document family, and the
# reference prefix is how the report ties an outcome to that document.
EVIDENCE_PREFIX = {
    "test": "tr-",
    "analysis": "an-",
    "review-of-design": "rd-",
    "inspection": "ir-",
    "similarity": "sr-",
}

# Margin the measured level must keep below the applicable limit, by the
# criticality of the function the emitting or receiving item serves.
CRITICALITY_MARGIN_DB = {
    "standard": 0.0,
    "mission-critical": 3.0,
    "safety-critical": 6.0,
}

DISPOSITIONS = frozenset(
    {"accept-as-is", "repair", "rework", "waiver", "retest-passed"}
)

_NON_NOMINAL = ("fail", "pass-with-deviation")

_REQUIRED_ENTRY_KEYS = (
    "activity_id",
    "requirement_id",
    "method",
    "result",
    "report_date",
)

_REQUIRED_REPORT_KEYS = ("planned_activities", "entries")


def _finding(code, subject, detail):
    """Build one report finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _norm_token(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    token = " ".join(value.strip().lower().replace("_", "-").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def normalize_method(method):
    """Return the canonical verification-method token."""
    token = _norm_token(method, "verification method")
    token = _METHOD_SYNONYMS.get(token, token)
    if token not in VERIFICATION_METHODS:
        raise ValueError(
            "unknown verification method %r; expected one of %s"
            % (method, ", ".join(VERIFICATION_METHODS))
        )
    return token


def normalize_result(result):
    """Return the canonical recorded-outcome token."""
    token = _norm_token(result, "result")
    token = _RESULT_SYNONYMS.get(token, token)
    if token not in RESULT_STATES:
        raise ValueError(
            "unknown result %r; expected one of %s" % (result, ", ".join(RESULT_STATES))
        )
    return token


def normalize_criticality(criticality):
    """Return the canonical function-criticality token."""
    token = _norm_token(criticality, "criticality")
    if token not in CRITICALITY_MARGIN_DB:
        raise ValueError(
            "unknown criticality %r; expected one of %s"
            % (criticality, ", ".join(sorted(CRITICALITY_MARGIN_DB)))
        )
    return token


def normalize_disposition(disposition):
    """Return the canonical nonconformance-disposition token."""
    token = _norm_token(disposition, "disposition")
    if token not in DISPOSITIONS:
        token = token.replace(" ", "-")
    if token not in DISPOSITIONS:
        raise ValueError(
            "unknown disposition %r; expected one of %s"
            % (disposition, ", ".join(sorted(DISPOSITIONS)))
        )
    return token


def parse_report_date(value):
    """Accept a date object or an ISO-8601 day string; reject anything else."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError(
            "report date must be an ISO-8601 string or a date, got %s"
            % type(value).__name__
        )
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("report date %r is not an ISO-8601 calendar day" % value)


def compute_corrected_level_db(indicated_dbuv, corrections_db=()):
    """Apply the measurement-chain corrections to the indicated reading.

    Each correction is a decibel term added to the receiver reading: a
    positive term (antenna-factor, cable-loss) raises the corrected level, a
    negative term (pre-amplifier gain) lowers it.
    """
    level = _as_float(indicated_dbuv, "indicated_dbuv")
    if isinstance(corrections_db, (str, bytes)) or not hasattr(
        corrections_db, "__iter__"
    ):
        raise ValueError("corrections_db must be an iterable of decibel terms")
    for index, term in enumerate(corrections_db):
        level += _as_float(term, "corrections_db[%d]" % index)
    return level


def compute_margin_db(limit_dbuv, corrected_dbuv):
    """Margin of the corrected level below the applicable limit, in dB."""
    limit = _as_float(limit_dbuv, "limit_dbuv")
    corrected = _as_float(corrected_dbuv, "corrected_dbuv")
    return limit - corrected


def required_margin_db(criticality="standard"):
    """Margin required by the criticality of the served function."""
    return CRITICALITY_MARGIN_DB[normalize_criticality(criticality)]


def margin_verdict(margin_db, criticality="standard"):
    """Return 'pass' when the margin meets the required margin, else 'fail'."""
    margin = _as_float(margin_db, "margin_db")
    required = required_margin_db(criticality)
    if margin >= required or math.isclose(margin, required, rel_tol=REL_TOL, abs_tol=0.0):
        return "pass"
    return "fail"


def evidence_reference_valid(method, evidence_ref):
    """True when the evidence reference matches the document family."""
    canonical = normalize_method(method)
    if not isinstance(evidence_ref, str):
        raise ValueError(
            "evidence_ref must be a string, got %s" % type(evidence_ref).__name__
        )
    ref = evidence_ref.strip().lower()
    if not ref:
        return False
    prefix = EVIDENCE_PREFIX[canonical]
    return ref.startswith(prefix) and len(ref) > len(prefix)


def _validate_measurement(measurement):
    if not isinstance(measurement, dict):
        raise ValueError(
            "measurement must be a mapping, got %s" % type(measurement).__name__
        )
    for key in ("limit_dbuv", "indicated_dbuv"):
        if key not in measurement:
            raise ValueError("measurement is missing required key %r" % key)
    corrections = measurement.get("corrections_db", ())
    corrected = compute_corrected_level_db(measurement["indicated_dbuv"], corrections)
    record = {
        "limit_dbuv": _as_float(measurement["limit_dbuv"], "limit_dbuv"),
        "indicated_dbuv": _as_float(measurement["indicated_dbuv"], "indicated_dbuv"),
        "corrections_db": [
            _as_float(term, "corrections_db") for term in corrections
        ],
        "corrected_dbuv": corrected,
        "criticality": normalize_criticality(measurement.get("criticality", "standard")),
    }
    record["margin_db"] = compute_margin_db(record["limit_dbuv"], corrected)
    record["required_margin_db"] = required_margin_db(record["criticality"])
    record["verdict"] = margin_verdict(record["margin_db"], record["criticality"])
    return record


def validate_report_entry(entry):
    """Normalize one report entry; raise on malformed input."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping, got %s" % type(entry).__name__)
    absent = [key for key in _REQUIRED_ENTRY_KEYS if key not in entry]
    if absent:
        raise ValueError("entry is missing required key(s): %s" % ", ".join(absent))
    record = {
        "activity_id": _norm_token(entry["activity_id"], "activity id"),
        "requirement_id": _norm_token(entry["requirement_id"], "requirement id"),
        "method": normalize_method(entry["method"]),
        "result": normalize_result(entry["result"]),
        "report_date": parse_report_date(entry["report_date"]),
    }
    evidence = entry.get("evidence_ref", "")
    if evidence is None:
        evidence = ""
    if not isinstance(evidence, str):
        raise ValueError(
            "evidence_ref must be a string when present, got %s"
            % type(evidence).__name__
        )
    record["evidence_ref"] = evidence.strip()
    measurement = entry.get("measurement")
    record["measurement"] = (
        None if measurement is None else _validate_measurement(measurement)
    )
    nonconformance = entry.get("nonconformance")
    if nonconformance is None:
        record["nonconformance"] = None
    else:
        if not isinstance(nonconformance, dict):
            raise ValueError(
                "nonconformance must be a mapping, got %s"
                % type(nonconformance).__name__
            )
        if "id" not in nonconformance:
            raise ValueError("nonconformance is missing required key 'id'")
        disposition = nonconformance.get("disposition")
        record["nonconformance"] = {
            "id": _norm_token(nonconformance["id"], "nonconformance id"),
            "disposition": (
                None if disposition is None else normalize_disposition(disposition)
            ),
        }
    return record


def evaluate_entry(entry):
    """Evaluate one report entry and return its record plus findings."""
    record = validate_report_entry(entry)
    findings = []
    subject = record["activity_id"]
    if record["result"] == "not-run":
        findings.append(
            _finding(
                "activity-not-executed",
                subject,
                "the campaign reports no outcome for this planned activity",
            )
        )
    else:
        if not evidence_reference_valid(record["method"], record["evidence_ref"]):
            findings.append(
                _finding(
                    "evidence-reference-invalid",
                    subject,
                    "outcome closed by %s needs a reference of the form %sNNN"
                    % (record["method"], EVIDENCE_PREFIX[record["method"]]),
                )
            )
    measurement = record["measurement"]
    if measurement is not None:
        if record["result"] == "pass" and measurement["verdict"] == "fail":
            findings.append(
                _finding(
                    "result-contradicts-measured-margin",
                    subject,
                    "recorded pass against a margin of %.3f dB, below the %.3f dB "
                    "required" % (measurement["margin_db"], measurement["required_margin_db"]),
                )
            )
        if record["result"] == "fail" and measurement["verdict"] == "pass":
            findings.append(
                _finding(
                    "result-contradicts-measured-margin",
                    subject,
                    "recorded fail against a margin of %.3f dB, at or above the "
                    "%.3f dB required"
                    % (measurement["margin_db"], measurement["required_margin_db"]),
                )
            )
    elif record["method"] == "test" and record["result"] != "not-run":
        findings.append(
            _finding(
                "measured-data-absent",
                subject,
                "an outcome closed by measurement must carry the measured level "
                "and the applicable limit",
            )
        )
    if record["result"] in _NON_NOMINAL:
        nonconformance = record["nonconformance"]
        if nonconformance is None:
            findings.append(
                _finding(
                    "nonconformance-missing",
                    subject,
                    "a %s outcome must raise a nonconformance" % record["result"],
                )
            )
        elif nonconformance["disposition"] is None:
            findings.append(
                _finding(
                    "nonconformance-undispositioned",
                    subject,
                    "nonconformance %s carries no disposition" % nonconformance["id"],
                )
            )
    record["findings"] = findings
    return record


def check_traceability(planned_activities, entries):
    """Compare the planned activity set with the reported entry set."""
    if isinstance(planned_activities, (str, bytes)) or not hasattr(
        planned_activities, "__iter__"
    ):
        raise ValueError("planned_activities must be an iterable of activity ids")
    planned = []
    for raw in planned_activities:
        token = _norm_token(raw, "planned activity id")
        if token in planned:
            raise ValueError("planned activity %r is listed twice" % token)
        planned.append(token)
    if not planned:
        raise ValueError("the planned activity list must not be empty")
    reported = []
    for raw in entries:
        token = validate_report_entry(raw)["activity_id"]
        if token in reported:
            raise ValueError("activity %r is reported twice" % token)
        reported.append(token)
    unreported = sorted(set(planned) - set(reported))
    unplanned = sorted(set(reported) - set(planned))
    return {
        "planned_count": len(planned),
        "reported_count": len(reported),
        "unreported_activities": unreported,
        "unplanned_entries": unplanned,
        "completeness_fraction": (len(planned) - len(unreported)) / float(len(planned)),
    }


def summarize_campaign(entries):
    """Count reported outcomes by state and report the pass fraction."""
    counts = dict((state, 0) for state in RESULT_STATES)
    total = 0
    for raw in entries:
        counts[validate_report_entry(raw)["result"]] += 1
        total += 1
    if total == 0:
        raise ValueError("a verification report must contain at least one entry")
    return {
        "entry_count": total,
        "counts": counts,
        "pass_fraction": counts["pass"] / float(total),
        "open_count": counts["fail"] + counts["not-run"],
    }


def assess_verification_report(report):
    """Assess one electromagnetic-effects verification report end to end."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %s" % type(report).__name__)
    absent = [key for key in _REQUIRED_REPORT_KEYS if key not in report]
    if absent:
        raise ValueError("report is missing required key(s): %s" % ", ".join(absent))
    evaluated = [evaluate_entry(raw) for raw in report["entries"]]
    if not evaluated:
        raise ValueError("a verification report must contain at least one entry")
    findings = []
    for record in evaluated:
        findings.extend(record["findings"])
    traceability = check_traceability(report["planned_activities"], evaluated)
    for activity_id in traceability["unreported_activities"]:
        findings.append(
            _finding(
                "planned-activity-unreported",
                activity_id,
                "a planned activity has no entry in the report",
            )
        )
    for activity_id in traceability["unplanned_entries"]:
        findings.append(
            _finding(
                "entry-outside-plan",
                activity_id,
                "the report carries an entry for an activity that was never planned",
            )
        )
    summary = summarize_campaign(evaluated)
    closed = not findings and summary["open_count"] == 0
    return {
        "verdict": "campaign-closed" if closed else "campaign-open",
        "closed": closed,
        "findings": findings,
        "traceability": traceability,
        "summary": summary,
        "entries": evaluated,
    }
