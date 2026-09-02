#!/usr/bin/env python3
"""Reliability block diagram (RBD) evaluation logic per ARP4761A.

Paraphrased summary, not reproduced standard text (standards-map.yaml,
arp4761a: gated): ARP4761A quantitative safety analyses use reliability
block diagrams to represent the success logic of a system as blocks
connected in series (all blocks must succeed) with redundancy expressed
inside each block (parallel, k-out-of-n, standby). Components fail at
constant rate lambda so reliability over mission time t is
R(t) = exp(-lambda * t) and the mean time to failure is 1 / lambda.

Model implemented here (assumptions stated, no repair):
- series block: R = product of exp(-lambda_i * t), exponential with
  rate sum(lambda_i), MTBF = 1 / sum(lambda_i).
- active parallel block (1 of n, rates may differ): R = 1 - product(1
  - R_i); MTBF from the exact inclusion-exclusion expansion.
- k-out-of-n block (identical units, common rate lambda, k required):
  R = sum_{j=k..n} C(n, j) R_u^j (1 - R_u)^(n - j) with R_u =
  exp(-lambda * t); MTBF = (1 / lambda) * sum_{j=k..n} 1 / j.
- cold standby block (1 of 2 identical units, perfect switching):
  R = exp(-lambda * t) * (1 + lambda * t), MTBF = 2 / lambda.
  Imperfect switching is modeled with the simplified form
  R = exp(-lambda * t) * (1 + lambda_s * t) with
  lambda_s = lambda + switch_rate: the switch failure rate is folded
  into the standby channel gain. Assumption stated: this is the
  leading-order standby form and stays accurate only while the switch
  hazard lambda_sw * t stays small; unlike the perfect-switch case it
  can drift above unity, so a repairable or state-space treatment of
  imperfect switching belongs in the markov-analysis leaf.

Every block reliability is expanded exactly into terms
c * t^p * exp(-a * t); the system (blocks in series) is the product of
those expansions, mission reliability is the expansion evaluated at t,
and the system MTBF is the exact integral from 0 to infinity.
Non-physical inputs (non-positive rates, negative time, k above n,
empty structure) raise ValueError.
"""

import math
from itertools import combinations

_DEFAULT_SWITCH_RATE = 0.0
_MAX_PARALLEL_ITEMS = 16
_IDENTICAL_REL_TOL = 1e-9
_BLOCK_TYPES = ("series", "parallel", "kofn", "standby")


