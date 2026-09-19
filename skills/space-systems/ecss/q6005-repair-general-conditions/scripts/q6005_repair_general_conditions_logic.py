"""Who may repair a hybrid, how often, and on what record.

Anchor: ECSS-Q-ST-60-05C clause 10.5.1 (the general conditions attaching to
repair work on hybrid microcircuits -- the operator, the number of times the
work may be attempted, and the records that travel with it). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Test the operator against the action: a named identity, a certification
   that covers this specific action, and a certification that had not expired
   on the day the work was done.
2. Count the attempts already spent. A bond site tolerates the original bond
   and one rebond; an element tolerates one repair. Both counts come from the
   unit's repair history, not from the operator's recollection.
3. Measure how much of the unit has been repaired. Past a stated fraction of
   its elements the unit is a rebuild rather than a repair, and the limit is
   on the unit as a whole rather than on any one element.
4. Check the record set that accompanies the work, matching names
   insensitively to case and separator so a differently punctuated entry
   still counts.
5. Return the permission with every failing condition named, so a refused
   repair says what would have to change.
"""

import math
from datetime import date

__all__ = [
    "FRACTION_TOLERANCE",
    "MAX_ATTEMPTS_PER_BOND_SITE",
    "MAX_REPAIRED_ELEMENT_FRACTION",
    "MAX_REPAIRS_PER_ELEMENT",
    "REQUIRED_REPAIR_RECORDS",
    "assess_repair_conditions",
    "bond_site_attempts",
    "element_repair_count",
    "missing_records",
    "operator_qualification",
    "repaired_element_fraction",
    "validate_repair_history",
]

# A bond site carries the original bond and one rebond; an element is repaired
# once. Beyond that the evidence of the first operation is gone.
MAX_ATTEMPTS_PER_BOND_SITE = 2
MAX_REPAIRS_PER_ELEMENT = 1

# Past this fraction of a unit's elements the work stops being a repair.
MAX_REPAIRED_ELEMENT_FRACTION = 0.10

# The fraction is a quotient of integers that lands exactly on the limit for
# the populations that matter. The comparison absorbs representation error
# here rather than by relaxing the limit.
FRACTION_TOLERANCE = 1e-9

REQUIRED_REPAIR_RECORDS = (
    "repair-authorization",
    "operator-identity",
    "repair-procedure-reference",
    "before-and-after-visual-record",
    "rescreen-record",
    "lot-travel-record-entry",
)


