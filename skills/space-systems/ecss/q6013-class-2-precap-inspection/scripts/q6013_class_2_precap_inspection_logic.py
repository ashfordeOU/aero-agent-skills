"""Pre-seal inspection assessment for a commercial EEE part lot at class 2.

Anchor: ECSS-Q-ST-60-13C clause 5.3.4 (customer inspection performed at the
manufacturer before the device is sealed, at the intermediate assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. The inspection only exists for a package with a cavity. A solid-encapsulated
   device is never opened and never sealed, so the answer there is that the
   requirement does not apply -- which is a different disposition from a
   requirement that applied and was waived.
2. The inspection happens BEFORE the seal. Once the lid is on, an internal
   defect is invisible and unrecoverable, so an inspection dated on or after
   the seal is void rather than late, and no amount of documentation recovers
   it.
3. The customer has to be able to attend, which makes the notice a real
   requirement: notice given with less than the agreed lead time in front of
   the seal is a finding even when someone did attend.
4. This class allows the inspection to be delegated to the manufacturer's own
   quality organisation or to a third party, which the class above does not.
   The delegation is only good where it names an approval reference and its
   issue; a delegation resting on a verbal agreement names nothing.
5. The defects are graded. A critical finding -- the bond, the die attach, the
   foreign material that will move in flight -- accepts on zero; majors and
   minors carry accept numbers. The lot is held before seal when any grade
   rejects, and each grade is reported, not just the first.
"""

__all__ = [
    "CAVITY_FAMILIES",
    "SOLID_FAMILIES",
    "DELEGATION_AGENTS",
    "CUSTOMER_AGENTS",
    "CRITICAL_ACCEPT_NUMBER",
    "parse_day",
    "package_needs_precap",
    "notice_record",
    "timing_record",
    "delegation_record",
    "defect_record",
    "assess_precap_inspection",
]

# Package families with an internal cavity that is closed by a seal operation.
CAVITY_FAMILIES = ("hermetic-cavity", "hermetic-hybrid", "metal-can", "ceramic-flat-pack")

# Package families with no cavity: the die is encapsulated, never sealed.
SOLID_FAMILIES = ("solid-encapsulated", "plastic-overmoulded", "glob-top")

# Who may carry out the inspection. The first two are the customer acting for
# itself; the rest are delegates and need an approved procedure behind them.
CUSTOMER_AGENTS = ("customer", "customer-representative")
DELEGATION_AGENTS = ("manufacturer-quality", "third-party-inspection-agency")

