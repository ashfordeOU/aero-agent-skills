#!/usr/bin/env python3
"""ECSS-E-ST-10-12C §9.4.1.2 — heavy-ion SEU / MCU / SMU rate prediction.

Paraphrase of the standard's common-knowledge procedure, not a verbatim copy.
Clause anchor: ECSS-E-ST-10-12C §9.4.1.2 (single event upsets from heavy ions).

Implements the deterministic, checkable engineering logic behind the leaf:
  * four-parameter Weibull cross-section versus LET, with a saturation-coverage
    check against the characterization test range,
  * the RPP (rectangular parallelepiped) method — trapezoidal integration of
    sigma(LET) * phi(LET) over the differential LET spectrum,
  * the IRPP chord-length correction — Cauchy mean chord length (4V/A) and the
    isotropic-equivalent effective LET for the sensitive-volume geometry,
  * upset-type categorization (SEU / MCU / SMU) from upset multiplicity,
  * MCU and SMU rate derivation from the SEU rate and the upset fractions,
  * environment-limited screening and the 10x design-margin assessment.

All rates are upsets/device/day. Stdlib only. Offline, deterministic.
"""

import math

SECONDS_PER_DAY = 86400.0

# Standard design-margin factor: the predicted rate must be no greater than
# one-tenth of the requirement.
DEFAULT_MARGIN_FACTOR = 10.0

METHOD_RPP = "RPP"
METHOD_IRPP = "IRPP"
METHODS = (METHOD_RPP, METHOD_IRPP)


class SEUError(ValueError):
    """Invalid input to a heavy-ion SEU rate function."""


# ---------------------------------------------------------------------------
# Cross-section model and fit screening
# ---------------------------------------------------------------------------

def weibull_cross_section(let, let_threshold, width, shape, sigma_sat):
    """Weibull heavy-ion SEU cross-section at a given LET.

    sigma(LET) = 0                                          for LET <= LETth
    sigma(LET) = sigma_sat * (1 - exp(-((LET-LETth)/W)^s))   for LET >  LETth

    ``let`` in MeV·cm²/mg, ``let_threshold`` (LETth) in MeV·cm²/mg (> 0),
    ``width`` (W) in MeV·cm²/mg (> 0), ``shape`` (s) dimensionless (> 0),
    ``sigma_sat`` in cm²/device (> 0).

    The value is never extrapolated above sigma_sat. Raises SEUError on
    invalid parameters.
    """
    if let_threshold <= 0:
        raise SEUError("let_threshold must be > 0 MeV·cm²/mg, got %r"
                       % (let_threshold,))
    if width <= 0:
        raise SEUError("width must be > 0 MeV·cm²/mg, got %r" % (width,))
    if shape <= 0:
        raise SEUError("shape must be > 0, got %r" % (shape,))
    if sigma_sat <= 0:
        raise SEUError("sigma_sat must be > 0 cm²/device, got %r" % (sigma_sat,))
    if let < 0:
        raise SEUError("let must be >= 0 MeV·cm²/mg, got %r" % (let,))
    if let <= let_threshold:
        return 0.0
    sigma = sigma_sat * (1.0 - math.exp(-(((let - let_threshold) / width) ** shape)))
    return min(sigma, sigma_sat)


def saturation_ratio(lets, let_threshold, width, shape, sigma_sat):
    """Fraction of sigma_sat reached at the highest tested LET."""
    if not lets:
        raise SEUError("lets must not be empty")
    top = max(lets)
    return weibull_cross_section(top, let_threshold, width, shape, sigma_sat) / sigma_sat


