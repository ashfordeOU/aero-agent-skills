"""Category two hybrid manufacturer assessment: justification plus conditions.

Anchor: ECSS-Q-ST-60-05 clause 5.2.2 (the less preferred procurement case for a
hybrid, where the maker holds no line approval, the customer has to be given a
justification for going that way, and a set of conditions has to hold before
such a maker becomes acceptable). Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate and audit the written justification against the elements that make
   it admissible: why no approved source serves, what makes this maker
   technically necessary, what the programme consequence is, what the risk
   assessment concluded, and the customer's agreement on it.
2. Refuse a justification that steps past an approved source that was actually
   available, unless that source was excluded and the exclusion is stated. The
   route is the less preferred one; skipping the preferred one needs a reason.
3. Grade the compensating conditions: a manufacturer audit still inside its
   validity window and free of open major findings, an agreed validation
   programme, baselined process documentation, a current quality-system
   certification, and the added lot-level testing that buys back the assurance
   an approved line would have supplied.
4. Report a weighted coverage figure alongside the unmet condition set, so a
   near miss is visible as a near miss rather than as a flat refusal.
5. Return one of three dispositions: acceptable, acceptable-with-open-actions
   (the justification stands and coverage is close but a condition is still
   open), or not-acceptable.
"""

import datetime

__all__ = [
    "JUSTIFICATION_ELEMENTS",
    "CONDITION_WEIGHTS",
    "AUDIT_VALIDITY_DAYS",
    "PROVISIONAL_COVERAGE",
    "COVERAGE_TOLERANCE",
    "parse_date",
    "audit_justification",
    "approved_source_bypass",
    "audit_condition",
    "grade_conditions",
    "assess_category_two_source",
]

# What a justification has to contain before a customer can act on it.
JUSTIFICATION_ELEMENTS = (
    "no-approved-source-statement",
    "technical-necessity",
    "programme-impact",
    "risk-assessment",
    "customer-agreement",
)

# The conditions that buy back the assurance an approved line would have given,
# with the share of that assurance each one carries. Shares sum to one.
CONDITION_WEIGHTS = (
    ("manufacturer-audit", 0.25),
    ("agreed-validation-programme", 0.25),
    ("baselined-process-documentation", 0.20),
    ("current-quality-certification", 0.15),
    ("added-lot-testing", 0.15),
)

# An audit older than this at the assessment day no longer describes the line.
AUDIT_VALIDITY_DAYS = 1095

# Coverage at or above this share, with an admissible justification, leaves the
# source usable while the remaining condition is closed out.
PROVISIONAL_COVERAGE = 0.75

# Coverage is a sum of binary-represented shares, so a run that should land
# exactly on a bound can miss it by a few ULPs. Absorb that here rather than by
# moving the bound.
COVERAGE_TOLERANCE = 1e-9

_CONDITION_NAMES = tuple(name for name, _ in CONDITION_WEIGHTS)