def _clean_token(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _as_date(value, label):
    """Return an ISO date string as a date, raising on anything malformed."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not a valid ISO date: %r" % (label, value))


def operator_qualification(operator, action, repair_date):
    """Return whether the operator may carry out this action on this day.

    Certification is per action and time-limited. An operator certified for
    rebonding is not thereby certified for element replacement, and a
    certification that had lapsed on the day of the work does not cover it.
    """
    if not isinstance(operator, dict):
        raise ValueError("operator must be a mapping")
    identity = operator.get("identifier")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("operator needs a non-empty 'identifier'")
    certified = operator.get("certified_actions", ())
    if isinstance(certified, str) or not isinstance(certified, (list, tuple, set, frozenset)):
        raise ValueError("operator 'certified_actions' must be a sequence of action names")
    covered = {_clean_token(item, "certified action") for item in certified}
    wanted = _clean_token(action, "action")
    when = _as_date(repair_date, "repair_date")
    expiry = operator.get("certification_expiry")
    reasons = []
    if wanted not in covered:
        reasons.append("the operator is not certified for %s" % wanted)
    if expiry is None:
        reasons.append("the operator's certification carries no expiry date")
    else:
        expires = _as_date(expiry, "certification_expiry")
        if expires < when:
            reasons.append(
                "the operator's certification expired on %s, before the repair on %s"
                % (expires.isoformat(), when.isoformat())
            )
    return {
        "identifier": identity.strip(),
        "action": wanted,
        "qualified": not reasons,
        "reasons": reasons,
    }


def validate_repair_history(history):
    """Return the unit's prior repair records, normalised."""
    if isinstance(history, dict) or not isinstance(history, (list, tuple)):
        raise ValueError("repair history must be a sequence of records")
    normalised = []
    for index, record in enumerate(history):
        if not isinstance(record, dict):
            raise ValueError("repair history[%d] must be a mapping" % index)
        if "element" not in record:
            raise ValueError("repair history[%d] needs an 'element'" % index)
        element = _clean_token(record["element"], "repair history[%d]['element']" % index)
        site = record.get("bond_site")
        if site is not None:
            site = _clean_token(site, "repair history[%d]['bond_site']" % index)
        normalised.append({"element": element, "bond_site": site})
    return normalised


def element_repair_count(history, element):
    """Return how many times an element has already been repaired."""
    wanted = _clean_token(element, "element")
    return sum(1 for record in validate_repair_history(history) if record["element"] == wanted)


def bond_site_attempts(history, bond_site):
    """Return the attempts already spent at a bond site, the original included."""
    if bond_site is None:
        return 0
    wanted = _clean_token(bond_site, "bond_site")
    prior = sum(
        1 for record in validate_repair_history(history) if record["bond_site"] == wanted
    )
    return prior + 1


def repaired_element_fraction(history, element, total_elements):
    """Return the fraction of the unit's elements repaired once this one is."""
    if not isinstance(total_elements, int) or isinstance(total_elements, bool):
        raise ValueError("total_elements must be an integer, got %r" % (total_elements,))
    if total_elements <= 0:
        raise ValueError("total_elements must be positive, got %d" % total_elements)
    touched = {record["element"] for record in validate_repair_history(history)}
    touched.add(_clean_token(element, "element"))
    if len(touched) > total_elements:
        raise ValueError(
            "%d elements have been repaired but the unit holds only %d"
            % (len(touched), total_elements)
        )
    return len(touched) / float(total_elements)


def missing_records(provided, required=REQUIRED_REPAIR_RECORDS):
    """Return the required repair records this work did not carry."""
    if isinstance(provided, str) or not isinstance(provided, (list, tuple, set, frozenset)):
        raise ValueError("provided records must be a sequence of record names")
    seen = {_clean_token(item, "record name") for item in provided}
    return [record for record in required if record not in seen]


def assess_repair_conditions(spec):
    """Run the full clause 10.5.1 assessment of one proposed repair.

    spec keys: action, operator, repair_date, element, total_elements,
    records_provided, optional bond_site and optional prior_repairs.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("action", "operator", "repair_date", "element", "total_elements",
                "records_provided"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    history = spec.get("prior_repairs", [])
    action = _clean_token(spec["action"], "action")
    element = _clean_token(spec["element"], "element")
    bond_site = spec.get("bond_site")
    qualification = operator_qualification(spec["operator"], action, spec["repair_date"])
    already = element_repair_count(history, element)
    attempts = bond_site_attempts(history, bond_site)
    fraction = repaired_element_fraction(history, element, spec["total_elements"])
    absent_records = missing_records(spec["records_provided"])

    over_fraction = fraction > MAX_REPAIRED_ELEMENT_FRACTION and not math.isclose(
        fraction, MAX_REPAIRED_ELEMENT_FRACTION, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    )

    blockers = list(qualification["reasons"])
    if already + 1 > MAX_REPAIRS_PER_ELEMENT:
        blockers.append(
            "element %s has been repaired %d time(s); the allowance is %d"
            % (element, already, MAX_REPAIRS_PER_ELEMENT)
        )
    if bond_site is not None and attempts > MAX_ATTEMPTS_PER_BOND_SITE:
        blockers.append(
            "bond site %s would be on attempt %d; the allowance is %d"
            % (_clean_token(bond_site, "bond_site"), attempts, MAX_ATTEMPTS_PER_BOND_SITE)
        )
    if over_fraction:
        blockers.append(
            "%.4f of the unit's elements would be repaired; the limit is %.4f"
            % (fraction, MAX_REPAIRED_ELEMENT_FRACTION)
        )
    if absent_records:
        blockers.append("repair record set incomplete: %s" % ", ".join(absent_records))

    findings = []
    if not over_fraction and math.isclose(
        fraction, MAX_REPAIRED_ELEMENT_FRACTION, rel_tol=0.0, abs_tol=FRACTION_TOLERANCE
    ):
        findings.append(
            "the unit is on its repaired-element limit; no further element may be repaired"
        )
    if bond_site is not None and attempts == MAX_ATTEMPTS_PER_BOND_SITE:
        findings.append(
            "bond site %s is on its last permitted attempt"
            % _clean_token(bond_site, "bond_site")
        )
    return {
        "action": action,
        "operator": qualification["identifier"],
        "operator_qualified": qualification["qualified"],
        "element": element,
        "element_prior_repairs": already,
        "bond_site_attempt": attempts if bond_site is not None else None,
        "repaired_element_fraction": fraction,
        "missing_records": absent_records,
        "permitted": not blockers,
        "blockers": blockers,
        "findings": findings,
    }
