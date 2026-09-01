"""Infrared thermography (IRT) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for planning and
interpreting infrared thermography inspections: surface temperature
rise of a semi-infinite solid under a constant heat flux, thermal
contrast between a defect region and a sound region, time of maximum
contrast and characteristic diffusion time for subsurface defects
(disbond, delamination, void, corrosion), the heating pulse energy
density needed for a target rise, and a detectability verdict against
a noise floor. All units are SI: heat flux in W/m^2, time in seconds,
temperature in kelvin, depth in meters, conductivity in W/(m*K),
diffusivity in m^2/s, energy density in J/m^2.

Contract exercised by scripts/test_thermography.py.
"""

import math

PI = math.pi


def _validated_properties(thermal_properties):
    """Return (k, rho, c, alpha) from a thermal properties dict.

    The dict must hold k (thermal conductivity, W/(m*K)), rho
    (density, kg/m^3), and c (specific heat, J/(kg*K)). Thermal
    diffusivity is computed as alpha = k / (rho * c).

    Raises ValueError for a missing, non-finite, or non-positive
    property.
    """
    if not isinstance(thermal_properties, dict):
        raise ValueError(
            "thermal_properties must be a dict with keys k, rho, c, "
            "got %r" % (thermal_properties,)
        )
    missing = [key for key in ("k", "rho", "c") if key not in thermal_properties]
    if missing:
        raise ValueError(
            "thermal_properties missing key(s): %s" % ", ".join(missing)
        )
    k = thermal_properties["k"]
    rho = thermal_properties["rho"]
    c = thermal_properties["c"]
    for name, value in (("k", k), ("rho", rho), ("c", c)):
        if not math.isfinite(value):
            raise ValueError(
                "thermal property %s must be finite, got %r" % (name, value)
            )
        if value <= 0:
            raise ValueError(
                "thermal property %s must be > 0, got %r" % (name, value)
            )
    alpha = k / (rho * c)
    return k, rho, c, alpha


def surface_temperature_rise(heat_flux, time_s, thermal_properties):
    """Return the surface temperature rise in kelvin.

    Semi-infinite solid solution for a constant surface heat flux q
    applied from t = 0:
        delta_T = (2 * q / k) * sqrt(alpha * t / pi)
    with alpha = k / (rho * c). The rise grows with sqrt(t): fast
    right after the pulse, slower later. Used to verify that a
    planned heating pulse does not overheat the part and to convert
    pulse energy to the expected signal level.

    Raises ValueError for a non-positive heat flux, a negative time,
    or invalid thermal properties.
    """
    if not math.isfinite(heat_flux):
        raise ValueError("heat flux must be finite, got %r" % (heat_flux,))
    if heat_flux <= 0:
        raise ValueError("heat flux must be > 0, got %r" % (heat_flux,))
    if not math.isfinite(time_s):
        raise ValueError("time must be finite, got %r" % (time_s,))
    if time_s < 0:
        raise ValueError("time must be >= 0, got %r" % (time_s,))
    k, rho, c, alpha = _validated_properties(thermal_properties)
    if time_s == 0.0:
        return 0.0
    return (2.0 * heat_flux / k) * math.sqrt(alpha * time_s / PI)


def heating_pulse_energy_density(target_rise_k, time_s, thermal_properties):
    """Return the heating pulse energy density in J/m^2.

    Inverse of surface_temperature_rise(): the constant surface heat
    flux (equivalently the pulse energy density for a short pulse
    delivered over time_s) needed for a target surface temperature
    rise:
        q = target_rise * k * sqrt(pi / (alpha * t)) / 2

    Raises ValueError for a negative target rise, a non-positive
    time, or invalid thermal properties.
    """
    if not math.isfinite(target_rise_k):
        raise ValueError("target rise must be finite, got %r" % (target_rise_k,))
    if target_rise_k < 0:
        raise ValueError("target rise must be >= 0, got %r" % (target_rise_k,))
    if not math.isfinite(time_s):
        raise ValueError("time must be finite, got %r" % (time_s,))
    if time_s <= 0:
        raise ValueError("time must be > 0, got %r" % (time_s,))
    k, rho, c, alpha = _validated_properties(thermal_properties)
    if target_rise_k == 0.0:
        return 0.0
    return target_rise_k * k * math.sqrt(PI / (alpha * time_s)) / 2.0


