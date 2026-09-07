#!/usr/bin/env python3
"""Walker-Forman crack growth logic: stress-ratio-affected fatigue crack
growth rates in the linear-elastic fracture mechanics domain (paraphrase,
common engineering knowledge, summary only).

UNITS CONVENTION (single convention, inherited from the crack-growth
sibling of this pack):
  sigma       in MPa
  a           in meters (single half-crack length of a through-thickness
              crack in a wide panel, geometry factor Y constant)
  K, dK, K_c  in MPa*sqrt(m)
  C           in (m/cycle) * (MPa*sqrt(m))^-m    Walker/Paris arm constant
  C_F         in (m/cycle) * (MPa*sqrt(m))^(1-m) Forman arm constant
  da/dN       in m/cycle

The applied cycle is pinned by sigma_max and the stress ratio
R = sigma_min/sigma_max = K_min/K_max in [-1, 1) with
sigma_min = R*sigma_max and the range dsigma = sigma_max*(1 - R); no R = 0
clamp, the pinned formulas stay defined down to R = -1. Model relations:

  K       = y * sigma * sqrt(pi * a)             mode I stress intensity
  dK(a)   = y * dsigma * sqrt(pi * a) = K_max*(1 - R), K_max = y*sigma_max*sqrt(pi*a)
  Walker equivalent range (Walker 1970, ASTM STP 462):
      dK_bar = dK / (1 - R)^(1 - gamma), gamma in (0, 1]; R = 0 or gamma = 1
      recovers dK (no correction); da/dN = C * dK_bar^m
  Forman rate (Forman, Kearney, Engle 1967, ASME J. Basic Engineering):
      da/dN = C_F * dK^m / ((1 - R)*K_c - dK), undefined at dK = (1 - R)*K_c
      (peak K = K_c, the fracture state); terminal acceleration as the
      denominator approaches zero
  Paris baseline (comparison denominator only, never a growth projection):
      C * dK^m, the R = 0, K_c-infinite limit of both arms
  block extension: forward-Euler substeps of 1.0 cycle when cycles <= 5000
      (else 5000 equal substeps), dK re-evaluated from the growing crack
      at every substep; the walker-versus-paris and forman-versus-paris
      ratios compare each arm against the Paris baseline.

The FAR-25.571 damage tolerance basis of transport aeroplanes (far-25,
cs-25, reference-only in standards-map.yaml) frames the certification
context of the rates by name only, never reproduced here.
"""

import math


def stress_intensity(sigma_mpa, a_m, y):
    """Mode I stress intensity K = y * sigma * sqrt(pi * a).

    sigma in MPa, a in meters, y dimensionless; returns K in MPa*sqrt(m).
    ValueError: sigma <= 0, a <= 0, or y <= 0.
    """
    if sigma_mpa <= 0:
        raise ValueError("stress must be > 0, got %r" % (sigma_mpa,))
    if a_m <= 0:
        raise ValueError("crack length must be > 0, got %r" % (a_m,))
    if y <= 0:
        raise ValueError("geometry factor must be > 0, got %r" % (y,))
    return y * sigma_mpa * math.sqrt(math.pi * a_m)


def walker_equivalent_range(dk_mpa, r, gamma):
    """Walker equivalent stress intensity range dK_bar = dK/(1-R)^(1-gamma).

    dK in MPa*sqrt(m); returns dK_bar in MPa*sqrt(m). R = K_min/K_max in
    [-1, 1): R = 0 recovers dK (1-R = 1), gamma = 1 recovers dK (no
    correction). ValueError: dk <= 0; r >= 1 or r < -1; gamma <= 0 or
    gamma > 1.
    """
    if dk_mpa <= 0:
        raise ValueError("stress intensity range must be > 0, got %r" % (dk_mpa,))
    if r >= 1.0:
        raise ValueError("stress ratio must be < 1, got %r" % (r,))
    if r < -1.0:
        raise ValueError("stress ratio must be >= -1, got %r" % (r,))
    if gamma <= 0.0 or gamma > 1.0:
        raise ValueError("Walker exponent must be in (0, 1], got %r" % (gamma,))
    return dk_mpa / (1.0 - r) ** (1.0 - gamma)


