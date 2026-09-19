"""Customer inspection, record review and release points on a hybrid build.

Anchor: ECSS-Q-ST-60-05C clause 11 (the buyer's rights to witness operations,
to review records and to release product at defined points in the production
flow). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate each point in the production plan: what kind of point it is, when
   it was scheduled, when the customer was told, what the customer said and
   whether the operation went ahead.
2. Measure the notice actually given as the days between the notification and
   the scheduled operation, and compare it with what that point required.
3. Check the record set the point depends on: a review the customer could not
   perform because the records were not there is not a review.
4. Grade each point. Proceeding past a point that needed a release, without
   one, is a breach; short notice, an absent record or an unrecorded
   non-attendance is a finding; everything else is compliant.
5. Roll the points up into a release decision over the whole plan, with the
   compliant fraction reported as a number.

The compliant fraction is a quotient of counts that lands exactly on one for
a clean plan, so it is compared with a tolerance rather than strictly.
"""

import datetime

__all__ = [
    "RATIO_TOLERANCE",
    "POINT_KINDS",
    "RESPONSES",
    "parse_date",
    "normalise_record_name",
    "validate_point",
    "notice_days",
    "notice_is_adequate",
    "record_gaps",
    "grade_point",
    "compliant_fraction",
    "assess_inspection_plan",
]

# A plan in which every point is compliant lands exactly on one.
RATIO_TOLERANCE = 1e-9

# What each kind of point obliges, and the notice it carries by default.
POINT_KINDS = {
    "hold": {
        "default_notice_days": 10,
        "release_required": True,
        "records_reviewed": False,
        "attendance_expected": True,
    },
    "witness": {
        "default_notice_days": 10,
        "release_required": False,
        "records_reviewed": False,
        "attendance_expected": True,
    },
    "record-review": {
        "default_notice_days": 5,
        "release_required": False,
        "records_reviewed": True,
        "attendance_expected": False,
    },
    "notification": {
        "default_notice_days": 2,
        "release_required": False,
        "records_reviewed": False,
        "attendance_expected": False,
    },
}

# Responses the customer can give at a point.
RESPONSES = (
    "released",
    "waived",
    "attended",
    "not-attended",
    "review-complete",
    "no-response",
)


