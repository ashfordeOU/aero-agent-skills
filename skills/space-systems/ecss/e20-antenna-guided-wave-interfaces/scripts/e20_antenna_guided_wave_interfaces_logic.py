"""Guided-wave interfaces on a spacecraft antenna port.

Anchor: ECSS-E-ST-20C clause 7.2.3.1 (power handling and impedance match at
connectors or waveguide flanges on antenna ports). Paraphrased into an
implementable procedure; no standard text is reproduced.

Offline, deterministic, stdlib only. The module turns a declared antenna
port into:

  * an interface category (coaxial-connector or waveguide-flange),
  * the mismatch figures derived from the voltage-standing-wave-ratio,
  * a moding check against the waveguide cutoff band or the coaxial
    higher-order-mode onset and characteristic-impedance tolerance,
  * a derated rf-power rating and the resulting power-handling-margin,
  * a finding list judged against the declared allowables.
"""

import math

SPEED_OF_LIGHT_M_S = 299792458.0

#: Absolute tolerance applied when a computed decibel or ratio figure meets a
#: declared limit exactly. Such a figure is a difference of logarithms and can
#: land a few ULPs on the wrong side of a limit it physically satisfies; the
#: engineering limit itself is never widened.
LIMIT_TOLERANCE = 1e-9

#: Return loss reported for a perfectly matched port (log10(0) has no value).
IDEAL_RETURN_LOSS_DB = 300.0

#: Usable single-mode band of a rectangular waveguide, expressed as multiples
#: of the dominant-mode cutoff: above the cutoff the guide is dispersive, and
#: below the first higher-order cutoff there is a practical guard band.
WAVEGUIDE_BAND_LOWER_FACTOR = 1.25
WAVEGUIDE_BAND_UPPER_FACTOR = 1.90

COAXIAL_NOMINAL_IMPEDANCE_OHM = 50.0
DEFAULT_IMPEDANCE_TOLERANCE_OHM = 2.0
DEFAULT_REQUIRED_POWER_MARGIN_DB = 3.0

COAXIAL_ALIASES = {
    "coaxial-connector", "coaxial", "coax", "sma", "smp", "smk",
    "tnc", "n-type", "type-n",
}
WAVEGUIDE_ALIASES = {
    "waveguide-flange", "waveguide", "flange", "wr-90", "wr90", "ubr", "cpr",
}


