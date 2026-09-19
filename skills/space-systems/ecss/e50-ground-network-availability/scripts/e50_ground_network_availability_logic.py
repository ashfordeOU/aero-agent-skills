"""Availability budgeting for a ground network.

Anchor: ECSS-E-ST-50C clause 5.8.6 -- availability of the ground network.
Paraphrased into an implementable procedure; no standard text is reproduced.

The clause is the largest availability block in the standard, and the
obligations behind its many items reduce to one discipline applied end to end:
the ground network is a chain of elements, each element has an availability
that comes from how often it fails and how long it takes to get back, the
chain composes, and the composed figure is what the mission is promised.

Four moves cover it:

  element      -- inherent availability from mean time between failures and
                  mean time to repair, and operational availability once
                  preventive maintenance is charged as well;
  composition  -- elements in series multiply; a redundant group is one minus
                  the product of its members' unavailabilities;
  budget       -- an availability is only meaningful with a period attached,
                  so it is restated as the outage seconds the period allows;
  apportionment-- the inverse: the per-element availability, or the mean time
                  to repair, that a chain needs to reach an end-to-end target.

The contributor analysis is the part a review actually uses. Unavailability
adds almost linearly along a chain, so naming the element that spends most of
the budget says where the next euro goes.
"""

import math

__all__ = [
    "COMPLIANT",
    "MARGINAL",
    "NON_COMPLIANT",
    "REL_TOL",
    "SECONDS_PER_YEAR",
    "validate_availability",
    "validate_positive",
    "validate_non_negative",
    "validate_element",
    "inherent_availability",
    "operational_availability",
    "series_availability",
    "redundant_group_availability",
    "element_availability",
    "allowed_outage_seconds",
    "apportion_series_availability",
    "required_mttr",
    "unavailability_contributions",
    "assess_ground_network_availability",
]

COMPLIANT = "compliant"
MARGINAL = "marginal"
NON_COMPLIANT = "non-compliant"

SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

# Relative tolerance for every comparison against a bound, so a chain sized to
# land exactly on its target is graded the same way on every platform.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_availability(value, name="availability"):
    """Return an availability in the closed interval zero to one."""
    a = _validate_number(value, name)
    if a < 0.0 or a > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return a


def validate_positive(value, name="value"):
    """Return a strictly positive value."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_non_negative(value, name="value"):
    """Return a value of zero or more."""
    number = _validate_number(value, name)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def inherent_availability(mtbf_s, mttr_s):
    """Return uptime over uptime plus corrective repair time."""
    mtbf = validate_positive(mtbf_s, "mtbf_s")
    mttr = validate_non_negative(mttr_s, "mttr_s")
    return mtbf / (mtbf + mttr)


def operational_availability(mtbf_s, mttr_s, preventive_s_per_cycle=0.0):
    """Return availability once planned downtime is charged as well.

    Preventive maintenance is downtime the mission does not get back, so a
    figure that omits it overstates what the network delivers.
    """
    mtbf = validate_positive(mtbf_s, "mtbf_s")
    mttr = validate_non_negative(mttr_s, "mttr_s")
    preventive = validate_non_negative(
        preventive_s_per_cycle, "preventive_s_per_cycle"
    )
    return mtbf / (mtbf + mttr + preventive)


def series_availability(values):
    """Return the availability of elements every transfer has to cross."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("values must be a list or tuple of availabilities")
    if len(values) == 0:
        raise ValueError("values must name at least one element")
    product = 1.0
    for index, value in enumerate(values):
        product *= validate_availability(value, "values[%d]" % index)
    return product


