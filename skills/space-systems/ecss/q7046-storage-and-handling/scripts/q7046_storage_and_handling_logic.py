#!/usr/bin/env python3
"""Storage and handling of threaded fasteners: protection, life, issue.

Anchor: ECSS-Q-ST-70-46 storage and handling clause on threaded
fasteners. The procedure below is a paraphrase into implementable steps;
no standard text is reproduced.

A fastener in stores is a part under a clock. The clock is set by the
corrosion protection it carries and by the environment it is kept in:
a bare passivated part in an uncontrolled store runs out long before a
sealed, desiccated, oil-preserved part in a controlled one. The clock is
also interrupted rather than paused by a package breach, because from
the moment the seal opens the part is in the room's environment and not
the package's.

Two other things are decided here.

Whether the environment is inside its limits at all. A store outside
its temperature or humidity band is not storing; the parts in it are on
hold until the excursion is assessed, and the length of the excursion is
what decides whether re-preservation is enough.

Whether the parts may be issued. Lots are not mixed in a bin, because a
mixed bin has no lot identity and therefore no traceability to the heat.
Issue is oldest-first so that the life the stores paid for is the life
that gets used. Threaded parts are not tipped in bulk, because the
threads damage each other and the damage is on the flanks where nobody
looks.

Dates are handled with whole days and whole months in integer
arithmetic, so a life computed here is the life computed anywhere.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import datetime

PROTECTION_BARE_PASSIVATED = "bare-passivated"
PROTECTION_PLATED = "plated"
PROTECTION_OIL_PRESERVED = "oil-preserved"
PROTECTION_SEALED_DESICCATED = "sealed-desiccated"

PROTECTIONS = (
    PROTECTION_BARE_PASSIVATED,
    PROTECTION_PLATED,
    PROTECTION_OIL_PRESERVED,
    PROTECTION_SEALED_DESICCATED,
)

STORAGE_CONTROLLED = "controlled"
STORAGE_UNCONTROLLED = "uncontrolled"
STORAGE_CLASSES = (STORAGE_CONTROLLED, STORAGE_UNCONTROLLED)

# Shelf life in whole months, by protection and storage class.
_SHELF_LIFE_MONTHS = {
    PROTECTION_BARE_PASSIVATED: {STORAGE_CONTROLLED: 24, STORAGE_UNCONTROLLED: 6},
    PROTECTION_PLATED: {STORAGE_CONTROLLED: 60, STORAGE_UNCONTROLLED: 18},
    PROTECTION_OIL_PRESERVED: {STORAGE_CONTROLLED: 60, STORAGE_UNCONTROLLED: 24},
    PROTECTION_SEALED_DESICCATED: {STORAGE_CONTROLLED: 120,
                                   STORAGE_UNCONTROLLED: 36},
}

# Environmental band each storage class is held to.
_ENVIRONMENT_LIMITS = {
    STORAGE_CONTROLLED: {
        "temperature_c": (15.0, 25.0),
        "relative_humidity_pct": (20.0, 55.0),
    },
    STORAGE_UNCONTROLLED: {
        "temperature_c": (0.0, 40.0),
        "relative_humidity_pct": (10.0, 75.0),
    },
}

# Re-inspection interval in whole months, as a fraction of the life.
_REINSPECTION_DIVISOR = 4

ISSUE_RELEASE = "release-for-issue"
ISSUE_REINSPECT = "re-inspect-before-issue"
ISSUE_REPRESERVE = "re-preserve-and-restart-the-clock"
ISSUE_QUARANTINE = "quarantine"

_SLACK_C = 1e-9


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_date(name, value):
    if not isinstance(value, datetime.date) or isinstance(value, datetime.datetime):
        raise ValueError("%s must be a datetime.date, got %r" % (name, value))
    return value


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _add_months(start, months):
    """Same day of the month, months later, clamped to the month length."""
    total = start.month - 1 + months
    year = start.year + total // 12
    month = total % 12 + 1
    day = start.day
    while True:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1


def shelf_life_months(protection, storage_class):
    """Whole months of life this protection gets in this store."""
    _require_choice("protection", protection, PROTECTIONS)
    _require_choice("storage_class", storage_class, STORAGE_CLASSES)
    return _SHELF_LIFE_MONTHS[protection][storage_class]


def reinspection_interval_months(protection, storage_class):
    """How often a lot in store is looked at before its life runs out."""
    life = shelf_life_months(protection, storage_class)
    return max(1, life // _REINSPECTION_DIVISOR)


def life_start_date(manufacture_date, package_breach_date=None):
    """The date the clock actually runs from.

    A package breach does not pause the clock, it restarts it against
    the room the parts are now in.
    """
    made = _require_date("manufacture_date", manufacture_date)
    if package_breach_date is None:
        return made
    breach = _require_date("package_breach_date", package_breach_date)
    if breach < made:
        raise ValueError(
            "the package was recorded as breached before the parts were made"
        )
    return breach


def expiry_date(manufacture_date, protection, storage_class,
                package_breach_date=None):
    """Date the lot's protection is no longer relied on."""
    start = life_start_date(manufacture_date, package_breach_date)
    months = shelf_life_months(protection, storage_class)
    return _add_months(start, months)


