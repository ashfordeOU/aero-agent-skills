#!/usr/bin/env python3
"""Device verification control document (ECSS-E-ST-20-40C clause 5.1.5).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The verification control document is one controlled record that carries
every device requirement through the verification stages. Three
properties make it a control document rather than a status list:

* it is baselined. An issue number and a revision label identify the
  record, and content that moves without the baseline moving leaves two
  documents claiming to be the same one;
* the stages are ordered -- qualification, acceptance, pre-launch,
  in-orbit -- and each stage assumes the applicable stage before it
  closed on the same requirement. A stage closed behind an open earlier
  stage is invisible cell by cell and obvious in stage order;
* closure is evidence-backed. A status of closed with no report,
  procedure or certificate reference behind it is an assertion the
  record was supposed to make traceable.

Not-applicable is a disposition, not closure: the row leaves the
denominator and is still counted and reported, so a document that moves
its hard rows there cannot read as fully closed. Closure fractions land
on their targets exactly, so the comparison absorbs the representation
error of a division instead of failing on it.
"""

import math

# Verification stages, in the order they run.
VERIFICATION_STAGES = ("qualification", "acceptance", "pre-launch", "in-orbit")
_STAGE_ALIASES = {
    "qualification": "qualification",
    "qual": "qualification",
    "acceptance": "acceptance",
    "acc": "acceptance",
    "pre-launch": "pre-launch",
    "prelaunch": "pre-launch",
    "launch site": "pre-launch",
    "in-orbit": "in-orbit",
    "inorbit": "in-orbit",
    "in flight": "in-orbit",
    "flight": "in-orbit",
}

# Row statuses a stage may carry.
STAGE_STATUSES = ("open", "in-work", "closed", "not-applicable")
_STATUS_ALIASES = {
    "open": "open",
    "not started": "open",
    "in-work": "in-work",
    "in work": "in-work",
    "ongoing": "in-work",
    "closed": "closed",
    "complete": "closed",
    "verified": "closed",
    "not-applicable": "not-applicable",
    "not applicable": "not-applicable",
    "n/a": "not-applicable",
    "na": "not-applicable",
}

