#!/usr/bin/env python3
"""Bird strike impact analysis logic (soft-body impact, paraphrase of common
knowledge; FAR-25 and CS-25 referenced, not reproduced).

UNITS CONVENTION (single convention, used everywhere in this module):
  mass        in kilograms
  velocity    in meters per second
  energy      in joules
  threshold   in joules

Bird strike certification frame for transport aeroplanes (summary):
FAR 25.631 requires the empennage structure to be designed so the
aeroplane can continue safe flight and landing after impact with a
4 pound bird at cruise velocity; the 8 pound bird class is used for
windshield, radome, and engine inlet assessments. The impact kinetic
energy E = 0.5 * m * v**2 is the governing parameter for soft-body
impact damage; comparing the strike energy with the component damage
threshold rates penetration and the residual strength after impact.
"""


def bird_mass_kg(pounds):
    """Convert a bird class mass in pounds to kilograms (1 lb = 0.45359237 kg).

    Raises ValueError when the mass is not strictly positive."""
    if pounds <= 0:
        raise ValueError("bird mass must be > 0, got %r" % (pounds,))
    return pounds * 0.45359237


def impact_energy(mass_kg, velocity_mps):
    """Impact kinetic energy E = 0.5 * m * v**2, in joules.

    Raises ValueError when the mass is not strictly positive or the
    velocity is negative."""
    if mass_kg <= 0:
        raise ValueError("bird mass must be > 0, got %r" % (mass_kg,))
    if velocity_mps < 0:
        raise ValueError("velocity must be >= 0, got %r" % (velocity_mps,))
    return 0.5 * mass_kg * velocity_mps ** 2


def specific_energy(velocity_mps):
    """Impact kinetic energy per unit bird mass, 0.5 * v**2, in J/kg.

    Raises ValueError when the velocity is negative."""
    if velocity_mps < 0:
        raise ValueError("velocity must be >= 0, got %r" % (velocity_mps,))
    return 0.5 * velocity_mps ** 2


def damage_severity_ratio(impact_energy_j, threshold_j):
    """Strike energy over the component damage threshold (dimensionless).

    Below 1 the strike stays under the threshold, above 1 it exceeds
    it. Raises ValueError when the impact energy is negative or the
    threshold is not strictly positive."""
    if impact_energy_j < 0:
        raise ValueError("impact energy must be >= 0, got %r" % (impact_energy_j,))
    if threshold_j <= 0:
        raise ValueError("threshold must be > 0, got %r" % (threshold_j,))
    return impact_energy_j / threshold_j


def penetration_verdict(impact_energy_j, threshold_j):
    """'penetration' when the strike energy reaches the component damage
    threshold, else 'no-penetration'.

    Raises ValueError when the impact energy is negative or the
    threshold is not strictly positive."""
    if impact_energy_j < 0:
        raise ValueError("impact energy must be >= 0, got %r" % (impact_energy_j,))
    if threshold_j <= 0:
        raise ValueError("threshold must be > 0, got %r" % (threshold_j,))
    return "penetration" if impact_energy_j >= threshold_j else "no-penetration"


def residual_strength_fraction(damage_energy_j, threshold_j):
    """Residual strength fraction after the strike, linear degradation model:
    max(0, 1 - 0.5 * E / threshold).

    An undamaged component gives 1.0, a strike at the threshold leaves
    0.5, and twice the threshold drives the fraction to 0.0. Raises
    ValueError when the damage energy is negative or the threshold is
    not strictly positive."""
    if damage_energy_j < 0:
        raise ValueError("damage energy must be >= 0, got %r" % (damage_energy_j,))
    if threshold_j <= 0:
        raise ValueError("threshold must be > 0, got %r" % (threshold_j,))
    frac = 1.0 - 0.5 * damage_energy_j / threshold_j
    return max(0.0, frac)
