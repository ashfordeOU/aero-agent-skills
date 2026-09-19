#!/usr/bin/env python3
"""Device definition phase review (ECSS-E-ST-20-40C clause 5.2.7).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The definition phase closes at a gate, and the gate has one job: decide
whether architecture work may start. Three things decide it.

* the data-item package. Each item the phase owes has a maturity, and
  the maturity required at this gate differs per item -- the
  requirements specification has to be baselined because the
  architecture is about to be built against it, while a plan may still
  be at for-review. A package counted by presence alone passes with
  drafts inside it;
* the review item discrepancies raised against that package. A major
  discrepancy left open is a gate stopper; a major one accepted with an
  action is a conditional pass, and only if the action is due BEFORE
  the work it constrains actually starts. An action due after the phase
  it was meant to protect is closure theatre;
* the gate decision itself, which is the conjunction of the two and
  never an average of them.

Closure ratios are counts over counts, so a threshold met exactly is met
and the comparison absorbs representation error rather than failing on
it.
"""

import datetime
import math

# Data items the definition phase owes at its closing gate, with the
# maturity each one has to have reached.
DATA_ITEM_MATURITIES = ("draft", "for-review", "baselined")

REQUIRED_MATURITY = {
    "device-requirements-specification": "baselined",
    "device-development-plan": "for-review",
    "pre-tailoring-matrix": "baselined",
    "preliminary-verification-plan": "for-review",
    "feasibility-and-risk-assessment": "for-review",
}
REQUIRED_DATA_ITEMS = tuple(sorted(REQUIRED_MATURITY))

_ITEM_ALIASES = {
    "device requirements specification": "device-requirements-specification",
    "requirements specification": "device-requirements-specification",
    "drs": "device-requirements-specification",
    "device development plan": "device-development-plan",
    "development plan": "device-development-plan",
    "pre tailoring matrix": "pre-tailoring-matrix",
    "pre-tailoring matrix": "pre-tailoring-matrix",
    "tailoring matrix": "pre-tailoring-matrix",
    "preliminary verification plan": "preliminary-verification-plan",
    "verification plan": "preliminary-verification-plan",
    "feasibility and risk assessment": "feasibility-and-risk-assessment",
    "feasibility assessment": "feasibility-and-risk-assessment",
}

_MATURITY_ALIASES = {
    "draft": "draft",
    "issue a": "draft",
    "for review": "for-review",
    "for-review": "for-review",
    "released for review": "for-review",
    "baselined": "baselined",
    "baseline": "baselined",
    "approved": "baselined",
}

# Discrepancy severities, worst first.
DISCREPANCY_SEVERITIES = ("major", "minor", "editorial")
DISPOSITIONS = ("closed", "accepted-with-action", "open", "rejected")

_SEVERITY_ALIASES = {
    "major": "major",
    "critical": "major",
    "minor": "minor",
    "editorial": "editorial",
    "typo": "editorial",
}

