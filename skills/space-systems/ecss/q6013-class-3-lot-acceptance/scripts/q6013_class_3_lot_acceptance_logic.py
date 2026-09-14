"""Lot acceptance route and verdict for a commercial EEE batch at class 3.

Anchor: ECSS-Q-ST-60-13C clause 6.3.5 (lot acceptance testing applied to a
batch of commercial parts at the lowest assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. At the lowest class the default is not a purchaser test campaign. A batch
   bought through a controlled channel from a manufacturer with a live quality
   system is accepted on that manufacturer's own routine conformance data, and
   the first job is therefore to work out which route this batch is on.
2. The route is escalated by conditions, not chosen. A batch from an
   uncontrolled channel, a batch whose manufacturer has no live certificate,
   and a batch sitting in a single-point-failure function all escalate to a
   full purchaser campaign; an open process change notice against the build
   and a batch older than the shelf-age limit escalate to a reduced one. The
   strictest triggered route governs and every trigger is reported, because a
   batch that clears one condition may still be held by another.
3. The evidence is then read against the route the batch is actually on.
   Manufacturer data counts only where it names a document, that document's
   issue, and the build month it covers; a report covering another month
   describes another batch.
4. Where a purchaser campaign is owed, the route names its subgroups and each
   one has to be present and passed. Manufacturer data does not substitute for
   a subgroup an escalation put there -- the escalation exists precisely
   because that data is no longer trusted on its own.
5. A performed subgroup is judged on the accept number and on the percent
   defective together, so a small sample cannot meet its count while sitting
   far above the rate.
"""

__all__ = [
    "ROUTES",
    "ROUTE_RANK",
    "CHANNEL_BASE_ROUTE",
    "ROUTE_SUBGROUPS",
    "SUBGROUPS_REDUCED",
    "SUBGROUPS_FULL",
    "SHELF_AGE_LIMIT_MONTHS",
    "RATE_TOLERANCE",
    "parse_month",
    "month_index",
    "lot_age_months",
    "route_escalations",
    "required_route",
    "manufacturer_data_record",
    "purchaser_test_record",
    "assess_lot_acceptance",
]

# Acceptance routes, from the lightest to the heaviest.
ROUTES = ("manufacturer-standard-data", "reduced-purchaser-lat", "full-purchaser-lat")
ROUTE_RANK = {route: rank for rank, route in enumerate(ROUTES)}

# The route a supply channel puts the batch on before any other condition.
CHANNEL_BASE_ROUTE = {
    "manufacturer-direct": "manufacturer-standard-data",
    "franchised-distributor": "manufacturer-standard-data",
    "independent-broker": "full-purchaser-lat",
    "unknown-origin": "full-purchaser-lat",
}

# Subgroups each purchaser route owes.
SUBGROUPS_REDUCED = ("electrical-end-point", "external-visual")
SUBGROUPS_FULL = (
    "electrical-end-point",
    "external-visual",
    "mechanical-and-environmental",
    "endurance-life",
)
ROUTE_SUBGROUPS = {
    "manufacturer-standard-data": (),
    "reduced-purchaser-lat": SUBGROUPS_REDUCED,
    "full-purchaser-lat": SUBGROUPS_FULL,
}

# A batch older than this at assessment escalates off the data-only route.
SHELF_AGE_LIMIT_MONTHS = 24

# Absorbs binary representation error when a rate lands on its allowance.
RATE_TOLERANCE = 1e-9


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _rate(label, value):
    """Return value as a percentage in 0..100."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a percentage number, got %r" % (label, value))
    number = float(value)
    if number < 0.0 or number > 100.0:
        raise ValueError("%s must lie in 0..100 percent, got %r" % (label, value))
    return number


def _flag(label, value):
    """Return value as a real boolean; an absent declaration is not a false."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
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


