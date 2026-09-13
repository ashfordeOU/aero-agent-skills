#!/usr/bin/env python3
"""Tether collecting-surface sizing (ECSS-E-ST-20-06C clause 10.2.2).

Deterministic, offline, stdlib-only implementation of the sizing procedure
for the surface a tether uses to exchange current with the ambient plasma.
The standard text is not reproduced; the clause is cited as an anchor only
and its intent is re-expressed as a checkable procedure:

  * compute the ambient random-flux current density from electron density
    and electron temperature,
  * apply the orbital-motion-limited enhancement for the collector geometry
    at its applied bias,
  * invert the result into the collecting area the intended application
    demands, with the required sizing margin,
  * confirm the area on record covers it, and
  * confirm the resulting surface current density stays inside the erosion
    and thermal rating of the collector material.
"""

import math

ELEMENTARY_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837015e-31
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

# Collector geometries with a closed-form orbital-motion-limited law.
GEOMETRY_SPHERE = "sphere"
GEOMETRY_CYLINDER = "cylinder"
GEOMETRY_FLAT_TAPE = "flat-tape"
GEOMETRIES = (GEOMETRY_SPHERE, GEOMETRY_CYLINDER, GEOMETRY_FLAT_TAPE)

# Sizing margin the collecting area must carry over the bare requirement.
REQUIRED_AREA_MARGIN = 1.2

# A collector whose characteristic radius exceeds this multiple of the Debye
# length has left the thin-sheath regime the orbital-motion-limited law is
# derived in, and the closed form overstates what it collects.
THIN_SHEATH_RADIUS_LIMIT = 1.0

# Slack used only to absorb float representation error at an exact boundary.
# It never widens an engineering limit.
BOUNDARY_REL_TOL = 1e-9
BOUNDARY_ABS_TOL = 1e-12


def _require_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _require_positive(value, name):
    out = _require_number(value, name)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))
    return out


def _require_non_negative(value, name):
    out = _require_number(value, name)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    return out


def _at_or_above(value, threshold):
    if value >= threshold:
        return True
    return math.isclose(
        value, threshold, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL
    )


def _at_or_below(value, threshold):
    if value <= threshold:
        return True
    return math.isclose(
        value, threshold, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL
    )


def _check_geometry(geometry):
    if geometry not in GEOMETRIES:
        raise ValueError(
            "unknown geometry %r; expected one of %s" % (geometry, GEOMETRIES)
        )
    return geometry


def mean_flux_speed(electron_temperature_ev):
    """Mean one-sided flux speed of a maxwellian electron population, m/s."""
    temperature = _require_positive(
        electron_temperature_ev, "electron_temperature_ev"
    )
    energy_j = temperature * ELEMENTARY_CHARGE_C
    return math.sqrt(energy_j / (2.0 * math.pi * ELECTRON_MASS_KG))


def thermal_current_density(electron_density_m3, electron_temperature_ev):
    """Random-flux electron current density onto a surface at plasma potential, A/m2."""
    density = _require_positive(electron_density_m3, "electron_density_m3")
    return ELEMENTARY_CHARGE_C * density * mean_flux_speed(electron_temperature_ev)


def debye_length_m(electron_density_m3, electron_temperature_ev):
    """Electron Debye length of the ambient plasma, metres."""
    density = _require_positive(electron_density_m3, "electron_density_m3")
    temperature = _require_positive(
        electron_temperature_ev, "electron_temperature_ev"
    )
    return math.sqrt(
        VACUUM_PERMITTIVITY_F_PER_M
        * temperature
        / (density * ELEMENTARY_CHARGE_C)
    )


def thin_sheath_valid(characteristic_radius_m, debye_m):
    """True when the collector is small enough for the thin-sheath closed form."""
    radius = _require_positive(characteristic_radius_m, "characteristic_radius_m")
    debye = _require_positive(debye_m, "debye_m")
    return _at_or_below(radius, THIN_SHEATH_RADIUS_LIMIT * debye)


def oml_enhancement(bias_v, electron_temperature_ev, geometry):
    """Current enhancement over the random flux at a positive bias.

    A sphere in the orbital-motion-limited regime collects in proportion to
    the bias energy; a cylinder collects as its square root; a broad flat
    surface gains nothing beyond the random flux because its sheath grows
    over an area that is already captured.
    """
    bias = _require_non_negative(bias_v, "bias_v")
    temperature = _require_positive(
        electron_temperature_ev, "electron_temperature_ev"
    )
    _check_geometry(geometry)
    ratio = bias / temperature
    if geometry == GEOMETRY_SPHERE:
        return 1.0 + ratio
    if geometry == GEOMETRY_CYLINDER:
        return (2.0 / math.sqrt(math.pi)) * math.sqrt(1.0 + ratio)
    return 1.0


def effective_current_density(
    electron_density_m3, electron_temperature_ev, bias_v, geometry
):
    """Current density the biased collector actually draws, A/m2."""
    return thermal_current_density(
        electron_density_m3, electron_temperature_ev
    ) * oml_enhancement(bias_v, electron_temperature_ev, geometry)