_DISPOSITION_ALIASES = {
    "closed": "closed",
    "resolved": "closed",
    "accepted-with-action": "accepted-with-action",
    "accepted with action": "accepted-with-action",
    "agreed with action": "accepted-with-action",
    "open": "open",
    "under discussion": "open",
    "rejected": "rejected",
    "not accepted": "rejected",
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_REVIEW_REQUIRED_KEYS = ("data_items", "discrepancies", "gate_date")
_REVIEW_OPTIONAL_KEYS = ("architecture_start", "closure_threshold")
_ITEM_KEYS = ("item", "maturity", "revision")
_DISCREPANCY_KEYS = ("id", "severity", "disposition", "action_due", "against")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(name, value):
    return " ".join(_text(name, value).lower().replace("_", " ").split())


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def parse_date(name, value):
    """Read an ISO calendar date, refusing anything that is not one."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text(name, value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (name, value))


def normalize_data_item(value):
    """Fold a data-item name onto one the definition phase owes."""
    key = _key("data item", value)
    folded = key.replace(" ", "-")
    if folded in REQUIRED_MATURITY:
        return folded
    if key in _ITEM_ALIASES:
        return _ITEM_ALIASES[key]
    raise ValueError(
        "unknown definition-phase data item %r; use one of %s"
        % (value, ", ".join(REQUIRED_DATA_ITEMS))
    )


def normalize_maturity(value):
    """Fold a maturity onto draft, for-review or baselined."""
    key = _key("maturity", value)
    if key in _MATURITY_ALIASES:
        return _MATURITY_ALIASES[key]
    raise ValueError(
        "unknown maturity %r; use one of %s" % (value, ", ".join(DATA_ITEM_MATURITIES))
    )


def maturity_rank(value):
    """Ordinal of a maturity, so two maturities can be compared."""
    return DATA_ITEM_MATURITIES.index(normalize_maturity(value))


def maturity_is_sufficient(actual, required):
    """True when the actual maturity reaches the one the gate requires."""
    return maturity_rank(actual) >= maturity_rank(required)


def normalize_severity(value):
    """Fold a discrepancy severity onto major, minor or editorial."""
    key = _key("severity", value)
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    raise ValueError(
        "unknown discrepancy severity %r; use one of %s"
        % (value, ", ".join(DISCREPANCY_SEVERITIES))
    )


def normalize_disposition(value):
    """Fold a disposition onto one of the four the gate recognises."""
    key = _key("disposition", value)
    if key in _DISPOSITION_ALIASES:
        return _DISPOSITION_ALIASES[key]
    raise ValueError(
        "unknown disposition %r; use one of %s" % (value, ", ".join(DISPOSITIONS))
    )


def validate_data_items(entries):
    """Check the submitted package and return it keyed by data item."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("data_items must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("data_items[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ITEM_KEYS))
        if unknown:
            raise ValueError(
                "data_items[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("item", "maturity"):
            if key not in entry:
                raise ValueError("data_items[%d] missing key: %s" % (index, key))
        name = normalize_data_item(entry["item"])
        if name in resolved:
            raise ValueError("duplicate data item %r in the package" % name)
        resolved[name] = {
            "item": name,
            "maturity": normalize_maturity(entry["maturity"]),
            "revision": _text(
                "data_items[%d].revision" % index, entry.get("revision", ""), allow_empty=True
            ),
        }
    return resolved


def validate_discrepancies(entries):
    """Check the discrepancy list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("discrepancies must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("discrepancies[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_DISCREPANCY_KEYS))
        if unknown:
            raise ValueError(
                "discrepancies[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "severity", "disposition"):
            if key not in entry:
                raise ValueError("discrepancies[%d] missing key: %s" % (index, key))
        rid = _text("discrepancies[%d].id" % index, entry["id"])
        if rid in seen:
            raise ValueError("duplicate discrepancy id %r" % rid)
        seen.add(rid)
        due = entry.get("action_due")
        resolved.append(
            {
                "id": rid,
                "severity": normalize_severity(entry["severity"]),
                "disposition": normalize_disposition(entry["disposition"]),
                "action_due": parse_date("discrepancies[%d].action_due" % index, due)
                if due
                else None,
                "against": _text(
                    "discrepancies[%d].against" % index,
                    entry.get("against", ""),
                    allow_empty=True,
                ),
            }
        )
    return resolved


def closure_ratio(discrepancies):
    """Fraction of discrepancies already closed at the gate."""
    if not discrepancies:
        raise ValueError("closure_ratio needs at least one discrepancy")
    closed = sum(1 for d in discrepancies if d["disposition"] == "closed")
    return closed / len(discrepancies)


def meets_closure_threshold(achieved, threshold):
    """True when closure reaches the threshold, exact landings included."""
    achieved = _fraction("achieved", achieved)
    threshold = _fraction("threshold", threshold)
    return achieved > threshold or math.isclose(
        achieved, threshold, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def missing_data_items(package):
    """Data items the definition phase owes and the package does not carry."""
    return [name for name in REQUIRED_DATA_ITEMS if name not in package]


def conduct_definition_phase_review(review):
    """Full clause 5.2.7 gate decision on one definition phase review.

    Returns the resolved package, the discrepancy tally, the closure ratio
    and the gate verdict, together with every finding that shaped it.
    """
    if not isinstance(review, dict):
        raise ValueError("review must be a mapping of package, discrepancies and dates")
    known = set(_REVIEW_REQUIRED_KEYS) | set(_REVIEW_OPTIONAL_KEYS)
    unknown = sorted(set(review) - known)
    if unknown:
        raise ValueError("unknown review keys: %s" % ", ".join(unknown))
    missing = [key for key in _REVIEW_REQUIRED_KEYS if key not in review]
    if missing:
        raise ValueError("review missing required keys: %s" % ", ".join(missing))

    package = validate_data_items(review["data_items"])
    discrepancies = validate_discrepancies(review["discrepancies"])
    gate_date = parse_date("gate_date", review["gate_date"])
    start = review.get("architecture_start")
    architecture_start = parse_date("architecture_start", start) if start else None
    if architecture_start is not None and architecture_start < gate_date:
        raise ValueError("architecture_start cannot precede the gate date")

    findings = []
    blocking = False
    conditional = False

    for name in missing_data_items(package):
        findings.append(
            {
                "code": "data-item-not-submitted",
                "item": name,
                "detail": "the definition phase owes %s and the package does not "
                "carry it" % name,
            }
        )
        blocking = True

    for name in sorted(package):
        entry = package[name]
        required = REQUIRED_MATURITY[name]
        if not maturity_is_sufficient(entry["maturity"], required):
            findings.append(
                {
                    "code": "data-item-below-required-maturity",
                    "item": name,
                    "maturity": entry["maturity"],
                    "required": required,
                    "detail": "%s is at %s and this gate requires %s"
                    % (name, entry["maturity"], required),
                }
            )
            blocking = True
        if not entry["revision"]:
            findings.append(
                {
                    "code": "data-item-without-revision",
                    "item": name,
                    "detail": "%s is submitted with no revision, so what was reviewed "
                    "cannot be identified later" % name,
                }
            )

    for record in discrepancies:
        if record["disposition"] == "open":
            if record["severity"] == "major":
                findings.append(
                    {
                        "code": "major-discrepancy-open",
                        "discrepancy": record["id"],
                        "detail": "major discrepancy %s is still open, which stops the "
                        "gate" % record["id"],
                    }
                )
                blocking = True
            else:
                conditional = True
                findings.append(
                    {
                        "code": "discrepancy-open",
                        "discrepancy": record["id"],
                        "severity": record["severity"],
                        "detail": "%s discrepancy %s is still open and has to be "
                        "carried as an action" % (record["severity"], record["id"]),
                    }
                )
        elif record["disposition"] == "accepted-with-action":
            conditional = True
            if record["action_due"] is None:
                findings.append(
                    {
                        "code": "action-without-due-date",
                        "discrepancy": record["id"],
                        "detail": "discrepancy %s is accepted with an action carrying "
                        "no due date" % record["id"],
                    }
                )
                blocking = True
            elif (
                architecture_start is not None
                and record["action_due"] > architecture_start
            ):
                findings.append(
                    {
                        "code": "action-due-after-architecture-start",
                        "discrepancy": record["id"],
                        "due": record["action_due"].isoformat(),
                        "detail": "the action on %s falls due after architecture work "
                        "starts, so it cannot protect it" % record["id"],
                    }
                )
                blocking = True
        elif record["disposition"] == "rejected" and record["severity"] == "major":
            findings.append(
                {
                    "code": "major-discrepancy-rejected",
                    "discrepancy": record["id"],
                    "detail": "major discrepancy %s is rejected, which needs a recorded "
                    "rationale rather than a disposition alone" % record["id"],
                }
            )
            conditional = True

    ratio = closure_ratio(discrepancies) if discrepancies else 1.0
    threshold = review.get("closure_threshold")
    if threshold is not None:
        threshold_value = _fraction("closure_threshold", threshold)
        if not meets_closure_threshold(ratio, threshold_value):
            findings.append(
                {
                    "code": "closure-threshold-missed",
                    "achieved": ratio,
                    "threshold": threshold_value,
                    "detail": "discrepancy closure reaches %.1f %% against a %.1f %% "
                    "threshold" % (100.0 * ratio, 100.0 * threshold_value),
                }
            )
            blocking = True

    if blocking:
        verdict = "not-closed"
    elif conditional or findings:
        verdict = "closed-with-actions"
    else:
        verdict = "closed"

    return {
        "package": package,
        "missing_data_items": missing_data_items(package),
        "discrepancy_count": len(discrepancies),
        "closure_ratio": ratio,
        "findings": findings,
        "verdict": verdict,
        "architecture_may_start": verdict != "not-closed",
    }
