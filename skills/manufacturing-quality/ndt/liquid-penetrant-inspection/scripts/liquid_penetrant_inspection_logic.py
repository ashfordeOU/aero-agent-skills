"""Liquid penetrant inspection (PT) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for liquid penetrant
inspection: capillary pressure and capillary rise that pull the
penetrant into a surface-breaking crack, Washburn equation penetration
depth during the dwell time, dwell time sizing for a crack of given
width and depth, instantaneous penetration rate, crack opening width to
effective capillary radius conversion, bleed-out indication width and
ratio for indication sizing, developer coverage mass, and indication to
background contrast ratio. All units are SI: surface tension in N/m,
pressure in Pa, radius and depth in meters, viscosity in Pa.s, time in
seconds, density in kg/m3.

Contract exercised by scripts/test_liquid_penetrant_inspection.py.
"""

import math

GRAVITY = 9.80665  # standard gravity, m/s2


def _wetting_cos(contact_angle_deg):
    """Return cos(contact angle) for a wetting penetrant.

    A penetrant must wet the surface to enter a crack by capillary
    action, so the contact angle must stay below 90 degrees. Raises
    ValueError for an angle outside [0, 90).
    """
    if contact_angle_deg < 0:
        raise ValueError(
            "contact angle must be >= 0, got %r" % (contact_angle_deg,)
        )
    if contact_angle_deg >= 90.0:
        raise ValueError(
            "penetrant must wet the surface: contact angle %r deg "
            ">= 90 deg gives no capillary pull" % (contact_angle_deg,)
        )
    return math.cos(math.radians(contact_angle_deg))


def capillary_pressure(surface_tension, contact_angle_deg, radius):
    """Return the capillary pressure in Pa across the penetrant meniscus.

    P = 2 * gamma * cos(theta) / r, with gamma the surface tension in
    N/m, theta the contact angle in degrees, and r the capillary radius
    in meters. This is the pressure difference that drives the
    penetrant into a surface-breaking crack. A smaller crack radius
    gives a higher driving pressure, which is why penetrant fills tight
    cracks.

    Raises ValueError for a non-positive surface tension or radius, or
    a contact angle outside [0, 90).
    """
    if surface_tension <= 0:
        raise ValueError(
            "surface tension must be > 0, got %r" % (surface_tension,)
        )
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    cos_theta = _wetting_cos(contact_angle_deg)
    return 2.0 * surface_tension * cos_theta / radius


def capillary_rise_height(
    surface_tension, contact_angle_deg, density, radius, gravity=GRAVITY
):
    """Return the capillary rise height in meters for a vertical crack.

    h = 2 * gamma * cos(theta) / (rho * g * r), the height at which the
    hydrostatic head balances the capillary pressure. Water in a 0.5 mm
    glass tube rises about 5.9 cm, the classic classroom check.

    Raises ValueError for a non-positive surface tension, density,
    radius, or gravity, or a contact angle outside [0, 90).
    """
    if surface_tension <= 0:
        raise ValueError(
            "surface tension must be > 0, got %r" % (surface_tension,)
        )
    if density <= 0:
        raise ValueError("density must be > 0, got %r" % (density,))
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if gravity <= 0:
        raise ValueError("gravity must be > 0, got %r" % (gravity,))
    cos_theta = _wetting_cos(contact_angle_deg)
    return 2.0 * surface_tension * cos_theta / (density * gravity * radius)


def washburn_penetration_depth(
    surface_tension, contact_angle_deg, viscosity, radius, time
):
    """Return the penetrant penetration depth in meters after time t.

    Washburn equation for capillary-driven flow with inertia neglected:
    L = sqrt(r * gamma * cos(theta) * t / (2 * eta)), with gamma the
    surface tension in N/m, eta the viscosity in Pa.s, r the effective
    capillary radius in meters, and t the dwell time in seconds. Depth
    grows as the square root of time, so doubling the dwell time only
    multiplies the penetration by sqrt(2).

    Raises ValueError for a non-positive surface tension, viscosity, or
    radius, a negative time, or a contact angle outside [0, 90).
    """
    if surface_tension <= 0:
        raise ValueError(
            "surface tension must be > 0, got %r" % (surface_tension,)
        )
    if viscosity <= 0:
        raise ValueError("viscosity must be > 0, got %r" % (viscosity,))
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if time < 0:
        raise ValueError("time must be >= 0, got %r" % (time,))
    cos_theta = _wetting_cos(contact_angle_deg)
    return math.sqrt(
        radius * surface_tension * cos_theta * time / (2.0 * viscosity)
    )


