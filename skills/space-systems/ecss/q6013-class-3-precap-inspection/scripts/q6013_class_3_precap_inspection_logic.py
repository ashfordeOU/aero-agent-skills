"""Pre-seal inspection assessment for a commercial EEE part lot at class 3.

Anchor: ECSS-Q-ST-60-13C clause 6.3.4 (customer inspection carried out at the
manufacturer before the device is sealed, at the lowest assurance class).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. At the lowest class the pre-seal inspection is not a standing duty. It
   exists only where a procurement document called it up, so a lot with no
   invocation is answered not-invoked -- a different disposition from a
   requirement that applied and was waived, and a different one again from a
   requirement that never applied to the package.
2. The inspection only exists for a package with a cavity. A solid
   encapsulated device is never opened and never sealed.
3. It happens in front of the seal. Once the lid is on, an internal defect is
   invisible and unrecoverable, so an inspection dated on or after the seal is
   void rather than late.
4. This class does not demand that the customer travel. A remote photographic
   review or a manufacturer report may carry the inspection, but each remote
   route has to name what makes it auditable: an identified device set and a
   report issue for the photographic route, and the manufacturer's own
   inspection procedure for the report-only route.
5. The sample is sized against the lot: a percentage of the lot, rounded up,
   never below a floor and never above the lot itself.
6. The findings are graded. A critical internal finding accepts on zero;
   majors and minors carry accept numbers. Every failing grade is reported.
"""

__all__ = [
    "CAVITY_FAMILIES",
    "SOLID_FAMILIES",
    "INVOCATION_SOURCES",
    "EVIDENCE_MODES",
    "REMOTE_MODES",
    "CRITICAL_ACCEPT_NUMBER",
    "MIN_SAMPLE_DEVICES",
    "SAMPLE_PERCENT_OF_LOT",
    "parse_day",
    "invocation_record",
    "package_needs_precap",
    "required_sample_size",
    "sample_record",
    "timing_record",
    "evidence_mode_record",
    "defect_record",
    "assess_precap_inspection",
]

# Package families with an internal cavity that a seal operation closes.
CAVITY_FAMILIES = ("hermetic-cavity", "hermetic-hybrid", "metal-can", "ceramic-flat-pack")

# Package families with no cavity: the die is encapsulated, never sealed.
SOLID_FAMILIES = ("solid-encapsulated", "plastic-overmoulded", "glob-top")

# Documents that can call the inspection up at this class.
INVOCATION_SOURCES = (
    "procurement-specification",
    "component-control-plan",
    "customer-written-request",
)

# How the inspection may be carried out at the lowest class.
EVIDENCE_MODES = ("on-site-witness", "remote-photographic-review", "manufacturer-report-only")
REMOTE_MODES = ("remote-photographic-review", "manufacturer-report-only")

# A critical internal finding accepts on zero; there is no tolerable count.
CRITICAL_ACCEPT_NUMBER = 0

# Sample sizing: this share of the lot, rounded up, never below the floor.
SAMPLE_PERCENT_OF_LOT = 2
MIN_SAMPLE_DEVICES = 3


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


def _named(mapping, key):
    """Return a stripped non-empty string field, or None where it is absent."""
    value = mapping.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def parse_day(label, value):
    """Return the (year, month, day) triple parsed from a YYYY-MM-DD string."""
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
    """Return a whole-day count for a (year, month, day) triple."""
    year, month, dom = day
    cumulative = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334][month - 1]
    leaps = (year - 1) // 4 - (year - 1) // 100 + (year - 1) // 400
    leap_this_year = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    extra = 1 if (leap_this_year and month > 2) else 0
    return 365 * (year - 1) + leaps + cumulative + extra + dom


