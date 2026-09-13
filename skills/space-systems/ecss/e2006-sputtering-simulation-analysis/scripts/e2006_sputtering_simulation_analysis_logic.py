#!/usr/bin/env python3
"""ECSS-E-ST-20-06C clause 11.3.4 -- sputter erosion from simulated ion trajectories.

Deterministic, offline, stdlib-only implementation of the clause 11.3.4
procedure: take the ion populations produced by an electric-propulsion
plume trajectory simulation, categorize each population, decide whether its
trajectory geometrically reaches a given external surface, evaluate the
energy- and angle-dependent sputter yield of the surface material, integrate
the removed thickness over the firing duration, and compare the result with
the erosion allowance declared for that surface.

The standard is referenced as the procedural anchor only; every model here is
a paraphrased, implementable engineering formulation.
"""

from __future__ import annotations

import math

# --- physical constants -------------------------------------------------
AMU_KG = 1.66053906660e-27

# --- model constants ----------------------------------------------------
#: Emission angles beyond this value point back towards the vehicle body.
BACKFLOW_ANGLE_DEG = 90.0
#: Populations at or below this energy are dominated by resonant
#: charge-exchange products rather than accelerated beam ions.
CHARGE_EXCHANGE_CEILING_EV = 50.0
#: Half-angle of the dense beam core of a gridded or Hall thruster.
BEAM_CORE_HALF_ANGLE_DEG = 20.0
#: Impact angles above this value are treated as grazing (no net removal).
GRAZING_LIMIT_DEG = 85.0
#: Yamamura-style angular exponents for the incidence enhancement factor.
ANGULAR_EXPONENT = 1.7
ANGULAR_DECAY = 1.2
#: Overall normalisation of the threshold yield model (atoms per ion).
YIELD_SCALE = 0.045
#: High-energy roll-off knee of the yield model, in eV.
YIELD_KNEE_EV = 2000.0
#: Minimum number of simulated trajectories per population for the result to
#: be statistically usable at clause 11.3.4 level.
DEFAULT_SAMPLE_FLOOR = 5000
#: Relative tolerance used when a computed depth sits exactly on an
#: allowance. Representation error must never turn a compliant surface red.
DEPTH_TOLERANCE_REL = 1e-9
DEPTH_TOLERANCE_ABS = 1e-12

POPULATION_KINDS = (
    "primary-beam",
    "beam-wing",
    "charge-exchange",
    "backflow",
)

#: Propellant ion species that a clause 11.3.4 simulation may emit.
ION_SPECIES = {
    "xenon-single": {"mass_amu": 131.29, "charge_state": 1},
    "xenon-double": {"mass_amu": 131.29, "charge_state": 2},
    "krypton-single": {"mass_amu": 83.80, "charge_state": 1},
    "krypton-double": {"mass_amu": 83.80, "charge_state": 2},
    "argon-single": {"mass_amu": 39.95, "charge_state": 1},
    "iodine-single": {"mass_amu": 126.90, "charge_state": 1},
}

#: Target materials found on external surfaces exposed to a plume.
TARGET_MATERIALS = {
    "aluminium-6061": {
        "mass_amu": 26.98,
        "density_kg_m3": 2700.0,
        "threshold_ev": 24.0,
    },
    "kapton-film": {
        "mass_amu": 12.01,
        "density_kg_m3": 1420.0,
        "threshold_ev": 18.0,
    },
    "fused-silica-cover": {
        "mass_amu": 20.03,
        "density_kg_m3": 2200.0,
        "threshold_ev": 30.0,
    },
    "molybdenum-grid": {
        "mass_amu": 95.95,
        "density_kg_m3": 10220.0,
        "threshold_ev": 55.0,
    },
    "titanium-6al4v": {
        "mass_amu": 47.87,
        "density_kg_m3": 4430.0,
        "threshold_ev": 35.0,
    },
    "silver-interconnect": {
        "mass_amu": 107.87,
        "density_kg_m3": 10490.0,
        "threshold_ev": 15.0,
    },
}


def _positive(value, label):
    """Return value as a strictly positive float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _non_negative(value, label):
    """Return value as a non-negative float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return out


