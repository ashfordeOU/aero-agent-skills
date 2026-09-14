"""Lot acceptance across the date codes of one commercial EEE delivery at class 2.

Anchor: ECSS-Q-ST-60-13C clause 5.3.5 (lot acceptance testing of purchased
date codes at the intermediate assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. A delivery carrying several date codes is several lots. At this class the
   delivery is not refused for that -- it is split, each code takes its own
   verdict, and the delivery is released only when every code passes. Merging
   the codes into one verdict lets a good week carry a bad one.
2. Each code has to show evidence for every required subgroup. The evidence may
   come from three sources at this class: the purchaser's own testing, the
   manufacturer's data for that code, or an acceptance the same code already
   earned on an earlier programme.
3. Manufacturer data is credited only where it names a document and an issue
   and says which subgroups it covers. A report with no issue describes
   whatever that document says today, and a report covering two subgroups does
   not cover the third.
4. A prior acceptance is credited only while it is still inside its validity
   window and only for the same manufacturing site and assembly location. A
   die from the same wafer assembled in a different plant is a different lot.
5. Purchaser testing is judged the usual way: failures against the subgroup's
   accept number and percent defective against the allowance, both of which
   have to hold on the same sample.
6. A code whose evidence leaves any required subgroup uncovered is held, and so
   is one whose evidence rejects. Every uncovered and every rejecting subgroup
   is named, not the first.
"""

import math

__all__ = [
    "ACCEPTANCE_TOLERANCE",
    "MARGINAL_FRACTION",
    "REQUIRED_SUBGROUPS",
    "CREDIT_SOURCES",
    "DEFAULT_VALIDITY_MONTHS",
    "validate_date_code",
    "months_between",
    "manufacturer_data_credit",
    "prior_acceptance_credit",
    "purchaser_test_verdict",
    "date_code_verdict",
    "assess_delivery_lot_acceptance",
]

# Percent-defective comparisons are a ratio of small integers scaled by 100; an
# exact equality with the allowance can land a few ULPs on the wrong side.
# Absorb the representation error here, never by relaxing the allowance.
ACCEPTANCE_TOLERANCE = 1e-9

# A code accepted having used this share of its allowance is reported as
# marginal: it passes, and the next code of the same build has no room.
MARGINAL_FRACTION = 0.8

# Every purchased date code has to show evidence for each of these.
REQUIRED_SUBGROUPS = ("electrical-end-points", "environmental-stress", "endurance-life")

# Where a subgroup's evidence may come from at this class.
CREDIT_SOURCES = ("purchaser-test", "manufacturer-data", "prior-acceptance")

