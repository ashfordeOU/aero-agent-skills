"""On-site quality and technical audit of a hybrid supplier's production line.

Anchor: ECSS-Q-ST-60-05 clause 6.3.3 (the on-site examination of the
production line carried out inside a category two validation, covering the
maturity of the quality system and the technical capability of the line).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* The audit answers two different questions and they are scored on separate
  axes. The quality system can be exemplary on a line that cannot hold a wire
  bond, and a line can be technically excellent while nothing about it is
  under control. A single blended score lets either failure hide behind the
  other, so both axes carry their own threshold and both must be met.
* The audit is an on-site exercise. An area examined only from a desk was not
  audited in the sense the route needs; it counts as uncovered rather than as
  covered more cheaply.
* The audit team is part of the evidence. A team without a quality auditor
  cannot read the system, and a team without a technology specialist cannot
  read the line, so a team short of either leaves the audit incomplete.
* A finding is graded by severity and by whether it was closed before the
  audit was signed. A critical finding left open decides the outcome on its
  own; closure moves a finding out of the open count but never out of the
  record.
* Validity runs from the audit date and is cut for each open major finding,
  because an open major is a reason the line may not be the line that was
  audited by the time the result is used.
"""

from __future__ import annotations

import math

# Which axis each audit area reports against, and what share of it it carries.
AUDIT_AREAS = {
    "quality-management-system-documentation": ("quality-system", 0.8),
    "process-control-and-monitoring": ("quality-system", 1.0),
    "nonconformance-and-corrective-action": ("quality-system", 1.0),
    "traceability-and-lot-identification": ("quality-system", 0.9),
    "calibration-and-measurement-control": ("quality-system", 0.7),
    "training-and-operator-certification": ("quality-system", 0.6),
    "cleanroom-and-contamination-control": ("technical-capability", 0.9),
    "die-and-substrate-attach-capability": ("technical-capability", 1.0),
    "wire-bond-and-interconnect-capability": ("technical-capability", 1.0),
    "sealing-and-encapsulation-capability": ("technical-capability", 0.9),
    "inspection-and-screening-capability": ("technical-capability", 0.8),
    "equipment-maintenance-and-capacity": ("technical-capability", 0.6),
}

AUDIT_AXES = ("quality-system", "technical-capability")

# Areas the audit exists to see; an area not examined on site leaves it short.
MANDATORY_AUDIT_AREAS = (
    "process-control-and-monitoring",
    "nonconformance-and-corrective-action",
    "traceability-and-lot-identification",
    "die-and-substrate-attach-capability",
    "wire-bond-and-interconnect-capability",
)

# How an area was examined, and whether that counts as having been audited.
ON_SITE_EXAMINATION_MODES = ("walked-on-site", "witnessed-on-site")
OFF_SITE_EXAMINATION_MODES = ("desk-review", "supplier-declaration", "not-examined")

# Maturity observed in an area, and the credit it earns on its axis.
MATURITY_CREDIT = {
    "established-and-effective": 1.0,
    "established-not-yet-effective": 0.7,
    "partly-established": 0.4,
    "not-established": 0.0,
}

# Roles an audit team has to carry between its members.
REQUIRED_AUDIT_ROLES = ("quality-auditor", "technology-specialist")
KNOWN_AUDIT_ROLES = REQUIRED_AUDIT_ROLES + ("customer-representative", "observer")

FINDING_SEVERITIES = ("critical", "major", "minor")

# Index each axis has to reach on its own.
AXIS_ACCEPTANCE_INDEX = {
    "quality-system": 0.80,
    "technical-capability": 0.85,
}

# Full validity term of an audit result, and the cut per open major finding.
BASE_AUDIT_VALIDITY_MONTHS = 24.0
VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS = 4.0
MINIMUM_AUDIT_VALIDITY_MONTHS = 6.0

# Indices are ratios of sums of weights; a case meant to sit on a bound can
# land a few units in the last place away from it.
AUDIT_TOLERANCE = 1e-9