def parse_month(label, value):
    """Return the (year, month) pair parsed from a YYYY-MM string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a YYYY-MM string, got %r" % (label, value))
    parts = value.strip().split("-")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("%s must be YYYY-MM, got %r" % (label, value))
    if len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValueError("%s must be YYYY-MM, got %r" % (label, value))
    year, month = int(parts[0]), int(parts[1])
    if month < 1 or month > 12:
        raise ValueError("%s month must lie in 01..12, got %r" % (label, value))
    return (year, month)


def month_index(pair):
    """Return a whole-month count for a (year, month) pair, for differencing."""
    year, month = pair
    return 12 * year + (month - 1)


def lot_age_months(manufacture_month, assessment_month):
    """Return the whole months between the build month and the assessment.

    A batch assessed before it was built is a data error, not an age of zero.
    """
    built = month_index(parse_month("manufacture_month", manufacture_month))
    assessed = month_index(parse_month("assessment_month", assessment_month))
    age = assessed - built
    if age < 0:
        raise ValueError(
            "assessment_month precedes manufacture_month by %d month(s)" % (-age)
        )
    return age


def _certificate_live(certificate, assessment_month):
    """Return whether a quality system certificate is named and still live."""
    if certificate is None:
        return False
    if not isinstance(certificate, dict):
        raise ValueError("quality_system_certificate must be a mapping or None")
    if _named(certificate, "reference") is None:
        return False
    expiry = certificate.get("expiry_month")
    if expiry is None:
        return False
    expires = month_index(parse_month("expiry_month", expiry))
    assessed = month_index(parse_month("assessment_month", assessment_month))
    return expires >= assessed


def route_escalations(lot):
    """Return every route trigger this batch raises, lightest route first.

    lot keys: source_channel, manufacture_month, assessment_month,
    process_change_notice_open, single_point_failure,
    quality_system_certificate.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    for key in (
        "source_channel",
        "manufacture_month",
        "assessment_month",
        "process_change_notice_open",
        "single_point_failure",
    ):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)
    channel = _token("source_channel", lot["source_channel"])
    if channel not in CHANNEL_BASE_ROUTE:
        raise ValueError(
            "unknown source_channel %r; known channels are %s"
            % (lot["source_channel"], ", ".join(sorted(CHANNEL_BASE_ROUTE)))
        )
    triggers = [
        {
            "route": CHANNEL_BASE_ROUTE[channel],
            "reason": "supply channel '%s'" % channel,
        }
    ]
    age = lot_age_months(lot["manufacture_month"], lot["assessment_month"])
    if age > SHELF_AGE_LIMIT_MONTHS:
        triggers.append(
            {
                "route": "reduced-purchaser-lat",
                "reason": "batch is %d month(s) old against a shelf-age limit of %d"
                % (age, SHELF_AGE_LIMIT_MONTHS),
            }
        )
    if _flag("process_change_notice_open", lot["process_change_notice_open"]):
        triggers.append(
            {
                "route": "reduced-purchaser-lat",
                "reason": "an open process change notice stands against this build",
            }
        )
    if not _certificate_live(lot.get("quality_system_certificate"), lot["assessment_month"]):
        triggers.append(
            {
                "route": "full-purchaser-lat",
                "reason": "no live quality system certificate is named for the manufacturer",
            }
        )
    if _flag("single_point_failure", lot["single_point_failure"]):
        triggers.append(
            {
                "route": "full-purchaser-lat",
                "reason": "the part sits in a single-point-failure function",
            }
        )
    triggers.sort(key=lambda item: ROUTE_RANK[item["route"]])
    return {"age_months": age, "triggers": triggers}


def required_route(lot):
    """Return the strictest route this batch's triggers demand."""
    escalation = route_escalations(lot)
    route = max(
        (item["route"] for item in escalation["triggers"]),
        key=lambda name: ROUTE_RANK[name],
    )
    return {
        "route": route,
        "age_months": escalation["age_months"],
        "triggers": escalation["triggers"],
        "governing_reasons": [
            item["reason"] for item in escalation["triggers"] if item["route"] == route
        ],
        "required_subgroups": list(ROUTE_SUBGROUPS[route]),
    }


def manufacturer_data_record(data, manufacture_month):
    """Return whether the manufacturer's conformance data can be credited.

    data keys: reference, issue, covers_month. A report covering another build
    month describes another batch and is not credited to this one.
    """
    built = parse_month("manufacture_month", manufacture_month)
    if data is None:
        return {
            "credited": False,
            "reference": None,
            "issue": None,
            "covers_month": None,
            "missing": ["manufacturer_data"],
        }
    if not isinstance(data, dict):
        raise ValueError("manufacturer_data must be a mapping or None")
    reference = _named(data, "reference")
    issue = _named(data, "issue")
    covers = data.get("covers_month")
    missing = []
    if reference is None:
        missing.append("reference")
    if issue is None:
        missing.append("issue")
    covered = None
    if covers is None:
        missing.append("covers_month")
    else:
        covered = parse_month("covers_month", covers)
        if covered != built:
            missing.append("covers_month matching the build month")
    return {
        "credited": not missing,
        "reference": reference,
        "issue": issue,
        "covers_month": covered,
        "missing": missing,
    }