def check_saturation_coverage(lets, let_threshold, width, shape, sigma_sat,
                              tolerance=0.01):
    """True when the characterization range reaches saturation within tolerance.

    A fit whose test range never approaches sigma_sat leaves sigma_sat
    unconstrained and can produce large high-LET errors, so the workflow
    requires sigma >= (1 - tolerance) * sigma_sat at the highest tested LET.

    Raises SEUError for an empty LET list or a non-positive tolerance.
    """
    if tolerance <= 0:
        raise SEUError("tolerance must be > 0, got %r" % (tolerance,))
    return saturation_ratio(lets, let_threshold, width, shape, sigma_sat) >= (
        1.0 - tolerance
    )


# ---------------------------------------------------------------------------
# Sensitive-volume geometry (RPP / IRPP)
# ---------------------------------------------------------------------------

def cauchy_mean_chord_length(volume_cm3, surface_area_cm2):
    """Cauchy mean chord length of a convex body: 4V/A.

    ``volume_cm3`` > 0 and ``surface_area_cm2`` > 0. Raises SEUError otherwise.
    """
    if volume_cm3 <= 0:
        raise SEUError("volume_cm3 must be > 0, got %r" % (volume_cm3,))
    if surface_area_cm2 <= 0:
        raise SEUError("surface_area_cm2 must be > 0, got %r" % (surface_area_cm2,))
    return 4.0 * volume_cm3 / surface_area_cm2


def rpp_mean_chord_length(x_cm, y_cm, z_cm):
    """Mean chord length of a rectangular parallelepiped of the given sides.

    Computes V = x*y*z and A = 2(xy + yz + zx), then returns 4V/A.

    Raises SEUError for any non-positive side.
    """
    for label, value in (("x_cm", x_cm), ("y_cm", y_cm), ("z_cm", z_cm)):
        if value <= 0:
            raise SEUError("%s must be > 0, got %r" % (label, value))
    volume = x_cm * y_cm * z_cm
    area = 2.0 * (x_cm * y_cm + y_cm * z_cm + z_cm * x_cm)
    return cauchy_mean_chord_length(volume, area)


def irpp_effective_let(let, sensitive_depth_cm, mean_chord_cm):
    """Isotropic-equivalent effective LET used by the IRPP correction.

    LET_eff = LET * (sensitive_depth / mean_chord_length)

    Oblique tracks through the sensitive volume deposit charge over a path
    longer than the nominal depth; scaling the incident LET by the depth-to-
    chord ratio yields the effective LET to evaluate the cross-section at.
    Values below the incident LET cannot arise (an oblique path is never
    shorter than the depth), so the ratio is used directly.

    Raises SEUError for a zero/negative LET, depth, or chord length.
    """
    if let < 0:
        raise SEUError("let must be >= 0 MeV·cm²/mg, got %r" % (let,))
    if sensitive_depth_cm <= 0:
        raise SEUError("sensitive_depth_cm must be > 0, got %r" % (sensitive_depth_cm,))
    if mean_chord_cm <= 0:
        raise SEUError("mean_chord_cm must be > 0, got %r" % (mean_chord_cm,))
    return let * (sensitive_depth_cm / mean_chord_cm)


# ---------------------------------------------------------------------------
# Numerical integration and the RPP / IRPP rate
# ---------------------------------------------------------------------------

def trapezoidal_integration(xs, ys):
    """Composite trapezoidal rule over strictly increasing abscissae.

    Raises SEUError for fewer than two points, mismatched lengths, or a
    non-strictly-increasing abscissa sequence.
    """
    if len(xs) != len(ys):
        raise SEUError("xs and ys must have equal length, got %d and %d"
                       % (len(xs), len(ys)))
    if len(xs) < 2:
        raise SEUError("need at least two points to integrate, got %d" % len(xs))
    total = 0.0
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        if dx <= 0:
            raise SEUError(
                "abscissae must be strictly increasing; got x[%d]=%r then x[%d]=%r"
                % (i, xs[i], i + 1, xs[i + 1])
            )
        total += dx * (ys[i] + ys[i + 1]) / 2.0
    return total


