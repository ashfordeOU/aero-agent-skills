"""Qualification of threaded-fastener manufacturers: capability and audits.

Anchor: ECSS-Q-ST-70-46C, the procurement clause requirement that fasteners be
bought only from a manufacturer whose capability has been demonstrated and
whose quality system has been audited. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Reduce a qualification-lot measurement sample to a mean and a sample
   standard deviation, and from those and the drawing limits to a capability
   index for each characteristic measured.
2. Take the governing capability as the weakest characteristic, because a
   manufacturer is only as capable as the feature it controls worst.
3. Reduce an audit to a demerit score with severity weights, and decide
   whether any single finding is severe enough to block on its own.
4. Age the audit against the reference date and the declared validity period.
5. Combine capability, audit outcome and audit currency into one status --
   qualified, conditionally-qualified or not-qualified -- with reasons, and
   return the qualification expiry date that follows from the audit.
"""

import math
from datetime import date

__all__ = [
    "SEVERITY_WEIGHTS",
    "BLOCKING_SEVERITIES",
    "INDEX_TOLERANCE",
    "parse_iso_date",
    "sample_statistics",
    "capability_index",
    "characteristic_capability",
    "governing_capability",
    "audit_demerit_score",
    "audit_currency",
    "qualification_expiry",
    "assess_source_qualification",
]

# Audit findings are grouped by severity and each severity carries a demerit
# weight; the total is what a threshold is set against.
SEVERITY_WEIGHTS = {
    "critical": 50.0,
    "major": 10.0,
    "minor": 3.0,
    "observation": 1.0,
}

# A finding at either of these severities blocks qualification on its own,
# whatever the demerit total says.
BLOCKING_SEVERITIES = ("critical",)

# Capability indices are ratios of floats; a manufacturer sitting exactly on
# the required index must not fail on representation error.
INDEX_TOLERANCE = 1e-9

_STATUSES = ("qualified", "conditionally-qualified", "not-qualified")


def parse_iso_date(value, label="date"):
    """Return a date from an ISO yyyy-mm-dd string or a date object."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))
    parts = value.split("-")
    if len(parts) != 3:
        raise ValueError("%s must look like yyyy-mm-dd, got %r" % (label, value))
    try:
        year, month, day = (int(p) for p in parts)
    except ValueError:
        raise ValueError("%s must look like yyyy-mm-dd, got %r" % (label, value))
    try:
        return date(year, month, day)
    except ValueError:
        raise ValueError("%s is not a real calendar date: %r" % (label, value))


def _as_float(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def sample_statistics(values):
    """Return (mean, sample standard deviation) of a measurement sample."""
    if not isinstance(values, (list, tuple)):
        raise ValueError("values must be a sequence of measurements")
    if len(values) < 2:
        raise ValueError("a capability sample needs at least two measurements")
    numbers = [_as_float(v, "measurement") for v in values]
    n = float(len(numbers))
    mean = sum(numbers) / n
    variance = sum((v - mean) ** 2 for v in numbers) / (n - 1.0)
    return (mean, math.sqrt(variance))


def capability_index(mean, sigma, lower_limit, upper_limit):
    """Return the one-sided-worst capability index of a centred-or-not process."""
    mean = _as_float(mean, "mean")
    sigma = _as_float(sigma, "sigma")
    lower = _as_float(lower_limit, "lower_limit")
    upper = _as_float(upper_limit, "upper_limit")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive, got %g" % sigma)
    if lower >= upper:
        raise ValueError("lower_limit %g must be below upper_limit %g" % (lower, upper))
    return min(upper - mean, mean - lower) / (3.0 * sigma)


def characteristic_capability(characteristic):
    """Reduce one measured characteristic to its capability index record."""
    if not isinstance(characteristic, dict):
        raise ValueError("characteristic must be a mapping")
    for key in ("name", "measurements", "lower_limit", "upper_limit"):
        if key not in characteristic:
            raise ValueError("characteristic missing required key '%s'" % key)
    name = characteristic["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("characteristic name must be a non-empty string")
    mean, sigma = sample_statistics(characteristic["measurements"])
    index = capability_index(
        mean, sigma, characteristic["lower_limit"], characteristic["upper_limit"]
    )
    return {
        "name": name.strip(),
        "sample_size": len(characteristic["measurements"]),
        "mean": mean,
        "sigma": sigma,
        "capability_index": index,
    }


def governing_capability(characteristics):
    """Return the weakest characteristic record; it governs the capability call."""
    if not isinstance(characteristics, (list, tuple)) or not characteristics:
        raise ValueError("at least one measured characteristic is required")
    records = [characteristic_capability(c) for c in characteristics]
    governing = records[0]
    for record in records[1:]:
        if record["capability_index"] < governing["capability_index"]:
            governing = record
    return {"records": records, "governing": governing}


def audit_demerit_score(findings, weights=None):
    """Return the weighted demerit total of an audit and its blocking findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    table = SEVERITY_WEIGHTS if weights is None else weights
    if not isinstance(table, dict) or not table:
        raise ValueError("severity weight table must be a non-empty mapping")
    total = 0.0
    counts = {}
    blocking = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValueError("finding[%d] must be a mapping" % index)
        severity = finding.get("severity")
        if severity not in table:
            raise ValueError(
                "finding[%d] severity %r is not one of %s"
                % (index, severity, sorted(table))
            )
        total += _as_float(table[severity], "weight for %s" % severity)
        counts[severity] = counts.get(severity, 0) + 1
        if severity in BLOCKING_SEVERITIES:
            blocking.append(finding.get("reference", "finding-%d" % index))
    return {"score": total, "counts": counts, "blocking": blocking}


