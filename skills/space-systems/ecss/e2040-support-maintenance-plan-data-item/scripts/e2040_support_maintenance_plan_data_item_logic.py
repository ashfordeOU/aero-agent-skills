"""Required contents of the device support and maintenance plan.

Anchor: ECSS-E-ST-20-40C Annex E (support and maintenance plan data item --
the after-delivery service owed, the upkeep the device needs and the
obsolescence position of its parts). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the supplied section list against the required contents of the plan.
2. Validate the service life and grade every after-delivery service
   commitment (offered response time against contracted response time, same
   unit, equality at the bound treated as met).
3. Compute how many times each upkeep task falls due inside the service life
   and compare with the count the plan declares.
4. Measure the unsupported window of each obsolescence item between its
   last-time-buy date and the end of the service life.
5. Size the lifetime-buy quantity across that window from consumption,
   attrition and stock on hand, rounding up with a tolerance so a quantity
   that lands on a whole unit stays on it.
6. Categorize each item as monitor, lifetime-buy or alternate-source against
   the storable quantity and report the findings.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "RESPONSE_TOLERANCE_HOURS",
    "QUANTITY_TOLERANCE",
    "MONTHS_PER_YEAR",
    "MITIGATION_MONITOR",
    "MITIGATION_LIFETIME_BUY",
    "MITIGATION_ALTERNATE_SOURCE",
    "missing_sections",
    "validate_service_life_months",
    "validate_commitment",
    "grade_commitment",
    "upkeep_occurrences",
    "validate_upkeep_task",
    "grade_upkeep_task",
    "unsupported_window_years",
    "ceil_with_tolerance",
    "lifetime_buy_quantity",
    "mitigation_category",
    "validate_obsolescence_item",
    "grade_obsolescence_item",
    "assess_support_plan",
]

REQUIRED_SECTIONS = (
    "scope",
    "after-delivery-service",
    "upkeep-activities",
    "obsolescence-management",
    "spares-and-logistics",
    "responsibilities-and-interfaces",
)

# Response-time comparisons are a difference of durations; an offered time
# equal to the contracted one can land a few ULPs on the wrong side.
RESPONSE_TOLERANCE_HOURS = 1e-9

# A quantity within this of a whole unit is that whole unit, not the next one.
QUANTITY_TOLERANCE = 1e-9

MONTHS_PER_YEAR = 12

MITIGATION_MONITOR = "monitor"
MITIGATION_LIFETIME_BUY = "lifetime-buy"
MITIGATION_ALTERNATE_SOURCE = "alternate-source"


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def missing_sections(sections):
    """Return the required sections absent from the supplied section list."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list or tuple of section names")
    present = set()
    for i, name in enumerate(sections):
        present.add(_identifier(name, "sections[%d]" % i).lower())
    return [name for name in REQUIRED_SECTIONS if name not in present]


def validate_service_life_months(months):
    """Return the validated service life in months."""
    value = _real(months, "service_life_months")
    if value <= 0.0:
        raise ValueError("service_life_months must be positive, got %g" % value)
    return value


def validate_commitment(commitment):
    """Return a normalized after-delivery service commitment."""
    if not isinstance(commitment, dict):
        raise ValueError("service commitment must be a mapping")
    for key in ("id", "offered_response_hours", "contracted_response_hours"):
        if key not in commitment:
            raise ValueError("service commitment missing required key '%s'" % key)
    identifier = _identifier(commitment["id"], "commitment id")
    offered = _real(commitment["offered_response_hours"], "offered_response_hours of %s" % identifier)
    contracted = _real(
        commitment["contracted_response_hours"], "contracted_response_hours of %s" % identifier
    )
    if offered <= 0.0:
        raise ValueError("offered_response_hours of %s must be positive" % identifier)
    if contracted <= 0.0:
        raise ValueError("contracted_response_hours of %s must be positive" % identifier)
    return {
        "id": identifier,
        "offered_response_hours": offered,
        "contracted_response_hours": contracted,
    }


def grade_commitment(commitment):
    """Return the graded commitment; met when the offered time is no later."""
    record = validate_commitment(commitment)
    offered = record["offered_response_hours"]
    contracted = record["contracted_response_hours"]
    met = offered < contracted or math.isclose(
        offered, contracted, rel_tol=0.0, abs_tol=RESPONSE_TOLERANCE_HOURS
    )
    record["met"] = met
    record["shortfall_hours"] = 0.0 if met else offered - contracted
    return record