def parse_date(value, label="date"):
    """Return a datetime.date from an ISO day string or a date instance."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    try:
        parts = text.split("-")
        if len(parts) != 3:
            raise ValueError
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def audit_justification(justification):
    """Return the element audit of the written customer justification."""
    if justification is None:
        raise ValueError("justification must be provided; the route is not available without one")
    if not isinstance(justification, dict):
        raise ValueError("justification must be a mapping of element -> declared")
    declared = {}
    for key, value in justification.items():
        if not isinstance(key, str):
            raise ValueError("justification element keys must be strings, got %r" % (key,))
        declared[key.strip().lower()] = bool(value)
    unknown = sorted(k for k in declared if k not in JUSTIFICATION_ELEMENTS)
    if unknown:
        raise ValueError("justification names elements outside the mandated set: %s" % ", ".join(unknown))
    present = [k for k in JUSTIFICATION_ELEMENTS if declared.get(k)]
    missing = [k for k in JUSTIFICATION_ELEMENTS if not declared.get(k)]
    return {
        "present": present,
        "missing": missing,
        "complete": not missing,
        "completeness": len(present) / float(len(JUSTIFICATION_ELEMENTS)),
    }


def approved_source_bypass(approved_sources):
    """Return the approved sources that were passed over without a stated reason."""
    if approved_sources is None:
        return []
    if not isinstance(approved_sources, (list, tuple)):
        raise ValueError("approved_sources must be a sequence of source records")
    bypassed = []
    for index, source in enumerate(approved_sources):
        if not isinstance(source, dict):
            raise ValueError("approved_sources[%d] must be a mapping" % index)
        if "name" not in source:
            raise ValueError("approved_sources[%d] must carry a 'name'" % index)
        name = source["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("approved_sources[%d] name must be a non-empty string" % index)
        if not bool(source.get("available", True)):
            continue
        reason = source.get("exclusion_reason")
        if isinstance(reason, str) and reason.strip():
            continue
        bypassed.append(name.strip())
    return bypassed


def audit_condition(name, evidence, assessment_date):
    """Return whether one compensating condition is satisfied, and why not."""
    if name not in _CONDITION_NAMES:
        raise ValueError("unknown compensating condition %r" % (name,))
    day = parse_date(assessment_date, "assessment_date")
    if evidence is None:
        return {"condition": name, "satisfied": False, "reason": "no evidence supplied"}
    if not isinstance(evidence, dict):
        raise ValueError("evidence for %s must be a mapping" % name)
    if name == "manufacturer-audit":
        performed = evidence.get("performed_on")
        if performed is None:
            return {"condition": name, "satisfied": False, "reason": "no audit date recorded"}
        performed_day = parse_date(performed, "performed_on")
        if performed_day > day:
            return {"condition": name, "satisfied": False, "reason": "audit is dated after the assessment day"}
        age_days = (day - performed_day).days
        open_major = evidence.get("open_major_findings", 0)
        if not isinstance(open_major, int) or isinstance(open_major, bool) or open_major < 0:
            raise ValueError("open_major_findings must be a non-negative integer")
        if age_days > AUDIT_VALIDITY_DAYS:
            return {
                "condition": name,
                "satisfied": False,
                "reason": "audit is %d day(s) old, past the %d day validity window"
                % (age_days, AUDIT_VALIDITY_DAYS),
                "age_days": age_days,
            }
        if open_major:
            return {
                "condition": name,
                "satisfied": False,
                "reason": "%d open major audit finding(s)" % open_major,
                "age_days": age_days,
            }
        return {"condition": name, "satisfied": True, "reason": "audit current and closed out", "age_days": age_days}
    if name == "current-quality-certification":
        expiry = evidence.get("valid_until")
        if expiry is None:
            return {"condition": name, "satisfied": False, "reason": "no certification expiry recorded"}
        expiry_day = parse_date(expiry, "valid_until")
        days_remaining = (expiry_day - day).days
        if days_remaining < 0:
            return {
                "condition": name,
                "satisfied": False,
                "reason": "certification expired %d day(s) ago" % (-days_remaining),
                "days_remaining": days_remaining,
            }
        return {
            "condition": name,
            "satisfied": True,
            "reason": "certification in force",
            "days_remaining": days_remaining,
        }
    agreed = bool(evidence.get("agreed", False))
    return {
        "condition": name,
        "satisfied": agreed,
        "reason": "agreed and recorded" if agreed else "not agreed",
    }


def grade_conditions(conditions, assessment_date):
    """Return the per-condition audit, the unmet set and the weighted coverage."""
    if conditions is None:
        conditions = {}
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping of condition -> evidence")
    unknown = sorted(k for k in conditions if k not in _CONDITION_NAMES)
    if unknown:
        raise ValueError("conditions name entries outside the compensating set: %s" % ", ".join(unknown))
    audits = []
    coverage = 0.0
    unmet = []
    for name, weight in CONDITION_WEIGHTS:
        result = audit_condition(name, conditions.get(name), assessment_date)
        result["weight"] = weight
        audits.append(result)
        if result["satisfied"]:
            coverage += weight
        else:
            unmet.append(name)
    return {
        "audits": audits,
        "unmet": unmet,
        "coverage": coverage,
        "all_met": not unmet,
    }


def assess_category_two_source(proposal, assessment_date):
    """Run the full clause 5.2.2 assessment for one non-approved hybrid maker.

    proposal keys: manufacturer, justification, optional approved_sources and
    conditions. Returns the disposition, the justification audit, the condition
    grading and the findings that drove the outcome.
    """
    if not isinstance(proposal, dict):
        raise ValueError("proposal must be a mapping")
    for key in ("manufacturer", "justification"):
        if key not in proposal:
            raise ValueError("proposal missing required key '%s'" % key)
    maker = proposal["manufacturer"]
    if not isinstance(maker, str) or not maker.strip():
        raise ValueError("manufacturer must be a non-empty name")
    justification = audit_justification(proposal["justification"])
    bypassed = approved_source_bypass(proposal.get("approved_sources"))
    grading = grade_conditions(proposal.get("conditions"), assessment_date)
    findings = []
    if justification["missing"]:
        findings.append(
            "justification is missing %d mandated element(s): %s"
            % (len(justification["missing"]), ", ".join(justification["missing"]))
        )
    if bypassed:
        findings.append(
            "approved source(s) passed over with no stated exclusion reason: %s"
            % ", ".join(bypassed)
        )
    for audit in grading["audits"]:
        if not audit["satisfied"]:
            findings.append("condition '%s' unmet: %s" % (audit["condition"], audit["reason"]))
    admissible = justification["complete"] and not bypassed
    near_enough = grading["coverage"] > PROVISIONAL_COVERAGE - COVERAGE_TOLERANCE
    if admissible and grading["all_met"]:
        disposition = "acceptable"
    elif admissible and near_enough:
        disposition = "acceptable-with-open-actions"
    else:
        disposition = "not-acceptable"
    return {
        "manufacturer": maker.strip(),
        "disposition": disposition,
        "justification_admissible": admissible,
        "justification": justification,
        "bypassed_approved_sources": bypassed,
        "conditions": grading,
        "coverage": grading["coverage"],
        "findings": findings,
    }