def walker_dadN(dk_mpa, r, gamma, c, m):
    """Walker rate da/dN = C * (dK_bar)^m with dK_bar the Walker equivalent
    range; C in (m/cycle)*(MPa*sqrt(m))^-m, dK in MPa*sqrt(m); returns
    da/dN in m/cycle. ValueErrors propagate (domain checks of the range
    function plus c <= 0, m <= 0).
    """
    if c <= 0:
        raise ValueError("rate constant C must be > 0, got %r" % (c,))
    if m <= 0:
        raise ValueError("exponent m must be > 0, got %r" % (m,))
    dk_bar = walker_equivalent_range(dk_mpa, r, gamma)
    return c * dk_bar ** m


def forman_dadN(dk_mpa, r, kc_mpa, c_forman, m):
    """Forman rate da/dN = C_F * (dK)^m / ((1-R)*K_c - dK).

    C_F in (m/cycle)*(MPa*sqrt(m))^(1-m), dK and K_c in MPa*sqrt(m);
    returns da/dN in m/cycle. ValueError: dk <= 0; r out of [-1, 1);
    kc <= 0; c_forman <= 0; m <= 0; dk >= (1-r)*K_c (peak K at or beyond
    K_c, the rate singularity: fracture state, out of this leaf).
    """
    if dk_mpa <= 0:
        raise ValueError("stress intensity range must be > 0, got %r" % (dk_mpa,))
    if r >= 1.0:
        raise ValueError("stress ratio must be < 1, got %r" % (r,))
    if r < -1.0:
        raise ValueError("stress ratio must be >= -1, got %r" % (r,))
    if kc_mpa <= 0:
        raise ValueError("fracture toughness K_c must be > 0, got %r" % (kc_mpa,))
    if c_forman <= 0:
        raise ValueError("Forman constant must be > 0, got %r" % (c_forman,))
    if m <= 0:
        raise ValueError("exponent m must be > 0, got %r" % (m,))
    denom = (1.0 - r) * kc_mpa - dk_mpa
    if denom <= 0.0:
        raise ValueError(
            "peak stress intensity at or beyond K_c (dK >= (1-R)*K_c): "
            "fracture state, out of the growth-rate domain")
    return c_forman * dk_mpa ** m / denom


def walker_vs_paris_ratio(dk_mpa, r, gamma, c, m):
    """Walker rate over the R = 0 Paris baseline C*dK^m at the same (C, m);
    equals (1-R)^(m*(gamma-1)) to roundoff. ValueErrors propagate.
    """
    baseline = c * dk_mpa ** m
    return walker_dadN(dk_mpa, r, gamma, c, m) / baseline


def forman_vs_paris_ratio(dk_mpa, r, kc_mpa, c_forman, c, m):
    """Forman rate over the R = 0 Paris baseline C*dK^m at the same (C, m);
    equals (C_F/C)/((1-R)*K_c - dK) to roundoff. ValueErrors propagate.
    """
    baseline = c * dk_mpa ** m
    return forman_dadN(dk_mpa, r, kc_mpa, c_forman, m) / baseline


def _require_cycle_count(cycles):
    """Validate an integer cycle count >= 1, returning it as an int.

    Non-integer or non-positive cycles raise ValueError. Integral float
    values (for example 2000.0) are accepted and converted.
    """
    if isinstance(cycles, bool) or not isinstance(cycles, (int, float)):
        raise ValueError("cycles must be an integer >= 1, got %r" % (cycles,))
    if isinstance(cycles, float) and not cycles.is_integer():
        raise ValueError("cycles must be an integer >= 1, got %r" % (cycles,))
    n = int(cycles)
    if n < 1:
        raise ValueError("cycles must be >= 1, got %r" % (cycles,))
    return n