def _as_number(value, what):
    """Coerce int/float to float, rejecting bool, strings and NaN/Inf."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (what, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (what, value))
    return out


def _positive_rate(value, what):
    """A component failure rate must be strictly positive (a zero rate has
    no finite MTBF and is not a modeled failure source)."""
    out = _as_number(value, what)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (what, out))
    return out


def _nonnegative_time(value):
    out = _as_number(value, "mission time t")
    if out < 0.0:
        raise ValueError("mission time t must be non-negative, got %g" % out)
    return out


def _positive_time(value):
    out = _as_number(value, "mission time t")
    if out <= 0.0:
        raise ValueError("mission time t must be positive, got %g" % out)
    return out


def _all_identical(rates, what):
    """k-out-of-n and standby blocks need identical unit rates."""
    ref = rates[0]
    for r in rates[1:]:
        if abs(r - ref) > _IDENTICAL_REL_TOL * max(abs(r), abs(ref)):
            raise ValueError(
                "%s requires identical unit failure rates, got %r" % (what, rates)
            )
    return ref


def _parse_block(block):
    """Validate one block dict -> (type, rates, k, switch_rate, name).

    Accepted keys: type, items (rates), k (kofn only), switch_rate
    (standby only), name (optional label). Unknown keys are ignored.
    """
    if not isinstance(block, dict):
        raise ValueError("each block must be a dict, got %r" % (block,))
    btype = block.get("type")
    if btype not in _BLOCK_TYPES:
        raise ValueError(
            "unknown block type %r (expected one of %s)"
            % (btype, ", ".join(_BLOCK_TYPES))
        )
    items = block.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("block %r must have a non-empty 'items' list of rates" % (btype,))
    rates = [_positive_rate(r, "failure rate in %s block" % btype) for r in items]
    name = block.get("name")
    if not isinstance(name, str) or not name.strip():
        name = None
    if btype == "kofn":
        k = block.get("k")
        if isinstance(k, bool) or not isinstance(k, int):
            raise ValueError("k-of-n block needs integer k, got %r" % (k,))
        if not 1 <= k <= len(rates):
            raise ValueError(
                "k=%d out of range for n=%d items (need 1 <= k <= n)" % (k, len(rates))
            )
        _all_identical(rates, "k-out-of-n block")
        return btype, rates, k, _DEFAULT_SWITCH_RATE, name
    if btype == "standby":
        if len(rates) != 2:
            raise ValueError(
                "cold standby block needs exactly 2 items (1 of 2), got %d" % len(rates)
            )
        _all_identical(rates, "cold standby block")
        sw = block.get("switch_rate", _DEFAULT_SWITCH_RATE)
        if isinstance(sw, bool):
            raise ValueError("switch_rate must be a number")
        sw = _as_number(sw, "switch_rate")
        if sw < 0.0:
            raise ValueError("switch_rate must be non-negative, got %g" % sw)
        return btype, rates, None, sw, name
    if btype == "parallel" and len(rates) > _MAX_PARALLEL_ITEMS:
        raise ValueError(
            "parallel block supports at most %d items for exact MTBF "
            "(got %d); pre-combine series paths into single rates"
            % (_MAX_PARALLEL_ITEMS, len(rates))
        )
    return btype, rates, None, _DEFAULT_SWITCH_RATE, name


def _terms_for_block(btype, rates, k, switch_rate):
    """Exact expansion of one block's reliability as a list of
    (coef, rate, tpow) meaning coef * t**tpow * exp(-rate * t)."""
    if btype == "series":
        return [(1.0, sum(rates), 0)]
    if btype == "parallel":
        merged = {}
        for size in range(1, len(rates) + 1):
            for idxs in combinations(range(len(rates)), size):
                total = sum(rates[i] for i in idxs)
                sign = 1.0 if size % 2 == 1 else -1.0
                merged[total] = merged.get(total, 0.0) + sign
        return [(coef, total, 0) for total, coef in merged.items()]
    if btype == "kofn":
        lam = rates[0]
        n = len(rates)
        merged = {}
        for j in range(k, n + 1):
            for m in range(0, n - j + 1):
                s = j + m
                coef = math.comb(n, j) * math.comb(n - j, m)
                if m % 2 == 1:
                    coef = -coef
                merged[s * lam] = merged.get(s * lam, 0.0) + coef
        return [(coef, total, 0) for total, coef in merged.items()]
    # standby: exp(-lam t) * (1 + (lam + switch_rate) * t)
    lam = rates[0]
    lam_s = lam + switch_rate
    return [(1.0, lam, 0), (lam_s, lam, 1)]


def _eval_terms(terms, t):
    return sum(coef * (t ** tpow) * math.exp(-rate * t) for coef, rate, tpow in terms)


def _integrate_terms(terms):
    """Exact integral of the expansion from 0 to infinity: MTBF.

    Integral of t**p * exp(-a t) dt over [0, inf) is p! / a**(p+1).
    """
    return sum(
        coef * math.factorial(tpow) / (rate ** (tpow + 1))
        for coef, rate, tpow in terms
    )


def _mul_terms(left, right):
    """Product of two expansions (series connection of two blocks)."""
    merged = {}
    for c1, r1, p1 in left:
        for c2, r2, p2 in right:
            key = (r1 + r2, p1 + p2)
            merged[key] = merged.get(key, 0.0) + c1 * c2
    return [(coef, rate, tpow) for (rate, tpow), coef in merged.items()]


def _structure_terms(structure):
    """Blocks are connected in series, so the system expansion is the
    product of the per-block expansions."""
    terms = [(1.0, 0.0, 0)]
    for block in structure:
        btype, rates, k, sw, _name = _parse_block(block)
        terms = _mul_terms(terms, _terms_for_block(btype, rates, k, sw))
    return terms


def _parse_structure(structure):
    """A structure is a non-empty list of block dicts in series."""
    if not isinstance(structure, list) or not structure:
        raise ValueError("structure must be a non-empty list of blocks")
    return [_parse_block(block) for block in structure]


def component_reliability(rate, t):
    """R(t) = exp(-lambda * t) for one constant-rate component."""
    lam = _positive_rate(rate, "failure rate")
    tt = _nonnegative_time(t)
    return math.exp(-lam * tt)


def series_reliability(rates, t):
    """Reliability of items in series: exp(-t * sum(rates))."""
    parsed = [_positive_rate(r, "series failure rate") for r in rates]
    tt = _nonnegative_time(t)
    return math.exp(-tt * sum(parsed))


def parallel_reliability(rates, t):
    """Active parallel (1 of n) reliability over possibly different rates."""
    parsed = [_positive_rate(r, "parallel failure rate") for r in rates]
    tt = _nonnegative_time(t)
    r = 1.0
    for lam in parsed:
        r *= 1.0 - math.exp(-lam * tt)
    return 1.0 - r


def kofn_reliability(rate, n, k, t):
    """k-out-of-n identical units, common rate:
    sum_{j=k..n} C(n, j) R^j (1 - R)^(n - j)."""
    lam = _positive_rate(rate, "failure rate")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer, got %r" % (n,))
    if isinstance(k, bool) or not isinstance(k, int):
        raise ValueError("k must be an integer, got %r" % (k,))
    if not 1 <= k <= n:
        raise ValueError("need 1 <= k <= n, got k=%d n=%d" % (k, n))
    tt = _nonnegative_time(t)
    r_u = math.exp(-lam * tt)
    total = 0.0
    for j in range(k, n + 1):
        total += math.comb(n, j) * (r_u ** j) * ((1.0 - r_u) ** (n - j))
    return total


def standby_reliability(unit_rate, switch_rate, t):
    """1 of 2 identical cold standby.

    Perfect switching (switch_rate = 0) gives exp(-lambda t) * (1 +
    lambda t). Imperfect switching uses the simplified form with
    lambda_s = lambda + switch_rate folded into the standby channel;
    the formula is an approximation valid while lambda_s * t is small.
    """
    lam = _positive_rate(unit_rate, "standby unit failure rate")
    if isinstance(switch_rate, bool):
        raise ValueError("switch_rate must be a number")
    sw = _as_number(switch_rate, "switch_rate")
    if sw < 0.0:
        raise ValueError("switch_rate must be non-negative, got %g" % sw)
    tt = _nonnegative_time(t)
    lam_s = lam + sw
    return math.exp(-lam * tt) * (1.0 + lam_s * tt)


def block_reliability(block, t):
    """Mission reliability of one block dict at time t."""
    _nonnegative_time(t)
    btype, rates, k, sw, _ = _parse_block(block)
    return _eval_terms(_terms_for_block(btype, rates, k, sw), t)


def block_mtbf(block):
    """Mean time to failure of one block (exact integral of R(t))."""
    btype, rates, k, sw, _ = _parse_block(block)
    return _integrate_terms(_terms_for_block(btype, rates, k, sw))


def block_equivalent_rate(block, t):
    """Constant rate equivalent to one block over mission t.

    Exact sum(lambda_i) for an exponential series block; otherwise the
    approximation lambda_block = -ln(R_block(t)) / t.
    """
    tt = _positive_time(t)
    btype, rates, k, sw, _ = _parse_block(block)
    terms = _terms_for_block(btype, rates, k, sw)
    r = _eval_terms(terms, tt)
    if btype == "series":
        return sum(rates)
    return -math.log(r) / tt


def system_reliability(structure, t):
    """Mission reliability of the whole series-of-blocks structure at t."""
    _nonnegative_time(t)
    return _eval_terms(_structure_terms(structure), t)


def system_mtbf(structure):
    """Mean time to failure of the whole structure (exact integral)."""
    return _integrate_terms(_structure_terms(structure))


def system_equivalent_rate(structure, t):
    """Approximate constant system failure rate -ln(R_sys(t)) / t."""
    tt = _positive_time(t)
    r = _eval_terms(_structure_terms(structure), tt)
    return -math.log(r) / tt


def _perturbed_structure(structure, block_index, item_index, factor):
    """Copy of structure with one rate parameter scaled by factor.

    k-of-n and standby blocks carry one shared unit rate, so the rate
    is scaled in every item slot; standby also exposes the switch_rate
    as a separate parameter via item_index == -1.
    """
    out = []
    for i, block in enumerate(structure):
        if i != block_index:
            out.append(dict(block))
            continue
        copy = dict(block)
        btype, rates, k, sw, _ = _parse_block(block)
        if btype in ("kofn", "standby"):
            if item_index == -1:
                if btype != "standby":
                    raise ValueError("switch_rate exists only on standby blocks")
                copy["switch_rate"] = sw * factor
            else:
                copy["items"] = [r * factor for r in rates]
        else:
            new_items = list(rates)
            new_items[item_index] = new_items[item_index] * factor
            copy["items"] = new_items
        out.append(copy)
    return out


def sensitivity_report(structure, t, pct=1.0):
    """One-at-a-time rate sensitivity at mission time t.

    For every rate parameter, scale the rate by (1 + pct/100), keep all
    other rates fixed, and report the elasticity
    e = -(dR/dlambda) * (lambda / R) approximated by the relative
    reliability drop per relative rate rise. Returns dicts sorted by
    descending elasticity with keys label, block_index, item_index,
    rate, elasticity. item_index -1 means the standby switch_rate.
    """
    tt = _nonnegative_time(t)
    if isinstance(pct, bool) or not isinstance(pct, (int, float)):
        raise ValueError("pct must be a number")
    frac = float(pct) / 100.0
    if not math.isfinite(frac) or frac <= 0.0:
        raise ValueError("pct must be a positive number, got %r" % (pct,))
    blocks = _parse_structure(structure)
    base = system_reliability(structure, tt)
    rows = []
    for bi, (btype, rates, k, sw, name) in enumerate(blocks):
        label_head = name if name else "block%d" % bi
        if btype in ("kofn", "standby"):
            lam = rates[0]
            perturbed = _perturbed_structure(structure, bi, 0, 1.0 + frac)
            r1 = system_reliability(perturbed, tt)
            rows.append(
                {
                    "label": "%s.item0 (shared unit rate)" % label_head,
                    "block_index": bi,
                    "item_index": 0,
                    "rate": lam,
                    "elasticity": (base - r1) / (base * frac),
                }
            )
            if btype == "standby":
                perturbed = _perturbed_structure(structure, bi, -1, 1.0 + frac)
                r1 = system_reliability(perturbed, tt)
                rows.append(
                    {
                        "label": "%s.switch_rate" % label_head,
                        "block_index": bi,
                        "item_index": -1,
                        "rate": sw,
                        "elasticity": (base - r1) / (base * frac),
                    }
                )
        else:
            for ji, lam in enumerate(rates):
                perturbed = _perturbed_structure(structure, bi, ji, 1.0 + frac)
                r1 = system_reliability(perturbed, tt)
                rows.append(
                    {
                        "label": "%s.item%d" % (label_head, ji),
                        "block_index": bi,
                        "item_index": ji,
                        "rate": lam,
                        "elasticity": (base - r1) / (base * frac),
                    }
                )
    rows.sort(key=lambda row: (-row["elasticity"], row["block_index"], row["item_index"]))
    return rows


def evaluate_rbd(structure, t, pct=1.0):
    """Evaluate a reliability block diagram at mission time t.

    structure: non-empty list of blocks in series. Each block dict:
      {"type": "series"|"parallel"|"kofn"|"standby",
       "items": [rates...], "k": int (kofn), "switch_rate": float
       (standby), "name": optional label}
    Returns:
      system_reliability  R_sys(t)
      mtbf                exact system mean time to failure
      block_reliabilities {block index: R_block(t)}
      dominant_component  dict or None: the rate parameter whose +pct%
                          rise costs the most system reliability
    """
    _nonnegative_time(t)
    blocks = _parse_structure(structure)
    block_rels = {
        i: _eval_terms(_terms_for_block(btype, rates, k, sw), t)
        for i, (btype, rates, k, sw, _name) in enumerate(blocks)
    }
    sys_terms = [(1.0, 0.0, 0)]
    for (btype, rates, k, sw, _name) in blocks:
        sys_terms = _mul_terms(sys_terms, _terms_for_block(btype, rates, k, sw))
    rows = sensitivity_report(structure, t, pct)
    dominant = rows[0] if rows and rows[0]["elasticity"] > 0.0 else None
    return {
        "system_reliability": _eval_terms(sys_terms, t),
        "mtbf": _integrate_terms(sys_terms),
        "block_reliabilities": block_rels,
        "dominant_component": dominant,
    }
