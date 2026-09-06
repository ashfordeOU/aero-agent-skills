"""Added mass coefficients of bodies accelerating through an inviscid
irrotational fluid (potential-flow kinetic-energy catalog).

Module: added_mass_coefficients_potential_flow_logic
Pack: aerodynamics/aeroelasticity (leaf added-mass-coefficients-potential-flow)

The added mass (virtual mass, apparent mass) of a body translating
rectilinearly through an inviscid irrotational fluid follows from the
kinetic energy T = (1/2)*rho*oint_S phi*(dphi/dn) dS of the irrotational
flow the body sets up (normal derivative positive into the body, Lamb
Hydrodynamics Art. 136 form).  For translation at speed U along a
principal direction that energy equals (1/2)*m_a*U^2, which fixes the
coefficient m_a of the shape.  This module is the closed-form catalog of
workflow step 2 of the SKILL.md (the catalog coefficient lookup of each
shape, per-unit-span for 2-D sections): the 2-D circular cylinder, the
2-D normal flat plate with its exactly zero tangential coefficient, the
2-D elliptic cylinder, the 3-D sphere, and the 3-D prolate and oblate
spheroids through the elementary reduction of the Lamb ellipsoid
coefficients alpha0, beta0, gamma0.  Workflow steps 3 to 5 (the energy
picture, the inertia model and the acceleration-reaction force of the
SKILL.md body) are served by the four scalar relations at the top of the
module.

Pure stdlib math only, closed form, deterministic, no RNG.  Every fluid
density rho is passed explicitly in kg/m^3.  Dimensional results are in
kg; the 2-D results are per unit span in kg/m.
"""

import math

# ---------------------------------------------------------------------------
# Scalar relations of the energy picture (SKILL.md workflow steps 3 to 5)
# ---------------------------------------------------------------------------

def kinetic_energy_of_translation(m_added, speed):
    """Return the fluid kinetic energy 0.5*m_added*speed^2 (J) of a body
    translating rectilinearly at speed (m/s), workflow step 3 of the
    SKILL.md energy picture.  m_added is the added mass (kg), speed the
    translation speed (m/s).  Raises ValueError if m_added <= 0 or speed
    < 0; returns 0.0 exactly at speed 0."""
    if m_added <= 0:
        raise ValueError("added mass must be positive")
    if speed < 0:
        raise ValueError("speed must be non-negative")
    return 0.5 * m_added * speed * speed


def acceleration_reaction_force(m_added, acceleration):
    """Return the force m_added*acceleration (N) the accelerating body
    must supply to the fluid to sustain the acceleration (m/s^2),
    workflow step 5 of the SKILL.md acceleration-reaction check.  It is
    the Newton third-law partner of the reaction the fluid exerts on the
    body, whose force is the negative, opposing the acceleration.  Raises
    ValueError if m_added <= 0."""
    if m_added <= 0:
        raise ValueError("added mass must be positive")
    return m_added * acceleration


def virtual_mass(m_body, m_added):
    """Return the virtual mass m_body + m_added (kg), the body mass
    augmented by the fluid inertia, workflow step 4 of the SKILL.md
    inertia model.  Raises ValueError if m_body <= 0 or m_added <= 0."""
    if m_body <= 0:
        raise ValueError("body mass must be positive")
    if m_added <= 0:
        raise ValueError("added mass must be positive")
    return m_body + m_added


def added_mass_fraction(m_added, m_body):
    """Return the added-mass fraction m_added/(m_body + m_added), the
    fluid-inertia share of the virtual mass (dimensionless), workflow
    step 4 of the SKILL.md inertia model.  Raises ValueError if m_body
    <= 0 or m_added <= 0."""
    if m_body <= 0:
        raise ValueError("body mass must be positive")
    if m_added <= 0:
        raise ValueError("added mass must be positive")
    return m_added / (m_body + m_added)


# ---------------------------------------------------------------------------
# 2-D catalog per unit span (kg/m), SKILL.md workflow step 2
# ---------------------------------------------------------------------------