def _spectrum_pairs(let_spectrum):
    """Normalize a LET spectrum to (lets, fluxes) with non-negative flux.

    Accepts a sequence of (LET, flux) pairs or of dicts with 'let'/'flux'.
    Raises SEUError for an empty, malformed, or negative-flux spectrum.
    """
    if not let_spectrum:
        raise SEUError("let_spectrum must not be empty")
    lets = []
    fluxes = []
    for i, point in enumerate(let_spectrum):
        if isinstance(point, dict):
            if "let" not in point or "flux" not in point:
                raise SEUError("let_spectrum point %d must contain 'let' and 'flux'" % i)
            let = point["let"]
            flux = point["flux"]
        else:
            try:
                let, flux = point
            except (TypeError, ValueError):
                raise SEUError(
                    "let_spectrum point %d must be a (let, flux) pair or a dict, got %r"
                    % (i, point)
                )
        if flux < 0:
            raise SEUError("let_spectrum point %d: flux must be >= 0, got %r"
                           % (i, flux))
        lets.append(float(let))
        fluxes.append(float(flux))
    return lets, fluxes


def spectrum_max_let(let_spectrum):
    """Highest LET present in the differential LET spectrum."""
    lets, _ = _spectrum_pairs(let_spectrum)
    return max(lets)


def environment_supports_upset(let_spectrum, let_threshold):
    """True when the spectrum maximum exceeds the device LET threshold.

    When False the device cannot be upset by heavy ions in this environment;
    that is an environment-limited result, not a device result, and the
    predicted rate is exactly zero by physics.
    """
    if let_threshold <= 0:
        raise SEUError("let_threshold must be > 0 MeV·cm²/mg, got %r" % (let_threshold,))
    return spectrum_max_let(let_spectrum) > let_threshold


def rpp_seu_rate(let_spectrum, let_threshold, width, shape, sigma_sat,
                 seconds_per_day=SECONDS_PER_DAY):
    """RPP SEU rate in upsets/device/day.

    Integrates sigma(LET) * phi(LET) over the differential LET spectrum using
    the trapezoidal rule, then converts per-second to per-day. The device
    Weibull parameters are evaluated directly at each spectral LET point.

    Raises SEUError for a malformed spectrum, invalid Weibull parameters, or a
    non-positive seconds_per_day.
    """
    if seconds_per_day <= 0:
        raise SEUError("seconds_per_day must be > 0, got %r" % (seconds_per_day,))
    lets, fluxes = _spectrum_pairs(let_spectrum)
    cross_sections = [
        weibull_cross_section(l, let_threshold, width, shape, sigma_sat) for l in lets
    ]
    rate_per_s = trapezoidal_integration(
        lets, [s * f for s, f in zip(cross_sections, fluxes)]
    )
    return rate_per_s * seconds_per_day


def irpp_seu_rate(let_spectrum, let_threshold, width, shape, sigma_sat,
                  sensitive_depth_cm, mean_chord_cm,
                  seconds_per_day=SECONDS_PER_DAY):
    """IRPP SEU rate in upsets/device/day.

    Applies the chord-length correction to each spectral LET point before
    evaluating the Weibull cross-section, then integrates exactly as the RPP
    method does. Use when the sensitive-volume geometry is well characterized
    or when RPP is judged too optimistic for oblique tracks.

    Raises SEUError for a malformed spectrum, invalid Weibull parameters, an
    invalid volume geometry, or a non-positive seconds_per_day.
    """
    if seconds_per_day <= 0:
        raise SEUError("seconds_per_day must be > 0, got %r" % (seconds_per_day,))
    lets, fluxes = _spectrum_pairs(let_spectrum)
    effective = [
        irpp_effective_let(l, sensitive_depth_cm, mean_chord_cm) for l in lets
    ]
    cross_sections = [
        weibull_cross_section(l, let_threshold, width, shape, sigma_sat)
        for l in effective
    ]
    rate_per_s = trapezoidal_integration(
        lets, [s * f for s, f in zip(cross_sections, fluxes)]
    )
    return rate_per_s * seconds_per_day


