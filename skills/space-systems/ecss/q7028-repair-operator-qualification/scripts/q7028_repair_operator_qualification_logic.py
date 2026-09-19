"""Repair operator qualification for printed-circuit-board assemblies.

Anchor: ECSS-Q-ST-70-28C, personnel clause -- a board repair is only as good
as the hand that made it, so an operator is qualified separately for each
class of repair they are allowed to perform, on training hours plus practical
acceptance samples, with a near-vision check, a currency window and a dated
certificate. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Read the training hours and the practical sample set the repair class
   demands, which differ class by class.
2. Grade the samples actually made against the accept count, and report the
   first-pass yield the operator achieved.
3. Apply the near-vision check validity at the assessment date.
4. Test currency: an operator who has not worked the class inside the window
   owes a practical set again, not the whole course.
5. Date the certificate expiry and name the action still owed -- full
   training, a practical sample set, or nothing.
"""

import datetime

__all__ = [
    "REPAIR_CLASS_REQUIREMENTS",
    "VISION_VALIDITY_MONTHS",
    "CURRENCY_MONTHS",
    "CERTIFICATE_VALIDITY_MONTHS",
    "ACTIONS",
    "add_months",
    "parse_date",
    "requirements_for",
    "sample_verdict",
    "vision_findings",
    "currency_findings",
    "certificate_expiry",
    "qualify_operator",
]

# Training hours, samples to be made, and samples that must be accepted, per
# class of repair. A harder class costs more of both.
REPAIR_CLASS_REQUIREMENTS = {
    "conductor": {"training_hours": 16.0, "samples_required": 4, "samples_to_accept": 4},
    "land": {"training_hours": 24.0, "samples_required": 6, "samples_to_accept": 5},
    "plated-hole": {"training_hours": 32.0, "samples_required": 6, "samples_to_accept": 6},
    "base-material": {"training_hours": 20.0, "samples_required": 4, "samples_to_accept": 4},
    "coating": {"training_hours": 8.0, "samples_required": 3, "samples_to_accept": 3},
    "component-replacement": {
        "training_hours": 40.0,
        "samples_required": 8,
        "samples_to_accept": 7,
    },
}

# How long a near-vision check, a period of currency and a certificate last.
VISION_VALIDITY_MONTHS = 12
CURRENCY_MONTHS = 6
CERTIFICATE_VALIDITY_MONTHS = 24

# What the operator still owes, weakest first.
ACTIONS = ("none", "practical-samples", "full-training")


