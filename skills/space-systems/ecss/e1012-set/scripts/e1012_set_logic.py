#!/usr/bin/env python3
"""ECSS-E-ST-10C §9.4.1.7 — single event transient (SET) rate prediction.

Paraphrase of the standard's common-knowledge procedure, not a verbatim copy.
Clause anchor: ECSS-E-ST-10C §9.4.1.7 (prediction of SET rates).

Implements the deterministic, checkable engineering logic behind the leaf:
  * four-parameter Weibull cross-section evaluation for heavy ions,
  * trapezoidal integration of the cross-section over the differential
    heavy-ion LET spectrum,
  * threshold/step-function cross-section integration over the differential
    proton energy spectrum,
  * the neutron rate formula R = sigma_n * flux_n * 86400,
  * summation of the three particle-family contributions into a total rate,
  * budget-compliance checking against a system-level SET rate budget,
    including the requirement-capture gap when no budget is on record.

All rates are in events/device/day. Stdlib only. Offline, deterministic.
"""

import math

SECONDS_PER_DAY = 86400.0

HEAVY_ION = "heavy_ion"
PROTON = "proton"
NEUTRON = "neutron"
PARTICLE_FAMILIES = (HEAVY_ION, PROTON, NEUTRON)


class SETError(ValueError):
    """Invalid input to a SET rate function."""


# ---------------------------------------------------------------------------
# Cross-section models
# ---------------------------------------------------------------------------

def weibull_cross_section(let, let_threshold, sigma_sat, width, shape):
    """Four-parameter Weibull heavy-ion SET cross-section at a given LET.

    sigma(LET) = 0                                        for LET <= L_th
    sigma(LET) = sigma_sat * (1 - exp(-((LET-L_th)/W)^s))  for LET >  L_th

    Parameters
    ----------
    let            — linear energy transfer in MeV·cm²/mg (>= 0)
    let_threshold  — LET threshold L_th in MeV·cm²/mg (> 0)
    sigma_sat      — saturation cross-section in cm²/device (> 0)
    width          — Weibull width parameter W in MeV·cm²/mg (> 0)
    shape          — Weibull shape exponent s (> 0)

    The result never exceeds sigma_sat. Raises SETError on invalid parameters.
    """
    if let_threshold <= 0:
        raise SETError("let_threshold must be > 0 MeV·cm²/mg, got %r" % (let_threshold,))
    if sigma_sat <= 0:
        raise SETError("sigma_sat must be > 0 cm²/device, got %r" % (sigma_sat,))
    if width <= 0:
        raise SETError("width must be > 0 MeV·cm²/mg, got %r" % (width,))
    if shape <= 0:
        raise SETError("shape must be > 0, got %r" % (shape,))
    if let < 0:
        raise SETError("let must be >= 0 MeV·cm²/mg, got %r" % (let,))
    if let <= let_threshold:
        return 0.0
    exponent = -(((let - let_threshold) / width) ** shape)
    sigma = sigma_sat * (1.0 - math.exp(exponent))
    if sigma > sigma_sat:
        sigma = sigma_sat
    return sigma


def proton_cross_section(energy, energy_threshold, sigma_sat):
    """Threshold/step proton SET cross-section.

    sigma(E) = sigma_sat for E >= E_th, else 0. Direct ionization by protons
    below the device reaction threshold is negligible and must be zeroed.

    Raises SETError on invalid parameters.
    """
    if energy_threshold <= 0:
        raise SETError(
            "energy_threshold must be > 0 MeV, got %r" % (energy_threshold,)
        )
    if sigma_sat <= 0:
        raise SETError("sigma_sat must be > 0 cm²/device, got %r" % (sigma_sat,))
    if energy < 0:
        raise SETError("energy must be >= 0 MeV, got %r" % (energy,))
    if energy < energy_threshold:
        return 0.0
    return sigma_sat


# ---------------------------------------------------------------------------
# Numerical integration
# ---------------------------------------------------------------------------

