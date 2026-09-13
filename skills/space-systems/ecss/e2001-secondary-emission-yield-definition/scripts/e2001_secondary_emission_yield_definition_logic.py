"""ECSS-E-ST-20-01C clause 9.1 -- secondary electron yield, as defined.

Deterministic, offline, stdlib-only implementation of the quantity every
multipactor provision rests on: the secondary electron yield of a surface,
written here as delta.  Every rule is a paraphrase of the clause intent
expressed as implementable logic; no standard text is reproduced.

The definition has three parts and this module implements all three.

1. What delta counts.  Delta is the number of electrons leaving the surface
   per electron arriving at it, over the whole emitted population -- true
   secondaries plus elastically and inelastically backscattered primaries.
   Measured from currents it is the emitted current divided by the incident
   current, which makes delta a pure ratio with no unit.
2. What delta depends on.  Delta is a function of the impact energy of the
   arriving electron and of its angle of incidence, not a single number for
   a material.  Vaughan's empirical curve is used as the deterministic
   reference shape: zero below a threshold energy, rising to a peak at the
   peak-yield energy, then decaying.
3. Why the two unity crossings matter.  The impact energies at which delta
   equals one bracket the band inside which an electron population grows.
   Outside that band the population decays whatever the geometry does, so
   the band -- not the peak value alone -- is what a multipactor provision
   consumes.
"""

import math

# Tolerances absorb floating-point representation error exactly at a
# definitional boundary such as delta == 1.  They never widen the boundary.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Vaughan curve constants.  E0 is the impact energy below which no
# secondary emission is credited.
DEFAULT_E0_EV = 12.5
LOW_SIDE_EXPONENT = 0.56
HIGH_SIDE_EXPONENT = 0.25
TAIL_BREAK_V = 3.6
TAIL_SCALE = 1.125
TAIL_EXPONENT = 0.35
# Largest reduced energy searched when hunting the upper unity crossing.
MAX_SEARCH_V = 10000.0
BISECTION_STEPS = 200

# Peak-yield bands used to categorize a surface.
LOW_YIELD_CEILING = 1.0
MODERATE_YIELD_CEILING = 1.5
ELEVATED_YIELD_CEILING = 2.5