# Stages that have to be closed before the device is released for flight.
FLIGHT_RELEASE_STAGES = ("qualification", "acceptance")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_DOCUMENT_REQUIRED_KEYS = ("control", "rows")
_DOCUMENT_OPTIONAL_KEYS = ("closure_targets",)
_CONTROL_KEYS = ("issue", "revision", "configuration_item")
_ROW_KEYS = ("requirement", "stages")
_STAGE_ENTRY_KEYS = ("status", "evidence", "method")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(value):
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def meets_closure_target(achieved, target):
    """True when closure reaches the target, exact landings included."""
    achieved = _fraction("achieved", achieved)
    target = _fraction("target", target)
    return achieved > target or math.isclose(
        achieved, target, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def normalize_stage(value):
    """Fold a stage spelling onto one of the four ordered stages."""
    key = _key(_text("stage", value))
    for candidate in (key, key.replace(" ", "-"), key.replace("-", " ")):
        if candidate in _STAGE_ALIASES:
            return _STAGE_ALIASES[candidate]
    raise ValueError(
        "unknown verification stage %r; use one of %s"
        % (value, ", ".join(VERIFICATION_STAGES))
    )


def normalize_status(value):
    """Fold a stage status onto open, in-work, closed or not-applicable."""
    key = _key(_text("status", value))
    for candidate in (key, key.replace(" ", "-"), key.replace("-", " ")):
        if candidate in _STATUS_ALIASES:
            return _STATUS_ALIASES[candidate]
    raise ValueError(
        "unknown stage status %r; use one of %s" % (value, ", ".join(STAGE_STATUSES))
    )


def stage_index(stage):
    """Position of a stage in the fixed verification order."""
    return VERIFICATION_STAGES.index(normalize_stage(stage))


def validate_control(control):
    """Check the document control block and return issue and revision."""
    if not isinstance(control, dict):
        raise ValueError("control must be a mapping of issue, revision and item")
    unknown = sorted(set(control) - set(_CONTROL_KEYS))
    if unknown:
        raise ValueError("control has unknown keys: %s" % ", ".join(unknown))
    if "issue" not in control:
        raise ValueError("control missing key: issue")
    issue = control["issue"]
    if isinstance(issue, bool) or not isinstance(issue, int):
        raise ValueError("control.issue must be an integer, got %r" % (issue,))
    if issue < 1:
        raise ValueError("control.issue must be at least 1, got %d" % issue)
    return {
        "issue": issue,
        "revision": _text("control.revision", control.get("revision", "")),
        "configuration_item": _text(
            "control.configuration_item",
            control.get("configuration_item", ""),
            allow_empty=True,
        ),
    }


def validate_rows(entries):
    """Check the requirement rows and return them resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("rows must be a list of requirement rows")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("rows[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ROW_KEYS))
        if unknown:
            raise ValueError(
                "rows[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "requirement" not in entry:
            raise ValueError("rows[%d] missing key: requirement" % index)
        requirement = _text("rows[%d].requirement" % index, entry["requirement"])
        if requirement in seen:
            raise ValueError("duplicate requirement row %r" % requirement)
        seen.add(requirement)
        stages = entry.get("stages", {})
        if not isinstance(stages, dict):
            raise ValueError("rows[%d].stages must be a mapping of stage to entry")
        folded = {}
        for raw_stage, raw_entry in stages.items():
            stage = normalize_stage(raw_stage)
            if stage in folded:
                raise ValueError(
                    "row %s repeats the %s stage" % (requirement, stage)
                )
            if not isinstance(raw_entry, dict):
                raise ValueError(
                    "row %s stage %s must be a mapping" % (requirement, stage)
                )
            stray = sorted(set(raw_entry) - set(_STAGE_ENTRY_KEYS))
            if stray:
                raise ValueError(
                    "row %s stage %s has unknown keys: %s"
                    % (requirement, stage, ", ".join(stray))
                )
            if "status" not in raw_entry:
                raise ValueError(
                    "row %s stage %s missing key: status" % (requirement, stage)
                )
            folded[stage] = {
                "status": normalize_status(raw_entry["status"]),
                "evidence": _text(
                    "row %s stage %s evidence" % (requirement, stage),
                    raw_entry.get("evidence", ""),
                    allow_empty=True,
                ),
                "method": _text(
                    "row %s stage %s method" % (requirement, stage),
                    raw_entry.get("method", ""),
                    allow_empty=True,
                ),
            }
        if not folded:
            raise ValueError("row %s records no verification stage" % requirement)
        resolved.append({"requirement": requirement, "stages": folded})
    return resolved


def applicable_stages(row):
    """Stages of one row that are not marked not-applicable, in order."""
    return [
        stage
        for stage in VERIFICATION_STAGES
        if stage in row["stages"] and row["stages"][stage]["status"] != (
            "not-applicable"
        )
    ]


def detect_stage_order_violations(rows):
    """Rows where a stage is closed behind an applicable earlier stage."""
    violations = []
    for row in rows:
        order = applicable_stages(row)
        for position, stage in enumerate(order):
            if row["stages"][stage]["status"] != "closed":
                continue
            for earlier in order[:position]:
                if row["stages"][earlier]["status"] != "closed":
                    violations.append(
                        {
                            "requirement": row["requirement"],
                            "stage": stage,
                            "blocked_by": earlier,
                            "blocked_by_status": row["stages"][earlier]["status"],
                        }
                    )
    return violations


def closures_without_evidence(rows):
    """Row and stage pairs recorded closed with no evidence reference."""
    return [
        {"requirement": row["requirement"], "stage": stage}
        for row in rows
        for stage in VERIFICATION_STAGES
        if stage in row["stages"]
        and row["stages"][stage]["status"] == "closed"
        and not row["stages"][stage]["evidence"]
    ]


def stage_counts(rows, stage):
    """Applicable, closed and not-applicable counts for one stage."""
    stage = normalize_stage(stage)
    applicable = 0
    closed = 0
    not_applicable = 0
    for row in rows:
        entry = row["stages"].get(stage)
        if entry is None:
            continue
        if entry["status"] == "not-applicable":
            not_applicable += 1
            continue
        applicable += 1
        if entry["status"] == "closed":
            closed += 1
    return {
        "applicable": applicable,
        "closed": closed,
        "not_applicable": not_applicable,
    }


def stage_closure(rows, stage):
    """Fraction of the applicable rows in a stage recorded closed."""
    counts = stage_counts(rows, stage)
    if counts["applicable"] == 0:
        raise ValueError(
            "no applicable row in the %s stage to compute closure over"
            % normalize_stage(stage)
        )
    return counts["closed"] / counts["applicable"]


def overall_closure(rows):
    """Fraction of every applicable stage entry recorded closed."""
    applicable = 0
    closed = 0
    for row in rows:
        for stage in applicable_stages(row):
            applicable += 1
            if row["stages"][stage]["status"] == "closed":
                closed += 1
    if applicable == 0:
        raise ValueError("document carries no applicable stage entry")
    return closed / applicable


def assess_verification_control_document(document):
    """Full clause 5.1.5 assessment of one verification control document.

    Returns the baseline, the per-stage closure, the findings and whether
    the record supports a flight release.
    """
    if not isinstance(document, dict):
        raise ValueError("document must be a mapping of control and rows")
    known = set(_DOCUMENT_REQUIRED_KEYS) | set(_DOCUMENT_OPTIONAL_KEYS)
    unknown = sorted(set(document) - known)
    if unknown:
        raise ValueError("unknown document keys: %s" % ", ".join(unknown))
    missing = [key for key in _DOCUMENT_REQUIRED_KEYS if key not in document]
    if missing:
        raise ValueError("document missing required keys: %s" % ", ".join(missing))

    control = validate_control(document["control"])
    rows = validate_rows(document["rows"])
    if not rows:
        raise ValueError("document must carry at least one requirement row")

    targets = document.get("closure_targets", {}) or {}
    if not isinstance(targets, dict):
        raise ValueError("closure_targets must be a mapping of stage to fraction")
    folded_targets = {}
    for raw_stage, value in targets.items():
        stage = normalize_stage(raw_stage)
        if stage in folded_targets:
            raise ValueError("closure_targets repeats the %s stage" % stage)
        folded_targets[stage] = _fraction("closure_targets[%s]" % stage, value)

    findings = []
    for violation in detect_stage_order_violations(rows):
        findings.append(
            {
                "code": "stage-closed-out-of-order",
                "requirement": violation["requirement"],
                "stage": violation["stage"],
                "detail": "requirement %s records %s closed while %s is still %s"
                % (
                    violation["requirement"],
                    violation["stage"],
                    violation["blocked_by"],
                    violation["blocked_by_status"],
                ),
            }
        )
    for gap in closures_without_evidence(rows):
        findings.append(
            {
                "code": "closure-without-evidence",
                "requirement": gap["requirement"],
                "stage": gap["stage"],
                "detail": "requirement %s records %s closed with no evidence "
                "reference" % (gap["requirement"], gap["stage"]),
            }
        )

    per_stage = {}
    for stage in VERIFICATION_STAGES:
        counts = stage_counts(rows, stage)
        entry = dict(counts)
        entry["closure"] = (
            counts["closed"] / counts["applicable"] if counts["applicable"] else None
        )
        per_stage[stage] = entry

    for stage in sorted(folded_targets):
        target = folded_targets[stage]
        achieved = per_stage[stage]["closure"]
        if achieved is None:
            findings.append(
                {
                    "code": "closure-target-without-applicable-row",
                    "stage": stage,
                    "detail": "a closure target is declared for %s but no row "
                    "applies to that stage" % stage,
                }
            )
        elif not meets_closure_target(achieved, target):
            findings.append(
                {
                    "code": "closure-target-missed",
                    "stage": stage,
                    "achieved": achieved,
                    "target": target,
                    "detail": "%s closure reaches %.1f %% against a %.1f %% target"
                    % (stage, 100.0 * achieved, 100.0 * target),
                }
            )

    release_ready = True
    for stage in FLIGHT_RELEASE_STAGES:
        closure = per_stage[stage]["closure"]
        if closure is None:
            continue
        if not math.isclose(closure, 1.0, rel_tol=REL_TOL, abs_tol=ABS_TOL):
            release_ready = False
    if any(f["code"] == "stage-closed-out-of-order" for f in findings):
        release_ready = False
    if any(f["code"] == "closure-without-evidence" for f in findings):
        release_ready = False

    return {
        "issue": control["issue"],
        "revision": control["revision"],
        "configuration_item": control["configuration_item"],
        "row_count": len(rows),
        "per_stage": per_stage,
        "overall_closure": overall_closure(rows),
        "findings": findings,
        "flight_release_supported": release_ready,
        "acceptable": not findings,
    }
