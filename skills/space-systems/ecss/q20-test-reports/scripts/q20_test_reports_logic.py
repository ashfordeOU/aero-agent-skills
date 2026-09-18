"""Quality-assurance grading of a test report.

Anchor: ECSS-Q-ST-20C clause 5.6.3.2 (content of test reports, completeness of
the recorded data, recording of discrepancies and approval of the report).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the report and refuse a malformed one: identification, the
   configuration tested, the procedure and revision run, the test window, the
   recorded results, the discrepancy record, the stated conclusion and the
   approval signatures.
2. Grade content: every mandatory section present and carrying something.
3. Grade data completeness: every parameter the procedure demanded either
   carries a finite measured value in the demanded unit, or is declared not
   measured with a justification; the completeness fraction is kept as
   evidence.
4. Grade each measured value against its acceptance limits, treating a value
   sitting on a limit as inside it within a stated tolerance.
5. Grade the discrepancy record: every anomaly seen during the run is written
   up, every write-up carries a nonconformance reference and a disposition.
6. Grade the approvals and the stated conclusion against the graded results,
   then return approve or return-for-correction with the findings.
"""

import math
from datetime import date

__all__ = [
    "REQUIRED_SECTIONS",
    "MANDATORY_APPROVAL_ROLES",
    "LIMIT_TOLERANCE",
    "normalise_identifier",
    "parse_iso_date",
    "validate_report",
    "section_findings",
    "data_completeness",
    "grade_measurement",
    "results_outcome",
    "discrepancy_findings",
    "approval_findings",
    "conclusion_findings",
    "assess_test_report",
]

# Sections a report carries before it can be graded at all. Ordered, because
# the findings are reported in this order.
REQUIRED_SECTIONS = (
    "identification",
    "article_configuration",
    "procedure_reference",
    "test_conditions",
    "conclusion",
)

# Signatures a report carries before it is an approved record.
MANDATORY_APPROVAL_ROLES = ("test-responsible", "product-assurance")

# A measured value that should sit exactly on its limit can land a few ULPs
# outside it. Absorb the representation error here rather than by widening the
# engineering limit.
LIMIT_TOLERANCE = 1e-9


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_iso_date(value, label):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        parts = [int(part) for part in value.strip().split("-")]
    except ValueError:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))
    if len(parts) != 3:
        raise ValueError("%s is not an ISO yyyy-mm-dd date: %r" % (label, value))
    try:
        return date(parts[0], parts[1], parts[2])
    except ValueError:
        raise ValueError("%s is not a real calendar date: %r" % (label, value))


def _validate_results(raw_results):
    """Return the normalised measured-result list of a report."""
    if raw_results is None:
        raw_results = []
    if not isinstance(raw_results, (list, tuple)):
        raise ValueError("report 'results' must be a sequence")
    results = {}
    for index, item in enumerate(raw_results):
        if not isinstance(item, dict):
            raise ValueError("results[%d] must be a mapping" % index)
        parameter = normalise_identifier(item.get("parameter"), "results[%d].parameter" % index)
        if parameter in results:
            raise ValueError("duplicate measured parameter %r" % parameter)
        entry = {"parameter": parameter}
        if item.get("not_measured", False):
            justification = item.get("justification")
            if not isinstance(justification, str) or not justification.strip():
                raise ValueError(
                    "results[%d] is declared not measured without a justification" % index
                )
            entry["not_measured"] = True
            entry["justification"] = justification.strip()
            entry["value"] = None
            entry["unit"] = None
        else:
            value = item.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("results[%d].value must be a real number" % index)
            if not math.isfinite(float(value)):
                raise ValueError("results[%d].value must be finite" % index)
            entry["not_measured"] = False
            entry["justification"] = None
            entry["value"] = float(value)
            entry["unit"] = normalise_identifier(item.get("unit"), "results[%d].unit" % index)
        results[parameter] = entry
    return results


def _validate_discrepancies(raw):
    """Return the normalised discrepancy list of a report."""
    if raw is None:
        raw = []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("report 'discrepancies' must be a sequence")
    entries = []
    seen = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("discrepancies[%d] must be a mapping" % index)
        anomaly = normalise_identifier(item.get("anomaly"), "discrepancies[%d].anomaly" % index)
        if anomaly in seen:
            raise ValueError("duplicate discrepancy for anomaly %r" % anomaly)
        seen.add(anomaly)
        reference = item.get("nonconformance_reference")
        disposition = item.get("disposition")
        entries.append(
            {
                "anomaly": anomaly,
                "nonconformance_reference": (
                    None if reference is None else normalise_identifier(
                        reference, "discrepancies[%d].nonconformance_reference" % index
                    )
                ),
                "disposition": (
                    None if disposition is None else normalise_identifier(
                        disposition, "discrepancies[%d].disposition" % index
                    )
                ),
            }
        )
    return entries


