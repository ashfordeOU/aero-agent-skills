"""Traceability records behind a wrapped assembly.

Anchor: ECSS-Q-ST-70-30C, wrapping records clauses (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Tie every wrap to the hand and the machine that made it. A wrap
   record with no operator or no tool cannot be reached by a
   containment action later, so the missing field is the defect, not a
   formality.
2. Hold the tool in date on the day of the wrap, not on the day of the
   audit. A tool whose calibration expired before it made the wrap
   taints the wraps it made after that date and no others, so the
   comparison is per wrap.
3. Hold the tool setup verification inside its own short window. The
   bit and sleeve are set at the start of a shift and drift with use,
   so the verification is a daily fact rather than an annual one, and
   it must not post-date the work it claims to cover.
4. Demand pull-test evidence per group. The destructive test is a
   property of the operator, tool and gauge together, so every such
   group present on the assembly owes at least one referenced pull
   test.
5. Watch the retention clock. A record set that falls out of retention
   before the hardware leaves service is evidence that will not exist
   when it is needed.
6. Return coverage figures with an itemized list of what is missing, so
   the package is closed on findings rather than on a percentage.

Every threshold is a declared project policy value the caller may
override, because the record scheme a programme adopts belongs to its
own process specification.

Stdlib only, offline, deterministic.
"""

import datetime

VALID_GAUGES = (20, 22, 24, 26, 28, 30)

# The tool setup is verified at the start of a shift, so the
# verification covers the wrap only within this many days of it.
TOOL_SETUP_VALIDITY_DAYS = 1

# Years the record set is kept after the wrap date.
RECORD_RETENTION_YEARS = 10
DAYS_PER_YEAR = 365

COMPLETE = "record-set-complete"
INCOMPLETE = "record-set-incomplete"

# Coverage is a ratio of two integer counts converted to a float, so a
# fully covered set can land a few units in the last place below one.
# This tolerance absorbs that representation error without letting a
# genuinely short set read as complete.
COVERAGE_TOLERANCE = 1.0e-12


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _optional_text(label, value):
    if value is None:
        return None
    return _text(label, value)


def _date(label, value):
    if isinstance(value, datetime.datetime) or not isinstance(value, datetime.date):
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                raise ValueError("%s must be an ISO date, got %r" % (label, value))
        raise ValueError("%s must be a date, got %r" % (label, value))
    return value


