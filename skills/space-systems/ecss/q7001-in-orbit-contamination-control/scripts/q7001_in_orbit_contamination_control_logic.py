"""In-orbit self-contamination budgeting for a spacecraft sensitive surface.

Anchor: ECSS-Q-ST-70-01 operations clause (controlling contamination once in
orbit: material outgassing, thruster plume backflow, venting and released
particles depositing on a sensitive surface). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each outgassing source: its outgassing area, its initial specific
   outgassing rate, the decay time constant of that rate, the view factor from
   the source to the sensitive surface, and the fraction of arriving mass the
   surface retains.
2. Integrate the decaying rate over the mission window analytically, so a long
   mission does not depend on a step size.
3. Add the thruster contribution: the backflow fraction of the propellant mass
   expelled by the firings that can see the surface.
4. Add the released-particle term, which obscures area rather than forming a
   film, and is reported separately for that reason.
5. Convert the deposited mass per unit area into a film thickness through the
   deposit density, compare it with the mission allocation, and name the
   dominant source.
"""

import math

__all__ = [
    "SECONDS_PER_DAY",
    "DEFAULT_DEPOSIT_DENSITY_KG_PER_M3",
    "ALLOCATION_TOLERANCE",
    "validate_source",
    "outgassed_mass_kg",
    "sticking_coefficient",
    "source_deposit_kg_per_m2",
    "thruster_deposit_kg_per_m2",
    "particle_obscuration_ppm",
    "film_thickness_nm",
    "assess_in_orbit_contamination",
]

SECONDS_PER_DAY = 86400.0

# Representative condensed-organic deposit density, kilograms per cubic metre.
DEFAULT_DEPOSIT_DENSITY_KG_PER_M3 = 1100.0

# Deposition totals are sums of exponentials; a result landing on the
# allocation must not be failed by the last bit of the sum.
ALLOCATION_TOLERANCE = 1e-18

REQUIRED_SOURCE_KEYS = (
    "name",
    "area_m2",
    "initial_rate_kg_per_m2_s",
    "decay_time_constant_days",
    "view_factor",
)

# Sticking falls off as the receiving surface warms; these two anchors define
# the linear taper used between them.
STICKING_COLD_K = 150.0
STICKING_WARM_K = 350.0