def _angle(value, label, lo=0.0, hi=180.0):
    """Return value as a float angle inside [lo, hi] or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if not math.isfinite(out) or not (lo <= out <= hi):
        raise ValueError("%s must lie in [%g, %g] deg, got %r" % (label, lo, hi, value))
    return out


def ion_energy_ev(species, accel_voltage_v):
    """Kinetic energy of one ion of *species* fallen through *accel_voltage_v*.

    A charge state of q gains q electron-volts per volt of net acceleration.
    """
    if species not in ION_SPECIES:
        raise ValueError("unknown ion species %r" % (species,))
    volts = _positive(accel_voltage_v, "accel_voltage_v")
    return ION_SPECIES[species]["charge_state"] * volts


def categorize_ion_population(energy_ev, emission_angle_deg):
    """Assign one simulated ion population to a clause 11.3.4 family.

    Returns one of POPULATION_KINDS. Energies at or below the
    charge-exchange ceiling are slow secondary ions regardless of angle;
    faster ions split between the dense beam core and its wings.
    """
    energy = _non_negative(energy_ev, "energy_ev")
    angle = _angle(emission_angle_deg, "emission_angle_deg", 0.0, 180.0)
    if angle > BACKFLOW_ANGLE_DEG:
        return "backflow"
    if energy <= CHARGE_EXCHANGE_CEILING_EV:
        return "charge-exchange"
    if angle <= BEAM_CORE_HALF_ANGLE_DEG:
        return "primary-beam"
    return "beam-wing"


def trajectory_intercepts_surface(emission_angle_deg, span_start_deg, span_end_deg):
    """True when a trajectory at *emission_angle_deg* crosses a surface span.

    The surface is described by the inclusive angular span it subtends as
    seen from the thruster exit plane.
    """
    angle = _angle(emission_angle_deg, "emission_angle_deg", 0.0, 180.0)
    start = _angle(span_start_deg, "span_start_deg", 0.0, 180.0)
    end = _angle(span_end_deg, "span_end_deg", 0.0, 180.0)
    if start >= end:
        raise ValueError(
            "surface span must satisfy span_start_deg < span_end_deg, got %g >= %g"
            % (start, end)
        )
    return start <= angle <= end


def impact_angle_deg(emission_angle_deg, surface_normal_deg):
    """Angle between the incoming trajectory and the surface normal, in deg."""
    emission = _angle(emission_angle_deg, "emission_angle_deg", 0.0, 180.0)
    normal = _angle(surface_normal_deg, "surface_normal_deg", 0.0, 180.0)
    return abs(emission - normal)


def angular_enhancement(incidence_deg):
    """Incidence-angle enhancement factor of the sputter yield.

    Normal incidence gives 1.0; oblique incidence raises the yield until the
    grazing limit, beyond which the ion is treated as reflected and the
    factor collapses to zero.
    """
    theta = _angle(incidence_deg, "incidence_deg", 0.0, 180.0)
    if theta >= GRAZING_LIMIT_DEG:
        return 0.0
    inv_cos = 1.0 / math.cos(math.radians(theta))
    return (inv_cos ** ANGULAR_EXPONENT) * math.exp(ANGULAR_DECAY * (1.0 - inv_cos))


def sputter_yield_atoms_per_ion(species, material, energy_ev, incidence_deg):
    """Atoms removed per incident ion, threshold model with angular term.

    Below the material sputter threshold the yield is exactly zero; above it
    the yield grows with the excess energy and rolls off at high energy as
    the ion penetrates past the near-surface layer.
    """
    if species not in ION_SPECIES:
        raise ValueError("unknown ion species %r" % (species,))
    if material not in TARGET_MATERIALS:
        raise ValueError("unknown target material %r" % (material,))
    energy = _non_negative(energy_ev, "energy_ev")
    target = TARGET_MATERIALS[material]
    threshold = target["threshold_ev"]
    if energy <= threshold:
        return 0.0
    projectile = ION_SPECIES[species]["mass_amu"]
    target_mass = target["mass_amu"]
    # Momentum-transfer efficiency between projectile and target atom.
    transfer = 4.0 * projectile * target_mass / ((projectile + target_mass) ** 2)
    excess = (energy / threshold) - 1.0
    roll_off = 1.0 / (1.0 + energy / YIELD_KNEE_EV)
    normal_yield = YIELD_SCALE * transfer * (excess ** 1.15) * roll_off
    return normal_yield * angular_enhancement(incidence_deg)


def erosion_depth_um(material, yield_atoms_per_ion, flux_ions_m2_s, duration_s):
    """Thickness removed from *material*, in micrometres.

    Removed atoms per unit area are converted to a depth through the atomic
    volume implied by the material molar mass and density.
    """
    if material not in TARGET_MATERIALS:
        raise ValueError("unknown target material %r" % (material,))
    y = _non_negative(yield_atoms_per_ion, "yield_atoms_per_ion")
    flux = _non_negative(flux_ions_m2_s, "flux_ions_m2_s")
    duration = _non_negative(duration_s, "duration_s")
    target = TARGET_MATERIALS[material]
    atom_volume_m3 = (target["mass_amu"] * AMU_KG) / target["density_kg_m3"]
    depth_m = y * flux * duration * atom_volume_m3
    return depth_m * 1.0e6


def check_simulation_fidelity(population, sample_floor=DEFAULT_SAMPLE_FLOOR):
    """Return a finding string when the trajectory sample count is too thin."""
    floor = _positive(sample_floor, "sample_floor")
    raw = population.get("sample_count")
    if raw is None:
        return "population %s: no trajectory sample_count on record" % (
            population.get("population_id", "<unnamed>"),
        )
    samples = _non_negative(raw, "sample_count")
    if samples < floor:
        return "population %s: %d simulated trajectories below the floor of %d" % (
            population.get("population_id", "<unnamed>"),
            int(samples),
            int(floor),
        )
    return None


def normalize_population(record):
    """Validate one simulated ion population and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("population record must be a mapping, got %r" % (record,))
    pop_id = record.get("population_id")
    if not pop_id:
        raise ValueError("population record missing population_id")
    species = record.get("species")
    if species not in ION_SPECIES:
        raise ValueError("population %s: unknown ion species %r" % (pop_id, species))
    energy = ion_energy_ev(species, record.get("accel_voltage_v"))
    emission = _angle(record.get("emission_angle_deg"), "emission_angle_deg", 0.0, 180.0)
    flux = _non_negative(record.get("flux_ions_m2_s"), "flux_ions_m2_s")
    return {
        "population_id": pop_id,
        "species": species,
        "energy_ev": energy,
        "emission_angle_deg": emission,
        "flux_ions_m2_s": flux,
        "sample_count": record.get("sample_count"),
        "kind": categorize_ion_population(energy, emission),
    }


