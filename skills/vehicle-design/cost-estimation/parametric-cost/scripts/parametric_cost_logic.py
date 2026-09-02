#!/usr/bin/env python3
"""Parametric cost estimating relationships and learning curves.

Cost estimation CERs for aircraft development and production programs:
learning curve exponent, unit cost, cumulative learning factor, and
weight-based development cost. All costs are in program currency
units, airframe mass in kg, and the learning curve lc is dimensionless
(0.85 typical). Invalid inputs raise ValueError.

Contract: docs/harness-contract.md gate 3, exercised by
scripts/test_parametric_cost.py (stdlib unittest, offline).
"""

import math


def learning_curve_exponent(lc):
    """Return the learning curve exponent s = ln(lc) / ln(2)."""
    if lc <= 0 or lc >= 1:
        raise ValueError("learning curve lc must satisfy 0 < lc < 1")
    return math.log(lc) / math.log(2)


def unit_cost(c1, n, lc):
    """Return the unit cost of unit n: c_n = c1 * n**s."""
    if c1 <= 0:
        raise ValueError("first-unit cost c1 must be positive")
    if n < 1:
        raise ValueError("unit number n must be >= 1")
    s = learning_curve_exponent(lc)
    return c1 * (n ** s)


def cumulative_learning_factor(n, lc):
    """Return the closed-form cumulative learning factor n**(s+1)/(s+1)."""
    if n < 1:
        raise ValueError("unit number n must be >= 1")
    s = learning_curve_exponent(lc)
    return (n ** (s + 1)) / (s + 1)


def development_cost(a, w, b):
    """Return the weight-based development cost CER: c_dev = a * w**b."""
    if a <= 0:
        raise ValueError("CER coefficient a must be positive")
    if w <= 0:
        raise ValueError("airframe mass w must be positive")
    if b <= 0:
        raise ValueError("CER exponent b must be positive")
    return a * (w ** b)


def total_program_cost(c1, n, lc, dev_cost):
    """Return the program cost rollup dict for a production run of n units."""
    unit_n = unit_cost(c1, n, lc)
    factor = cumulative_learning_factor(n, lc)
    production_total = c1 * factor
    return {
        "unit_n": unit_n,
        "cumulative_factor": factor,
        "production_total": production_total,
        "program_total": production_total + dev_cost,
    }