def collected_current(
    area_m2, electron_density_m3, electron_temperature_ev, bias_v, geometry
):
    """Current a collecting surface of the given area draws, amperes."""
    area = _require_positive(area_m2, "area_m2")
    return area * effective_current_density(
        electron_density_m3, electron_temperature_ev, bias_v, geometry
    )


def required_collecting_area(
    target_current_a, electron_density_m3, electron_temperature_ev, bias_v, geometry
):
    """Bare collecting area needed to carry the operating current, m2."""
    target = _require_positive(target_current_a, "target_current_a")
    density = effective_current_density(
        electron_density_m3, electron_temperature_ev, bias_v, geometry
    )
    if density <= 0.0:
        raise ValueError("effective current density collapsed to zero")
    return target / density


def sized_collecting_area(
    target_current_a,
    electron_density_m3,
    electron_temperature_ev,
    bias_v,
    geometry,
    margin=REQUIRED_AREA_MARGIN,
):
    """Collecting area to carry the operating current including the margin, m2."""
    factor = _require_positive(margin, "margin")
    if factor < 1.0:
        raise ValueError("margin must be >= 1.0, got %r" % (margin,))
    return factor * required_collecting_area(
        target_current_a, electron_density_m3, electron_temperature_ev, bias_v, geometry
    )


def area_margin(available_m2, required_m2):
    """Ratio of the collecting area on record to the bare requirement."""
    available = _require_positive(available_m2, "available_m2")
    required = _require_positive(required_m2, "required_m2")
    return available / required


def surface_current_density(current_a, area_m2):
    """Current per unit collecting area, A/m2."""
    current = _require_positive(current_a, "current_a")
    area = _require_positive(area_m2, "area_m2")
    return current / area


def density_within_rating(current_a, area_m2, max_density_a_per_m2):
    """True when the drawn current density stays inside the material rating."""
    limit = _require_positive(max_density_a_per_m2, "max_density_a_per_m2")
    return _at_or_below(surface_current_density(current_a, area_m2), limit)


def verify_collecting_surface(spec):
    """Run the clause 10.2.2 sizing check over one collector specification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping, got %r" % (type(spec),))
    for key in (
        "operating_current_a",
        "available_area_m2",
        "electron_density_m3",
        "electron_temperature_ev",
        "bias_v",
        "geometry",
    ):
        if key not in spec:
            raise ValueError("spec is missing required field %r" % (key,))
    geometry = _check_geometry(spec["geometry"])
    target = _require_positive(spec["operating_current_a"], "operating_current_a")
    available = _require_positive(spec["available_area_m2"], "available_area_m2")
    density = spec["electron_density_m3"]
    temperature = spec["electron_temperature_ev"]
    bias = spec["bias_v"]
    margin_factor = spec.get("required_margin", REQUIRED_AREA_MARGIN)
    required = required_collecting_area(target, density, temperature, bias, geometry)
    sized = sized_collecting_area(
        target, density, temperature, bias, geometry, margin_factor
    )
    margin = area_margin(available, required)
    area_ok = _at_or_above(available, sized)
    findings = []
    if not area_ok:
        findings.append(
            "collecting area %.6g m2 is below the %.6g m2 needed for %.6g A "
            "at the required margin" % (available, sized, target)
        )
    deliverable = collected_current(available, density, temperature, bias, geometry)
    if not _at_or_above(deliverable, target):
        findings.append(
            "collecting area draws only %.6g A against an operating demand of %.6g A"
            % (deliverable, target)
        )
    rating = spec.get("max_current_density_a_per_m2")
    density_ok = True
    drawn_density = surface_current_density(target, available)
    if rating is not None:
        density_ok = density_within_rating(target, available, rating)
        if not density_ok:
            findings.append(
                "surface current density %.6g A/m2 exceeds the %.6g A/m2 rating"
                % (drawn_density, rating)
            )
    sheath_ok = True
    radius = spec.get("characteristic_radius_m")
    debye = debye_length_m(density, temperature)
    if radius is not None:
        sheath_ok = thin_sheath_valid(radius, debye)
        if not sheath_ok:
            findings.append(
                "characteristic radius %.6g m exceeds the %.6g m Debye length; "
                "the thin-sheath closed form overstates the collected current"
                % (radius, debye)
            )
    return {
        "geometry": geometry,
        "enhancement": oml_enhancement(bias, temperature, geometry),
        "effective_current_density_a_per_m2": effective_current_density(
            density, temperature, bias, geometry
        ),
        "required_area_m2": required,
        "sized_area_m2": sized,
        "available_area_m2": available,
        "area_margin": margin,
        "collectable_current_a": deliverable,
        "surface_current_density_a_per_m2": drawn_density,
        "debye_length_m": debye,
        "thin_sheath_valid": sheath_ok,
        "findings": findings,
        "compliant": not findings,
    }