def trapezoidal_integration(xs, ys):
    """Composite trapezoidal rule over strictly increasing abscissae.

    Returns sum over segments of (x[i+1]-x[i]) * (y[i]+y[i+1]) / 2.

    Raises SETError for fewer than two points, mismatched lengths, or a
    non-strictly-increasing abscissa sequence.
    """
    if len(xs) != len(ys):
        raise SETError(
            "xs and ys must have equal length, got %d and %d" % (len(xs), len(ys))
        )
    if len(xs) < 2:
        raise SETError("need at least two points to integrate, got %d" % len(xs))
    total = 0.0
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        if dx <= 0:
            raise SETError(
                "abscissae must be strictly increasing; got x[%d]=%r then x[%d]=%r"
                % (i, xs[i], i + 1, xs[i + 1])
            )
        total += dx * (ys[i] + ys[i + 1]) / 2.0
    return total


def _spectrum_pairs(spectrum, x_key, y_key):
    """Normalize a spectrum into (xs, ys) with non-negative ordinates.

    Accepts a sequence of (x, y) pairs or of dicts carrying ``x_key``/``y_key``.
    Raises SETError for a malformed or negative-flux spectrum.
    """
    if not spectrum:
        raise SETError("spectrum must not be empty")
    xs = []
    ys = []
    for i, point in enumerate(spectrum):
        if isinstance(point, dict):
            if x_key not in point or y_key not in point:
                raise SETError(
                    "spectrum point %d must contain %r and %r" % (i, x_key, y_key)
                )
            x = point[x_key]
            y = point[y_key]
        else:
            try:
                x, y = point
            except (TypeError, ValueError):
                raise SETError(
                    "spectrum point %d must be a (x, y) pair or a dict, got %r"
                    % (i, point)
                )
        if y < 0:
            raise SETError(
                "spectrum point %d: flux must be >= 0, got %r — a negative flux is "
                "a data error, not a conservative choice" % (i, y)
            )
        xs.append(float(x))
        ys.append(float(y))
    return xs, ys


# ---------------------------------------------------------------------------
# Per-family rate computation
# ---------------------------------------------------------------------------

def heavy_ion_set_rate(let_spectrum, weibull_params, seconds_per_day=SECONDS_PER_DAY):
    """Heavy-ion SET rate in events/device/day.

    Evaluates the Weibull cross-section at each spectral LET point, integrates
    sigma(LET) * phi(LET) over the differential LET spectrum with the
    trapezoidal rule, then converts per-second to per-day.

    ``let_spectrum`` — sequence of (LET, flux) pairs; flux in
        particles/(cm²·s·MeV·cm²/mg), LET in MeV·cm²/mg.
    ``weibull_params`` — dict with keys let_threshold, sigma_sat, width, shape.

    Raises SETError on a malformed spectrum, missing Weibull parameter, or
    non-positive seconds_per_day.
    """
    if seconds_per_day <= 0:
        raise SETError("seconds_per_day must be > 0, got %r" % (seconds_per_day,))
    params = _require_weibull_params(weibull_params)
    xs, ys = _spectrum_pairs(let_spectrum, "let", "flux")
    sigma = [
        weibull_cross_section(x, params["let_threshold"], params["sigma_sat"],
                              params["width"], params["shape"])
        for x in xs
    ]
    rate_per_s = trapezoidal_integration(xs, [s * f for s, f in zip(sigma, ys)])
    return rate_per_s * seconds_per_day


def proton_set_rate(proton_spectrum, energy_threshold, sigma_sat,
                    seconds_per_day=SECONDS_PER_DAY):
    """Proton SET rate in events/device/day via the threshold cross-section model.

    Integrates sigma(E) * phi(E) over the differential proton energy spectrum
    with the trapezoidal rule and converts to per-day.

    ``proton_spectrum`` — sequence of (energy, flux) pairs; energy in MeV,
        flux in particles/(cm²·s·MeV).

    Raises SETError on a malformed spectrum or invalid model parameters.
    """
    if seconds_per_day <= 0:
        raise SETError("seconds_per_day must be > 0, got %r" % (seconds_per_day,))
    xs, ys = _spectrum_pairs(proton_spectrum, "energy", "flux")
    sigma = [proton_cross_section(x, energy_threshold, sigma_sat) for x in xs]
    rate_per_s = trapezoidal_integration(xs, [s * f for s, f in zip(sigma, ys)])
    return rate_per_s * seconds_per_day