# ---------------------------------------------------------------------------
# Upset-type categorization and MCU / SMU derivation
# ---------------------------------------------------------------------------

def categorize_upset_event(bits_affected, bits_per_word, same_word):
    """Categorize one upset event as 'SEU', 'MCU', or 'SMU'.

    bits_affected — number of storage cells flipped by the event (>= 1)
    bits_per_word — cells per logical word of the affected memory (>= 1)
    same_word     — True when every flipped cell belongs to one logical word

    One flipped cell is an SEU. Multiple flipped cells in a single word form an
    SMU (uncorrectable by single-bit EDAC); multiple cells spread over more
    than one word form an MCU.

    Raises SEUError for a non-positive bit count, a non-positive word width, or
    a single-word event claiming more flipped cells than the word holds.
    """
    if bits_affected < 1:
        raise SEUError("bits_affected must be >= 1, got %r" % (bits_affected,))
    if bits_per_word < 1:
        raise SEUError("bits_per_word must be >= 1, got %r" % (bits_per_word,))
    if bits_affected == 1:
        return "SEU"
    if same_word:
        if bits_affected > bits_per_word:
            raise SEUError(
                "single-word event cannot affect %d cells of a %d-cell word"
                % (bits_affected, bits_per_word)
            )
        return "SMU"
    return "MCU"


def derive_mcu_smu_rates(seu_rate, mcu_fraction, smu_fraction):
    """Derive MCU and SMU rates from the SEU rate and the upset fractions.

    MCU rate = SEU rate * mcu_fraction
    SMU rate = MCU rate * smu_fraction

    ``mcu_fraction`` is the fraction of upsets affecting more than one cell;
    ``smu_fraction`` is the fraction of MCU events whose cells share a word.
    For an EDAC-covered memory the SMU rate is the uncorrectable rate and the
    SMU rate, not the total SEU rate, drives the reliability budget.

    Returns a dict with seu_rate, mcu_rate, smu_rate and uncorrectable_rate.

    Raises SEUError for a negative rate or a fraction outside [0, 1].
    """
    if seu_rate < 0:
        raise SEUError("seu_rate must be >= 0 upsets/device/day, got %r" % (seu_rate,))
    for label, fraction in (("mcu_fraction", mcu_fraction),
                            ("smu_fraction", smu_fraction)):
        if fraction < 0 or fraction > 1:
            raise SEUError("%s must lie in [0, 1], got %r" % (label, fraction))
    mcu_rate = seu_rate * mcu_fraction
    smu_rate = mcu_rate * smu_fraction
    return {
        "seu_rate": seu_rate,
        "mcu_rate": mcu_rate,
        "smu_rate": smu_rate,
        "uncorrectable_rate": smu_rate,
    }


# ---------------------------------------------------------------------------
# Design-margin assessment
# ---------------------------------------------------------------------------