def dwell_time_for_depth(
    depth, surface_tension, contact_angle_deg, viscosity, radius
):
    """Return the dwell time in seconds to reach the given depth.

    Inverting the Washburn equation: t = 2 * eta * L^2 /
    (r * gamma * cos(theta)). Dwell time scales with the square of the
    depth, so a crack twice as deep needs four times the dwell time,
    and it scales inversely with the capillary radius, so a tighter
    crack needs a longer dwell.

    Raises ValueError for a non-positive depth, surface tension,
    viscosity, or radius, or a contact angle outside [0, 90).
    """
    if depth <= 0:
        raise ValueError("depth must be > 0, got %r" % (depth,))
    if surface_tension <= 0:
        raise ValueError(
            "surface tension must be > 0, got %r" % (surface_tension,)
        )
    if viscosity <= 0:
        raise ValueError("viscosity must be > 0, got %r" % (viscosity,))
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    cos_theta = _wetting_cos(contact_angle_deg)
    return (
        2.0 * viscosity * depth * depth
        / (radius * surface_tension * cos_theta)
    )


def penetration_rate(
    surface_tension, contact_angle_deg, viscosity, radius, depth
):
    """Return the instantaneous penetration rate dL/dt in m/s.

    dL/dt = r * gamma * cos(theta) / (4 * eta * L). The rate falls as
    the front advances, so most of the penetration happens early in the
    dwell time.

    Raises ValueError for a non-positive surface tension, viscosity,
    radius, or depth, or a contact angle outside [0, 90).
    """
    if surface_tension <= 0:
        raise ValueError(
            "surface tension must be > 0, got %r" % (surface_tension,)
        )
    if viscosity <= 0:
        raise ValueError("viscosity must be > 0, got %r" % (viscosity,))
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if depth <= 0:
        raise ValueError("depth must be > 0, got %r" % (depth,))
    cos_theta = _wetting_cos(contact_angle_deg)
    return (
        radius * surface_tension * cos_theta
        / (4.0 * viscosity * depth)
    )


def crack_radius_from_width(width):
    """Return the effective capillary radius in meters for a slit crack.

    A narrow slit of opening width w behaves as a capillary of radius
    r = w / 2 for the Washburn equation.

    Raises ValueError for a non-positive width.
    """
    if width <= 0:
        raise ValueError("width must be > 0, got %r" % (width,))
    return width / 2.0


def bleed_out_width(flaw_width, bleed_factor):
    """Return the indication width in meters for a given flaw width.

    The developer draws excess penetrant out of the flaw, so the
    visible indication is wider than the actual flaw opening. Tight
    cracks typically bleed out 3 to 5 times their opening width, so
    indication_width = flaw_width * bleed_factor.

    Raises ValueError for a non-positive flaw width or bleed factor.
    """
    if flaw_width <= 0:
        raise ValueError("flaw width must be > 0, got %r" % (flaw_width,))
    if bleed_factor <= 0:
        raise ValueError(
            "bleed factor must be > 0, got %r" % (bleed_factor,)
        )
    return flaw_width * bleed_factor


def bleed_out_ratio(indication_width, flaw_width):
    """Return the bleed-out ratio, indication width over flaw width.

    A ratio near 1 means the indication is essentially the flaw size; a
    ratio of 3 to 5 is typical for tight fatigue cracks whose opening
    is far narrower than the visible bleed-out.

    Raises ValueError for a non-positive indication width or flaw width.
    """
    if indication_width <= 0:
        raise ValueError(
            "indication width must be > 0, got %r" % (indication_width,)
        )
    if flaw_width <= 0:
        raise ValueError("flaw width must be > 0, got %r" % (flaw_width,))
    return indication_width / flaw_width


def developer_coverage_mass(area, areal_density):
    """Return the developer mass in kg for a part area.

    m = area * areal_density, with area in m2 and areal density in
    kg/m2. Dry developer is typically applied at 0.1 to 0.2 kg/m2 of
    part surface.

    Raises ValueError for a negative area or a non-positive areal
    density.
    """
    if area < 0:
        raise ValueError("area must be >= 0, got %r" % (area,))
    if areal_density <= 0:
        raise ValueError(
            "areal density must be > 0, got %r" % (areal_density,)
        )
    return area * areal_density


def contrast_ratio(background_reflectance, indication_reflectance):
    """Return the indication to background contrast ratio, 0 to 1.

    Contrast = abs(bg - ind) / max(bg, ind). A fluorescent penetrant
    indication is bright against a dark background, a visible dye
    indication is dark against a white developer background; both give
    a ratio near 1. A ratio near 0 means the indication is
    indistinguishable from the background.

    Raises ValueError for a non-positive background reflectance or a
    negative indication reflectance.
    """
    if background_reflectance <= 0:
        raise ValueError(
            "background reflectance must be > 0, got %r"
            % (background_reflectance,)
        )
    if indication_reflectance < 0:
        raise ValueError(
            "indication reflectance must be >= 0, got %r"
            % (indication_reflectance,)
        )
    return abs(background_reflectance - indication_reflectance) / max(
        background_reflectance, indication_reflectance
    )