def neutron_set_rate(sigma_n, neutron_flux, seconds_per_day=SECONDS_PER_DAY):
    """Neutron SET rate: R_n = sigma_n * phi_n * 86400 (events/device/day).

    ``sigma_n``      — effective neutron cross-section in cm²/device (> 0)
    ``neutron_flux`` — total neutron flux in particles/(cm²·s) (>= 0)

    Raises SETError for a non-positive cross-section, a negative flux, or a
    non-positive conversion factor.
    """
    if sigma_n <= 0:
        raise SETError("sigma_n must be > 0 cm²/device, got %r" % (sigma_n,))
    if neutron_flux < 0:
        raise SETError("neutron_flux must be >= 0 particles/(cm²·s), got %r"
                       % (neutron_flux,))
    if seconds_per_day <= 0:
        raise SETError("seconds_per_day must be > 0, got %r" % (seconds_per_day,))
    return sigma_n * neutron_flux * seconds_per_day


def total_set_rate(heavy_ion_rate, proton_rate, neutron_rate):
    """Sum the three particle-family contributions into a total SET rate.

    All three contributions must already be on the same per-day basis.

    Raises SETError for any negative contribution.
    """
    for label, value in (("heavy_ion_rate", heavy_ion_rate),
                         ("proton_rate", proton_rate),
                         ("neutron_rate", neutron_rate)):
        if value < 0:
            raise SETError("%s must be >= 0 events/device/day, got %r"
                           % (label, value))
    return heavy_ion_rate + proton_rate + neutron_rate


# ---------------------------------------------------------------------------
# Budget compliance
# ---------------------------------------------------------------------------

def check_set_budget(device_id, total_rate, budget_rate):
    """Compare a total SET rate against the device's allowable rate budget.

    ``budget_rate`` of None means no budget is on record. That is not a pass:
    an absent budget is a requirement-capture gap and is reported as a finding.

    Returns a dict with keys device_id, total_rate, budget_rate, compliant,
    exceedance, finding. Findings carry an ``issue`` key of either
    'set_rate_budget_exceeded' or 'budget_not_captured'.

    Raises SETError for a negative total rate or a non-positive budget.
    """
    if total_rate < 0:
        raise SETError("total_rate must be >= 0 events/device/day, got %r"
                       % (total_rate,))
    if budget_rate is None:
        return {
            "device_id": device_id,
            "total_rate": total_rate,
            "budget_rate": None,
            "compliant": False,
            "exceedance": None,
            "finding": {
                "issue": "budget_not_captured",
                "device_id": device_id,
                "total_rate": total_rate,
            },
        }
    if budget_rate <= 0:
        raise SETError("budget_rate must be > 0 events/device/day when supplied, "
                       "got %r" % (budget_rate,))
    exceedance = total_rate - budget_rate
    compliant = total_rate <= budget_rate
    finding = None
    if not compliant:
        finding = {
            "issue": "set_rate_budget_exceeded",
            "device_id": device_id,
            "total_rate": total_rate,
            "budget_rate": budget_rate,
            "exceedance": exceedance,
        }
    return {
        "device_id": device_id,
        "total_rate": total_rate,
        "budget_rate": budget_rate,
        "compliant": compliant,
        "exceedance": exceedance,
        "finding": finding,
    }


# ---------------------------------------------------------------------------
# Whole-device evaluation
# ---------------------------------------------------------------------------