def audit_currency(audit_date, reference_date, validity_days):
    """Return how much of the audit's validity is left on the reference date."""
    audited = parse_iso_date(audit_date, "audit_date")
    reference = parse_iso_date(reference_date, "reference_date")
    if not isinstance(validity_days, int) or isinstance(validity_days, bool):
        raise ValueError("validity_days must be an integer")
    if validity_days <= 0:
        raise ValueError("validity_days must be positive, got %d" % validity_days)
    if audited > reference:
        raise ValueError("audit_date is after the reference date")
    elapsed = (reference - audited).days
    return {
        "elapsed_days": elapsed,
        "remaining_days": validity_days - elapsed,
        "current": elapsed <= validity_days,
    }


def qualification_expiry(audit_date, validity_days):
    """Return the date the qualification granted by this audit runs out."""
    audited = parse_iso_date(audit_date, "audit_date")
    if not isinstance(validity_days, int) or isinstance(validity_days, bool):
        raise ValueError("validity_days must be an integer")
    if validity_days <= 0:
        raise ValueError("validity_days must be positive, got %d" % validity_days)
    return date.fromordinal(audited.toordinal() + validity_days)


def assess_source_qualification(spec):
    """Decide the qualification status of a fastener manufacturer.

    spec keys: manufacturer, characteristics (sequence), required_index,
    audit_date, reference_date, validity_days, audit_findings (sequence),
    optional demerit_limit.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("manufacturer", "characteristics", "required_index", "audit_date",
                "reference_date", "validity_days", "audit_findings"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    manufacturer = spec["manufacturer"]
    if not isinstance(manufacturer, str) or not manufacturer.strip():
        raise ValueError("manufacturer must be a non-empty string")
    required = _as_float(spec["required_index"], "required_index")
    if required <= 0.0:
        raise ValueError("required_index must be positive, got %g" % required)
    demerit_limit = _as_float(spec.get("demerit_limit", 20.0), "demerit_limit")
    if demerit_limit < 0.0:
        raise ValueError("demerit_limit must be non-negative")

    capability = governing_capability(spec["characteristics"])
    audit = audit_demerit_score(spec["audit_findings"])
    currency = audit_currency(
        spec["audit_date"], spec["reference_date"], spec["validity_days"]
    )

    achieved = capability["governing"]["capability_index"]
    capable = achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=INDEX_TOLERANCE
    )
    within_demerits = audit["score"] < demerit_limit or math.isclose(
        audit["score"], demerit_limit, rel_tol=0.0, abs_tol=INDEX_TOLERANCE
    )

    reasons = []
    if not capable:
        reasons.append(
            "governing characteristic '%s' reaches index %.3f against a required %.3f"
            % (capability["governing"]["name"], achieved, required)
        )
    if audit["blocking"]:
        reasons.append(
            "audit carries blocking findings: %s" % ", ".join(str(b) for b in audit["blocking"])
        )
    if not within_demerits:
        reasons.append(
            "audit demerit score %.1f exceeds the limit of %.1f"
            % (audit["score"], demerit_limit)
        )
    if not currency["current"]:
        reasons.append(
            "audit lapsed %d days before the reference date" % abs(currency["remaining_days"])
        )

    if audit["blocking"] or not capable:
        status = "not-qualified"
    elif reasons:
        status = "conditionally-qualified"
    else:
        status = "qualified"
    if status not in _STATUSES:
        raise ValueError("internal status error: %r" % (status,))

    return {
        "manufacturer": manufacturer.strip(),
        "capability": capability,
        "achieved_index": achieved,
        "required_index": required,
        "audit": audit,
        "currency": currency,
        "expiry": qualification_expiry(spec["audit_date"], spec["validity_days"]),
        "status": status,
        "reasons": reasons,
    }
