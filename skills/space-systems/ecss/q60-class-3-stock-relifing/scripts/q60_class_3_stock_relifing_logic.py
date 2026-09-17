"""Renewing the storage validity of time-expired Class 3 EEE stock.

Anchor: ECSS-Q-ST-60C clause 6.3.10 (restoring the validity of stored Class 3
parts whose original storage period has run out). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Read the date code so the manufacture point, and therefore the total life
   the part was ever entitled to, is fixed from the part rather than from the
   purchase order.
2. Measure elapsed storage against the period the lot was issued when it was
   accepted, treating a lot sitting exactly on its period as still inside it.
3. Compute the renewed period a relife earns, which decays with every cycle
   already used and stops entirely once the cycle allowance is spent.
4. Trim that renewed period to the total-life headroom still left from the
   manufacture point, so no sequence of relifes can outrun the part's life.
5. Assemble the evidence set the package seal and the moisture level owe, and
   separate evidence that is missing from evidence that was taken and failed.
6. Decide a disposition per lot, then allocate a limited relife test capacity
   across the stock by the build demand each lot would release per test slot.
"""

import datetime

__all__ = [
    "RELIFE_DISPOSITIONS",
    "REQUIRED_LOT_FIELDS",
    "PACKAGE_SEALS",
    "RETINNABLE_FAILURES",
    "parse_date_code",
    "manufacture_date",
    "total_life_headroom_days",
    "elapsed_storage_days",
    "period_expired",
    "relife_grant_days",
    "effective_grant_days",
    "owed_relife_tests",
    "outstanding_evidence",
    "lot_disposition",
    "campaign_priority",
    "assess_relifing_stock",
]

# Dispositions, from a lot that never needed relifing to one with no life left.
RELIFE_DISPOSITIONS = (
    "in-period",
    "relife-granted",
    "relife-conditional",
    "rescreening-referral",
    "scrap",
)

# A stored lot record with any of these missing cannot be reasoned about.
REQUIRED_LOT_FIELDS = (
    "lot_id",
    "part_number",
    "date_code",
    "quantity",
    "storage_period_days",
    "relife_cycles_used",
    "package_seal",
    "stored_since",
)

# How the lot was actually packaged, which sets the evidence it owes.
PACKAGE_SEALS = (
    "dry-pack-sealed",
    "dry-pack-opened",
    "hermetic-tray",
    "uncontrolled-bag",
)

# A failure that a re-tinning and re-screening route can still recover from.
RETINNABLE_FAILURES = ("solderability-sample",)

# Calendar days credited per year of permissible life. A fixed day count keeps
# the arithmetic integer and identical on every platform.
DAYS_PER_LIFE_YEAR = 365


def _require_positive_int(value, label):
    """Return value when it is a positive integer, else raise."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive integer, got %r" % (label, value))
    return value


def _require_non_negative_int(value, label):
    """Return value when it is a non-negative integer, else raise."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (label, value))
    return value