def assess_design_margin(predicted_rate, requirement_rate,
                         margin_factor=DEFAULT_MARGIN_FACTOR, rate_label="SEU"):
    """Compare a predicted upset rate against the system requirement.

    A 10x design margin is standard: the predicted rate must be no greater than
    one-tenth of the requirement. Both conditions are reported separately —
    a rate that passes the requirement numerically but carries less than the
    required margin is still flagged.

    ``predicted_rate``   — predicted rate in upsets/device/day (>= 0)
    ``requirement_rate`` — system requirement in upsets/device/day (> 0)
    ``margin_factor``    — required margin factor (> 0), default 10
    ``rate_label``       — which rate is being assessed ('SEU' or 'SMU')

    Returns a dict with rate_label, predicted_rate, requirement_rate,
    margin_factor, margin_ratio, requirement_met, margin_met, compliant, and
    finding (issue 'seu_rate_exceeds_requirement' or 'margin_below_factor',
    None when compliant).

    Raises SEUError for a negative predicted rate, a non-positive requirement,
    or a non-positive margin factor.
    """
    if predicted_rate < 0:
        raise SEUError("predicted_rate must be >= 0 upsets/device/day, got %r"
                       % (predicted_rate,))
    if requirement_rate <= 0:
        raise SEUError("requirement_rate must be > 0 upsets/device/day, got %r"
                       % (requirement_rate,))
    if margin_factor <= 0:
        raise SEUError("margin_factor must be > 0, got %r" % (margin_factor,))

    if predicted_rate == 0:
        margin_ratio = float("inf")
    else:
        margin_ratio = requirement_rate / predicted_rate

    requirement_met = predicted_rate <= requirement_rate
    margin_met = margin_ratio >= margin_factor
    compliant = requirement_met and margin_met

    finding = None
    if not requirement_met:
        finding = {
            "issue": "seu_rate_exceeds_requirement",
            "rate_label": rate_label,
            "predicted_rate": predicted_rate,
            "requirement_rate": requirement_rate,
        }
    elif not margin_met:
        finding = {
            "issue": "margin_below_factor",
            "rate_label": rate_label,
            "predicted_rate": predicted_rate,
            "requirement_rate": requirement_rate,
            "margin_ratio": margin_ratio,
            "margin_factor": margin_factor,
        }

    return {
        "rate_label": rate_label,
        "predicted_rate": predicted_rate,
        "requirement_rate": requirement_rate,
        "margin_factor": margin_factor,
        "margin_ratio": margin_ratio,
        "requirement_met": requirement_met,
        "margin_met": margin_met,
        "compliant": compliant,
        "finding": finding,
    }


# ---------------------------------------------------------------------------
# Whole-device evaluation
# ---------------------------------------------------------------------------

def _require_field(spec, key, device_id):
    value = spec.get(key)
    if value is None:
        raise SEUError("device %r: missing required field %r" % (device_id, key))
    return value