def redundant_group_availability(values):
    """Return the availability of members any one of which suffices."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("values must be a list or tuple of availabilities")
    if len(values) == 0:
        raise ValueError("values must name at least one member")
    down = 1.0
    for index, value in enumerate(values):
        down *= 1.0 - validate_availability(value, "values[%d]" % index)
    return 1.0 - down


def element_availability(element):
    """Return the availability of one chain element from its description.

    An element is a mapping carrying a name and either a stated availability,
    or a mean time between failures with a mean time to repair. A redundancy
    count above one puts that many identical members in a redundant group.
    """
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping")
    name = element.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("element needs a non-empty name")
    if "availability" in element:
        unit = validate_availability(element["availability"], "%s.availability" % name)
    elif "mtbf_s" in element:
        unit = operational_availability(
            element["mtbf_s"],
            element.get("mttr_s", 0.0),
            element.get("preventive_s_per_cycle", 0.0),
        )
    else:
        raise ValueError(
            "element %r needs either an availability or an mtbf_s/mttr_s pair" % name
        )
    redundancy = element.get("redundancy", 1)
    if isinstance(redundancy, bool) or not isinstance(redundancy, int):
        raise ValueError("%s.redundancy must be an integer count" % name)
    if redundancy < 1:
        raise ValueError("%s.redundancy must be at least 1" % name)
    if redundancy == 1:
        return unit
    return redundant_group_availability([unit] * redundancy)


def validate_element(element):
    """Return a normalized element record, raising on anything unusable."""
    available = element_availability(element)
    return {
        "name": element["name"],
        "availability": available,
        "redundancy": int(element.get("redundancy", 1)),
    }


def allowed_outage_seconds(availability, period_s=SECONDS_PER_YEAR):
    """Return the outage a period allows at this availability."""
    a = validate_availability(availability, "availability")
    period = validate_positive(period_s, "period_s")
    return (1.0 - a) * period


def apportion_series_availability(target_availability, elements):
    """Return the equal per-element availability a series chain needs."""
    target = validate_availability(target_availability, "target_availability")
    if isinstance(elements, bool) or not isinstance(elements, int):
        raise ValueError("elements must be an integer count")
    if elements < 1:
        raise ValueError("elements must be at least 1, got %r" % (elements,))
    if target == 0.0:
        return 0.0
    if target == 1.0:
        return 1.0
    return math.exp(math.log(target) / elements)


def required_mttr(mtbf_s, target_availability):
    """Return the repair time an element needs to reach a target.

    Zero means only an instantaneous repair suffices. A target of one is
    unreachable with any finite repair time and is rejected rather than
    answered with zero, which would read as an achievable requirement.
    """
    mtbf = validate_positive(mtbf_s, "mtbf_s")
    target = validate_availability(target_availability, "target_availability")
    if target == 1.0:
        raise ValueError("an availability of exactly 1 admits no finite repair time")
    if target == 0.0:
        return math.inf
    return mtbf * (1.0 - target) / target


def unavailability_contributions(elements):
    """Return each element's share of the chain unavailability, worst first."""
    if isinstance(elements, (str, bytes)) or not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a list or tuple")
    if len(elements) == 0:
        raise ValueError("elements must name at least one element")
    records = [validate_element(element) for element in elements]
    total = sum(1.0 - record["availability"] for record in records)
    rows = []
    for record in records:
        down = 1.0 - record["availability"]
        rows.append(
            {
                "name": record["name"],
                "availability": record["availability"],
                "unavailability": down,
                "share": (down / total) if total > 0.0 else 0.0,
            }
        )
    rows.sort(key=lambda row: (-row["unavailability"], row["name"]))
    return rows


def assess_ground_network_availability(
    elements,
    required_availability,
    period_s=SECONDS_PER_YEAR,
    margin_factor=1.0,
):
    """Grade a ground network chain against its availability requirement."""
    required = validate_availability(required_availability, "required_availability")
    period = validate_positive(period_s, "period_s")
    factor = _validate_number(margin_factor, "margin_factor")
    if factor < 1.0:
        raise ValueError("margin_factor must be at least 1, got %r" % (margin_factor,))
    rows = unavailability_contributions(elements)
    achieved = series_availability([row["availability"] for row in rows])
    required_unavailability = 1.0 - required
    goal_unavailability = required_unavailability / factor
    goal = 1.0 - goal_unavailability
    achieved_unavailability = 1.0 - achieved
    tolerance = REL_TOL * max(required_unavailability, 1e-300)
    if achieved_unavailability <= goal_unavailability + tolerance:
        verdict = COMPLIANT
    elif achieved_unavailability <= required_unavailability + tolerance:
        verdict = MARGINAL
    else:
        verdict = NON_COMPLIANT
    findings = []
    if verdict == NON_COMPLIANT:
        findings.append(
            "chain reaches %.9g against a requirement of %.9g; the network "
            "does not meet the stated availability" % (achieved, required)
        )
    elif verdict == MARGINAL:
        findings.append(
            "chain reaches %.9g and meets %.9g, but holds less than the factor "
            "of %.6g of headroom asked for" % (achieved, required, factor)
        )
    if verdict != COMPLIANT and rows:
        worst = rows[0]
        findings.append(
            "%s spends %.1f%% of the chain unavailability and is where the "
            "budget goes first" % (worst["name"], 100.0 * worst["share"])
        )
        findings.append(
            "each of the %d elements has to reach %.9g for the chain to make "
            "the target with its headroom"
            % (len(rows), apportion_series_availability(goal, len(rows)))
        )
    return {
        "elements": rows,
        "achieved_availability": achieved,
        "achieved_unavailability": achieved_unavailability,
        "required_availability": required,
        "margin_factor": factor,
        "goal_availability": goal,
        "period_s": period,
        "outage_seconds_per_period": allowed_outage_seconds(achieved, period),
        "allowed_outage_seconds_per_period": allowed_outage_seconds(required, period),
        "per_element_apportionment": apportion_series_availability(goal, len(rows)),
        "worst_element": rows[0]["name"] if rows else None,
        "verdict": verdict,
        "findings": findings,
    }