def add_months(day, months):
    """Return the date `months` after `day`, clamping a short month."""
    if not isinstance(day, datetime.date) or isinstance(day, datetime.datetime):
        raise ValueError("day must be a datetime.date, got %r" % (day,))
    if not isinstance(months, int) or isinstance(months, bool):
        raise ValueError("months must be an integer, got %r" % (months,))
    total = day.month - 1 + months
    year = day.year + total // 12
    month = total % 12 + 1
    following = datetime.date(year + month // 12, month % 12 + 1, 1)
    last_day = (following - datetime.timedelta(days=1)).day
    return datetime.date(year, month, min(day.day, last_day))


def parse_date(value, label="date"):
    """Return a date from an ISO string or a date object."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError("%s '%s' is not an ISO date" % (label, value))
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _count(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def requirements_for(repair_class):
    """Return the training and sample requirements of one repair class."""
    token = _token(repair_class, "repair_class")
    if token not in REPAIR_CLASS_REQUIREMENTS:
        raise ValueError(
            "unknown repair_class '%s'; expected one of %s"
            % (token, ", ".join(sorted(REPAIR_CLASS_REQUIREMENTS)))
        )
    requirements = dict(REPAIR_CLASS_REQUIREMENTS[token])
    requirements["repair_class"] = token
    return requirements


def sample_verdict(repair_class, samples_made, samples_accepted):
    """Grade the practical sample set an operator produced."""
    requirements = requirements_for(repair_class)
    made = _count(samples_made, "samples_made")
    accepted = _count(samples_accepted, "samples_accepted")
    if accepted > made:
        raise ValueError(
            "samples_accepted (%d) cannot exceed samples_made (%d)" % (accepted, made)
        )
    findings = []
    if made < requirements["samples_required"]:
        findings.append(
            "only %d practical samples were made, %d are required for the %s class"
            % (made, requirements["samples_required"], requirements["repair_class"])
        )
    if accepted < requirements["samples_to_accept"]:
        findings.append(
            "only %d samples were accepted, %d must be for the %s class"
            % (accepted, requirements["samples_to_accept"], requirements["repair_class"])
        )
    yield_fraction = (accepted / made) if made else 0.0
    return {
        "repair_class": requirements["repair_class"],
        "samples_made": made,
        "samples_accepted": accepted,
        "samples_required": requirements["samples_required"],
        "samples_to_accept": requirements["samples_to_accept"],
        "first_pass_yield": yield_fraction,
        "passed": not findings,
        "findings": findings,
    }


def vision_findings(vision_check_date, assessment_date):
    """Grade the near-vision check validity at the assessment date."""
    checked = parse_date(vision_check_date, "vision_check_date")
    assessed = parse_date(assessment_date, "assessment_date")
    expiry = add_months(checked, VISION_VALIDITY_MONTHS)
    if assessed > expiry:
        return [
            "the near-vision check of %s lapsed on %s, before the assessment on %s"
            % (checked.isoformat(), expiry.isoformat(), assessed.isoformat())
        ]
    return []


def currency_findings(last_worked_date, assessment_date):
    """Grade how long it is since the operator last worked this class."""
    if last_worked_date is None:
        return ["the operator has no recorded work in this repair class"]
    worked = parse_date(last_worked_date, "last_worked_date")
    assessed = parse_date(assessment_date, "assessment_date")
    limit = add_months(worked, CURRENCY_MONTHS)
    if assessed > limit:
        return [
            "the operator last worked this class on %s, outside the %d month currency "
            "window" % (worked.isoformat(), CURRENCY_MONTHS)
        ]
    return []


def certificate_expiry(certified_on):
    """Return the date a certificate issued on `certified_on` lapses."""
    return add_months(parse_date(certified_on, "certified_on"), CERTIFICATE_VALIDITY_MONTHS)


def qualify_operator(record, repair_class, assessment_date):
    """Decide whether an operator is qualified for one repair class today.

    record keys: training_hours, samples_made, samples_accepted,
    vision_check_date, certified_on, optional last_worked_date.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in (
        "training_hours",
        "samples_made",
        "samples_accepted",
        "vision_check_date",
        "certified_on",
    ):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)

    requirements = requirements_for(repair_class)
    assessed = parse_date(assessment_date, "assessment_date")
    findings = []
    action = "none"

    hours = record["training_hours"]
    if not isinstance(hours, (int, float)) or isinstance(hours, bool):
        raise ValueError("training_hours must be a real number, got %r" % (hours,))
    hours = float(hours)
    if hours < 0.0:
        raise ValueError("training_hours must be non-negative, got %g" % hours)
    if hours < requirements["training_hours"]:
        findings.append(
            "%g training hours recorded, %g are required for the %s class"
            % (hours, requirements["training_hours"], requirements["repair_class"])
        )
        action = "full-training"

    samples = sample_verdict(
        repair_class, record["samples_made"], record["samples_accepted"]
    )
    if not samples["passed"]:
        findings.extend(samples["findings"])
        if action != "full-training":
            action = "practical-samples"

    findings.extend(vision_findings(record["vision_check_date"], assessed))

    currency = currency_findings(record.get("last_worked_date"), assessed)
    if currency:
        findings.extend(currency)
        if action == "none":
            action = "practical-samples"

    expiry = certificate_expiry(record["certified_on"])
    if assessed > expiry:
        findings.append(
            "the certificate issued on %s lapsed on %s"
            % (parse_date(record["certified_on"], "certified_on").isoformat(),
               expiry.isoformat())
        )
        if action == "none":
            action = "practical-samples"

    return {
        "repair_class": requirements["repair_class"],
        "assessment_date": assessed.isoformat(),
        "training_hours": hours,
        "training_hours_required": requirements["training_hours"],
        "samples": samples,
        "certificate_expiry": expiry.isoformat(),
        "action_required": action,
        "findings": findings,
        "qualified": not findings,
    }