def _validate_approvals(raw):
    """Return the normalised approval list of a report."""
    if raw is None:
        raw = []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("report 'approvals' must be a sequence")
    approvals = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("approvals[%d] must be a mapping" % index)
        role = normalise_identifier(item.get("role"), "approvals[%d].role" % index)
        if role in approvals:
            raise ValueError("duplicate approval role %r" % role)
        approvals[role] = parse_iso_date(item.get("date"), "approvals[%d].date" % index)
    return approvals


def validate_report(report):
    """Return a normalised report record; raise on a malformed one."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    record = {
        "sections": {},
        "results": _validate_results(report.get("results")),
        "discrepancies": _validate_discrepancies(report.get("discrepancies")),
        "approvals": _validate_approvals(report.get("approvals")),
        "test_end_date": parse_iso_date(report.get("test_end_date"), "test_end_date"),
        "issue_date": parse_iso_date(report.get("issue_date"), "issue_date"),
    }
    if record["issue_date"] < record["test_end_date"]:
        raise ValueError("issue_date precedes test_end_date")
    for key in REQUIRED_SECTIONS:
        value = report.get(key)
        record["sections"][key] = value.strip() if isinstance(value, str) else value
    observed = report.get("observed_anomalies")
    if observed is None:
        observed = []
    if not isinstance(observed, (list, tuple)):
        raise ValueError("report 'observed_anomalies' must be a sequence")
    record["observed_anomalies"] = [
        normalise_identifier(item, "observed_anomalies[%d]" % i)
        for i, item in enumerate(observed)
    ]
    return record


def section_findings(record):
    """Return a finding per mandatory report section that is absent or blank."""
    findings = []
    for key in REQUIRED_SECTIONS:
        value = record["sections"].get(key)
        if value is None or (isinstance(value, str) and not value):
            findings.append("report section '%s' is absent or blank" % key)
    return findings


def _validate_required_parameters(required_parameters):
    """Return the normalised list of parameters the procedure demanded."""
    if not isinstance(required_parameters, (list, tuple)) or not required_parameters:
        raise ValueError("required_parameters must be a non-empty sequence")
    parameters = []
    seen = set()
    for index, item in enumerate(required_parameters):
        if not isinstance(item, dict):
            raise ValueError("required_parameters[%d] must be a mapping" % index)
        pid = normalise_identifier(item.get("id"), "required_parameters[%d].id" % index)
        if pid in seen:
            raise ValueError("duplicate required parameter %r" % pid)
        seen.add(pid)
        unit = normalise_identifier(item.get("unit"), "required_parameters[%d].unit" % index)
        entry = {"id": pid, "unit": unit, "minimum": None, "maximum": None}
        for bound in ("minimum", "maximum"):
            value = item.get(bound)
            if value is None:
                continue
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("required_parameters[%d].%s must be a real number" % (index, bound))
            if not math.isfinite(float(value)):
                raise ValueError("required_parameters[%d].%s must be finite" % (index, bound))
            entry[bound] = float(value)
        if entry["minimum"] is not None and entry["maximum"] is not None:
            if entry["minimum"] > entry["maximum"]:
                raise ValueError("required_parameters[%d] has an inverted limit band" % index)
        parameters.append(entry)
    return parameters


def data_completeness(record, required_parameters):
    """Return the data-completeness result of a report."""
    parameters = _validate_required_parameters(required_parameters)
    missing = []
    wrong_unit = []
    declared_not_measured = []
    recorded = 0
    for parameter in parameters:
        entry = record["results"].get(parameter["id"])
        if entry is None:
            missing.append(parameter["id"])
            continue
        if entry["not_measured"]:
            declared_not_measured.append(parameter["id"])
            continue
        if entry["unit"] != parameter["unit"]:
            wrong_unit.append(parameter["id"])
            continue
        recorded += 1
    extra = [pid for pid in record["results"] if pid not in {p["id"] for p in parameters}]
    findings = []
    if missing:
        findings.append("procedure parameters with no recorded result: %s" % ", ".join(missing))
    if wrong_unit:
        findings.append("results recorded in the wrong unit: %s" % ", ".join(wrong_unit))
    if extra:
        findings.append("results the procedure did not demand: %s" % ", ".join(sorted(extra)))
    return {
        "required_count": len(parameters),
        "recorded_count": recorded,
        "missing": missing,
        "wrong_unit": wrong_unit,
        "declared_not_measured": declared_not_measured,
        "extra": sorted(extra),
        "completeness_ratio": recorded / float(len(parameters)),
        "findings": findings,
    }


def grade_measurement(value, minimum=None, maximum=None):
    """Return 'within', 'below' or 'above' for a value against its limits."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be a real number")
    measured = float(value)
    if not math.isfinite(measured):
        raise ValueError("value must be finite")
    if minimum is None and maximum is None:
        raise ValueError("a measurement needs at least one limit to be graded")
    if minimum is not None:
        limit = float(minimum)
        if measured < limit and not math.isclose(
            measured, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            return "below"
    if maximum is not None:
        limit = float(maximum)
        if measured > limit and not math.isclose(
            measured, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
        ):
            return "above"
    return "within"


def results_outcome(record, required_parameters):
    """Return the per-parameter grading and the overall measured outcome."""
    parameters = _validate_required_parameters(required_parameters)
    graded = {}
    out_of_limit = []
    for parameter in parameters:
        entry = record["results"].get(parameter["id"])
        if entry is None or entry["not_measured"]:
            continue
        if parameter["minimum"] is None and parameter["maximum"] is None:
            graded[parameter["id"]] = "unlimited"
            continue
        verdict = grade_measurement(entry["value"], parameter["minimum"], parameter["maximum"])
        graded[parameter["id"]] = verdict
        if verdict != "within":
            out_of_limit.append(parameter["id"])
    return {
        "graded": graded,
        "out_of_limit": out_of_limit,
        "measured_outcome": "pass" if not out_of_limit else "fail",
    }


def discrepancy_findings(record):
    """Return the findings of the discrepancy record."""
    written = {item["anomaly"]: item for item in record["discrepancies"]}
    findings = []
    unwritten = [a for a in record["observed_anomalies"] if a not in written]
    if unwritten:
        findings.append("anomalies seen during the run with no discrepancy entry: %s" % ", ".join(unwritten))
    for anomaly in sorted(written):
        entry = written[anomaly]
        if entry["nonconformance_reference"] is None:
            findings.append("discrepancy %s carries no nonconformance reference" % anomaly)
        if entry["disposition"] is None:
            findings.append("discrepancy %s carries no disposition" % anomaly)
    return findings


def approval_findings(record):
    """Return the approval findings of a report."""
    findings = []
    for role in MANDATORY_APPROVAL_ROLES:
        signed = record["approvals"].get(role)
        if signed is None:
            findings.append("missing %s approval" % role)
            continue
        if signed < record["test_end_date"]:
            findings.append("%s approval predates the end of the test" % role)
        elif signed > record["issue_date"]:
            findings.append("%s approval is dated after the report issued" % role)
    return findings


def conclusion_findings(record, outcome):
    """Return a finding when the stated conclusion contradicts the results."""
    stated = record["sections"].get("conclusion")
    if not isinstance(stated, str) or not stated:
        return []
    verdict = stated.strip().lower()
    if verdict not in ("pass", "fail"):
        return ["report conclusion %r is neither pass nor fail" % stated]
    if verdict == "pass" and outcome["measured_outcome"] == "fail":
        return [
            "report concludes pass with parameters outside limits: %s"
            % ", ".join(outcome["out_of_limit"])
        ]
    if verdict == "pass":
        open_items = [
            item["anomaly"] for item in record["discrepancies"] if item["disposition"] is None
        ]
        if open_items:
            return ["report concludes pass with undispositioned discrepancies: %s" % ", ".join(sorted(open_items))]
    return []


def assess_test_report(report, required_parameters):
    """Grade a whole test report and return the approval verdict."""
    record = validate_report(report)
    completeness = data_completeness(record, required_parameters)
    outcome = results_outcome(record, required_parameters)
    findings = []
    findings.extend(section_findings(record))
    findings.extend(completeness["findings"])
    findings.extend(discrepancy_findings(record))
    findings.extend(approval_findings(record))
    findings.extend(conclusion_findings(record, outcome))
    return {
        "completeness_ratio": completeness["completeness_ratio"],
        "recorded_count": completeness["recorded_count"],
        "required_count": completeness["required_count"],
        "graded_parameters": outcome["graded"],
        "out_of_limit": outcome["out_of_limit"],
        "measured_outcome": outcome["measured_outcome"],
        "findings": findings,
        "verdict": "approved" if not findings else "returned-for-correction",
    }