def parse_iso_date(value, label="date"):
    """Return an ISO date string or date object as a date."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def parse_date_code(date_code):
    """Return the (year, week) a four-digit YYWW date code names.

    The two-digit year is read into the current century, which is what a stock
    of parts bought for a current programme actually carries.
    """
    if not isinstance(date_code, str):
        raise ValueError("date_code must be a string, got %r" % (date_code,))
    code = date_code.strip()
    if len(code) != 4 or not code.isdigit():
        raise ValueError("date_code must be four digits (YYWW), got %r" % (date_code,))
    year = 2000 + int(code[:2])
    week = int(code[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week %d is outside 1..53" % week)
    return (year, week)


def manufacture_date(date_code):
    """Return the Monday of the week a date code names."""
    year, week = parse_date_code(date_code)
    try:
        return datetime.date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError(
            "date_code %r names week %d, which %d does not have" % (date_code, week, year)
        )


def total_life_headroom_days(date_code, as_of_date, total_life_years):
    """Return the days of permissible life the part still has from manufacture.

    The headroom never goes negative: a part already past its total life has no
    headroom rather than a debt, and the disposition is decided on that.
    """
    _require_positive_int(total_life_years, "total_life_years")
    made = manufacture_date(date_code)
    as_of = parse_iso_date(as_of_date, "as_of_date")
    if as_of < made:
        raise ValueError("as_of_date %s precedes the manufacture week %s" % (as_of, made))
    used = (as_of - made).days
    return max(0, total_life_years * DAYS_PER_LIFE_YEAR - used)


def elapsed_storage_days(stored_since, as_of_date):
    """Return the calendar days the lot has been in store."""
    start = parse_iso_date(stored_since, "stored_since")
    end = parse_iso_date(as_of_date, "as_of_date")
    if end < start:
        raise ValueError("as_of_date %s precedes stored_since %s" % (end, start))
    return (end - start).days


def period_expired(stored_since, as_of_date, storage_period_days):
    """Return True when the issued storage period has run out.

    A lot sitting exactly on its period is still inside it; the period names the
    last day the acceptance evidence is good for, not the first day it is not.
    """
    _require_positive_int(storage_period_days, "storage_period_days")
    return elapsed_storage_days(stored_since, as_of_date) > storage_period_days


def relife_grant_days(storage_period_days, relife_cycles_used, max_relife_cycles=3,
                      share_numerator=1, share_denominator=2):
    """Return the renewed period the next relife cycle would earn, in days.

    Each successive cycle earns a smaller share of the originally issued period,
    so a lot cannot be kept alive indefinitely by repeating the operation. The
    arithmetic is integer throughout, so the grant is the same on every
    platform. A lot that has spent its cycle allowance earns nothing.
    """
    _require_positive_int(storage_period_days, "storage_period_days")
    _require_non_negative_int(relife_cycles_used, "relife_cycles_used")
    _require_positive_int(max_relife_cycles, "max_relife_cycles")
    _require_positive_int(share_numerator, "share_numerator")
    _require_positive_int(share_denominator, "share_denominator")
    if share_numerator >= share_denominator:
        raise ValueError("share_numerator must be smaller than share_denominator")
    if relife_cycles_used >= max_relife_cycles:
        return 0
    power = relife_cycles_used + 1
    return (storage_period_days * share_numerator ** power) // (
        share_denominator ** power
    )


def effective_grant_days(grant_days, headroom_days):
    """Return the grant trimmed to the total life the part has left."""
    _require_non_negative_int(grant_days, "grant_days")
    _require_non_negative_int(headroom_days, "headroom_days")
    return min(grant_days, headroom_days)


def owed_relife_tests(package_seal, moisture_sensitivity_level, hermetic=False):
    """Return the evidence set a lot owes before its validity can be renewed."""
    if package_seal not in PACKAGE_SEALS:
        raise ValueError(
            "package_seal must be one of %s, got %r" % (PACKAGE_SEALS, package_seal)
        )
    if (
        not isinstance(moisture_sensitivity_level, int)
        or isinstance(moisture_sensitivity_level, bool)
        or not 1 <= moisture_sensitivity_level <= 6
    ):
        raise ValueError(
            "moisture_sensitivity_level must be an integer in 1..6, got %r"
            % (moisture_sensitivity_level,)
        )
    if not isinstance(hermetic, bool):
        raise ValueError("hermetic must be a bool, got %r" % (hermetic,))
    owed = {"external-visual", "solderability-sample"}
    if package_seal in ("dry-pack-opened", "uncontrolled-bag"):
        if moisture_sensitivity_level >= 3:
            owed.add("moisture-bake")
    if package_seal == "uncontrolled-bag":
        owed.add("electrical-ambient-reverification")
    if hermetic:
        owed.add("fine-and-gross-leak")
    return tuple(sorted(owed))


def outstanding_evidence(owed_tests, recorded_results):
    """Split the owed evidence into what is missing and what was taken and failed.

    An owed test with no record is missing, not a pass. Reading an absent record
    as a pass is the single failure this split exists to prevent.
    """
    if not isinstance(owed_tests, (list, tuple)):
        raise ValueError("owed_tests must be a sequence of test names")
    if not isinstance(recorded_results, dict):
        raise ValueError("recorded_results must be a mapping of test name to result")
    for name, outcome in recorded_results.items():
        if outcome not in ("pass", "fail"):
            raise ValueError(
                "recorded result for %r must be 'pass' or 'fail', got %r" % (name, outcome)
            )
    missing = tuple(sorted(t for t in owed_tests if t not in recorded_results))
    failed = tuple(
        sorted(t for t in owed_tests if recorded_results.get(t) == "fail")
    )
    return {"missing": missing, "failed": failed}


def lot_disposition(expired, grant_days, headroom_days, missing_tests, failed_tests):
    """Return the disposition one stored lot has earned."""
    if not isinstance(expired, bool):
        raise ValueError("expired must be a bool, got %r" % (expired,))
    _require_non_negative_int(grant_days, "grant_days")
    _require_non_negative_int(headroom_days, "headroom_days")
    for label, seq in (("missing_tests", missing_tests), ("failed_tests", failed_tests)):
        if not isinstance(seq, (list, tuple)):
            raise ValueError("%s must be a sequence of test names" % label)
    if not expired:
        return "in-period"
    if failed_tests:
        if all(name in RETINNABLE_FAILURES for name in failed_tests):
            return "rescreening-referral"
        return "scrap"
    if grant_days <= 0 or headroom_days <= 0:
        return "scrap"
    if missing_tests:
        return "relife-conditional"
    return "relife-granted"


def campaign_priority(build_demand, owed_test_count):
    """Return the build demand one test slot releases for this lot.

    Ordering the campaign by this rather than by lot size is what keeps a large
    lot nobody has asked for from consuming the whole test capacity.
    """
    _require_non_negative_int(build_demand, "build_demand")
    _require_positive_int(owed_test_count, "owed_test_count")
    return build_demand / owed_test_count


def assess_relifing_stock(lots, as_of_date, test_capacity=None, total_life_years=5,
                          max_relife_cycles=3):
    """Run the full clause 6.3.10 relifing assessment over a stock of lots."""
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("lots must be a non-empty sequence of stored lot records")
    _require_positive_int(total_life_years, "total_life_years")
    _require_positive_int(max_relife_cycles, "max_relife_cycles")
    if test_capacity is not None:
        _require_non_negative_int(test_capacity, "test_capacity")
    as_of = parse_iso_date(as_of_date, "as_of_date")

    assessed = []
    seen = set()
    findings = []
    for index, lot in enumerate(lots):
        if not isinstance(lot, dict):
            raise ValueError("lots[%d] must be a mapping" % index)
        for field in REQUIRED_LOT_FIELDS:
            if field not in lot or lot[field] in (None, ""):
                raise ValueError("lots[%d] missing required field '%s'" % (index, field))
        lot_id = str(lot["lot_id"]).strip()
        if lot_id in seen:
            raise ValueError("lot %s appears more than once in the stock" % lot_id)
        seen.add(lot_id)

        quantity = _require_positive_int(lot["quantity"], "lots[%d]['quantity']" % index)
        period = _require_positive_int(
            lot["storage_period_days"], "lots[%d]['storage_period_days']" % index
        )
        cycles = _require_non_negative_int(
            lot["relife_cycles_used"], "lots[%d]['relife_cycles_used']" % index
        )
        demand = _require_non_negative_int(
            lot.get("build_demand", 0), "lots[%d]['build_demand']" % index
        )
        if demand > quantity:
            raise ValueError(
                "lots[%d] build_demand %d exceeds the %d parts the lot holds"
                % (index, demand, quantity)
            )
        msl = lot.get("moisture_sensitivity_level", 1)
        owed = owed_relife_tests(
            str(lot["package_seal"]).strip(), msl, bool(lot.get("hermetic", False))
        )
        evidence = outstanding_evidence(owed, lot.get("recorded_results", {}) or {})
        elapsed = elapsed_storage_days(lot["stored_since"], as_of)
        expired = period_expired(lot["stored_since"], as_of, period)
        headroom = total_life_headroom_days(lot["date_code"], as_of, total_life_years)
        grant = relife_grant_days(period, cycles, max_relife_cycles)
        effective = effective_grant_days(grant, headroom)
        disposition = lot_disposition(
            expired, effective, headroom, evidence["missing"], evidence["failed"]
        )
        if expired and headroom == 0:
            findings.append(
                "lot %s has used the whole permissible life its date code allows"
                % lot_id
            )
        if expired and cycles >= max_relife_cycles:
            findings.append(
                "lot %s has spent its %d relife cycles and earns no further period"
                % (lot_id, max_relife_cycles)
            )
        for name in evidence["missing"]:
            findings.append("lot %s owes %s and has no record of it" % (lot_id, name))
        for name in evidence["failed"]:
            findings.append("lot %s failed %s" % (lot_id, name))
        assessed.append(
            {
                "lot_id": lot_id,
                "part_number": str(lot["part_number"]).strip().upper(),
                "quantity": quantity,
                "build_demand": demand,
                "elapsed_storage_days": elapsed,
                "storage_period_days": period,
                "expired": expired,
                "relife_cycles_used": cycles,
                "grant_days": grant,
                "headroom_days": headroom,
                "renewed_period_days": effective if disposition in (
                    "relife-granted",
                ) else 0,
                "owed_tests": owed,
                "missing_tests": evidence["missing"],
                "failed_tests": evidence["failed"],
                "priority": campaign_priority(demand, len(owed)),
                "disposition": disposition,
            }
        )

    workable = [
        lot for lot in assessed
        if lot["disposition"] in ("relife-granted", "relife-conditional")
    ]
    ordered = sorted(
        workable, key=lambda lot: (-lot["priority"], lot["lot_id"])
    )
    capacity_left = test_capacity if test_capacity is not None else None
    scheduled = []
    deferred = []
    for lot in ordered:
        cost = len(lot["owed_tests"])
        if capacity_left is None or cost <= capacity_left:
            scheduled.append(lot["lot_id"])
            if capacity_left is not None:
                capacity_left -= cost
        else:
            deferred.append(lot["lot_id"])
    if deferred:
        findings.append(
            "%d lot(s) deferred: the relife test capacity does not reach them"
            % len(deferred)
        )

    demand_total = sum(lot["build_demand"] for lot in assessed)
    scheduled_set = set(scheduled)
    demand_covered = sum(
        lot["build_demand"] for lot in assessed if lot["lot_id"] in scheduled_set
    )
    return {
        "as_of": as_of.isoformat(),
        "lots": assessed,
        "lot_count": len(assessed),
        "scheduled": tuple(scheduled),
        "deferred": tuple(deferred),
        "capacity_used": (
            None if test_capacity is None else test_capacity - capacity_left
        ),
        "scrap_lot_ids": tuple(
            sorted(lot["lot_id"] for lot in assessed if lot["disposition"] == "scrap")
        ),
        "demand_total": demand_total,
        "demand_covered": demand_covered,
        "demand_coverage": (demand_covered / demand_total) if demand_total else 0.0,
        "findings": findings,
        "stock_clear": not findings,
    }