def _positive(value, label):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _within_limit(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def _at_least(value, limit):
    """True when value reaches limit, absorbing representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def categorize_port_interface(interface):
    """Reduce a declared interface name to its guided-wave category."""
    if not isinstance(interface, str):
        raise ValueError("interface must be a string, got %r" % (interface,))
    key = interface.strip().lower()
    if key in COAXIAL_ALIASES:
        return "coaxial-connector"
    if key in WAVEGUIDE_ALIASES:
        return "waveguide-flange"
    raise ValueError(
        "uncategorized interface %r; declare a coaxial-connector or a "
        "waveguide-flange" % (interface,)
    )


def reflection_coefficient_from_vswr(vswr):
    """Magnitude of the reflection coefficient for a given standing-wave ratio."""
    s = float(vswr)
    if not math.isfinite(s) or s < 1.0:
        raise ValueError("vswr must be a finite value >= 1, got %r" % (vswr,))
    return (s - 1.0) / (s + 1.0)


def vswr_from_reflection_coefficient(gamma):
    """Standing-wave ratio implied by a reflection-coefficient magnitude."""
    g = float(gamma)
    if not 0.0 <= g < 1.0:
        raise ValueError("gamma must lie in [0, 1), got %r" % (gamma,))
    return (1.0 + g) / (1.0 - g)


def return_loss_db(vswr):
    """Return loss of the interface, positive decibels."""
    gamma = reflection_coefficient_from_vswr(vswr)
    if gamma <= 0.0:
        return IDEAL_RETURN_LOSS_DB
    return -20.0 * math.log10(gamma)


def mismatch_loss_db(vswr):
    """Transmitted-power loss caused by the reflection, positive decibels."""
    gamma = reflection_coefficient_from_vswr(vswr)
    return -10.0 * math.log10(1.0 - gamma * gamma)


def standing_wave_power_enhancement(vswr):
    """Peak-power enhancement at the standing-wave maximum, as a ratio."""
    gamma = reflection_coefficient_from_vswr(vswr)
    return (1.0 + gamma) ** 2


def effective_peak_power_w(applied_peak_power_w, vswr):
    """Applied peak rf-power raised by the standing-wave enhancement."""
    applied = _positive(applied_peak_power_w, "applied_peak_power_w")
    return applied * standing_wave_power_enhancement(vswr)


def rectangular_waveguide_cutoff_hz(broad_wall_m, narrow_wall_m, m=1, n=0):
    """Cutoff frequency of the TE(m,n) mode of an air-filled rectangular guide."""
    a = _positive(broad_wall_m, "broad_wall_m")
    b = _positive(narrow_wall_m, "narrow_wall_m")
    if b > a:
        raise ValueError(
            "narrow_wall_m (%r) must not exceed broad_wall_m (%r)"
            % (narrow_wall_m, broad_wall_m)
        )
    for label, order in (("m", m), ("n", n)):
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            raise ValueError("%s must be an integer >= 0, got %r" % (label, order))
    if m == 0 and n == 0:
        raise ValueError("m and n cannot both be zero; TE(0,0) does not propagate")
    return 0.5 * SPEED_OF_LIGHT_M_S * math.sqrt((m / a) ** 2 + (n / b) ** 2)


def waveguide_single_mode_band_hz(broad_wall_m, narrow_wall_m):
    """Usable single-mode band (lower, upper) of a rectangular waveguide."""
    cutoff = rectangular_waveguide_cutoff_hz(broad_wall_m, narrow_wall_m)
    return (
        WAVEGUIDE_BAND_LOWER_FACTOR * cutoff,
        WAVEGUIDE_BAND_UPPER_FACTOR * cutoff,
    )


def coaxial_characteristic_impedance_ohm(
    inner_radius_m, outer_radius_m, relative_permittivity=1.0
):
    """Characteristic impedance of a coaxial line."""
    a = _positive(inner_radius_m, "inner_radius_m")
    b = _positive(outer_radius_m, "outer_radius_m")
    eps = _positive(relative_permittivity, "relative_permittivity")
    if b <= a:
        raise ValueError(
            "outer_radius_m (%r) must exceed inner_radius_m (%r)"
            % (outer_radius_m, inner_radius_m)
        )
    if eps < 1.0:
        raise ValueError("relative_permittivity must be >= 1, got %r" % (eps,))
    return (59.9585 / math.sqrt(eps)) * math.log(b / a)


def coaxial_higher_order_mode_onset_hz(
    inner_radius_m, outer_radius_m, relative_permittivity=1.0
):
    """Frequency at which the first higher-order coaxial mode starts to propagate."""
    a = _positive(inner_radius_m, "inner_radius_m")
    b = _positive(outer_radius_m, "outer_radius_m")
    eps = _positive(relative_permittivity, "relative_permittivity")
    if b <= a:
        raise ValueError(
            "outer_radius_m (%r) must exceed inner_radius_m (%r)"
            % (outer_radius_m, inner_radius_m)
        )
    return SPEED_OF_LIGHT_M_S / (math.sqrt(eps) * math.pi * (a + b))


def derated_power_rating_w(rated_power_w, *factors):
    """Apply successive derating factors to a ground-measured rf-power rating."""
    rating = _positive(rated_power_w, "rated_power_w")
    for i, factor in enumerate(factors):
        f = float(factor)
        if not 0.0 < f <= 1.0:
            raise ValueError(
                "derating factor %d must lie in (0, 1], got %r" % (i, factor)
            )
        rating *= f
    return rating


def power_handling_margin_db(derated_rating_w, effective_peak_w):
    """Decibel margin between the derated rating and the effective peak rf-power."""
    rating = _positive(derated_rating_w, "derated_rating_w")
    peak = _positive(effective_peak_w, "effective_peak_w")
    return 10.0 * math.log10(rating / peak)


def _check_moding(port, category, frequency_hz, findings, computed):
    if category == "waveguide-flange":
        cutoff = rectangular_waveguide_cutoff_hz(
            port.get("broad_wall_m"), port.get("narrow_wall_m")
        )
        lower, upper = waveguide_single_mode_band_hz(
            port.get("broad_wall_m"), port.get("narrow_wall_m")
        )
        computed["cutoff_frequency_hz"] = cutoff
        computed["single_mode_band_hz"] = (lower, upper)
        if frequency_hz <= cutoff:
            findings.append("operating-frequency-at-or-below-waveguide-cutoff")
        elif not (_at_least(frequency_hz, lower) and _within_limit(frequency_hz, upper)):
            findings.append("operating-frequency-outside-single-mode-band")
        return
    eps = port.get("relative_permittivity", 1.0)
    onset = coaxial_higher_order_mode_onset_hz(
        port.get("inner_radius_m"), port.get("outer_radius_m"), eps
    )
    impedance = coaxial_characteristic_impedance_ohm(
        port.get("inner_radius_m"), port.get("outer_radius_m"), eps
    )
    computed["higher_order_mode_onset_hz"] = onset
    computed["characteristic_impedance_ohm"] = impedance
    if not _within_limit(frequency_hz, onset):
        findings.append("operating-frequency-above-higher-order-mode-onset")
    nominal = float(port.get("nominal_impedance_ohm", COAXIAL_NOMINAL_IMPEDANCE_OHM))
    tolerance = _positive(
        port.get("impedance_tolerance_ohm", DEFAULT_IMPEDANCE_TOLERANCE_OHM),
        "impedance_tolerance_ohm",
    )
    if not _within_limit(abs(impedance - nominal), tolerance):
        findings.append("characteristic-impedance-outside-tolerance")


def assess_guided_wave_port(port):
    """Full clause 7.2.3.1 assessment for one antenna port."""
    if not isinstance(port, dict):
        raise ValueError("port must be a mapping, got %r" % (type(port).__name__,))
    port_id = port.get("id")
    if not port_id:
        raise ValueError("port needs a non-empty 'id'")
    category = categorize_port_interface(port.get("interface"))
    frequency = _positive(port.get("operating_frequency_hz"), "operating_frequency_hz")

    findings = []
    computed = {"id": port_id, "interface_category": category,
                "operating_frequency_hz": frequency}
    _check_moding(port, category, frequency, findings, computed)

    measured_vswr = port.get("measured_vswr")
    if measured_vswr is None:
        raise ValueError("port %r needs a measured_vswr" % (port_id,))
    computed["reflection_coefficient"] = reflection_coefficient_from_vswr(measured_vswr)
    computed["return_loss_db"] = return_loss_db(measured_vswr)
    computed["mismatch_loss_db"] = mismatch_loss_db(measured_vswr)
    computed["power_enhancement"] = standing_wave_power_enhancement(measured_vswr)

    allowable_vswr = port.get("allowable_vswr")
    if allowable_vswr is None:
        findings.append("no-allowable-vswr-on-record")
    elif not _within_limit(float(measured_vswr), float(allowable_vswr)):
        findings.append("measured-vswr-exceeds-allowable")

    effective = effective_peak_power_w(port.get("applied_peak_power_w"), measured_vswr)
    rating = derated_power_rating_w(
        port.get("rated_power_w"),
        port.get("vacuum_derating_factor", 1.0),
        port.get("temperature_derating_factor", 1.0),
    )
    margin = power_handling_margin_db(rating, effective)
    computed["effective_peak_power_w"] = effective
    computed["derated_rating_w"] = rating
    computed["power_handling_margin_db"] = margin
    required = float(
        port.get("required_power_margin_db", DEFAULT_REQUIRED_POWER_MARGIN_DB)
    )
    if not _at_least(margin, required):
        findings.append("power-handling-margin-below-required")

    computed["findings"] = findings
    computed["compliant"] = not findings
    return computed


def assess_antenna_port_set(ports):
    """Assess every declared antenna port and aggregate the outcome."""
    if not isinstance(ports, list) or not ports:
        raise ValueError("ports must be a non-empty list")
    seen = set()
    results = []
    for port in ports:
        result = assess_guided_wave_port(port)
        if result["id"] in seen:
            raise ValueError("duplicate port id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    worst = min(r["power_handling_margin_db"] for r in results)
    return {
        "ports": results,
        "worst_power_handling_margin_db": worst,
        "non_compliant_ports": [r["id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }
