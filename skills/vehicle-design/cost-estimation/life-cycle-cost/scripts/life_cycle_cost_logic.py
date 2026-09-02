#!/usr/bin/env python3
"""Life-cycle cost estimation for aircraft programs.

Full LCC rollup: RDT&E, production, operations and support, and
disposal phases; power-law CERs; learning curves (Nth unit cost and
exact cumulative average unit cost); present value discounting of
future year cash flows; inflation escalation; and an uncertainty
range. All costs are in program currency units, the discount rate i
and inflation rate f are dimensionless fractions per year, and the
learning curve lc is dimensionless (0.85 typical). Invalid inputs
raise ValueError.

Contract: docs/harness-contract.md gate 3, exercised by
scripts/test_life_cycle_cost.py (stdlib unittest, offline).
"""

import math


def cer_cost(a, x, b):
    """Return the power-law CER cost: cost = a * x**b.

    a is the CER coefficient, x the driver (mass, flight hours,
    thrust, quantity), b the exponent. Valid only inside the driver
    range of the source data.
    """
    if a <= 0:
        raise ValueError("CER coefficient a must be positive")
    if x <= 0:
        raise ValueError("CER driver x must be positive")
    if b <= 0:
        raise ValueError("CER exponent b must be positive")
    return a * (x ** b)


def _learning_curve_exponent(lc):
    if lc <= 0 or lc >= 1:
        raise ValueError("learning curve lc must satisfy 0 < lc < 1")
    return math.log(lc) / math.log(2)


def unit_cost(c1, n, lc):
    """Return the cost of unit n: c_n = c1 * n**s."""
    if c1 <= 0:
        raise ValueError("first-unit cost c1 must be positive")
    if n < 1:
        raise ValueError("unit number n must be >= 1")
    s = _learning_curve_exponent(lc)
    return c1 * (n ** s)


def cumulative_average_unit_cost(c1, n, lc):
    """Return the exact cumulative average unit cost over units 1..n.

    sum(c_k, k=1..n) / n. This is the exact discrete average; the
    closed form n**(s+1)/(s+1) used by parametric-cost approximates
    the cumulative total, not the exact sum.
    """
    if c1 <= 0:
        raise ValueError("first-unit cost c1 must be positive")
    if n < 1:
        raise ValueError("unit number n must be >= 1")
    s = _learning_curve_exponent(lc)
    total = sum(c1 * (k ** s) for k in range(1, n + 1))
    return total / n


def present_value(fv, i, n):
    """Return the present value of a single future amount fv at year n."""
    if fv <= 0:
        raise ValueError("future value fv must be positive")
    if i <= 0:
        raise ValueError("discount rate i must be positive")
    if n < 0:
        raise ValueError("year n must be >= 0")
    return fv / ((1.0 + i) ** n)


def annuity_present_value(a, i, n):
    """Return the present value of a uniform annual series a over n years."""
    if a <= 0:
        raise ValueError("annual amount a must be positive")
    if i <= 0:
        raise ValueError("discount rate i must be positive")
    if n < 1:
        raise ValueError("years n must be >= 1")
    return a * (1.0 - (1.0 + i) ** (-n)) / i


def escalated_cost(cost, f, years):
    """Return the cost escalated at inflation rate f for years."""
    if cost <= 0:
        raise ValueError("cost must be positive")
    if f < 0:
        raise ValueError("inflation rate f must be >= 0")
    if years < 0:
        raise ValueError("years must be >= 0")
    return cost * ((1.0 + f) ** years)


def lcc_total(rdte, production, os_annual, years, i, disposal):
    """Return the LCC rollup dict for the four lifecycle phases.

    Total = RDT&E + production + present value of the O&S annual
    stream over years + present value of the disposal cost at the
    end of the service life. The dict carries each discounted phase
    and the total.
    """
    for label, val in (
        ("rdte", rdte),
        ("production", production),
        ("os_annual", os_annual),
        ("disposal", disposal),
    ):
        if val < 0:
            raise ValueError("%s cost must be >= 0" % label)
    if i <= 0:
        raise ValueError("discount rate i must be positive")
    if years < 1:
        raise ValueError("years must be >= 1")
    os_pv = annuity_present_value(os_annual, i, years) if os_annual > 0 else 0.0
    disposal_pv = present_value(disposal, i, years) if disposal > 0 else 0.0
    return {
        "rdte": rdte,
        "production": production,
        "os_present_value": os_pv,
        "disposal_present_value": disposal_pv,
        "total": rdte + production + os_pv + disposal_pv,
    }


def uncertainty_range(point, low_frac, high_frac):
    """Return (point*(1-low_frac), point*(1+high_frac)) as a tuple.

    low_frac and high_frac are fractions of the point estimate, e.g.
    0.2 and 0.3 give a band from 80% to 130% of the point value.
    """
    if point <= 0:
        raise ValueError("point estimate must be positive")
    if low_frac < 0 or low_frac >= 1:
        raise ValueError("low_frac must satisfy 0 <= low_frac < 1")
    if high_frac < 0:
        raise ValueError("high_frac must be >= 0")
    return (point * (1.0 - low_frac), point * (1.0 + high_frac))