def _advance(cycles, sigma_max_mpa, r, a0_m, y, model, gamma, kc_mpa,
             c, c_forman, m, stations):
    """Forward-Euler substep march shared by block_extension and
    piecewise_block_extension. Returns (a_final, rows) where rows holds one
    dict per station cycle: keys cycle, a_m, dk_mpa, dk_bar_mpa, rate.
    Substep is exactly 1.0 cycle when cycles <= 5000, else 5000 equal
    substeps. dK is re-evaluated from the growing crack at every substep.
    """
    n = _require_cycle_count(cycles)
    if model not in ("walker", "forman"):
        raise ValueError("model must be 'walker' or 'forman', got %r" % (model,))
    if sigma_max_mpa <= 0:
        raise ValueError("sigma_max must be > 0, got %r" % (sigma_max_mpa,))
    if a0_m <= 0:
        raise ValueError("initial crack length must be > 0, got %r" % (a0_m,))
    if r >= 1.0:
        raise ValueError("stress ratio must be < 1, got %r" % (r,))
    if r < -1.0:
        raise ValueError("stress ratio must be >= -1, got %r" % (r,))
    if gamma <= 0.0 or gamma > 1.0:
        raise ValueError("Walker exponent must be in (0, 1], got %r" % (gamma,))
    n_steps = n if n <= 5000 else 5000
    step = float(n) / float(n_steps)
    a = a0_m
    dsigma = sigma_max_mpa * (1.0 - r)
    rows = []
    sta = list(stations)
    si = 0
    cyc = 0.0
    if si < len(sta) and abs(cyc - sta[si]) < 1e-9 * max(1.0, abs(sta[si])):
        dk = y * dsigma * math.sqrt(math.pi * a)
        rows.append(_row(cyc, a, dk, r, gamma, model, kc_mpa, c, c_forman, m))
        si += 1
    for _ in range(n_steps):
        dk = y * dsigma * math.sqrt(math.pi * a)
        if model == "forman":
            denom = (1.0 - r) * kc_mpa - dk
            if denom <= 0.0:
                raise ValueError(
                    "peak stress intensity reaches K_c during the block at "
                    "cycle %.1f: fracture state reached, rate model invalid"
                    % (cyc,))
            rate = c_forman * dk ** m / denom
        else:
            dk_bar = dk / (1.0 - r) ** (1.0 - gamma)
            rate = c * dk_bar ** m
        a += rate * step
        cyc += step
        if si < len(sta) and abs(cyc - sta[si]) < 1e-9 * max(1.0, abs(sta[si])):
            dk = y * dsigma * math.sqrt(math.pi * a)
            rows.append(_row(cyc, a, dk, r, gamma, model, kc_mpa, c, c_forman, m))
            si += 1
    return a, rows


def _row(cyc, a, dk, r, gamma, model, kc_mpa, c, c_forman, m):
    dk_bar = dk / (1.0 - r) ** (1.0 - gamma)
    if model == "forman":
        rate = c_forman * dk ** m / ((1.0 - r) * kc_mpa - dk)
    else:
        rate = c * dk_bar ** m
    return {"cycle": cyc, "a_m": a, "dk_mpa": dk, "dk_bar_mpa": dk_bar,
            "rate": rate}