def purchaser_test_record(tests, required_subgroups):
    """Return the per-subgroup verdicts for the purchaser campaign performed.

    Each test is a mapping of subgroup, sample_size, failures, accept_number
    and allowable_percent_defective.
    """
    wanted = tuple(required_subgroups)
    for name in wanted:
        if name not in SUBGROUPS_FULL:
            raise ValueError("unknown required subgroup %r" % (name,))
    if tests is None:
        tests = []
    if not isinstance(tests, (list, tuple)):
        raise ValueError("purchaser_tests must be a list of mappings")
    subgroups = {}
    for index, test in enumerate(tests):
        if not isinstance(test, dict):
            raise ValueError("purchaser_tests[%d] must be a mapping" % index)
        for key in ("subgroup", "sample_size", "failures", "accept_number"):
            if key not in test:
                raise ValueError("purchaser_tests[%d] missing required key '%s'" % (index, key))
        name = _token("purchaser_tests[%d]['subgroup']" % index, test["subgroup"])
        if name not in SUBGROUPS_FULL:
            raise ValueError(
                "unknown subgroup %r; known subgroups are %s"
                % (test["subgroup"], ", ".join(sorted(SUBGROUPS_FULL)))
            )
        if name in subgroups:
            raise ValueError("subgroup %r is reported twice for the same batch" % (name,))
        sample = _count("purchaser_tests[%d]['sample_size']" % index, test["sample_size"])
        if sample < 1:
            raise ValueError("purchaser_tests[%d]['sample_size'] must be at least 1" % index)
        failures = _count("purchaser_tests[%d]['failures']" % index, test["failures"])
        if failures > sample:
            raise ValueError(
                "purchaser_tests[%d] reports %d failures in a sample of %d"
                % (index, failures, sample)
            )
        accept = _count("purchaser_tests[%d]['accept_number']" % index, test["accept_number"])
        allowance = _rate(
            "purchaser_tests[%d]['allowable_percent_defective']" % index,
            test.get("allowable_percent_defective", 100.0),
        )
        observed = 100.0 * failures / sample
        within_count = failures <= accept
        within_rate = observed <= allowance + RATE_TOLERANCE
        subgroups[name] = {
            "subgroup": name,
            "sample_size": sample,
            "failures": failures,
            "accept_number": accept,
            "observed_percent_defective": observed,
            "allowable_percent_defective": allowance,
            "within_accept_number": within_count,
            "within_allowance": within_rate,
            "accepted": within_count and within_rate,
        }
    uncovered = [name for name in wanted if name not in subgroups]
    rejecting = [name for name in wanted if name in subgroups and not subgroups[name]["accepted"]]
    extra = sorted(name for name in subgroups if name not in wanted)
    return {
        "required_subgroups": list(wanted),
        "subgroups": subgroups,
        "uncovered": uncovered,
        "rejecting": rejecting,
        "beyond_the_route": extra,
        "accepted": not uncovered and not rejecting,
    }


def assess_lot_acceptance(spec):
    """Run the full clause 6.3.5 lot acceptance assessment for one batch.

    spec keys: lot_reference, source_channel, manufacture_month,
    assessment_month, process_change_notice_open, single_point_failure,
    optional quality_system_certificate, manufacturer_data and
    purchaser_tests.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "lot_reference" not in spec:
        raise ValueError("spec missing required key 'lot_reference'")
    lot_reference = _named(spec, "lot_reference")
    if lot_reference is None:
        raise ValueError("lot_reference must be a non-empty string")
    routing = required_route(spec)
    route = routing["route"]
    data = manufacturer_data_record(spec.get("manufacturer_data"), spec["manufacture_month"])
    campaign = purchaser_test_record(
        spec.get("purchaser_tests"), routing["required_subgroups"]
    )

    findings = []
    if route == "manufacturer-standard-data":
        if not data["credited"]:
            findings.append(
                "the data-only route rests on the manufacturer's conformance report, and "
                "this one is missing %s" % ", ".join(data["missing"])
            )
    else:
        for name in campaign["uncovered"]:
            findings.append(
                "subgroup '%s' is owed by the '%s' route and no purchaser result covers it"
                % (name, route)
            )
        for name in campaign["rejecting"]:
            record = campaign["subgroups"][name]
            if not record["within_accept_number"]:
                findings.append(
                    "subgroup '%s': %d failure(s) against an accept number of %d"
                    % (name, record["failures"], record["accept_number"])
                )
            if not record["within_allowance"]:
                findings.append(
                    "subgroup '%s': %.3f percent defective against an allowance of %.3f"
                    % (name, record["observed_percent_defective"],
                       record["allowable_percent_defective"])
                )
        if campaign["uncovered"] and data["credited"]:
            findings.append(
                "the manufacturer's report is credited but does not fill an escalated "
                "subgroup; the escalation is what put the subgroup there"
            )
    accepted = (
        data["credited"] if route == "manufacturer-standard-data" else campaign["accepted"]
    )
    return {
        "lot_reference": lot_reference,
        "route": route,
        "age_months": routing["age_months"],
        "triggers": routing["triggers"],
        "governing_reasons": routing["governing_reasons"],
        "manufacturer_data": data,
        "campaign": campaign,
        "accepted": accepted,
        "disposition": "accept-lot" if accepted else "hold-lot",
        "findings": findings,
    }