def cylinder_added_mass(rho, R):
    """Return rho*pi*R^2 (kg/m per unit span), the added mass of the 2-D
    circular cylinder of radius R (m) in a fluid of density rho (kg/m^3),
    identical for motion in any in-plane direction by symmetry.  Raises
    ValueError if rho <= 0 or R <= 0."""
    if rho <= 0:
        raise ValueError("fluid density must be positive")
    if R <= 0:
        raise ValueError("radius must be positive")
    return rho * math.pi * R * R


def flat_plate_added_masses(rho, a):
    """Return (rho*pi*a*a, 0.0) (kg/m per unit span), the added masses of
    the 2-D normal flat plate of half-width a (m): the normal
    coefficient rho*pi*a*a for motion perpendicular to the plate and the
    tangential coefficient EXACTLY 0.0 for motion in the plate plane (a
    sliding plate disturbs no irrotational flow).  Raises ValueError if
    rho <= 0 or a <= 0."""
    if rho <= 0:
        raise ValueError("fluid density must be positive")
    if a <= 0:
        raise ValueError("half-width must be positive")
    return rho * math.pi * a * a, 0.0


def elliptic_cylinder_added_masses(rho, a, b):
    """Return {'m_along_a': rho*pi*b*b, 'm_along_b': rho*pi*a*a} (kg/m
    per unit span) for the elliptic cylinder section x^2/a^2 + y^2/b^2 =
    1: motion along a semi-axis couples to the OTHER semi-axis squared.
    Contains the circle limit a = b = R (rho*pi*R^2 both ways) and the
    plate limit b -> 0 ((0, rho*pi*a^2)).  Raises ValueError if rho <= 0,
    a <= 0 or b <= 0."""
    if rho <= 0:
        raise ValueError("fluid density must be positive")
    if a <= 0:
        raise ValueError("semi-axis a must be positive")
    if b <= 0:
        raise ValueError("semi-axis b must be positive")
    return {'m_along_a': rho * math.pi * b * b,
            'm_along_b': rho * math.pi * a * a}


# ---------------------------------------------------------------------------
# 3-D catalog (kg), SKILL.md workflow step 2
# ---------------------------------------------------------------------------

def sphere_added_mass(rho, R):
    """Return (2.0/3.0)*rho*pi*R^3 (kg), the added mass of the sphere of
    radius R (m), exactly half its displaced fluid mass.  Raises
    ValueError if rho <= 0 or R <= 0."""
    if rho <= 0:
        raise ValueError("fluid density must be positive")
    if R <= 0:
        raise ValueError("radius must be positive")
    return (2.0 / 3.0) * rho * math.pi * R * R * R


def _prolate_lamb_coefficients(a, b):
    """Return (alpha0, beta0), the Lamb ellipsoid coefficients (Art. 114
    integrals, elementary reduction) of the prolate spheroid x^2/a^2 +
    (y^2+z^2)/b^2 = 1 with a > b > 0.  Eccentricity e = sqrt(1 - (b/a)^2),
    alpha0 = 2*(1-e^2)/e^3*(0.5*ln((1+e)/(1-e)) - e), beta0 = 1 -
    alpha0/2.  Raises ValueError unless a > b > 0 (the a == b sphere
    branch is handled by the caller, never dividing by e)."""
    if a <= 0 or b <= 0 or b >= a:
        raise ValueError("prolate spheroid requires a > b > 0")
    e = math.sqrt(1.0 - (b / a) * (b / a))
    alpha0 = (2.0 * (1.0 - e * e) / (e ** 3)
              * (0.5 * math.log((1.0 + e) / (1.0 - e)) - e))
    beta0 = 1.0 - alpha0 / 2.0
    return alpha0, beta0