def block_extension(cycles, sigma_max_mpa, r, a0_m, y, model, gamma, kc_mpa,
                    c, c_forman, m):
    """Crack extension over a cycle block at constant stress ratio R.

    Returns a dict with keys: a0_m, a_final_m, extension_m, rate_start,
    rate_final, dk_start_mpa, dk_final_mpa, dk_bar_start_mpa and rows
    (list of station dicts at cycles 0, N/4, N/2, 3N/4, N). ValueErrors
    as in _advance plus the forman singularity guard during the march.
    """
    n = _require_cycle_count(cycles)
    if model not in ("walker", "forman"):
        raise ValueError("model must be 'walker' or 'forman', got %r" % (model,))
    if sigma_max_mpa <= 0:
        raise ValueError("sigma_max must be > 0, got %r" % (sigma_max_mpa,))
    if a0_m <= 0:
        raise ValueError("initial crack length must be > 0, got %r" % (a0_m,))
    if y <= 0:
        raise ValueError("geometry factor must be > 0, got %r" % (y,))
    if r >= 1.0:
        raise ValueError("stress ratio must be < 1, got %r" % (r,))
    if r < -1.0:
        raise ValueError("stress ratio must be >= -1, got %r" % (r,))
    if gamma <= 0.0 or gamma > 1.0:
        raise ValueError("Walker exponent must be in (0, 1], got %r" % (gamma,))
    stations = [0.0, float(n) / 4.0, float(n) / 2.0,
                3.0 * float(n) / 4.0, float(n)]
    a_start = a0_m
    dsigma = sigma_max_mpa * (1.0 - r)
    dk_start = y * dsigma * math.sqrt(math.pi * a_start)
    dk_bar_start = dk_start / (1.0 - r) ** (1.0 - gamma)
    if model == "forman":
        if (1.0 - r) * kc_mpa - dk_start <= 0.0:
            raise ValueError(
                "initial crack at or beyond the Forman singularity "
                "(peak K >= K_c)")
        rate_start = c_forman * dk_start ** m / ((1.0 - r) * kc_mpa - dk_start)
    else:
        rate_start = c * dk_bar_start ** m
    a_final, rows = _advance(n, sigma_max_mpa, r, a0_m, y, model, gamma,
                             kc_mpa, c, c_forman, m, stations)
    dk_final = y * dsigma * math.sqrt(math.pi * a_final)
    if model == "forman":
        rate_final = c_forman * dk_final ** m / ((1.0 - r) * kc_mpa - dk_final)
    else:
        dk_bar_final = dk_final / (1.0 - r) ** (1.0 - gamma)
        rate_final = c * dk_bar_final ** m
    return {"a0_m": a_start, "a_final_m": a_final,
            "extension_m": a_final - a_start, "rate_start": rate_start,
            "rate_final": rate_final, "dk_start_mpa": dk_start,
            "dk_final_mpa": dk_final, "dk_bar_start_mpa": dk_bar_start,
            "rows": rows}


def piecewise_block_extension(segments, a0_m, y, model, gamma, kc_mpa,
                              c, c_forman, m):
    """Crack extension over a piecewise-R block: segments is a list of
    (cycles, sigma_max_mpa, r) tuples applied in order, each segment run by
    the same substep march as block_extension starting from the previous
    segment's final crack length. Returns a dict with keys a0_m,
    a_final_m, extension_m, and segments (list of per-segment dicts with
    keys cycles, r, sigma_max_mpa, a0_m, a_final_m, extension_m,
    rate_start, rate_final). A two-segment split of one constant-R block
    reproduces the single block bit for bit. ValueErrors as block_extension.
    """
    if not segments:
        raise ValueError("segments must not be empty")
    if model not in ("walker", "forman"):
        raise ValueError("model must be 'walker' or 'forman', got %r" % (model,))
    a = a0_m
    seg_out = []
    for (cycles, sigma_max_mpa, r) in segments:
        n = _require_cycle_count(cycles)
        stations = [0.0, float(n) / 4.0, float(n) / 2.0,
                    3.0 * float(n) / 4.0, float(n)]
        dsigma = sigma_max_mpa * (1.0 - r)
        dk0 = y * dsigma * math.sqrt(math.pi * a)
        if model == "forman":
            if (1.0 - r) * kc_mpa - dk0 <= 0.0:
                raise ValueError("segment starts at or beyond the Forman "
                                 "singularity (peak K >= K_c)")
            rate0 = forman_dadN(dk0, r, kc_mpa, c_forman, m)
        else:
            rate0 = walker_dadN(dk0, r, gamma, c, m)
        a_end, _rows = _advance(n, sigma_max_mpa, r, a, y, model, gamma,
                                kc_mpa, c, c_forman, m, stations)
        dk_end = y * dsigma * math.sqrt(math.pi * a_end)
        if model == "forman":
            rate_end = forman_dadN(dk_end, r, kc_mpa, c_forman, m)
        else:
            rate_end = walker_dadN(dk_end, r, gamma, c, m)
        seg_out.append({"cycles": n, "r": r, "sigma_max_mpa": sigma_max_mpa,
                        "a0_m": a, "a_final_m": a_end,
                        "extension_m": a_end - a, "rate_start": rate0,
                        "rate_final": rate_end})
        a = a_end
    return {"a0_m": a0_m, "a_final_m": a, "extension_m": a - a0_m,
            "segments": seg_out}
