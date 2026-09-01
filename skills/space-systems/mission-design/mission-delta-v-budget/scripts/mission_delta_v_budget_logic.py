"""Spacecraft mission delta-v budget math.

Deterministic, offline, stdlib-only helpers for a spacecraft mission
delta-v budget: sum the delta-v contributions (launch insertion, orbit
transfer, plane change, station keeping, deorbit), apply a margin
allocation, and convert the budgeted delta-v into propellant mass with
the Tsiolkovsky rocket equation from the dry mass and the specific
impulse. All units are SI: delta-v in m/s, masses in kg, specific
impulse in seconds, g0 = 9.80665 m/s^2 (standard gravity), margin as a
fraction (0.15 means 15 percent).

The Tsiolkovsky rocket equation: dv = Isp * g0 * ln(m0 / mf) with m0
the initial (wet) mass and mf the final (dry) mass. Inverting it for a
given delta-v budget, dry mass, and specific impulse gives the
propellant mass m_prop = m_dry * (exp(dv / (Isp * g0)) - 1) and the
initial mass m0 = m_dry * exp(dv / (Isp * g0)).

Contract exercised by scripts/test_mission_delta_v_budget.py.
"""

import math

G0 = 9.80665  # standard gravity, m/s^2


def tsiolkovsky_delta_v(mass_ratio, isp, g0=G0):
    """Return the delta-v in m/s for the given mass ratio and specific impulse.

    dv = Isp * g0 * ln(mass_ratio), the Tsiolkovsky rocket equation.
    A mass ratio of e with a 300 s specific impulse gives exactly
    2941.995 m/s. A mass ratio of 1 (no propellant) gives 0 m/s.

    Raises ValueError for a mass ratio below 1, or a non-positive
    specific impulse or g0.
    """
    if mass_ratio < 1.0:
        raise ValueError("mass_ratio must be >= 1, got %r" % (mass_ratio,))
    if isp <= 0:
        raise ValueError("isp must be > 0, got %r" % (isp,))
    if g0 <= 0:
        raise ValueError("g0 must be > 0, got %r" % (g0,))
    return isp * g0 * math.log(mass_ratio)


def mass_ratio(delta_v, isp, g0=G0):
    """Return the initial to final mass ratio m0 / mf for the delta-v.

    m0 / mf = exp(dv / (Isp * g0)), the inverse of the rocket
    equation. A zero delta-v gives a mass ratio of exactly 1.

    Raises ValueError for a negative delta-v, or a non-positive
    specific impulse or g0.
    """
    if delta_v < 0.0:
        raise ValueError("delta_v must be >= 0, got %r" % (delta_v,))
    if isp <= 0:
        raise ValueError("isp must be > 0, got %r" % (isp,))
    if g0 <= 0:
        raise ValueError("g0 must be > 0, got %r" % (g0,))
    return math.exp(delta_v / (isp * g0))


def propellant_mass(delta_v, dry_mass, isp, g0=G0):
    """Return the propellant mass in kg for the delta-v budget.

    m_prop = m_dry * (exp(dv / (Isp * g0)) - 1). A zero delta-v needs
    zero propellant; a higher specific impulse needs less propellant
    for the same delta-v. For a 2941.995 m/s budget with a 1000 kg dry
    mass and a 300 s specific impulse the propellant mass is about
    1718.28 kg (mass ratio e).

    Raises ValueError for a negative delta-v, a non-positive dry mass,
    or a non-positive specific impulse or g0.
    """
    if delta_v < 0.0:
        raise ValueError("delta_v must be >= 0, got %r" % (delta_v,))
    if dry_mass <= 0:
        raise ValueError("dry_mass must be > 0, got %r" % (dry_mass,))
    if isp <= 0:
        raise ValueError("isp must be > 0, got %r" % (isp,))
    if g0 <= 0:
        raise ValueError("g0 must be > 0, got %r" % (g0,))
    return dry_mass * (math.exp(delta_v / (isp * g0)) - 1.0)


def wet_mass(delta_v, dry_mass, isp, g0=G0):
    """Return the initial wet mass in kg: dry mass plus propellant mass.

    m0 = m_dry * exp(dv / (Isp * g0)) = m_dry + m_prop. A zero
    delta-v leaves the wet mass equal to the dry mass.

    Raises ValueError for a negative delta-v, a non-positive dry mass,
    or a non-positive specific impulse or g0.
    """
    if delta_v < 0.0:
        raise ValueError("delta_v must be >= 0, got %r" % (delta_v,))
    if dry_mass <= 0:
        raise ValueError("dry_mass must be > 0, got %r" % (dry_mass,))
    if isp <= 0:
        raise ValueError("isp must be > 0, got %r" % (isp,))
    if g0 <= 0:
        raise ValueError("g0 must be > 0, got %r" % (g0,))
    return dry_mass * math.exp(delta_v / (isp * g0))