def _gauge(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value not in VALID_GAUGES:
        raise ValueError(
            "%s %r is outside the record scheme (have %s)"
            % (label, value, ", ".join(str(g) for g in VALID_GAUGES))
        )
    return value


def days_between(earlier, later):
    """Whole days from the earlier date to the later one."""
    return (_date("later", later) - _date("earlier", earlier)).days


def validate_tool(tool):
    """Validate one tool record and return a normalized copy."""
    if not isinstance(tool, dict):
        raise ValueError("tool must be a mapping")
    tool_id = _text("tool id", tool.get("id"))
    return {
        "id": tool_id,
        "calibration_due_date": _date(
            "tool %s calibration_due_date" % tool_id, tool.get("calibration_due_date")
        ),
        "setup_verification_date": _date(
            "tool %s setup_verification_date" % tool_id,
            tool.get("setup_verification_date"),
        ),
    }


def validate_wrap_record(record):
    """Validate one wrap record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("wrap record must be a mapping")
    wrap_id = _text("wrap id", record.get("id"))
    return {
        "id": wrap_id,
        "operator_id": _optional_text(
            "wrap %s operator_id" % wrap_id, record.get("operator_id")
        ),
        "tool_id": _optional_text("wrap %s tool_id" % wrap_id, record.get("tool_id")),
        "gauge": _gauge("wrap %s gauge" % wrap_id, record.get("gauge")),
        "wrap_date": _date("wrap %s wrap_date" % wrap_id, record.get("wrap_date")),
        "pull_test_reference": _optional_text(
            "wrap %s pull_test_reference" % wrap_id, record.get("pull_test_reference")
        ),
        "inspection_reference": _optional_text(
            "wrap %s inspection_reference" % wrap_id, record.get("inspection_reference")
        ),
    }


def validate_package(package):
    """Validate one assembly record package and return a normalized copy."""
    if not isinstance(package, dict):
        raise ValueError("package must be a mapping")
    assembly_id = _text("assembly id", package.get("assembly_id"))
    wraps = package.get("wraps")
    if not isinstance(wraps, list) or not wraps:
        raise ValueError("assembly %s needs a non-empty wrap list" % assembly_id)
    tools = package.get("tools", [])
    if isinstance(tools, dict):
        # A package that has already been through this function carries
        # its tools keyed by id; re-validating one is a no-op rather
        # than a type error, so the helpers can take either form.
        tools = list(tools.values())
    if not isinstance(tools, (list, tuple)):
        raise ValueError("assembly %s tools must be a sequence" % assembly_id)
    normalized_tools = {}
    for tool in tools:
        norm = validate_tool(tool)
        if norm["id"] in normalized_tools:
            raise ValueError("assembly %s has two records for tool %s" % (assembly_id, norm["id"]))
        normalized_tools[norm["id"]] = norm
    normalized_wraps = []
    seen = set()
    for record in wraps:
        norm = validate_wrap_record(record)
        if norm["id"] in seen:
            raise ValueError("assembly %s has two records for wrap %s" % (assembly_id, norm["id"]))
        seen.add(norm["id"])
        normalized_wraps.append(norm)
    return {
        "assembly_id": assembly_id,
        "certified_operators": [
            _text("certified operator id", op)
            for op in package.get("certified_operators", [])
        ],
        "tools": normalized_tools,
        "wraps": normalized_wraps,
    }


def group_key(record):
    """Operator, tool and gauge group one wrap record belongs to."""
    norm = validate_wrap_record(record)
    return (norm["operator_id"], norm["tool_id"], norm["gauge"])


def wrap_findings(record, tools, certified_operators):
    """Findings about the traceability of one wrap record."""
    norm = validate_wrap_record(record)
    findings = []
    if norm["operator_id"] is None:
        findings.append("no-operator-on-the-wrap-record")
    elif certified_operators and norm["operator_id"] not in certified_operators:
        findings.append("operator-not-in-the-certified-list")
    if norm["inspection_reference"] is None:
        findings.append("no-inspection-reference-on-the-wrap-record")
    if norm["tool_id"] is None:
        findings.append("no-tool-on-the-wrap-record")
        return findings
    tool = tools.get(norm["tool_id"])
    if tool is None:
        findings.append("tool-not-described-in-the-package")
        return findings
    if days_between(norm["wrap_date"], tool["calibration_due_date"]) < 0:
        findings.append("tool-calibration-expired-before-the-wrap")
    setup_age = days_between(tool["setup_verification_date"], norm["wrap_date"])
    if setup_age < 0:
        findings.append("tool-setup-verified-after-the-wrap")
    elif setup_age > TOOL_SETUP_VALIDITY_DAYS:
        findings.append("tool-setup-verification-older-than-its-window")
    return findings


def groups_without_pull_test(package):
    """Operator, tool and gauge groups on the assembly with no pull test."""
    norm = validate_package(package)
    seen = set()
    covered = set()
    for record in norm["wraps"]:
        key = (record["operator_id"], record["tool_id"], record["gauge"])
        seen.add(key)
        if record["pull_test_reference"] is not None:
            covered.add(key)
    return sorted(
        seen - covered, key=lambda k: tuple("" if part is None else str(part) for part in k)
    )


def retention_findings(package, on_date):
    """Findings about wrap records approaching the end of retention."""
    norm = validate_package(package)
    day = _date("on_date", on_date)
    expiring = []
    for record in norm["wraps"]:
        age = days_between(record["wrap_date"], day)
        if age > RECORD_RETENTION_YEARS * DAYS_PER_YEAR:
            expiring.append(record["id"])
    return expiring


def audit_wrapping_records(package, on_date):
    """Audit one assembly record package on a given date."""
    norm = validate_package(package)
    certified = set(norm["certified_operators"])
    per_wrap = []
    for record in norm["wraps"]:
        findings = wrap_findings(record, norm["tools"], certified)
        per_wrap.append(
            {
                "id": record["id"],
                "group": (record["operator_id"], record["tool_id"], record["gauge"]),
                "findings": findings,
                "traceable": not findings,
            }
        )
    uncovered = groups_without_pull_test(norm)
    expiring = retention_findings(norm, on_date)
    traceable = [w["id"] for w in per_wrap if w["traceable"]]
    coverage = len(traceable) / float(len(per_wrap))
    package_findings = []
    if uncovered:
        package_findings.append("group-without-a-referenced-pull-test")
    if expiring:
        package_findings.append("wrap-records-past-their-retention-period")
    complete = coverage >= 1.0 - COVERAGE_TOLERANCE and not package_findings
    return {
        "assembly_id": norm["assembly_id"],
        "wraps": per_wrap,
        "untraceable_ids": [w["id"] for w in per_wrap if not w["traceable"]],
        "groups_without_pull_test": uncovered,
        "records_past_retention": expiring,
        "traceability_coverage": coverage,
        "package_findings": package_findings,
        "status": COMPLETE if complete else INCOMPLETE,
        "complete": complete,
    }