def _require_weibull_params(weibull_params):
    """Validate a four-parameter Weibull parameter dict."""
    if not isinstance(weibull_params, dict):
        raise SETError("weibull_params must be a dict, got %r" % (weibull_params,))
    required = ("let_threshold", "sigma_sat", "width", "shape")
    for key in required:
        if weibull_params.get(key) is None:
            raise SETError(
                "heavy-ion device record missing required Weibull parameter %r" % key
            )
    return {
        "let_threshold": float(weibull_params["let_threshold"]),
        "sigma_sat": float(weibull_params["sigma_sat"]),
        "width": float(weibull_params["width"]),
        "shape": float(weibull_params["shape"]),
    }


def _require_section(device_spec, family):
    """Return the cross-section parameter dict for one particle family."""
    section = device_spec.get(family)
    if section is None:
        raise SETError(
            "device %r missing required %s cross-section record"
            % (device_spec.get("device_id", "<unknown>"), family)
        )
    if not isinstance(section, dict):
        raise SETError("device %s record must be a dict, got %r" % (family, section))
    return section


def evaluate_device(device_spec, environment):
    """Full SET rate evaluation for one device against one mission environment.

    ``device_spec`` keys:
      device_id  — identifier
      heavy_ion  — dict with let_threshold, sigma_sat, width, shape
      proton     — dict with energy_threshold, sigma_sat
      neutron    — dict with sigma_n
      set_budget — optional allowable SET rate in events/device/day; None or
                   absent means no budget on record

    ``environment`` keys:
      let_spectrum    — (LET, flux) pairs, particles/(cm²·s·MeV·cm²/mg)
      proton_spectrum — (energy, flux) pairs, particles/(cm²·s·MeV)
      neutron_flux    — total neutron flux in particles/(cm²·s)

    A device record missing any of the three cross-section records is rejected
    before it enters the rate calculation. Returns a result dict carrying each
    family rate, the total rate, and the budget-compliance result.
    """
    if not isinstance(device_spec, dict):
        raise SETError("device_spec must be a dict, got %r" % (device_spec,))
    if not isinstance(environment, dict):
        raise SETError("environment must be a dict, got %r" % (environment,))

    device_id = device_spec.get("device_id", "<unknown>")

    heavy_ion_params = _require_weibull_params(_require_section(device_spec, HEAVY_ION))
    proton_params = _require_section(device_spec, PROTON)
    neutron_params = _require_section(device_spec, NEUTRON)

    if environment.get("let_spectrum") is None:
        raise SETError("environment missing required 'let_spectrum'")
    if environment.get("proton_spectrum") is None:
        raise SETError("environment missing required 'proton_spectrum'")
    if environment.get("neutron_flux") is None:
        raise SETError("environment missing required 'neutron_flux'")

    if proton_params.get("energy_threshold") is None:
        raise SETError("device %r: proton record missing 'energy_threshold'" % device_id)
    if proton_params.get("sigma_sat") is None:
        raise SETError("device %r: proton record missing 'sigma_sat'" % device_id)
    if neutron_params.get("sigma_n") is None:
        raise SETError("device %r: neutron record missing 'sigma_n'" % device_id)

    hi_rate = heavy_ion_set_rate(environment["let_spectrum"], heavy_ion_params)
    p_rate = proton_set_rate(environment["proton_spectrum"],
                             proton_params["energy_threshold"],
                             proton_params["sigma_sat"])
    n_rate = neutron_set_rate(neutron_params["sigma_n"], environment["neutron_flux"])
    total = total_set_rate(hi_rate, p_rate, n_rate)
    budget = check_set_budget(device_id, total, device_spec.get("set_budget"))

    return {
        "device_id": device_id,
        "heavy_ion_rate": hi_rate,
        "proton_rate": p_rate,
        "neutron_rate": n_rate,
        "total_rate": total,
        "budget_rate": budget["budget_rate"],
        "compliant": budget["compliant"],
        "finding": budget["finding"],
    }


def evaluate_all(device_specs, environment):
    """Evaluate a sequence of device records against one environment.

    Returns a list of results in input order. Raises SETError on the first
    invalid device record.
    """
    return [evaluate_device(spec, environment) for spec in device_specs]


def set_findings(results):
    """Findings from an evaluate_all result list (empty means all devices pass)."""
    return [r["finding"] for r in results if not r["compliant"]]