def invocation_record(invoked_by):
    """Return whether a procurement document called the inspection up.

    None, an empty string or the token 'none' all mean the inspection was
    never invoked at this class, which is not a waiver of anything.
    """
    if invoked_by is None:
        return {"source": None, "invoked": False}
    if isinstance(invoked_by, str) and not invoked_by.strip():
        return {"source": None, "invoked": False}
    key = _token("invoked_by", invoked_by)
    if key in ("none", "not-invoked"):
        return {"source": None, "invoked": False}
    if key not in INVOCATION_SOURCES:
        raise ValueError(
            "unknown invoked_by %r; known sources are %s, or 'none'"
            % (invoked_by, ", ".join(sorted(INVOCATION_SOURCES)))
        )
    return {"source": key, "invoked": True}


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


def required_sample_size(lot_size):
    """Return the devices that have to be opened and looked at for this lot.

    A share of the lot rounded up, lifted to the floor, and never larger than
    the lot. The arithmetic is integer throughout so the boundary is exact.
    """
    lot = _count("lot_size", lot_size)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    share = -(-lot * SAMPLE_PERCENT_OF_LOT // 100)
    return min(lot, max(MIN_SAMPLE_DEVICES, share))


def sample_record(lot_size, sample_size):
    """Return the sample record: what was looked at against what was owed."""
    lot = _count("lot_size", lot_size)
    inspected = _count("sample_size", sample_size)
    if inspected < 1:
        raise ValueError("sample_size must be at least 1, got %d" % inspected)
    if inspected > lot:
        raise ValueError(
            "sample_size %d exceeds lot_size %d; the sample is drawn from the lot"
            % (inspected, lot)
        )
    required = required_sample_size(lot)
    return {
        "lot_size": lot,
        "sample_size": inspected,
        "required_sample_size": required,
        "shortfall": max(0, required - inspected),
        "sufficient": inspected >= required,
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


def evidence_mode_record(inspection):
    """Return the admissibility record for how the inspection was carried out.

    inspection keys: mode, report_reference, and for the remote routes
    report_issue, device_positions_identified, manufacturer_procedure_reference.
    """
    if not isinstance(inspection, dict):
        raise ValueError("inspection must be a mapping")
    if "mode" not in inspection:
        raise ValueError("inspection missing required key 'mode'")
    mode = _token("mode", inspection["mode"])
    if mode not in EVIDENCE_MODES:
        raise ValueError(
            "unknown inspection mode %r; known modes are %s"
            % (inspection["mode"], ", ".join(sorted(EVIDENCE_MODES)))
        )
    reference = _named(inspection, "report_reference")
    issue = _named(inspection, "report_issue")
    procedure = _named(inspection, "manufacturer_procedure_reference")
    identified = inspection.get("device_positions_identified", False)
    if not isinstance(identified, bool):
        raise ValueError(
            "device_positions_identified must be a boolean, got %r" % (identified,)
        )
    missing = []
    if reference is None:
        missing.append("report_reference")
    if mode in REMOTE_MODES and issue is None:
        missing.append("report_issue")
    if mode == "remote-photographic-review" and not identified:
        missing.append("device_positions_identified")
    if mode == "manufacturer-report-only" and procedure is None:
        missing.append("manufacturer_procedure_reference")
    return {
        "mode": mode,
        "remote": mode in REMOTE_MODES,
        "report_reference": reference,
        "report_issue": issue,
        "manufacturer_procedure_reference": procedure,
        "device_positions_identified": identified,
        "missing": missing,
        "admissible": not missing,
    }


def defect_record(sample_size, defects, accept_numbers=None):
    """Return the graded defect record for the devices that were opened.

    defects keys: critical, major, minor. accept_numbers may set 'major' and
    'minor'; the critical accept number is fixed at zero and cannot be raised.
    """
    inspected = _count("sample_size", sample_size)
    if inspected < 1:
        raise ValueError("sample_size must be at least 1, got %d" % inspected)
    if not isinstance(defects, dict):
        raise ValueError("defects must be a mapping with critical, major and minor counts")
    for key in ("critical", "major", "minor"):
        if key not in defects:
            raise ValueError("defects missing required key '%s'" % key)
    counts = {
        key: _count("defects['%s']" % key, defects[key])
        for key in ("critical", "major", "minor")
    }
    total = sum(counts.values())
    if total > inspected:
        raise ValueError(
            "defects total %d exceed the sample of %d devices opened" % (total, inspected)
        )
    accept_numbers = accept_numbers or {}
    if not isinstance(accept_numbers, dict):
        raise ValueError("accept_numbers must be a mapping")
    if "critical" in accept_numbers:
        if _count("accept_numbers['critical']", accept_numbers["critical"]) != 0:
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
            "percent_of_sample": 100.0 * counts[grade] / inspected,
        }
    rejecting = [grade for grade in ("critical", "major", "minor") if not grades[grade]["accepted"]]
    return {
        "sample_size": inspected,
        "grades": grades,
        "total_defects": total,
        "rejecting_grades": rejecting,
        "accepted": not rejecting,
    }


def assess_precap_inspection(spec):
    """Run the full clause 6.3.4 pre-seal assessment for one class 3 lot.

    spec keys: invoked_by, package_family, lot_size, sample_size, defects,
    inspection, inspection_date, seal_date, optional accept_numbers.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "package_family" not in spec:
        raise ValueError("spec missing required key 'package_family'")
    invocation = invocation_record(spec.get("invoked_by"))
    family = _token("package_family", spec["package_family"])
    if not invocation["invoked"]:
        return {
            "package_family": family,
            "invocation": invocation,
            "applicable": False,
            "accepted": True,
            "disposition": "not-invoked-at-this-class",
            "findings": [
                "no procurement document called the pre-seal inspection up at this class, "
                "so it was never owed; that is not a waiver of a requirement that applied"
            ],
            "timing": None,
            "sample": None,
            "evidence": None,
            "defects": None,
        }
    if not package_needs_precap(family):
        return {
            "package_family": family,
            "invocation": invocation,
            "applicable": False,
            "accepted": True,
            "disposition": "not-applicable-no-cavity",
            "findings": [
                "family '%s' has no cavity and is never sealed, so the inspection called up "
                "by '%s' has nothing to look into" % (family, invocation["source"])
            ],
            "timing": None,
            "sample": None,
            "evidence": None,
            "defects": None,
        }
    required = (
        "lot_size",
        "sample_size",
        "defects",
        "inspection",
        "inspection_date",
        "seal_date",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    timing = timing_record(spec["inspection_date"], spec["seal_date"])
    sample = sample_record(spec["lot_size"], spec["sample_size"])
    evidence = evidence_mode_record(spec["inspection"])
    defects = defect_record(spec["sample_size"], spec["defects"], spec.get("accept_numbers"))

    findings = []
    if timing["void"]:
        findings.append(
            "the inspection is dated %d day(s) after the seal; once the lid is on the "
            "interior cannot be seen, so the record is void rather than late"
            % (-timing["days_before_seal"])
        )
    if not sample["sufficient"]:
        findings.append(
            "only %d device(s) were opened against the %d this lot of %d owes; the sample "
            "is short by %d"
            % (
                sample["sample_size"],
                sample["required_sample_size"],
                sample["lot_size"],
                sample["shortfall"],
            )
        )
    if not evidence["admissible"]:
        findings.append(
            "the '%s' route is missing %s, so nothing in the record can be reopened later"
            % (evidence["mode"], ", ".join(evidence["missing"]))
        )
    for grade in defects["rejecting_grades"]:
        record = defects["grades"][grade]
        findings.append(
            "%s findings: %d against an accept number of %d"
            % (grade, record["found"], record["accept_number"])
        )
    accepted = (
        not timing["void"]
        and sample["sufficient"]
        and evidence["admissible"]
        and defects["accepted"]
    )
    return {
        "package_family": family,
        "invocation": invocation,
        "applicable": True,
        "timing": timing,
        "sample": sample,
        "evidence": evidence,
        "defects": defects,
        "accepted": accepted,
        "disposition": "release-for-seal" if accepted else "hold-before-seal",
        "findings": findings,
    }
