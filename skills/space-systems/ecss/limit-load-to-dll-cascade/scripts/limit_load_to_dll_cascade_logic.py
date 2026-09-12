"""
Limit Load to DLL Cascade — ECSS-E-ST-32C clauses 4.2.7–4.2.8.

Deterministic, offline, stdlib-only module.

Definitions
-----------
LL   — Limit Load: maximum load expected over the structure's service life.
DLL  — Design Limit Load: DLL = LL × LUF.
LUF  — Load Uncertainty Factor: must be >= 1.0 (clause 4.2.8).
Transfer factor — maps a parent-level LL to a child-level LL through the
    structural interface response.
"""

import math


class LimitLoadCascadeError(Exception):
    """Raised when inputs violate ECSS-E-ST-32C load cascade rules."""


def _to_float(value, name):
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric, got {type(value).__name__!r}")
    return float(value)


def validate_luf(luf):
    """
    Validate that a Load Uncertainty Factor meets the clause 4.2.8 floor.
    Raises LimitLoadCascadeError for LUF < 1.0.
    """
    luf = _to_float(luf, "luf")
    if luf < 1.0:
        raise LimitLoadCascadeError(
            f"LUF must be >= 1.0 per ECSS-E-ST-32C clause 4.2.8; received {luf}"
        )
    return luf


def compute_dll(ll, luf):
    """
    Compute the Design Limit Load for a single load value.

    DLL = LL × LUF

    Parameters
    ----------
    ll  : float — Limit Load (any sign; sign denotes direction).
    luf : float — Load Uncertainty Factor, must be >= 1.0.

    Returns
    -------
    float — Design Limit Load.
    """
    ll = _to_float(ll, "ll")
    luf = validate_luf(luf)
    return ll * luf


def propagate_level(parent_ll, transfer_factor, luf):
    """
    Derive child LL and child DLL from the parent LL.

    child_ll  = parent_ll × transfer_factor
    child_dll = child_ll  × luf

    Parameters
    ----------
    parent_ll       : float — LL arriving from the parent structural level.
    transfer_factor : float — structural response factor >= 0.0.
                      > 1.0 amplification, < 1.0 attenuation, = 1.0 pass-through.
    luf             : float — LUF for the child level, must be >= 1.0.

    Returns
    -------
    dict with keys 'll' (child LL) and 'dll' (child DLL).
    """
    parent_ll = _to_float(parent_ll, "parent_ll")
    transfer_factor = _to_float(transfer_factor, "transfer_factor")
    if transfer_factor < 0.0:
        raise LimitLoadCascadeError(
            f"transfer_factor must be >= 0.0; received {transfer_factor}"
        )
    luf = validate_luf(luf)
    child_ll = parent_ll * transfer_factor
    child_dll = child_ll * luf
    return {"ll": child_ll, "dll": child_dll}


def cascade(root_ll, levels):
    """
    Recursively propagate LL through a structural hierarchy.

    Each entry in `levels` defines one structural level below the root.
    The cascade feeds the child LL of level N as the parent LL of level N+1.

    Parameters
    ----------
    root_ll : float — LL at the topmost structural level.
    levels  : list of dict, each with keys:
                'name'            — str, structural level label.
                'transfer_factor' — float >= 0.0.
                'luf'             — float >= 1.0.

    Returns
    -------
    list of dict with keys 'name', 'll', 'dll' for every level.
    """
    if not isinstance(levels, list):
        raise TypeError("levels must be a list")
    if len(levels) == 0:
        raise LimitLoadCascadeError("levels must be non-empty")

    root_ll = _to_float(root_ll, "root_ll")
    results = []
    current_ll = root_ll

    for i, level in enumerate(levels):
        if not isinstance(level, dict):
            raise TypeError(f"levels[{i}] must be a dict")
        for key in ("name", "transfer_factor", "luf"):
            if key not in level:
                raise KeyError(f"levels[{i}] missing required key '{key}'")
        result = propagate_level(current_ll, level["transfer_factor"], level["luf"])
        result["name"] = level["name"]
        results.append(result)
        current_ll = result["ll"]

    return results


def combine_loads(components, method="SRSS"):
    """
    Combine multiple scalar load components into a single resultant.

    Parameters
    ----------
    components : list of float — individual load components.
    method     : str — 'SRSS' (square-root-sum-of-squares) or 'ABS' (absolute sum).
                 SRSS is valid only for statistically independent random components.
                 ABS must be used for correlated or deterministic components.

    Returns
    -------
    float — combined load magnitude.
    """
    if not isinstance(components, list):
        raise TypeError("components must be a list")
    if len(components) == 0:
        raise LimitLoadCascadeError("components must be non-empty")
    floats = []
    for i, c in enumerate(components):
        floats.append(_to_float(c, f"components[{i}]"))

    if method == "SRSS":
        return math.sqrt(sum(v ** 2 for v in floats))
    elif method == "ABS":
        return sum(abs(v) for v in floats)
    else:
        raise LimitLoadCascadeError(
            f"Unknown combination method '{method}'; expected 'SRSS' or 'ABS'"
        )


def build_dll_table(root_ll, levels):
    """
    Convenience wrapper: return a list of dicts suitable for reporting.

    Each dict: {'name', 'll', 'dll', 'luf', 'transfer_factor'}.
    Root row is included first with name='root', transfer_factor=None.
    """
    root_ll = _to_float(root_ll, "root_ll")
    rows = [{"name": "root", "ll": root_ll, "dll": None,
             "transfer_factor": None, "luf": None}]
    if not isinstance(levels, list) or len(levels) == 0:
        raise LimitLoadCascadeError("levels must be a non-empty list")
    current_ll = root_ll
    for i, level in enumerate(levels):
        if not isinstance(level, dict):
            raise TypeError(f"levels[{i}] must be a dict")
        for key in ("name", "transfer_factor", "luf"):
            if key not in level:
                raise KeyError(f"levels[{i}] missing required key '{key}'")
        result = propagate_level(current_ll, level["transfer_factor"], level["luf"])
        rows.append({
            "name": level["name"],
            "ll": result["ll"],
            "dll": result["dll"],
            "transfer_factor": level["transfer_factor"],
            "luf": level["luf"],
        })
        current_ll = result["ll"]
    return rows