def upkeep_occurrences(service_life_months, interval_months):
    """Return the whole number of times an interval falls due inside the life."""
    life = validate_service_life_months(service_life_months)
    interval = _real(interval_months, "interval_months")
    if interval <= 0.0:
        raise ValueError("interval_months must be positive, got %g" % interval)
    ratio = life / interval
    nearest = math.floor(ratio + QUANTITY_TOLERANCE)
    return int(nearest)


def validate_upkeep_task(task):
    """Return a normalized upkeep task."""
    if not isinstance(task, dict):
        raise ValueError("upkeep task must be a mapping")
    for key in ("id", "interval_months", "declared_occurrences"):
        if key not in task:
            raise ValueError("upkeep task missing required key '%s'" % key)
    identifier = _identifier(task["id"], "upkeep task id")
    interval = _real(task["interval_months"], "interval_months of %s" % identifier)
    if interval <= 0.0:
        raise ValueError("interval_months of %s must be positive" % identifier)
    declared = task["declared_occurrences"]
    if not isinstance(declared, int) or isinstance(declared, bool):
        raise ValueError("declared_occurrences of %s must be an integer" % identifier)
    if declared < 0:
        raise ValueError("declared_occurrences of %s must not be negative" % identifier)
    return {"id": identifier, "interval_months": interval, "declared_occurrences": declared}


def grade_upkeep_task(task, service_life_months):
    """Return the graded upkeep task with computed and declared occurrences."""
    record = validate_upkeep_task(task)
    computed = upkeep_occurrences(service_life_months, record["interval_months"])
    record["computed_occurrences"] = computed
    record["consistent"] = computed == record["declared_occurrences"]
    return record


def unsupported_window_years(last_time_buy_year, service_life_end_year):
    """Return the years between the last-time-buy date and the end of life."""
    ltb = _real(last_time_buy_year, "last_time_buy_year")
    end = _real(service_life_end_year, "service_life_end_year")
    gap = end - ltb
    if gap <= 0.0:
        return 0.0
    return gap


def ceil_with_tolerance(value, tolerance=QUANTITY_TOLERANCE):
    """Round a quantity up to a whole unit, keeping a near-integer where it is."""
    amount = _real(value, "value")
    tol = _real(tolerance, "tolerance")
    if tol < 0.0:
        raise ValueError("tolerance must not be negative")
    nearest = round(amount)
    if abs(amount - nearest) <= tol:
        return int(nearest)
    return int(math.ceil(amount))


def lifetime_buy_quantity(annual_consumption, window_years, attrition_fraction, stock_on_hand):
    """Return the whole units to buy before resupply ends, never below zero."""
    consumption = _real(annual_consumption, "annual_consumption")
    if consumption < 0.0:
        raise ValueError("annual_consumption must not be negative")
    years = _real(window_years, "window_years")
    if years < 0.0:
        raise ValueError("window_years must not be negative")
    attrition = _real(attrition_fraction, "attrition_fraction")
    if attrition < 0.0 or attrition >= 1.0:
        raise ValueError("attrition_fraction must lie in [0, 1), got %g" % attrition)
    stock = _real(stock_on_hand, "stock_on_hand")
    if stock < 0.0:
        raise ValueError("stock_on_hand must not be negative")
    demand = consumption * years * (1.0 + attrition)
    shortfall = demand - stock
    if shortfall <= 0.0:
        return 0
    return ceil_with_tolerance(shortfall)


def mitigation_category(window_years, required_quantity, storable_quantity):
    """Return the mitigation category for an obsolescence item."""
    years = _real(window_years, "window_years")
    if years < 0.0:
        raise ValueError("window_years must not be negative")
    if not isinstance(required_quantity, int) or isinstance(required_quantity, bool):
        raise ValueError("required_quantity must be an integer")
    if required_quantity < 0:
        raise ValueError("required_quantity must not be negative")
    if not isinstance(storable_quantity, int) or isinstance(storable_quantity, bool):
        raise ValueError("storable_quantity must be an integer")
    if storable_quantity < 0:
        raise ValueError("storable_quantity must not be negative")
    if years <= 0.0 or required_quantity == 0:
        return MITIGATION_MONITOR
    if required_quantity <= storable_quantity:
        return MITIGATION_LIFETIME_BUY
    return MITIGATION_ALTERNATE_SOURCE