def evaluate_device(device_spec, let_spectrum, method=METHOD_RPP):
    """Full heavy-ion SEU/MCU/SMU evaluation for one device.

    ``device_spec`` keys:
      device_id          — identifier
      weibull            — dict with let_threshold, width, shape, sigma_sat
      mcu_fraction       — fraction of upsets affecting more than one cell [0, 1]
      smu_fraction       — fraction of MCU events sharing one word [0, 1]
      requirement_rate   — system SEU requirement in upsets/device/day (> 0)
      sensitive_volume   — required only for method='IRPP': either
                           {'x_cm','y_cm','z_cm','depth_cm'} or
                           {'volume_cm3','surface_area_cm2','depth_cm'}
      edac               — optional bool; when True the SMU rate, not the SEU
                           rate, is the rate assessed against the requirement
      margin_factor      — optional override of the required margin factor

    ``method`` is 'RPP' (default) or 'IRPP'.

    Returns a dict with device_id, method, environment_limited, seu_rate,
    mcu_rate, smu_rate, uncorrectable_rate, assessed_rate_label,
    assessed_rate, margin, and finding.

    Raises SEUError for an unknown method, a missing Weibull parameter, a
    missing fraction, a missing requirement, or an invalid IRPP geometry.
    """
    if method not in METHODS:
        raise SEUError("method must be one of %s, got %r"
                       % (", ".join(METHODS), method))
    if not isinstance(device_spec, dict):
        raise SEUError("device_spec must be a dict, got %r" % (device_spec,))

    device_id = device_spec.get("device_id", "<unknown>")
    weibull = _require_field(device_spec, "weibull", device_id)
    if not isinstance(weibull, dict):
        raise SEUError("device %r: 'weibull' must be a dict, got %r"
                       % (device_id, weibull))
    params = {}
    for key in ("let_threshold", "width", "shape", "sigma_sat"):
        params[key] = _require_field(weibull, key, device_id)

    mcu_fraction = _require_field(device_spec, "mcu_fraction", device_id)
    smu_fraction = _require_field(device_spec, "smu_fraction", device_id)
    requirement_rate = _require_field(device_spec, "requirement_rate", device_id)

    if not environment_supports_upset(let_spectrum, params["let_threshold"]):
        # Environment-limited result: the spectrum peak does not reach the
        # device threshold, so the predicted rate is zero by physics.
        return {
            "device_id": device_id,
            "method": method,
            "environment_limited": True,
            "seu_rate": 0.0,
            "mcu_rate": 0.0,
            "smu_rate": 0.0,
            "uncorrectable_rate": 0.0,
            "assessed_rate_label": "SMU" if device_spec.get("edac") else "SEU",
            "assessed_rate": 0.0,
            "margin": assess_design_margin(
                0.0, requirement_rate,
                device_spec.get("margin_factor", DEFAULT_MARGIN_FACTOR),
                "SMU" if device_spec.get("edac") else "SEU",
            ),
            "finding": None,
        }

    if method == METHOD_IRPP:
        volume = _require_field(device_spec, "sensitive_volume", device_id)
        if not isinstance(volume, dict):
            raise SEUError("device %r: 'sensitive_volume' must be a dict, got %r"
                           % (device_id, volume))
        depth = _require_field(volume, "depth_cm", device_id)
        if "mean_chord_cm" in volume:
            mean_chord = volume["mean_chord_cm"]
            if mean_chord <= 0:
                raise SEUError("device %r: mean_chord_cm must be > 0, got %r"
                               % (device_id, mean_chord))
        elif all(k in volume for k in ("x_cm", "y_cm", "z_cm")):
            mean_chord = rpp_mean_chord_length(
                volume["x_cm"], volume["y_cm"], volume["z_cm"]
            )
        elif "volume_cm3" in volume and "surface_area_cm2" in volume:
            mean_chord = cauchy_mean_chord_length(
                volume["volume_cm3"], volume["surface_area_cm2"]
            )
        else:
            raise SEUError(
                "device %r: IRPP sensitive_volume needs mean_chord_cm, or "
                "x_cm/y_cm/z_cm, or volume_cm3/surface_area_cm2" % device_id
            )
        seu_rate = irpp_seu_rate(
            let_spectrum, params["let_threshold"], params["width"],
            params["shape"], params["sigma_sat"], depth, mean_chord,
        )
    else:
        seu_rate = rpp_seu_rate(
            let_spectrum, params["let_threshold"], params["width"],
            params["shape"], params["sigma_sat"],
        )

    rates = derive_mcu_smu_rates(seu_rate, mcu_fraction, smu_fraction)

    if device_spec.get("edac"):
        assessed_label = "SMU"
        assessed_rate = rates["smu_rate"]
    else:
        assessed_label = "SEU"
        assessed_rate = rates["seu_rate"]

    margin = assess_design_margin(
        assessed_rate, requirement_rate,
        device_spec.get("margin_factor", DEFAULT_MARGIN_FACTOR),
        assessed_label,
    )

    return {
        "device_id": device_id,
        "method": method,
        "environment_limited": False,
        "seu_rate": rates["seu_rate"],
        "mcu_rate": rates["mcu_rate"],
        "smu_rate": rates["smu_rate"],
        "uncorrectable_rate": rates["uncorrectable_rate"],
        "assessed_rate_label": assessed_label,
        "assessed_rate": assessed_rate,
        "margin": margin,
        "finding": margin["finding"],
    }


def evaluate_all(device_specs, let_spectrum, method=METHOD_RPP):
    """Evaluate a sequence of device records against one LET spectrum.

    Returns results in input order. Raises SEUError on the first invalid record.
    """
    return [evaluate_device(spec, let_spectrum, method) for spec in device_specs]


def seu_findings(results):
    """Findings from an evaluate_all result list (empty means all devices pass)."""
    return [r["finding"] for r in results if r["finding"] is not None]