def _is_unity(value):
    """True when a yield is at unity within representation error."""
    return math.isclose(value, 1.0, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _at_most(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _require_number(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    return float(value)


def total_emission_yield(true_secondary_yield, backscattered_yield):
    """Delta as clause 9.1 counts it: every electron leaving, per arrival.

    Splitting the emitted population into true secondaries and
    backscattered primaries is a measurement convenience; the yield the
    multipactor provisions use is the sum of the two.
    """
    true_part = _require_number("true-secondary yield", true_secondary_yield)
    back_part = _require_number("backscattered yield", backscattered_yield)
    if true_part < 0.0:
        raise ValueError("true-secondary yield cannot be negative, got %r" % (true_part,))
    if back_part < 0.0:
        raise ValueError("backscattered yield cannot be negative, got %r" % (back_part,))
    return true_part + back_part


def yield_from_currents(incident_current_a, emitted_current_a):
    """Delta measured as a current ratio: emitted current over incident."""
    incident = _require_number("incident current", incident_current_a)
    emitted = _require_number("emitted current", emitted_current_a)
    if incident <= 0.0:
        raise ValueError("incident current must be positive, got %r" % (incident,))
    if emitted < 0.0:
        raise ValueError("emitted current cannot be negative, got %r" % (emitted,))
    return emitted / incident


def angle_corrected_parameters(
    peak_yield_normal, peak_energy_normal_ev, incidence_angle_deg=0.0, smoothness=1.0
):
    """Shift the peak yield and peak energy for off-normal incidence.

    A grazing primary deposits its energy nearer the surface, so more
    secondaries escape: both the peak yield and the energy at which it
    occurs rise with the angle measured from the surface normal.  The
    smoothness factor carries the surface roughness, from a rough surface
    that barely responds to angle up to a polished one that responds fully.
    """
    peak_yield = _require_number("peak yield", peak_yield_normal)
    peak_energy = _require_number("peak-yield energy", peak_energy_normal_ev)
    angle = _require_number("incidence angle", incidence_angle_deg)
    rough = _require_number("smoothness factor", smoothness)
    if peak_yield <= 0.0:
        raise ValueError("peak yield must be positive, got %r" % (peak_yield,))
    if peak_energy <= 0.0:
        raise ValueError("peak-yield energy must be positive, got %r" % (peak_energy,))
    if not 0.0 <= angle < 90.0:
        raise ValueError("incidence angle must be in [0, 90) degrees, got %r" % (angle,))
    if not 0.0 <= rough <= 2.0:
        raise ValueError("smoothness factor must be in [0, 2], got %r" % (rough,))
    theta = math.radians(angle)
    return (
        peak_yield * (1.0 + rough * theta * theta / (2.0 * math.pi)),
        peak_energy * (1.0 + rough * theta * theta / math.pi),
    )


def vaughan_yield(
    impact_energy_ev,
    peak_yield_normal,
    peak_energy_normal_ev,
    threshold_energy_ev=DEFAULT_E0_EV,
    incidence_angle_deg=0.0,
    smoothness=1.0,
):
    """Delta at one impact energy, on Vaughan's empirical curve."""
    energy = _require_number("impact energy", impact_energy_ev)
    threshold = _require_number("threshold energy", threshold_energy_ev)
    if energy < 0.0:
        raise ValueError("impact energy cannot be negative, got %r" % (energy,))
    if threshold < 0.0:
        raise ValueError("threshold energy cannot be negative, got %r" % (threshold,))
    peak_yield, peak_energy = angle_corrected_parameters(
        peak_yield_normal, peak_energy_normal_ev, incidence_angle_deg, smoothness
    )
    if peak_energy <= threshold:
        raise ValueError("peak-yield energy must exceed the threshold energy")
    reduced = (energy - threshold) / (peak_energy - threshold)
    if reduced <= 0.0:
        return 0.0
    if reduced <= 1.0:
        return peak_yield * (reduced * math.exp(1.0 - reduced)) ** LOW_SIDE_EXPONENT
    if reduced <= TAIL_BREAK_V:
        return peak_yield * (reduced * math.exp(1.0 - reduced)) ** HIGH_SIDE_EXPONENT
    return peak_yield * TAIL_SCALE / (reduced ** TAIL_EXPONENT)


def _bisect_unity(lower_ev, upper_ev, curve):
    """Locate the impact energy where the curve crosses unity, by bisection."""
    low, high = lower_ev, upper_ev
    for _ in range(BISECTION_STEPS):
        mid = 0.5 * (low + high)
        if curve(mid) >= 1.0:
            high = mid
        else:
            low = mid
    return 0.5 * (low + high)


def first_crossover_energy(
    peak_yield_normal,
    peak_energy_normal_ev,
    threshold_energy_ev=DEFAULT_E0_EV,
    incidence_angle_deg=0.0,
    smoothness=1.0,
):
    """Lower impact energy at which delta reaches one, or None if it never does."""
    peak_yield, peak_energy = angle_corrected_parameters(
        peak_yield_normal, peak_energy_normal_ev, incidence_angle_deg, smoothness
    )
    threshold = _require_number("threshold energy", threshold_energy_ev)
    if peak_energy <= threshold:
        raise ValueError("peak-yield energy must exceed the threshold energy")
    if _at_most(peak_yield, 1.0):
        # A peak yield at or below unity -- unity itself included, with its
        # representation error absorbed -- never exceeds one, so no crossing
        # exists and the surface carries no susceptible band.
        return None

    def curve(energy):
        return vaughan_yield(
            energy,
            peak_yield_normal,
            peak_energy_normal_ev,
            threshold_energy_ev,
            incidence_angle_deg,
            smoothness,
        )

    return _bisect_unity(threshold, peak_energy, curve)


def second_crossover_energy(
    peak_yield_normal,
    peak_energy_normal_ev,
    threshold_energy_ev=DEFAULT_E0_EV,
    incidence_angle_deg=0.0,
    smoothness=1.0,
):
    """Upper impact energy at which delta falls back to one, or None."""
    peak_yield, peak_energy = angle_corrected_parameters(
        peak_yield_normal, peak_energy_normal_ev, incidence_angle_deg, smoothness
    )
    threshold = _require_number("threshold energy", threshold_energy_ev)
    if peak_energy <= threshold:
        raise ValueError("peak-yield energy must exceed the threshold energy")
    if _at_most(peak_yield, 1.0):
        # A peak yield at or below unity -- unity itself included, with its
        # representation error absorbed -- never exceeds one, so no crossing
        # exists and the surface carries no susceptible band.
        return None

    def curve(energy):
        return vaughan_yield(
            energy,
            peak_yield_normal,
            peak_energy_normal_ev,
            threshold_energy_ev,
            incidence_angle_deg,
            smoothness,
        )

    ceiling = threshold + MAX_SEARCH_V * (peak_energy - threshold)
    if curve(ceiling) >= 1.0:
        return None

    low, high = peak_energy, ceiling
    for _ in range(BISECTION_STEPS):
        mid = 0.5 * (low + high)
        if curve(mid) >= 1.0:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def susceptible_energy_band(
    peak_yield_normal,
    peak_energy_normal_ev,
    threshold_energy_ev=DEFAULT_E0_EV,
    incidence_angle_deg=0.0,
    smoothness=1.0,
):
    """The impact-energy band inside which an electron population can grow."""
    lower = first_crossover_energy(
        peak_yield_normal,
        peak_energy_normal_ev,
        threshold_energy_ev,
        incidence_angle_deg,
        smoothness,
    )
    upper = second_crossover_energy(
        peak_yield_normal,
        peak_energy_normal_ev,
        threshold_energy_ev,
        incidence_angle_deg,
        smoothness,
    )
    if lower is None or upper is None:
        return {
            "lower_crossover_ev": lower,
            "upper_crossover_ev": upper,
            "band_width_ev": None,
            "degenerate": True,
            "growth_possible": False,
        }
    degenerate = math.isclose(upper, lower, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return {
        "lower_crossover_ev": lower,
        "upper_crossover_ev": upper,
        "band_width_ev": upper - lower,
        "degenerate": degenerate,
        "growth_possible": (upper > lower) and not degenerate,
    }


def is_in_growth_band(
    impact_energy_ev,
    peak_yield_normal,
    peak_energy_normal_ev,
    threshold_energy_ev=DEFAULT_E0_EV,
    incidence_angle_deg=0.0,
    smoothness=1.0,
):
    """True only where delta exceeds one -- a yield at unity is not growth.

    At a crossover the computed yield lands a few units-in-the-last-place
    either side of one, so the unity case is recognised by tolerance and
    reported as replacement, not growth.
    """
    delta = vaughan_yield(
        impact_energy_ev,
        peak_yield_normal,
        peak_energy_normal_ev,
        threshold_energy_ev,
        incidence_angle_deg,
        smoothness,
    )
    if _is_unity(delta):
        return False
    return delta > 1.0


def categorize_surface_yield(peak_yield):
    """Sort a surface by its peak yield into the bands a provision reasons over.

    A peak yield at or below unity cannot sustain growth at any impact
    energy, so such a surface carries no susceptible band at all.
    """
    value = _require_number("peak yield", peak_yield)
    if value <= 0.0:
        raise ValueError("peak yield must be positive, got %r" % (value,))
    if _at_most(value, LOW_YIELD_CEILING):
        return "low-yield"
    if _at_most(value, MODERATE_YIELD_CEILING):
        return "moderate-yield"
    if _at_most(value, ELEVATED_YIELD_CEILING):
        return "elevated-yield"
    return "high-yield"


def evaluate_yield_definition(spec):
    """Apply the whole clause 9.1 definition to one declared surface.

    Returns the angle-corrected curve parameters, the susceptible band, the
    surface categorization and the yield at each impact energy the caller
    listed, with each energy marked as inside or outside the growth band.
    """
    if not isinstance(spec, dict):
        raise ValueError("surface specification must be a mapping")
    for key in ("peak_yield", "peak_energy_ev"):
        if key not in spec:
            raise ValueError("surface specification missing required key: %s" % key)
    peak_yield = spec["peak_yield"]
    peak_energy = spec["peak_energy_ev"]
    threshold = spec.get("threshold_energy_ev", DEFAULT_E0_EV)
    angle = spec.get("incidence_angle_deg", 0.0)
    rough = spec.get("smoothness", 1.0)
    energies = spec.get("impact_energies_ev", [])
    if not isinstance(energies, (list, tuple)):
        raise ValueError("impact energies must be a list")
    effective_peak, effective_energy = angle_corrected_parameters(
        peak_yield, peak_energy, angle, rough
    )
    band = susceptible_energy_band(peak_yield, peak_energy, threshold, angle, rough)
    samples = []
    for energy in energies:
        delta = vaughan_yield(energy, peak_yield, peak_energy, threshold, angle, rough)
        samples.append(
            {
                "impact_energy_ev": _require_number("impact energy", energy),
                "yield": delta,
                "in_growth_band": is_in_growth_band(
                    energy, peak_yield, peak_energy, threshold, angle, rough
                ),
            }
        )
    return {
        "effective_peak_yield": effective_peak,
        "effective_peak_energy_ev": effective_energy,
        "category": categorize_surface_yield(effective_peak),
        "band": band,
        "samples": samples,
        "growth_possible": band["growth_possible"],
    }