def sum_delta_v(contributions):
    """Return the total delta-v in m/s as the sum of the contributions.

    Each contribution is a positive magnitude in m/s (launch insertion,
    orbit transfer, plane change, station keeping, deorbit). An empty
    list sums to zero; the total never subtracts.

    Raises ValueError for any negative contribution.
    """
    contribs = [float(c) for c in contributions]
    if any(c < 0.0 for c in contribs):
        raise ValueError("delta-v contributions must be >= 0, got %r" % (contribs,))
    return sum(contribs)


def apply_margin(total_delta_v, margin_fraction):
    """Return the budgeted delta-v in m/s after the margin allocation.

    dv_budget = dv_total * (1 + margin_fraction). A margin fraction of
    0.15 adds 15 percent to the nominal total. A zero margin returns
    the total unchanged.

    Raises ValueError for a negative total or a negative margin
    fraction.
    """
    if total_delta_v < 0.0:
        raise ValueError("total_delta_v must be >= 0, got %r" % (total_delta_v,))
    if margin_fraction < 0.0:
        raise ValueError("margin_fraction must be >= 0, got %r" % (margin_fraction,))
    return total_delta_v * (1.0 + margin_fraction)


class MissionDeltaVBudget(object):
    """A spacecraft mission delta-v budget with margin and propellant sizing.

    Holds the delta-v contributions, the margin allocation, the dry
    mass, and the specific impulse; computes the nominal and budgeted
    totals, the propellant and wet masses from the Tsiolkovsky rocket
    equation, and reports the budget against an available delta-v
    capability.
    """

    def __init__(self, contributions, margin_fraction=0.0, dry_mass=None, isp=None, g0=G0):
        if margin_fraction < 0.0:
            raise ValueError("margin_fraction must be >= 0, got %r" % (margin_fraction,))
        if dry_mass is not None and dry_mass <= 0:
            raise ValueError("dry_mass must be > 0, got %r" % (dry_mass,))
        if isp is not None and isp <= 0:
            raise ValueError("isp must be > 0, got %r" % (isp,))
        if g0 <= 0:
            raise ValueError("g0 must be > 0, got %r" % (g0,))
        self.contributions = [float(c) for c in contributions]
        if any(c < 0.0 for c in self.contributions):
            raise ValueError(
                "delta-v contributions must be >= 0, got %r" % (self.contributions,)
            )
        self.margin_fraction = float(margin_fraction)
        self.dry_mass = None if dry_mass is None else float(dry_mass)
        self.isp = None if isp is None else float(isp)
        self.g0 = float(g0)

    def total_delta_v(self):
        """Return the nominal delta-v in m/s (sum of contributions)."""
        return sum(self.contributions)

    def budgeted_delta_v(self):
        """Return the budgeted delta-v in m/s after the margin allocation."""
        return apply_margin(self.total_delta_v(), self.margin_fraction)

    def propellant_mass(self):
        """Return the required propellant mass in kg from the budget.

        Uses the budgeted delta-v (nominal total plus margin), the dry
        mass, and the specific impulse with the Tsiolkovsky rocket
        equation. Raises ValueError when dry mass or specific impulse
        was not set on the budget.
        """
        if self.dry_mass is None or self.isp is None:
            raise ValueError("dry_mass and isp are required for propellant sizing")
        return propellant_mass(self.budgeted_delta_v(), self.dry_mass, self.isp, self.g0)

    def wet_mass(self):
        """Return the initial wet mass in kg (dry plus propellant)."""
        if self.dry_mass is None or self.isp is None:
            raise ValueError("dry_mass and isp are required for propellant sizing")
        return self.dry_mass + self.propellant_mass()

    def propellant_fraction(self):
        """Return the propellant mass fraction of the wet mass."""
        wet = self.wet_mass()
        return self.propellant_mass() / wet

    def fits(self, available_delta_v):
        """Return True when the budgeted delta-v fits the capability.

        The budget closes when the budgeted total (nominal plus margin)
        is at most the available delta-v of the propulsion subsystem.
        """
        return self.budgeted_delta_v() <= available_delta_v

    def report(self):
        """Return a dict summary of the budget and the propellant sizing."""
        r = {
            "total_delta_v_m_s": self.total_delta_v(),
            "margin_fraction": self.margin_fraction,
            "budgeted_delta_v_m_s": self.budgeted_delta_v(),
            "contributions": list(self.contributions),
        }
        if self.dry_mass is not None and self.isp is not None:
            r["dry_mass_kg"] = self.dry_mass
            r["isp_s"] = self.isp
            r["propellant_mass_kg"] = self.propellant_mass()
            r["wet_mass_kg"] = self.wet_mass()
            r["propellant_fraction"] = self.propellant_fraction()
        return r