def thermal_contrast(sound_temp, defect_temp):
    """Return the absolute thermal contrast in kelvin.

    contrast = T_defect - T_sound. A positive contrast means the
    defect region is hotter than the sound region, the usual sign
    for a heat-trapping disbond, delamination, or void under pulsed
    heating.

    Raises ValueError for a non-finite temperature.
    """
    if not math.isfinite(sound_temp):
        raise ValueError("sound temperature must be finite, got %r" % (sound_temp,))
    if not math.isfinite(defect_temp):
        raise ValueError(
            "defect temperature must be finite, got %r" % (defect_temp,)
        )
    return defect_temp - sound_temp


def normalized_thermal_contrast(sound_temp, defect_temp):
    """Return the normalized thermal contrast.

    normalized = (T_defect - T_sound) / T_sound. Normalizing by the
    sound temperature removes part of the dependence on the absolute
    heating level, making comparisons across inspections more stable.

    Raises ValueError for a non-positive sound temperature or a
    non-finite temperature.
    """
    if not math.isfinite(sound_temp):
        raise ValueError("sound temperature must be finite, got %r" % (sound_temp,))
    if sound_temp <= 0:
        raise ValueError(
            "sound temperature must be > 0 for normalization, got %r" % (sound_temp,)
        )
    if not math.isfinite(defect_temp):
        raise ValueError(
            "defect temperature must be finite, got %r" % (defect_temp,)
        )
    return (defect_temp - sound_temp) / sound_temp


def characteristic_diffusion_time(defect_depth, thermal_diffusivity):
    """Return the thermal diffusion time in seconds: t = z^2 / alpha.

    The reference time for a heat pulse to diffuse from the surface
    to a defect at depth z. The useful observation window is set
    around this time (roughly half the diffusion time to a few times
    it); before it the defect has not warmed, after it lateral
    spreading washes the contrast out.

    Raises ValueError for a non-positive depth or diffusivity.
    """
    if not math.isfinite(defect_depth):
        raise ValueError("defect depth must be finite, got %r" % (defect_depth,))
    if defect_depth <= 0:
        raise ValueError("defect depth must be > 0, got %r" % (defect_depth,))
    if not math.isfinite(thermal_diffusivity):
        raise ValueError(
            "thermal diffusivity must be finite, got %r" % (thermal_diffusivity,)
        )
    if thermal_diffusivity <= 0:
        raise ValueError(
            "thermal diffusivity must be > 0, got %r" % (thermal_diffusivity,)
        )
    return defect_depth ** 2 / thermal_diffusivity


def time_of_max_contrast(defect_depth, thermal_diffusivity):
    """Return an estimate of the time of maximum contrast in seconds.

    For a flat subsurface defect (disbond, delamination) at depth z
    under pulsed heating, the temperature difference between the
    defect region and the sound region peaks near
        t_max ~ z^2 / (2 * alpha)
    from the one-dimensional slab response. This is an estimate:
    the true peak shifts with the defect lateral size, the pulse
    duration, and the backing material, so the acquisition should
    bracket t_max rather than sample it exactly.

    Raises ValueError for a non-positive depth or diffusivity.
    """
    return characteristic_diffusion_time(defect_depth, thermal_diffusivity) / 2.0


def detectability_verdict(contrast, noise_floor, min_snr=2.0):
    """Return a detectability verdict dict for a measured contrast.

    snr = contrast / noise_floor. The verdict is DETECTABLE when
    snr >= min_snr (default 2.0, a common detection threshold), and
    NOT DETECTABLE otherwise; a negative contrast (defect colder
    than sound) is never detectable.

    Raises ValueError for a non-finite contrast, a non-positive
    noise floor, or a non-positive min_snr.
    """
    if not math.isfinite(contrast):
        raise ValueError("contrast must be finite, got %r" % (contrast,))
    if not math.isfinite(noise_floor):
        raise ValueError("noise floor must be finite, got %r" % (noise_floor,))
    if noise_floor <= 0:
        raise ValueError("noise floor must be > 0, got %r" % (noise_floor,))
    if not math.isfinite(min_snr):
        raise ValueError("min_snr must be finite, got %r" % (min_snr,))
    if min_snr <= 0:
        raise ValueError("min_snr must be > 0, got %r" % (min_snr,))
    snr = contrast / noise_floor
    detectable = snr >= min_snr
    return {
        "snr": snr,
        "min_snr": min_snr,
        "detectable": detectable,
        "verdict": "DETECTABLE" if detectable else "NOT DETECTABLE",
    }
