"""Reliability allocation: flow one top-level system reliability
requirement down to per-item design targets.

The system failure rate per flight hour (or its MTBF equivalent) is
split into per-item target rates by equal split, where every item
receives the same share and the item rates sum to the system rate, or
by complexity-weighted apportionment, where each item receives
system_rate x w_i / sum(w) with w an item complexity or part-count
weight chosen by the design team. The module verifies the series-sum
closure identity (allocated item rates sum to the system rate) and
reports each item margin capability / target - 1 against predicted
item capability rates.

Pure Python stdlib, deterministic, no RNG, no data tables. The
apportionment schemes are pure weighted splits of one top-level
budget; the weights are design-team inputs. ARP4761A guidance is
referenced, not reproduced.
"""

import math

ITEMS_MAX = 64


def _positive_number(value):
    """True when value is a positive int or float (bool excluded)."""
    return (isinstance(value, (int, float))
            and not isinstance(value, bool) and value > 0)


def mtbf_to_rate(mtbf):
    """Convert an MTBF target in hours to the constant failure rate.

    rate = 1.0 / mtbf. An MTBF system requirement enters the flow-down
    as its rate equivalent, the (e) MTBF support.
    """
    if not _positive_number(mtbf):
        raise ValueError("mtbf must be a positive number of hours")
    return 1.0 / mtbf


def equal_split(system_rate, n_items):
    """Split the system rate into n_items identical per-item rates.

    Each item receives system_rate / n_items. For a non-redundant
    series chain the item rates sum to the system rate, so equal
    split divides the system failure rate evenly.
    """
    if not _positive_number(system_rate):
        raise ValueError("system_rate must be a positive number")
    if (isinstance(n_items, bool) or not isinstance(n_items, int)
            or n_items < 1 or n_items > ITEMS_MAX):
        raise ValueError("n_items must be an integer in 1..ITEMS_MAX")
    share = system_rate / n_items
    return [share] * n_items


def complexity_weighted_alloc(system_rate, weights):
    """Allocate the system rate by normalized complexity weights.

    Item i receives system_rate x w_i / sum(weights) in weights
    order, the w_i being item complexity or part-count weights that
    are design-team data.
    """
    if not _positive_number(system_rate):
        raise ValueError("system_rate must be a positive number")
    if not weights:
        raise ValueError("weights must not be empty")
    if len(weights) > ITEMS_MAX:
        raise ValueError("more than ITEMS_MAX weights")
    for w in weights:
        if not _positive_number(w):
            raise ValueError("every weight must be a positive number")
    total_w = float(sum(weights))
    return [system_rate * w / total_w for w in weights]


def closure_check(item_rates, system_rate):
    """Check the series-sum closure of allocated budgets.

    Returns a dict with total = sum(item_rates), the given
    system_rate, relative_error = (total - system_rate) / system_rate
    and exact = math.isclose(total, system_rate, rel_tol=1e-12,
    abs_tol=1e-12). The allocated item budgets must add back up to
    the system budget.
    """
    if not item_rates:
        raise ValueError("item_rates must not be empty")
    for r in item_rates:
        if not _positive_number(r):
            raise ValueError("every item rate must be a positive number")
    if not _positive_number(system_rate):
        raise ValueError("system_rate must be a positive number")
    total = float(sum(item_rates))
    return {
        "total": total,
        "system_rate": float(system_rate),
        "relative_error": (total - system_rate) / system_rate,
        "exact": math.isclose(total, system_rate,
                              rel_tol=1e-12, abs_tol=1e-12),
    }


def margin_report(item_rates, item_capabilities):
    """Report each item margin capability / target - 1.0.

    Returns one dict per item, {"item", "target", "capability",
    "margin"}, in input order. Margin below 0.0 means the predicted
    capability rate is better (lower) than the budget, slack; margin
    above 0.0 means the predicted rate exceeds the budget, deficit.
    """
    if not item_rates or not item_capabilities:
        raise ValueError("item_rates and item_capabilities must not be empty")
    if len(item_rates) != len(item_capabilities):
        raise ValueError("item_rates and item_capabilities must match in length")
    for r in item_rates:
        if not _positive_number(r):
            raise ValueError("every item rate must be a positive number")
    for c in item_capabilities:
        if not _positive_number(c):
            raise ValueError("every capability rate must be a positive number")
    return [
        {"item": i, "target": item_rates[i],
         "capability": item_capabilities[i],
         "margin": item_capabilities[i] / item_rates[i] - 1.0}
        for i in range(len(item_rates))
    ]