def parse_date(value, label):
    """Return an ISO date string or date as a date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError("%s is not an ISO date: %r" % (label, value)) from exc
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def normalise_record_name(value, label="record name"):
    """Return a record name folded to one spelling for comparison."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _names(values, label):
    """Return a normalised set of record names from a sequence."""
    if isinstance(values, str) or not isinstance(values, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a sequence of record names" % label)
    return {normalise_record_name(v, label) for v in values}


def validate_point(point, index=0):
    """Return the normalised record of one customer inspection point."""
    label = "points[%d]" % index
    if not isinstance(point, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("point_id", "kind", "scheduled_on", "notified_on"):
        if key not in point:
            raise ValueError("%s missing required key '%s'" % (label, key))
    point_id = point["point_id"]
    if not isinstance(point_id, str) or not point_id.strip():
        raise ValueError("%s['point_id'] must be a non-empty string" % label)
    kind = point["kind"]
    if not isinstance(kind, str) or kind.strip().lower() not in POINT_KINDS:
        raise ValueError(
            "%s['kind'] must be one of %s, got %r" % (label, ", ".join(sorted(POINT_KINDS)), kind)
        )
    kind = kind.strip().lower()
    response = point.get("response", "no-response")
    if not isinstance(response, str) or response.strip().lower() not in RESPONSES:
        raise ValueError(
            "%s['response'] must be one of %s, got %r" % (label, ", ".join(RESPONSES), response)
        )
    notice_required = point.get("notice_required_days", POINT_KINDS[kind]["default_notice_days"])
    if not isinstance(notice_required, int) or isinstance(notice_required, bool):
        raise ValueError("%s['notice_required_days'] must be an integer" % label)
    if notice_required < 0:
        raise ValueError("%s['notice_required_days'] must not be negative" % label)
    proceeded = point.get("proceeded", False)
    if not isinstance(proceeded, bool):
        raise ValueError("%s['proceeded'] must be a boolean" % label)
    return {
        "point_id": point_id.strip(),
        "kind": kind,
        "scheduled_on": parse_date(point["scheduled_on"], "%s['scheduled_on']" % label),
        "notified_on": parse_date(point["notified_on"], "%s['notified_on']" % label),
        "response": response.strip().lower(),
        "notice_required_days": notice_required,
        "proceeded": proceeded,
        "records_required": _names(
            point.get("records_required", []), "%s['records_required']" % label
        ),
        "records_provided": _names(
            point.get("records_provided", []), "%s['records_provided']" % label
        ),
        "non_attendance_recorded": bool(point.get("non_attendance_recorded", False)),
    }


def notice_days(point, index=0):
    """Return the days of notice given; negative means told after the event."""
    record = validate_point(point, index)
    return (record["scheduled_on"] - record["notified_on"]).days


def notice_is_adequate(point, index=0):
    """Return whether the notice given met the notice the point required."""
    record = validate_point(point, index)
    return notice_days(point, index) >= record["notice_required_days"]


def record_gaps(point, index=0):
    """Return the records this point needed that were not made available."""
    record = validate_point(point, index)
    return sorted(record["records_required"] - record["records_provided"])


def grade_point(point, index=0):
    """Grade one point as compliant, a finding or a breach."""
    record = validate_point(point, index)
    kind = POINT_KINDS[record["kind"]]
    given = notice_days(point, index)
    adequate = given >= record["notice_required_days"]
    gaps = record_gaps(point, index)
    response = record["response"]

    breaches = []
    findings = []

    if kind["release_required"] and record["proceeded"] and response not in ("released", "waived"):
        breaches.append(
            "point %s was passed without a customer release or a recorded waiver"
            % record["point_id"]
        )
    if kind["records_reviewed"] and record["proceeded"] and response not in (
        "review-complete",
        "waived",
    ):
        breaches.append(
            "records at point %s were not reviewed before the build continued"
            % record["point_id"]
        )
    if not adequate:
        findings.append(
            "point %s gave %d day(s) of notice against %d required"
            % (record["point_id"], given, record["notice_required_days"])
        )
    if gaps:
        findings.append(
            "point %s did not make %d record(s) available: %s"
            % (record["point_id"], len(gaps), ", ".join(gaps))
        )
    if (
        kind["attendance_expected"]
        and response in ("not-attended", "no-response")
        and not record["non_attendance_recorded"]
    ):
        findings.append(
            "point %s proceeded without the customer and without a non-attendance record"
            % record["point_id"]
        )
    if kind["release_required"] and not record["proceeded"] and response in ("released", "waived"):
        findings.append(
            "point %s was released but the operation has not been performed" % record["point_id"]
        )

    if breaches:
        status = "breach"
    elif findings:
        status = "finding"
    else:
        status = "compliant"
    return {
        "point_id": record["point_id"],
        "kind": record["kind"],
        "notice_days": given,
        "notice_required_days": record["notice_required_days"],
        "notice_adequate": adequate,
        "response": response,
        "proceeded": record["proceeded"],
        "record_gaps": gaps,
        "breaches": breaches,
        "findings": findings,
        "status": status,
    }


def compliant_fraction(graded):
    """Return the fraction of graded points that came out compliant."""
    if isinstance(graded, dict) or not isinstance(graded, (list, tuple)):
        raise ValueError("graded must be a sequence of graded points")
    if not graded:
        raise ValueError("no graded points to summarise")
    compliant = sum(1 for g in graded if g["status"] == "compliant")
    return compliant / float(len(graded))


def assess_inspection_plan(spec):
    """Run the full clause 11 customer inspection and review assessment.

    spec keys: points -- a sequence of point records. Optional
    plan_agreed (default False) records whether the customer agreed the set
    of points before the build started; without that agreement the plan
    itself is a finding, however well each point was run.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "points" not in spec:
        raise ValueError("spec missing required key 'points'")
    points = spec["points"]
    if isinstance(points, dict) or not isinstance(points, (list, tuple)):
        raise ValueError("spec['points'] must be a sequence of point records")
    if not points:
        raise ValueError("an inspection plan with no points cannot be assessed")
    plan_agreed = spec.get("plan_agreed", False)
    if not isinstance(plan_agreed, bool):
        raise ValueError("plan_agreed must be a boolean")

    graded = [grade_point(point, index) for index, point in enumerate(points)]
    seen = set()
    for record in graded:
        if record["point_id"] in seen:
            raise ValueError("duplicate point id %r in the plan" % record["point_id"])
        seen.add(record["point_id"])

    breached = [g for g in graded if g["status"] == "breach"]
    flagged = [g for g in graded if g["status"] == "finding"]
    fraction = compliant_fraction(graded)

    plan_findings = []
    if not plan_agreed:
        plan_findings.append("the set of customer points was not agreed before the build")

    if breached:
        disposition = "release-withheld"
    elif flagged or plan_findings:
        disposition = "cleared-with-findings"
    else:
        disposition = "cleared"
    return {
        "point_count": len(graded),
        "points": graded,
        "hold_points": [g["point_id"] for g in graded if g["kind"] == "hold"],
        "breached_points": [g["point_id"] for g in breached],
        "flagged_points": [g["point_id"] for g in flagged],
        "plan_findings": plan_findings,
        "compliant_fraction": fraction,
        "fully_compliant": abs(fraction - 1.0) <= RATIO_TOLERANCE and not plan_findings,
        "disposition": disposition,
        "released": disposition != "release-withheld",
    }