def validate_source(source):
    """Return a normalized outgassing source, raising on anything invalid."""
    if not isinstance(source, dict):
        raise ValueError("an outgassing source must be a mapping")
    for key in REQUIRED_SOURCE_KEYS:
        if key not in source:
            raise ValueError("outgassing source missing required key '%s'" % key)
    name = source["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("source name must be a non-empty string")
    numbers = {}
    for key in ("area_m2", "initial_rate_kg_per_m2_s", "decay_time_constant_days"):
        value = source[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be a real number" % key)
        value = float(value)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (key, source[key]))
        numbers[key] = value
    view_factor = source["view_factor"]
    if isinstance(view_factor, bool) or not isinstance(view_factor, (int, float)):
        raise ValueError("view_factor must be a real number")
    view_factor = float(view_factor)
    if not math.isfinite(view_factor) or view_factor < 0.0 or view_factor > 1.0:
        raise ValueError("view_factor must lie in [0, 1], got %r" % (source["view_factor"],))
    return {
        "name": name.strip(),
        "area_m2": numbers["area_m2"],
        "initial_rate_kg_per_m2_s": numbers["initial_rate_kg_per_m2_s"],
        "decay_time_constant_days": numbers["decay_time_constant_days"],
        "view_factor": view_factor,
    }


def outgassed_mass_kg(source, mission_days):
    """Return the mass a decaying source emits over the mission window.

    The specific rate decays as r0 * exp(-t / tau), so the emitted mass is the
    analytic integral r0 * tau * (1 - exp(-T / tau)) times the area.
    """
    normalized = validate_source(source)
    if isinstance(mission_days, bool) or not isinstance(mission_days, (int, float)):
        raise ValueError("mission_days must be a real number")
    days = float(mission_days)
    if not math.isfinite(days) or days < 0.0:
        raise ValueError("mission_days must be non-negative and finite, got %r" % (mission_days,))
    tau_s = normalized["decay_time_constant_days"] * SECONDS_PER_DAY
    window_s = days * SECONDS_PER_DAY
    integral = tau_s * (1.0 - math.exp(-window_s / tau_s))
    return normalized["initial_rate_kg_per_m2_s"] * normalized["area_m2"] * integral


def sticking_coefficient(surface_temperature_k):
    """Return the fraction of arriving mass a surface at this temperature keeps."""
    if isinstance(surface_temperature_k, bool) or not isinstance(
        surface_temperature_k, (int, float)
    ):
        raise ValueError("surface_temperature_k must be a real number")
    temperature = float(surface_temperature_k)
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("surface_temperature_k must be positive and finite")
    if temperature <= STICKING_COLD_K:
        return 1.0
    if temperature >= STICKING_WARM_K:
        return 0.0
    span = STICKING_WARM_K - STICKING_COLD_K
    return (STICKING_WARM_K - temperature) / span


def source_deposit_kg_per_m2(source, mission_days, surface_temperature_k,
                             surface_area_m2):
    """Return the mass one source deposits per unit of receiving surface."""
    normalized = validate_source(source)
    if isinstance(surface_area_m2, bool) or not isinstance(surface_area_m2, (int, float)):
        raise ValueError("surface_area_m2 must be a real number")
    area = float(surface_area_m2)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("surface_area_m2 must be positive and finite")
    emitted = outgassed_mass_kg(source, mission_days)
    arriving = emitted * normalized["view_factor"]
    retained = arriving * sticking_coefficient(surface_temperature_k)
    return retained / area


def thruster_deposit_kg_per_m2(firings, surface_temperature_k, surface_area_m2):
    """Return the mass thruster backflow deposits per unit receiving area."""
    if not isinstance(firings, (list, tuple)):
        raise ValueError("firings must be a sequence of firing records")
    if isinstance(surface_area_m2, bool) or not isinstance(surface_area_m2, (int, float)):
        raise ValueError("surface_area_m2 must be a real number")
    area = float(surface_area_m2)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("surface_area_m2 must be positive and finite")
    sticking = sticking_coefficient(surface_temperature_k)
    total = 0.0
    for index, firing in enumerate(firings):
        if not isinstance(firing, dict):
            raise ValueError("firings[%d] must be a mapping" % index)
        for key in ("propellant_kg", "backflow_fraction", "view_factor"):
            if key not in firing:
                raise ValueError("firings[%d] missing required key '%s'" % (index, key))
        propellant = firing["propellant_kg"]
        if isinstance(propellant, bool) or not isinstance(propellant, (int, float)):
            raise ValueError("firings[%d].propellant_kg must be a real number" % index)
        propellant = float(propellant)
        if not math.isfinite(propellant) or propellant < 0.0:
            raise ValueError("firings[%d].propellant_kg must be non-negative" % index)
        for key in ("backflow_fraction", "view_factor"):
            value = firing[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("firings[%d].%s must be a real number" % (index, key))
            value = float(value)
            if not math.isfinite(value) or value < 0.0 or value > 1.0:
                raise ValueError("firings[%d].%s must lie in [0, 1]" % (index, key))
        total += (
            propellant
            * float(firing["backflow_fraction"])
            * float(firing["view_factor"])
            * sticking
        )
    return total / area


def particle_obscuration_ppm(released_particles, surface_area_m2):
    """Return the obscuration released particles add to the surface."""
    if not isinstance(released_particles, (list, tuple)):
        raise ValueError("released_particles must be a sequence")
    if isinstance(surface_area_m2, bool) or not isinstance(surface_area_m2, (int, float)):
        raise ValueError("surface_area_m2 must be a real number")
    area = float(surface_area_m2)
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("surface_area_m2 must be positive and finite")
    projected_m2 = 0.0
    for index, entry in enumerate(released_particles):
        if not isinstance(entry, dict):
            raise ValueError("released_particles[%d] must be a mapping" % index)
        for key in ("diameter_micron", "count", "capture_fraction"):
            if key not in entry:
                raise ValueError(
                    "released_particles[%d] missing required key '%s'" % (index, key)
                )
        diameter = entry["diameter_micron"]
        if isinstance(diameter, bool) or not isinstance(diameter, (int, float)):
            raise ValueError("released_particles[%d].diameter_micron must be numeric" % index)
        diameter = float(diameter)
        if not math.isfinite(diameter) or diameter <= 0.0:
            raise ValueError("released_particles[%d].diameter_micron must be positive" % index)
        count = entry["count"]
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("released_particles[%d].count must be an integer" % index)
        if count < 0:
            raise ValueError("released_particles[%d].count must not be negative" % index)
        capture = entry["capture_fraction"]
        if isinstance(capture, bool) or not isinstance(capture, (int, float)):
            raise ValueError("released_particles[%d].capture_fraction must be numeric" % index)
        capture = float(capture)
        if not math.isfinite(capture) or capture < 0.0 or capture > 1.0:
            raise ValueError("released_particles[%d].capture_fraction must lie in [0, 1]" % index)
        radius_m = 0.5 * diameter * 1e-6
        projected_m2 += float(count) * capture * math.pi * radius_m * radius_m
    return 1.0e6 * projected_m2 / area


def film_thickness_nm(deposit_kg_per_m2, density_kg_per_m3=None):
    """Convert a deposited mass per unit area into a film thickness."""
    if isinstance(deposit_kg_per_m2, bool) or not isinstance(
        deposit_kg_per_m2, (int, float)
    ):
        raise ValueError("deposit_kg_per_m2 must be a real number")
    deposit = float(deposit_kg_per_m2)
    if not math.isfinite(deposit) or deposit < 0.0:
        raise ValueError("deposit_kg_per_m2 must be non-negative and finite")
    density = (
        DEFAULT_DEPOSIT_DENSITY_KG_PER_M3 if density_kg_per_m3 is None else density_kg_per_m3
    )
    if isinstance(density, bool) or not isinstance(density, (int, float)):
        raise ValueError("density must be a real number")
    density = float(density)
    if not math.isfinite(density) or density <= 0.0:
        raise ValueError("density must be positive and finite")
    return (deposit / density) * 1.0e9


def assess_in_orbit_contamination(budget):
    """Run the full in-orbit self-contamination assessment.

    budget keys: sources (sequence of outgassing sources), mission_days,
    surface_area_m2, surface_temperature_k, allocation_nm, and optionally
    firings, released_particles, obscuration_allocation_ppm and
    deposit_density_kg_per_m3.
    """
    if not isinstance(budget, dict):
        raise ValueError("budget must be a mapping")
    for key in (
        "sources",
        "mission_days",
        "surface_area_m2",
        "surface_temperature_k",
        "allocation_nm",
    ):
        if key not in budget:
            raise ValueError("budget missing required key '%s'" % key)
    sources = budget["sources"]
    if not isinstance(sources, (list, tuple)) or not sources:
        raise ValueError("budget['sources'] must be a non-empty sequence")
    allocation = budget["allocation_nm"]
    if isinstance(allocation, bool) or not isinstance(allocation, (int, float)):
        raise ValueError("allocation_nm must be a real number")
    allocation = float(allocation)
    if not math.isfinite(allocation) or allocation <= 0.0:
        raise ValueError("allocation_nm must be positive and finite")

    area = budget["surface_area_m2"]
    temperature = budget["surface_temperature_k"]
    density = budget.get("deposit_density_kg_per_m3")

    contributions = []
    seen = set()
    total_deposit = 0.0
    for source in sources:
        normalized = validate_source(source)
        if normalized["name"] in seen:
            raise ValueError("source name %r appears twice" % normalized["name"])
        seen.add(normalized["name"])
        deposit = source_deposit_kg_per_m2(
            source, budget["mission_days"], temperature, area
        )
        total_deposit += deposit
        contributions.append(
            {
                "name": normalized["name"],
                "deposit_kg_per_m2": deposit,
                "thickness_nm": film_thickness_nm(deposit, density),
            }
        )

    firings = budget.get("firings") or []
    thruster_deposit = thruster_deposit_kg_per_m2(firings, temperature, area)
    if firings:
        total_deposit += thruster_deposit
        contributions.append(
            {
                "name": "thruster-plume-backflow",
                "deposit_kg_per_m2": thruster_deposit,
                "thickness_nm": film_thickness_nm(thruster_deposit, density),
            }
        )

    obscuration = particle_obscuration_ppm(budget.get("released_particles") or [], area)
    total_thickness = film_thickness_nm(total_deposit, density)

    findings = []
    within_film = total_thickness < allocation or math.isclose(
        total_thickness, allocation, rel_tol=1e-12, abs_tol=ALLOCATION_TOLERANCE
    )
    if not within_film:
        findings.append(
            "deposited film %.4f nm exceeds the %.4f nm mission allocation"
            % (total_thickness, allocation)
        )
    obscuration_allocation = budget.get("obscuration_allocation_ppm")
    if obscuration_allocation is not None:
        if isinstance(obscuration_allocation, bool) or not isinstance(
            obscuration_allocation, (int, float)
        ):
            raise ValueError("obscuration_allocation_ppm must be a real number")
        obscuration_allocation = float(obscuration_allocation)
        if not math.isfinite(obscuration_allocation) or obscuration_allocation < 0.0:
            raise ValueError("obscuration_allocation_ppm must be non-negative and finite")
        within_particles = obscuration < obscuration_allocation or math.isclose(
            obscuration, obscuration_allocation, rel_tol=1e-12, abs_tol=1e-15
        )
        if not within_particles:
            findings.append(
                "released-particle obscuration %.4f ppm exceeds the %.4f ppm allocation"
                % (obscuration, obscuration_allocation)
            )
    if sticking_coefficient(temperature) <= 0.0:
        findings.append(
            "the receiving surface is warm enough that nothing is retained; "
            "confirm the temperature used is the cold-case one"
        )

    dominant = max(contributions, key=lambda entry: entry["deposit_kg_per_m2"])
    return {
        "contributions": contributions,
        "total_deposit_kg_per_m2": total_deposit,
        "total_thickness_nm": total_thickness,
        "allocation_nm": allocation,
        "thickness_margin_nm": allocation - total_thickness,
        "particle_obscuration_ppm": obscuration,
        "dominant_source": dominant["name"],
        "within_allocation": not findings,
        "findings": findings,
    }