def validate_obsolescence_item(item):
    """Return a normalized obsolescence item."""
    if not isinstance(item, dict):
        raise ValueError("obsolescence item must be a mapping")
    required = (
        "id",
        "last_time_buy_year",
        "annual_consumption",
        "attrition_fraction",
        "stock_on_hand",
        "storable_quantity",
    )
    for key in required:
        if key not in item:
            raise ValueError("obsolescence item missing required key '%s'" % key)
    identifier = _identifier(item["id"], "obsolescence item id")
    storable = item["storable_quantity"]
    if not isinstance(storable, int) or isinstance(storable, bool):
        raise ValueError("storable_quantity of %s must be an integer" % identifier)
    if storable < 0:
        raise ValueError("storable_quantity of %s must not be negative" % identifier)
    return {
        "id": identifier,
        "last_time_buy_year": _real(item["last_time_buy_year"], "last_time_buy_year"),
        "annual_consumption": _real(item["annual_consumption"], "annual_consumption"),
        "attrition_fraction": _real(item["attrition_fraction"], "attrition_fraction"),
        "stock_on_hand": _real(item["stock_on_hand"], "stock_on_hand"),
        "storable_quantity": storable,
    }


def grade_obsolescence_item(item, service_life_end_year):
    """Return the graded obsolescence item with window, buy quantity and category."""
    record = validate_obsolescence_item(item)
    window = unsupported_window_years(record["last_time_buy_year"], service_life_end_year)
    quantity = lifetime_buy_quantity(
        record["annual_consumption"],
        window,
        record["attrition_fraction"],
        record["stock_on_hand"],
    )
    record["unsupported_window_years"] = window
    record["lifetime_buy_quantity"] = quantity
    record["mitigation"] = mitigation_category(window, quantity, record["storable_quantity"])
    return record


def assess_support_plan(plan):
    """Run the full Annex E support and maintenance plan content assessment.

    plan keys: sections, service_life_months, service_life_end_year,
    commitments, upkeep_tasks, obsolescence_items.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    required = (
        "sections",
        "service_life_months",
        "service_life_end_year",
        "commitments",
        "upkeep_tasks",
        "obsolescence_items",
    )
    for key in required:
        if key not in plan:
            raise ValueError("plan missing required key '%s'" % key)
    life = validate_service_life_months(plan["service_life_months"])
    end_year = _real(plan["service_life_end_year"], "service_life_end_year")

    absent = missing_sections(plan["sections"])
    for name, value in (
        ("commitments", plan["commitments"]),
        ("upkeep_tasks", plan["upkeep_tasks"]),
        ("obsolescence_items", plan["obsolescence_items"]),
    ):
        if not isinstance(value, (list, tuple)):
            raise ValueError("plan['%s'] must be a sequence" % name)

    commitments = [grade_commitment(c) for c in plan["commitments"]]
    tasks = [grade_upkeep_task(t, life) for t in plan["upkeep_tasks"]]
    items = [grade_obsolescence_item(i, end_year) for i in plan["obsolescence_items"]]

    findings = []
    for name in absent:
        findings.append("required section %r is absent from the plan" % name)
    for record in commitments:
        if not record["met"]:
            findings.append(
                "service commitment %s responds %.3f h later than contracted"
                % (record["id"], record["shortfall_hours"])
            )
    for record in tasks:
        if not record["consistent"]:
            findings.append(
                "upkeep task %s declares %d occurrences, the interval gives %d over the life"
                % (record["id"], record["declared_occurrences"], record["computed_occurrences"])
            )
    for record in items:
        if record["mitigation"] == MITIGATION_ALTERNATE_SOURCE:
            findings.append(
                "obsolescence item %s needs %d units over %.2f unsupported years, above the "
                "storable %d, so a lifetime buy cannot cover it"
                % (
                    record["id"],
                    record["lifetime_buy_quantity"],
                    record["unsupported_window_years"],
                    record["storable_quantity"],
                )
            )
    return {
        "missing_sections": absent,
        "service_life_months": life,
        "commitments": commitments,
        "upkeep_tasks": tasks,
        "obsolescence_items": items,
        "total_lifetime_buy_units": sum(r["lifetime_buy_quantity"] for r in items),
        "compliant": not findings,
        "findings": findings,
    }