# How long an acceptance earned on an earlier programme stays good for.
DEFAULT_VALIDITY_MONTHS = 24


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _token(label, value):
    """Return a lowercase hyphenated token for a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return "-".join(value.strip().lower().replace("_", "-").split())


def _subgroup_name(label, value):
    """Return a required-subgroup name, refusing one outside the required set."""
    name = _token(label, value)
    if name not in REQUIRED_SUBGROUPS:
        raise ValueError(
            "%s names %r, which is not one of %s"
            % (label, value, ", ".join(REQUIRED_SUBGROUPS))
        )
    return name


def validate_date_code(date_code):
    """Return the (year, week) pair parsed from a four-digit YYWW date code."""
    if not isinstance(date_code, str):
        raise ValueError("date_code must be a four-digit YYWW string, got %r" % (date_code,))
    code = date_code.strip()
    if len(code) != 4 or not code.isdigit():
        raise ValueError("date_code must be four digits YYWW, got %r" % (date_code,))
    week = int(code[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (date_code,))
    return (int(code[:2]), week)


def months_between(earlier, later):
    """Return the whole months from one YYYY-MM month to another.

    A part-month does not count: an acceptance is still inside a 24 month
    window on the day 24 months after it, and outside it the day after.
    """
    def _month(label, value):
        if not isinstance(value, str):
            raise ValueError("%s must be a YYYY-MM string, got %r" % (label, value))
        parts = value.strip().split("-")
        if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
            raise ValueError("%s must be YYYY-MM, got %r" % (label, value))
        if not all(part.isdigit() for part in parts):
            raise ValueError("%s must be YYYY-MM, got %r" % (label, value))
        year, month = int(parts[0]), int(parts[1])
        if month < 1 or month > 12:
            raise ValueError("%s month must lie in 01..12, got %r" % (label, value))
        return year * 12 + (month - 1)

    return _month("later", later) - _month("earlier", earlier)


def manufacturer_data_credit(record):
    """Return the subgroups a manufacturer data package may be credited for.

    record keys: document_reference, issue, covers (a sequence of subgroup
    names). Evidence with no issue is not credited at all.
    """
    if not isinstance(record, dict):
        raise ValueError("manufacturer data record must be a mapping")
    reference = record.get("document_reference")
    issue = record.get("issue")
    has_reference = isinstance(reference, str) and bool(reference.strip())
    has_issue = isinstance(issue, str) and bool(issue.strip())
    covers = record.get("covers", ())
    if not isinstance(covers, (list, tuple)):
        raise ValueError("manufacturer data 'covers' must be a sequence of subgroup names")
    named = []
    for index, item in enumerate(covers):
        name = _subgroup_name("covers[%d]" % index, item)
        if name not in named:
            named.append(name)
    credited = named if (has_reference and has_issue) else []
    reasons = []
    if not has_reference:
        reasons.append("manufacturer data names no document reference")
    elif not has_issue:
        reasons.append(
            "manufacturer data reference '%s' carries no issue; it points at whatever that "
            "document says today" % reference.strip()
        )
    if has_reference and has_issue and not named:
        reasons.append("manufacturer data names no subgroup it covers")
    return {
        "document_reference": reference.strip() if has_reference else None,
        "issue": issue.strip() if has_issue else None,
        "claimed": named,
        "credited": credited,
        "reasons": reasons,
    }


def prior_acceptance_credit(record, assessment_month, validity_months=DEFAULT_VALIDITY_MONTHS):
    """Return the subgroups a prior acceptance of the same code may be credited for.

    record keys: accepted_month (YYYY-MM), manufacturing_site, assembly_location,
    covers, plus the current lot's site and location to compare against.
    """
    if not isinstance(record, dict):
        raise ValueError("prior acceptance record must be a mapping")
    for key in ("accepted_month", "manufacturing_site", "assembly_location", "lot_manufacturing_site", "lot_assembly_location"):
        if key not in record:
            raise ValueError("prior acceptance record missing required key '%s'" % key)
    window = _count("validity_months", validity_months)
    if window < 1:
        raise ValueError("validity_months must be at least 1, got %d" % window)
    age = months_between(record["accepted_month"], assessment_month)
    if age < 0:
        raise ValueError(
            "prior acceptance is dated after the assessment month; it cannot be credited"
        )
    covers = record.get("covers", ())
    if not isinstance(covers, (list, tuple)):
        raise ValueError("prior acceptance 'covers' must be a sequence of subgroup names")
    named = []
    for index, item in enumerate(covers):
        name = _subgroup_name("covers[%d]" % index, item)
        if name not in named:
            named.append(name)
    same_site = _token("manufacturing_site", record["manufacturing_site"]) == _token(
        "lot_manufacturing_site", record["lot_manufacturing_site"]
    )
    same_assembly = _token("assembly_location", record["assembly_location"]) == _token(
        "lot_assembly_location", record["lot_assembly_location"]
    )
    in_window = age <= window
    reasons = []
    if not in_window:
        reasons.append(
            "prior acceptance is %d months old against a %d month validity window"
            % (age, window)
        )
    if not same_site:
        reasons.append("prior acceptance was earned at a different manufacturing site")
    if not same_assembly:
        reasons.append("prior acceptance was earned at a different assembly location")
    usable = in_window and same_site and same_assembly
    return {
        "age_months": age,
        "validity_months": window,
        "in_window": in_window,
        "same_manufacturing_site": same_site,
        "same_assembly_location": same_assembly,
        "claimed": named,
        "credited": named if usable else [],
        "reasons": reasons,
    }


def purchaser_test_verdict(subgroup, allowable_percent):
    """Return the accept/reject record for one purchaser-tested subgroup.

    subgroup keys: name, sample_size, failures, optional accept_number and
    optional allowable_percent overriding the code-level allowance.
    """
    if not isinstance(subgroup, dict):
        raise ValueError("subgroup must be a mapping")
    for key in ("name", "sample_size", "failures"):
        if key not in subgroup:
            raise ValueError("subgroup missing required key '%s'" % key)
    name = _subgroup_name("subgroup name", subgroup["name"])
    sample = _count("sample_size", subgroup["sample_size"])
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    fails = _count("failures", subgroup["failures"])
    if fails > sample:
        raise ValueError("subgroup '%s' reports %d failures in a sample of %d" % (name, fails, sample))
    accept_number = _count("accept_number", subgroup.get("accept_number", 0))
    allowance = _real("allowable_percent", subgroup.get("allowable_percent", allowable_percent))
    if allowance < 0.0 or allowance > 100.0:
        raise ValueError("allowable_percent must lie in 0..100, got %g" % allowance)
    observed = 100.0 * fails / sample
    within_accept_number = fails <= accept_number
    within_allowance = observed < allowance or math.isclose(
        observed, allowance, rel_tol=0.0, abs_tol=ACCEPTANCE_TOLERANCE
    )
    accepted = within_accept_number and within_allowance
    return {
        "name": name,
        "sample_size": sample,
        "failures": fails,
        "accept_number": accept_number,
        "percent_defective": observed,
        "allowable_percent": allowance,
        "within_accept_number": within_accept_number,
        "within_allowance": within_allowance,
        "accepted": accepted,
        "marginal": accepted and allowance > 0.0 and observed >= MARGINAL_FRACTION * allowance,
    }


def date_code_verdict(entry, assessment_month, allowable_percent, validity_months=DEFAULT_VALIDITY_MONTHS):
    """Return the acceptance record for one purchased date code.

    entry keys: date_code, optional subgroups (purchaser testing), optional
    manufacturer_data, optional prior_acceptance.
    """
    if not isinstance(entry, dict):
        raise ValueError("date code entry must be a mapping")
    if "date_code" not in entry:
        raise ValueError("date code entry missing required key 'date_code'")
    validate_date_code(entry["date_code"])
    code = entry["date_code"].strip()

    tested = [
        purchaser_test_verdict(item, allowable_percent)
        for item in entry.get("subgroups", ())
    ]
    names = [record["name"] for record in tested]
    if len(names) != len(set(names)):
        raise ValueError("date code %s tests the same subgroup twice" % code)

    data = manufacturer_data_credit(entry["manufacturer_data"]) if "manufacturer_data" in entry else None
    prior = (
        prior_acceptance_credit(entry["prior_acceptance"], assessment_month, validity_months)
        if "prior_acceptance" in entry
        else None
    )

    coverage = {}
    for record in tested:
        coverage[record["name"]] = "purchaser-test"
    if data:
        for name in data["credited"]:
            coverage.setdefault(name, "manufacturer-data")
    if prior:
        for name in prior["credited"]:
            coverage.setdefault(name, "prior-acceptance")

    uncovered = [name for name in REQUIRED_SUBGROUPS if name not in coverage]
    rejecting = [record["name"] for record in tested if not record["accepted"]]

    findings = []
    for name in uncovered:
        findings.append(
            "date code %s shows no admissible evidence for subgroup '%s'" % (code, name)
        )
    if data:
        for reason in data["reasons"]:
            findings.append("date code %s: %s" % (code, reason))
    if prior:
        for reason in prior["reasons"]:
            findings.append("date code %s: %s" % (code, reason))
    for record in tested:
        if not record["within_accept_number"]:
            findings.append(
                "date code %s subgroup '%s': %d failures exceed the accept number %d"
                % (code, record["name"], record["failures"], record["accept_number"])
            )
        elif not record["within_allowance"]:
            findings.append(
                "date code %s subgroup '%s': %.3f%% defective exceeds the allowable %.3f%%"
                % (code, record["name"], record["percent_defective"], record["allowable_percent"])
            )
        elif record["marginal"]:
            findings.append(
                "date code %s subgroup '%s' accepted at %.3f%% of an allowable %.3f%%; little "
                "margin left" % (code, record["name"], record["percent_defective"], record["allowable_percent"])
            )
    accepted = not uncovered and not rejecting
    return {
        "date_code": code,
        "subgroups": tested,
        "manufacturer_data": data,
        "prior_acceptance": prior,
        "coverage": coverage,
        "uncovered_subgroups": uncovered,
        "rejecting_subgroups": rejecting,
        "accepted": accepted,
        "disposition": "release-date-code" if accepted else "hold-date-code",
        "findings": findings,
    }


def assess_delivery_lot_acceptance(spec):
    """Run the full clause 5.3.5 assessment over every date code in a delivery.

    spec keys: date_codes (a sequence of date code entries), assessment_month,
    allowable_percent, optional validity_months.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("date_codes", "assessment_month", "allowable_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    entries = spec["date_codes"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec['date_codes'] must be a non-empty sequence of date code entries")
    allowance = _real("allowable_percent", spec["allowable_percent"])
    window = _count("validity_months", spec.get("validity_months", DEFAULT_VALIDITY_MONTHS))
    records = [
        date_code_verdict(entry, spec["assessment_month"], allowance, window) for entry in entries
    ]
    codes = [record["date_code"] for record in records]
    if len(codes) != len(set(codes)):
        raise ValueError("the delivery lists the same date code twice; one code takes one verdict")
    held = [record["date_code"] for record in records if not record["accepted"]]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    accepted = not held
    return {
        "assessment_month": spec["assessment_month"],
        "date_codes": records,
        "code_count": len(records),
        "held_date_codes": held,
        "accepted": accepted,
        "disposition": "release-delivery" if accepted else "hold-delivery",
        "findings": findings,
    }