VERDICTS = (
    "line-supports-category-two-validation",
    "line-supports-validation-with-open-actions",
    "line-does-not-support-category-two-validation",
    "supplier-audit-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _text(value, label):
    """Return ``value`` as a non-empty string or raise."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def area_axis(name):
    """Axis one audit area reports against; unknown area names are rejected."""
    if name not in AUDIT_AREAS:
        raise ValueError(
            "unknown audit area %r (known: %s)" % (name, ", ".join(sorted(AUDIT_AREAS)))
        )
    return AUDIT_AREAS[name][0]


def area_weight(name):
    """Share of its axis one audit area carries."""
    if name not in AUDIT_AREAS:
        raise ValueError(
            "unknown audit area %r (known: %s)" % (name, ", ".join(sorted(AUDIT_AREAS)))
        )
    return AUDIT_AREAS[name][1]


def examination_is_on_site(mode):
    """True when an area was examined in the way the route needs."""
    _text(mode, "examination mode")
    if mode in ON_SITE_EXAMINATION_MODES:
        return True
    if mode in OFF_SITE_EXAMINATION_MODES:
        return False
    raise ValueError(
        "unknown examination mode %r (known: %s)"
        % (mode, ", ".join(sorted(ON_SITE_EXAMINATION_MODES + OFF_SITE_EXAMINATION_MODES)))
    )


def maturity_credit(level):
    """Credit a maturity level earns on its axis."""
    if level not in MATURITY_CREDIT:
        raise ValueError(
            "unknown maturity level %r (known: %s)"
            % (level, ", ".join(sorted(MATURITY_CREDIT)))
        )
    return MATURITY_CREDIT[level]


def normalize_area(raw):
    """Validate one audit-area record and fill its defaults."""
    if not isinstance(raw, dict):
        raise ValueError("area must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("area")
    area_weight(name)  # validation only
    mode = raw.get("examination", "not-examined")
    examination_is_on_site(mode)  # validation only
    level = raw.get("maturity", "not-established")
    maturity_credit(level)  # validation only
    return {"area": name, "examination": mode, "maturity": level}


def assess_area(raw):
    """Grade one audit area into a credit on its axis, plus its findings."""
    record = normalize_area(raw)
    name = record["area"]
    mode = record["examination"]
    level = record["maturity"]
    on_site = examination_is_on_site(mode)
    weight = area_weight(name)
    # An area nobody stood in front of earns nothing, whatever the paperwork
    # said the maturity was.
    credit = maturity_credit(level) if on_site else 0.0
    findings = []
    if not on_site:
        findings.append("area-not-examined-on-site")
    if on_site and level != "established-and-effective":
        findings.append("area-maturity-%s" % (level,))
    uncovered_mandatory = name in MANDATORY_AUDIT_AREAS and not on_site
    if uncovered_mandatory:
        findings.append("mandatory-area-not-audited-on-site")
    return {
        "area": name,
        "axis": area_axis(name),
        "examination": mode,
        "maturity": level,
        "on_site": on_site,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "uncovered_mandatory": uncovered_mandatory,
        "findings": findings,
    }


def axis_index(records, axis):
    """Weighted credit over total weight for one axis of the audit."""
    if axis not in AUDIT_AXES:
        raise ValueError("unknown audit axis %r (known: %s)" % (axis, ", ".join(AUDIT_AXES)))
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    total_weight = 0.0
    earned = 0.0
    for record in records:
        if record["axis"] != axis:
            continue
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("axis %r carries no weight in this audit" % (axis,))
    return earned / total_weight


def missing_team_roles(team):
    """Required audit-team roles nobody on the team carries."""
    if not isinstance(team, (list, tuple)):
        raise ValueError("team must be a list or tuple, got %r" % (type(team).__name__,))
    carried = set()
    for member in team:
        if not isinstance(member, dict):
            raise ValueError("team member must be a mapping, got %r" % (type(member).__name__,))
        _text(member.get("name"), "team member name")
        role = member.get("role")
        if role not in KNOWN_AUDIT_ROLES:
            raise ValueError(
                "unknown audit role %r (known: %s)" % (role, ", ".join(KNOWN_AUDIT_ROLES))
            )
        carried.add(role)
    return [role for role in REQUIRED_AUDIT_ROLES if role not in carried]


def normalize_finding(raw):
    """Validate one audit finding and fill its closure default."""
    if not isinstance(raw, dict):
        raise ValueError("finding must be a mapping, got %r" % (type(raw).__name__,))
    finding_id = _text(raw.get("finding_id"), "finding_id")
    severity = raw.get("severity")
    if severity not in FINDING_SEVERITIES:
        raise ValueError(
            "unknown finding severity %r (known: %s)"
            % (severity, ", ".join(FINDING_SEVERITIES))
        )
    closed = raw.get("closed_before_signature", False)
    if not isinstance(closed, bool):
        raise ValueError("closed_before_signature must be a boolean, got %r" % (closed,))
    area = raw.get("area")
    if area is not None:
        area_weight(area)  # validation only
    return {
        "finding_id": finding_id,
        "severity": severity,
        "area": area,
        "closed_before_signature": closed,
    }


def open_finding_counts(findings):
    """How many findings of each severity are still open at signature."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a list or tuple, got %r" % (type(findings).__name__,))
    counts = {severity: 0 for severity in FINDING_SEVERITIES}
    seen = set()
    for raw in findings:
        record = normalize_finding(raw)
        if record["finding_id"] in seen:
            raise ValueError("duplicate finding identifier %r" % (record["finding_id"],))
        seen.add(record["finding_id"])
        if not record["closed_before_signature"]:
            counts[record["severity"]] += 1
    return counts