# A critical internal defect accepts on zero; there is no tolerable count.
CRITICAL_ACCEPT_NUMBER = 0


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _token(label, value):
    """Return a lowercase hyphenated token for a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return "-".join(value.strip().lower().replace("_", "-").split())


def parse_day(label, value):
    """Return the (year, month, day) triple parsed from a YYYY-MM-DD string.

    The triple is directly comparable, so ordering questions need no calendar
    arithmetic and no dependency outside the standard library.
    """
    if not isinstance(value, str):
        raise ValueError("%s must be a YYYY-MM-DD string, got %r" % (label, value))
    parts = value.strip().split("-")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("%s must be YYYY-MM-DD, got %r" % (label, value))
    if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        raise ValueError("%s must be YYYY-MM-DD, got %r" % (label, value))
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    if month < 1 or month > 12:
        raise ValueError("%s month must lie in 01..12, got %r" % (label, value))
    length = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if day < 1 or day > length:
        raise ValueError("%s day is out of range for its month, got %r" % (label, value))
    return (year, month, day)


def _ordinal(day):
    """Return a day count for a (year, month, day) triple, for differencing."""
    year, month, dom = day
    cumulative = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334][month - 1]
    leaps = (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400
    leap_this_year = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    extra = 1 if (leap_this_year and month > 2) else 0
    return 365 * (year - 1) + leaps + cumulative + extra + dom


def package_needs_precap(package_family):
    """Return whether the family has a cavity that a seal operation closes."""
    key = _token("package_family", package_family)
    if key in CAVITY_FAMILIES:
        return True
    if key in SOLID_FAMILIES:
        return False
    raise ValueError(
        "unknown package_family %r; known families are %s"
        % (package_family, ", ".join(sorted(CAVITY_FAMILIES + SOLID_FAMILIES)))
    )


def notice_record(notice_date, seal_date, agreed_lead_days):
    """Return the notice record: how much warning the customer actually had."""
    lead = _count("agreed_lead_days", agreed_lead_days)
    given = _ordinal(parse_day("notice_date", notice_date))
    seal = _ordinal(parse_day("seal_date", seal_date))
    actual = seal - given
    adequate = actual >= lead
    return {
        "agreed_lead_days": lead,
        "actual_lead_days": actual,
        "adequate": adequate,
    }


def timing_record(inspection_date, seal_date):
    """Return the timing record for the inspection against the seal operation.

    An inspection on the seal day is not admissible: the seal closes the only
    view of the interior, so the inspection has to sit strictly in front of it.
    """
    inspected = _ordinal(parse_day("inspection_date", inspection_date))
    seal = _ordinal(parse_day("seal_date", seal_date))
    days_before = seal - inspected
    return {
        "days_before_seal": days_before,
        "before_seal": days_before > 0,
        "void": days_before <= 0,
    }


def delegation_record(inspection):
    """Return the delegation record for whoever carried out the inspection.

    inspection keys: agent, optional approval_reference and approval_issue.
    """
    if not isinstance(inspection, dict):
        raise ValueError("inspection must be a mapping")
    if "agent" not in inspection:
        raise ValueError("inspection missing required key 'agent'")
    agent = _token("agent", inspection["agent"])
    if agent not in CUSTOMER_AGENTS + DELEGATION_AGENTS:
        raise ValueError(
            "unknown agent %r; known agents are %s"
            % (inspection["agent"], ", ".join(sorted(CUSTOMER_AGENTS + DELEGATION_AGENTS)))
        )
    delegated = agent in DELEGATION_AGENTS
    reference = inspection.get("approval_reference")
    issue = inspection.get("approval_issue")
    has_reference = isinstance(reference, str) and bool(reference.strip())
    has_issue = isinstance(issue, str) and bool(issue.strip())
    accepted = (not delegated) or (has_reference and has_issue)
    return {
        "agent": agent,
        "delegated": delegated,
        "approval_reference": reference.strip() if has_reference else None,
        "approval_issue": issue.strip() if has_issue else None,
        "accepted": accepted,
    }


def defect_record(lot_size, sample_size, defects, accept_numbers=None):
    """Return the graded defect record for the inspected sample.

    defects keys: critical, major, minor. accept_numbers may set 'major' and
    'minor'; the critical accept number is fixed at zero and cannot be raised.
    """
    lot = _count("lot_size", lot_size)
    sample = _count("sample_size", sample_size)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    if sample > lot:
        raise ValueError(
            "sample_size %d exceeds lot_size %d; the sample is drawn from the lot" % (sample, lot)
        )
    if not isinstance(defects, dict):
        raise ValueError("defects must be a mapping with critical, major and minor counts")
    for key in ("critical", "major", "minor"):
        if key not in defects:
            raise ValueError("defects missing required key '%s'" % key)
    counts = {key: _count("defects['%s']" % key, defects[key]) for key in ("critical", "major", "minor")}
    total = sum(counts.values())
    if total > sample:
        raise ValueError(
            "defects total %d exceed the sample of %d devices inspected" % (total, sample)
        )
    accept_numbers = accept_numbers or {}
    if not isinstance(accept_numbers, dict):
        raise ValueError("accept_numbers must be a mapping")
    if "critical" in accept_numbers and _count("accept_numbers['critical']", accept_numbers["critical"]) != 0:
        raise ValueError("the critical accept number is fixed at zero and cannot be raised")
    limits = {
        "critical": CRITICAL_ACCEPT_NUMBER,
        "major": _count("accept_numbers['major']", accept_numbers.get("major", 0)),
        "minor": _count("accept_numbers['minor']", accept_numbers.get("minor", 0)),
    }
    grades = {}
    for grade in ("critical", "major", "minor"):
        grades[grade] = {
            "found": counts[grade],
            "accept_number": limits[grade],
            "accepted": counts[grade] <= limits[grade],
            "percent_of_sample": 100.0 * counts[grade] / sample,
        }
    rejecting = [grade for grade in ("critical", "major", "minor") if not grades[grade]["accepted"]]
    return {
        "lot_size": lot,
        "sample_size": sample,
        "grades": grades,
        "total_defects": total,
        "rejecting_grades": rejecting,
        "accepted": not rejecting,
    }


def assess_precap_inspection(spec):
    """Run the full clause 5.3.4 pre-seal inspection assessment for one lot.

    spec keys: package_family, lot_size, sample_size, defects, inspection
    (agent and optional approval reference and issue), seal_date,
    inspection_date, notice_date, agreed_lead_days, optional accept_numbers.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "package_family" not in spec:
        raise ValueError("spec missing required key 'package_family'")
    needs = package_needs_precap(spec["package_family"])
    family = _token("package_family", spec["package_family"])
    if not needs:
        return {
            "package_family": family,
            "applicable": False,
            "accepted": True,
            "disposition": "not-applicable-no-cavity",
            "findings": [
                "family '%s' has no cavity and is never sealed; the pre-seal inspection does "
                "not apply, which is not the same as a waiver" % family
            ],
            "notice": None,
            "timing": None,
            "delegation": None,
            "defects": None,
        }
    required = (
        "lot_size",
        "sample_size",
        "defects",
        "inspection",
        "seal_date",
        "inspection_date",
        "notice_date",
        "agreed_lead_days",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    timing = timing_record(spec["inspection_date"], spec["seal_date"])
    notice = notice_record(spec["notice_date"], spec["seal_date"], spec["agreed_lead_days"])
    delegation = delegation_record(spec["inspection"])
    defects = defect_record(
        spec["lot_size"], spec["sample_size"], spec["defects"], spec.get("accept_numbers")
    )

    findings = []
    if timing["void"]:
        findings.append(
            "the inspection is dated %d day(s) after the seal; once the lid is on the "
            "interior cannot be seen, so the record is void rather than late"
            % (-timing["days_before_seal"])
        )
    if not notice["adequate"]:
        findings.append(
            "notice gave %d day(s) against an agreed lead of %d; the customer could not have "
            "arranged to attend" % (notice["actual_lead_days"], notice["agreed_lead_days"])
        )
    if not delegation["accepted"]:
        findings.append(
            "the inspection was delegated to '%s' with no approved procedure reference and "
            "issue behind it" % delegation["agent"]
        )
    for grade in defects["rejecting_grades"]:
        record = defects["grades"][grade]
        findings.append(
            "%s defects: %d found against an accept number of %d"
            % (grade, record["found"], record["accept_number"])
        )
    accepted = (
        not timing["void"]
        and notice["adequate"]
        and delegation["accepted"]
        and defects["accepted"]
    )
    return {
        "package_family": family,
        "applicable": True,
        "notice": notice,
        "timing": timing,
        "delegation": delegation,
        "defects": defects,
        "accepted": accepted,
        "disposition": "release-for-seal" if accepted else "hold-before-seal",
        "findings": findings,
    }