def _within_allowance(depth_um, allowance_um):
    """Depth is compliant when it is below, or numerically on, the allowance."""
    if depth_um <= allowance_um:
        return True
    return math.isclose(
        depth_um,
        allowance_um,
        rel_tol=DEPTH_TOLERANCE_REL,
        abs_tol=DEPTH_TOLERANCE_ABS,
    )


def assess_surface_erosion(surface, populations, duration_s):
    """Integrate erosion on one external surface over every population.

    Returns a mapping with the total depth, the per-population contributions,
    the allowance comparison and any findings raised for that surface.
    """
    if not isinstance(surface, dict):
        raise ValueError("surface record must be a mapping, got %r" % (surface,))
    surface_id = surface.get("surface_id")
    if not surface_id:
        raise ValueError("surface record missing surface_id")
    material = surface.get("material")
    if material not in TARGET_MATERIALS:
        raise ValueError("surface %s: unknown material %r" % (surface_id, material))
    duration = _non_negative(duration_s, "duration_s")
    normal = _angle(surface.get("normal_angle_deg"), "normal_angle_deg", 0.0, 180.0)
    span_start = surface.get("span_start_deg")
    span_end = surface.get("span_end_deg")

    contributions = []
    findings = []
    total_um = 0.0
    for raw in populations:
        pop = normalize_population(raw)
        if not trajectory_intercepts_surface(
            pop["emission_angle_deg"], span_start, span_end
        ):
            continue
        incidence = impact_angle_deg(pop["emission_angle_deg"], normal)
        y = sputter_yield_atoms_per_ion(
            pop["species"], material, pop["energy_ev"], incidence
        )
        depth = erosion_depth_um(material, y, pop["flux_ions_m2_s"], duration)
        total_um += depth
        contributions.append(
            {
                "population_id": pop["population_id"],
                "kind": pop["kind"],
                "incidence_deg": incidence,
                "yield_atoms_per_ion": y,
                "depth_um": depth,
            }
        )
        fidelity = check_simulation_fidelity(pop)
        if fidelity:
            findings.append(fidelity)

    allowance = surface.get("erosion_allowance_um")
    if allowance is None:
        if contributions:
            findings.append(
                "surface %s: ion trajectories reach it but no erosion allowance "
                "is on record" % surface_id
            )
        compliant = False if contributions else True
    else:
        allowance = _non_negative(allowance, "erosion_allowance_um")
        compliant = _within_allowance(total_um, allowance)
        if not compliant:
            findings.append(
                "surface %s: erosion depth %.4g um exceeds the allowance %.4g um"
                % (surface_id, total_um, allowance)
            )
    return {
        "surface_id": surface_id,
        "material": material,
        "total_depth_um": total_um,
        "erosion_allowance_um": allowance,
        "contributions": contributions,
        "findings": findings,
        "compliant": compliant and not findings,
    }


def assess_sputtering_campaign(surfaces, populations, duration_s):
    """Run the clause 11.3.4 assessment across every surface in the campaign."""
    if not surfaces:
        raise ValueError("at least one surface is required for the assessment")
    if not populations:
        raise ValueError("at least one ion population is required")
    results = [assess_surface_erosion(s, populations, duration_s) for s in surfaces]
    findings = []
    for result in results:
        findings.extend(result["findings"])
    worst = max(results, key=lambda r: r["total_depth_um"])
    return {
        "surfaces": results,
        "findings": findings,
        "worst_surface_id": worst["surface_id"],
        "worst_depth_um": worst["total_depth_um"],
        "compliant": all(r["compliant"] for r in results),
    }