def prolate_spheroid_added_masses(rho, a, b):
    """Return {'axial': ..., 'transverse': ...} (kg), the added masses of
    the prolate spheroid x^2/a^2 + (y^2+z^2)/b^2 = 1 with a >= b, axial
    for motion along the a symmetry axis and transverse for motion along
    b.  For a == b exactly both entries equal the sphere value
    (2.0/3.0)*rho*pi*a^3 (the exact e = 0 branch, no division by e).
    Otherwise alpha0 from the Lamb integral reduction, beta0 = 1 -
    alpha0/2, M_disp = (4.0/3.0)*rho*pi*a*b*b, and the coefficients are
    M_disp*alpha0/(2 - alpha0) and M_disp*beta0/(2 - beta0).  Raises
    ValueError if rho <= 0, a <= 0, b <= 0 or b > a."""
    if rho <= 0:
        raise ValueError("fluid density must be positive")
    if a <= 0:
        raise ValueError("axial semi-axis a must be positive")
    if b <= 0:
        raise ValueError("equatorial semi-axis b must be positive")
    if b > a:
        raise ValueError("prolate spheroid requires a >= b")
    if a == b:
        m_sphere = (2.0 / 3.0) * rho * math.pi * a * a * a
        return {'axial': m_sphere, 'transverse': m_sphere}
    alpha0, beta0 = _prolate_lamb_coefficients(a, b)
    m_disp = (4.0 / 3.0) * rho * math.pi * a * b * b
    axial = m_disp * alpha0 / (2.0 - alpha0)
    transverse = m_disp * beta0 / (2.0 - beta0)
    return {'axial': axial, 'transverse': transverse}


def _oblate_lamb_coefficients(a, c):
    """Return (gamma0, alpha0), the Lamb ellipsoid coefficients of the
    oblate spheroid (x^2+y^2)/a^2 + z^2/c^2 = 1 with a > c > 0.
    Eccentricity e = sqrt(1 - (c/a)^2), gamma0 = 2*(e -
    (c/a)*asin(e))/e^3, alpha0 = beta0 = 1 - gamma0/2.  Raises ValueError
    unless a > c > 0 (the a == c sphere branch is handled by the caller,
    never dividing by e)."""
    if a <= 0 or c <= 0 or c >= a:
        raise ValueError("oblate spheroid requires a > c > 0")
    e = math.sqrt(1.0 - (c / a) * (c / a))
    gamma0 = (2.0 * (e - (c / a) * math.asin(e)) / (e ** 3))
    alpha0 = 1.0 - gamma0 / 2.0
    return gamma0, alpha0


def oblate_spheroid_added_masses(rho, a, c):
    """Return {'polar': ..., 'equatorial': ...} (kg), the added masses of
    the oblate spheroid (x^2+y^2)/a^2 + z^2/c^2 = 1 with a >= c, polar
    for motion along the z symmetry axis (semi-axis c) and equatorial for
    motion along a.  For a == c exactly both entries equal the sphere
    value (2.0/3.0)*rho*pi*a^3.  Otherwise gamma0 from the Lamb integral
    reduction, alpha0 = 1 - gamma0/2, M_disp = (4.0/3.0)*rho*pi*a*a*c,
    and the coefficients are M_disp*gamma0/(2 - gamma0) and
    M_disp*alpha0/(2 - alpha0).  Raises ValueError if rho <= 0, a <= 0,
    c <= 0 or c > a."""
    if rho <= 0:
        raise ValueError("fluid density must be positive")
    if a <= 0:
        raise ValueError("equatorial semi-axis a must be positive")
    if c <= 0:
        raise ValueError("polar semi-axis c must be positive")
    if c > a:
        raise ValueError("oblate spheroid requires a >= c")
    if a == c:
        m_sphere = (2.0 / 3.0) * rho * math.pi * a * a * a
        return {'polar': m_sphere, 'equatorial': m_sphere}
    gamma0, alpha0 = _oblate_lamb_coefficients(a, c)
    m_disp = (4.0 / 3.0) * rho * math.pi * a * a * c
    polar = m_disp * gamma0 / (2.0 - gamma0)
    equatorial = m_disp * alpha0 / (2.0 - alpha0)
    return {'polar': polar, 'equatorial': equatorial}