def remaining_life_days(manufacture_date, protection, storage_class, today,
                        package_breach_date=None):
    """Whole days left before the protection expires; negative once past."""
    now = _require_date("today", today)
    made = _require_date("manufacture_date", manufacture_date)
    if now < made:
        raise ValueError("today is before the manufacture date of the lot")
    expiry = expiry_date(manufacture_date, protection, storage_class,
                         package_breach_date)
    return (expiry - now).days


def environment_verdict(storage_class, temperature_c, relative_humidity_pct):
    """Whether the store is inside the band the class is held to."""
    _require_choice("storage_class", storage_class, STORAGE_CLASSES)
    temperature = _require_number("temperature_c", temperature_c)
    humidity = _require_number("relative_humidity_pct", relative_humidity_pct)
    if humidity < 0.0 or humidity > 100.0:
        raise ValueError(
            "relative_humidity_pct must lie between 0 and 100, got %s"
            % relative_humidity_pct
        )
    limits = _ENVIRONMENT_LIMITS[storage_class]
    t_low, t_high = limits["temperature_c"]
    h_low, h_high = limits["relative_humidity_pct"]
    excursions = []
    if temperature < t_low - _SLACK_C or temperature > t_high + _SLACK_C:
        excursions.append(
            "temperature %.1f C is outside the %.1f..%.1f C band for a %s store"
            % (temperature, t_low, t_high, storage_class)
        )
    if humidity < h_low - _SLACK_C or humidity > h_high + _SLACK_C:
        excursions.append(
            "relative humidity %.1f%% is outside the %.1f..%.1f%% band for a "
            "%s store" % (humidity, h_low, h_high, storage_class)
        )
    return {
        "storage_class": storage_class,
        "within_limits": not excursions,
        "excursions": excursions,
        "temperature_band_c": (t_low, t_high),
        "humidity_band_pct": (h_low, h_high),
    }


def handling_findings(case):
    """Handling conditions that damage threads or lose lot identity."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    findings = []
    lots = _require_count(
        "lots_in_container", case.get("lots_in_container", 1), minimum=1
    )
    if lots > 1:
        findings.append(
            "%d lots share one container; a mixed container has no lot "
            "identity and therefore no route back to a heat" % lots
        )
    if case.get("bulk_tipped"):
        findings.append(
            "the parts were tipped in bulk; threaded parts damage each other's "
            "flanks, where the damage is not visible in a bin check"
        )
    if case.get("dissimilar_metals_in_container"):
        findings.append(
            "dissimilar metals share the container; contact plus store humidity "
            "is a galvanic couple, not a storage arrangement"
        )
    if case.get("issue_order") not in (None, "oldest-first"):
        findings.append(
            "issue order is %r; issuing anything but oldest-first spends the "
            "life of the newest lot and expires the oldest in place"
            % case.get("issue_order")
        )
    return findings


def assess_storage(case):
    """Release, re-inspect, re-preserve or quarantine one stored lot."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot_id = case.get("lot_id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("case needs a non-empty string lot_id, got %r" % (lot_id,))
    protection = _require_choice("protection", case.get("protection"), PROTECTIONS)
    storage_class = _require_choice(
        "storage_class", case.get("storage_class"), STORAGE_CLASSES
    )
    made = _require_date("manufacture_date", case.get("manufacture_date"))
    today = _require_date("today", case.get("today"))
    breach = case.get("package_breach_date")
    remaining = remaining_life_days(made, protection, storage_class, today, breach)
    interval = reinspection_interval_months(protection, storage_class)
    environment = environment_verdict(
        storage_class,
        case.get("temperature_c", 20.0),
        case.get("relative_humidity_pct", 40.0),
    )
    findings = list(environment["excursions"])
    findings.extend(handling_findings(case))
    if breach is not None:
        findings.append(
            "the package was breached; the life runs from the breach against "
            "the room the parts are now in, not from manufacture"
        )
    if remaining < 0:
        findings.append(
            "the protection expired %d day(s) ago" % abs(remaining)
        )
        disposition = ISSUE_QUARANTINE
    elif not environment["within_limits"]:
        disposition = ISSUE_REPRESERVE
    elif findings:
        disposition = ISSUE_REINSPECT
    else:
        disposition = ISSUE_RELEASE
    return {
        "lot_id": lot_id,
        "protection": protection,
        "storage_class": storage_class,
        "expiry_date": expiry_date(made, protection, storage_class, breach),
        "remaining_life_days": remaining,
        "reinspection_interval_months": interval,
        "environment": environment,
        "disposition": disposition,
        "findings": findings,
    }