def audit_validity_months(open_major_count):
    """Validity term left once open major findings are struck off."""
    if isinstance(open_major_count, bool) or not isinstance(open_major_count, int):
        raise ValueError("open_major_count must be a whole number, got %r" % (open_major_count,))
    if open_major_count < 0:
        raise ValueError("open_major_count must not be negative, got %r" % (open_major_count,))
    term = BASE_AUDIT_VALIDITY_MONTHS - (
        float(open_major_count) * VALIDITY_PENALTY_PER_OPEN_MAJOR_MONTHS
    )
    if term < MINIMUM_AUDIT_VALIDITY_MONTHS:
        return 0.0
    return term


def assess_supplier_audit(supplier_id, line_id, team, areas, findings=()):
    """Grade a whole on-site supplier audit and name one verdict."""
    _text(supplier_id, "supplier_id")
    _text(line_id, "line_id")
    if not isinstance(areas, (list, tuple)):
        raise ValueError("areas must be a list or tuple, got %r" % (type(areas).__name__,))

    role_gaps = missing_team_roles(team)
    counts = open_finding_counts(findings)

    declared_areas = {}
    for raw in areas:
        record = normalize_area(raw)
        if record["area"] in declared_areas:
            raise ValueError("duplicate audit area %r" % (record["area"],))
        declared_areas[record["area"]] = record
    area_records = []
    for name in sorted(AUDIT_AREAS):
        area_records.append(assess_area(declared_areas.get(name, {"area": name})))

    indices = {axis: axis_index(area_records, axis) for axis in AUDIT_AXES}
    axis_short = [
        axis
        for axis in AUDIT_AXES
        if indices[axis] < AXIS_ACCEPTANCE_INDEX[axis] - AUDIT_TOLERANCE
    ]
    term = audit_validity_months(counts["major"])

    reported = []
    for role in role_gaps:
        reported.append(
            {"item": "audit-team", "finding": "required-audit-role-absent", "detail": role}
        )
    for record in area_records:
        for finding in record["findings"]:
            reported.append(
                {"item": record["area"], "finding": finding, "detail": record["examination"]}
            )
    for axis in axis_short:
        reported.append(
            {
                "item": axis,
                "finding": "axis-index-below-threshold",
                "detail": "%.4f of %.4f" % (indices[axis], AXIS_ACCEPTANCE_INDEX[axis]),
            }
        )
    for severity in FINDING_SEVERITIES:
        if counts[severity] > 0:
            reported.append(
                {
                    "item": "audit-findings",
                    "finding": "open-%s-finding" % (severity,),
                    "detail": "%d open" % (counts[severity],),
                }
            )

    incomplete = bool(role_gaps) or any(r["uncovered_mandatory"] for r in area_records)
    blocked = bool(axis_short) or counts["critical"] > 0 or term <= 0.0
    if incomplete:
        verdict = "supplier-audit-incomplete"
    elif blocked:
        verdict = "line-does-not-support-category-two-validation"
    elif reported:
        verdict = "line-supports-validation-with-open-actions"
    else:
        verdict = "line-supports-category-two-validation"
    return {
        "supplier_id": supplier_id,
        "line_id": line_id,
        "missing_team_roles": role_gaps,
        "area_records": area_records,
        "axis_indices": indices,
        "axes_below_threshold": axis_short,
        "open_finding_counts": counts,
        "validity_months": term,
        "findings": reported,
        "verdict": verdict,
        "line_supports_validation": verdict
        in (
            "line-supports-category-two-validation",
            "line-supports-validation-with-open-actions",
        ),
    }
