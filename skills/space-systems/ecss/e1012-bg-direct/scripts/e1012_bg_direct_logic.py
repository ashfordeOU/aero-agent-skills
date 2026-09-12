"""
ECSS-E-ST-10-12C §10.4.2 — sensor background from direct ionisation.

Computes the background event rate in a spaceborne sensor produced by
charged particles traversing the active volume.  Paraphrased procedure;
ECSS clause is the normative anchor only.

stdlib only; offline; deterministic.
"""

# Recognised particle-population identifiers
KNOWN_PARTICLE_TYPES = frozenset({
    "trapped_proton",
    "trapped_electron",
    "gcr_proton",
    "gcr_heavy",
    "sep_proton",
    "sep_heavy",
})

# Hemisphere factor for isotropic omnidirectional flux onto a flat
# single-face detector: only the forward hemisphere illuminates one face.
_HEMISPHERE_FACTOR = 0.5


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_particle(particle):
    """Raise KeyError or ValueError if the particle record is malformed."""
    required = {"type", "flux_cm2_s", "let_mev_cm2_mg"}
    missing = required - particle.keys()
    if missing:
        raise KeyError(f"Particle record missing fields: {sorted(missing)}")
    if particle["type"] not in KNOWN_PARTICLE_TYPES:
        raise ValueError(
            f"Unknown particle type '{particle['type']}'. "
            f"Recognised types: {sorted(KNOWN_PARTICLE_TYPES)}"
        )
    if particle["flux_cm2_s"] < 0:
        raise ValueError("flux_cm2_s must be >= 0")
    if particle["let_mev_cm2_mg"] <= 0:
        raise ValueError("let_mev_cm2_mg must be > 0")


def validate_sensor(sensor):
    """Raise KeyError or ValueError if the sensor spec is malformed."""
    required = {"area_cm2", "thickness_cm", "density_g_cm3", "threshold_mev"}
    missing = required - sensor.keys()
    if missing:
        raise KeyError(f"Sensor spec missing fields: {sorted(missing)}")
    if sensor["area_cm2"] <= 0:
        raise ValueError("area_cm2 must be > 0")
    if sensor["thickness_cm"] <= 0:
        raise ValueError("thickness_cm must be > 0")
    if sensor["density_g_cm3"] <= 0:
        raise ValueError("density_g_cm3 must be > 0")
    if sensor["threshold_mev"] < 0:
        raise ValueError("threshold_mev must be >= 0")


# ---------------------------------------------------------------------------
# Physics kernels
# ---------------------------------------------------------------------------

def compute_deposited_energy_mev(let_mev_cm2_mg, density_g_cm3, path_length_cm):
    """
    Energy deposited per particle crossing (MeV).

    E [MeV] = LET [MeV·cm²/mg] × density [mg/cm³] × path_length [cm]
             = LET × (density_g_cm3 × 1000) × path_length_cm

    Assumes straight-line path of given length through the active material.
    """
    if let_mev_cm2_mg <= 0:
        raise ValueError("let_mev_cm2_mg must be > 0")
    if density_g_cm3 <= 0:
        raise ValueError("density_g_cm3 must be > 0")
    if path_length_cm <= 0:
        raise ValueError("path_length_cm must be > 0")
    density_mg_cm3 = density_g_cm3 * 1000.0
    return let_mev_cm2_mg * density_mg_cm3 * path_length_cm


def particle_above_threshold(deposited_mev, threshold_mev):
    """Return True if deposited energy meets or exceeds the detection threshold."""
    return deposited_mev >= threshold_mev


def compute_hit_rate(flux_cm2_s, area_cm2):
    """
    Raw hit rate (events/s) for a flat detector in an isotropic field.

    rate = flux [/cm²/s] × area [cm²] × hemisphere_factor
    """
    if flux_cm2_s < 0:
        raise ValueError("flux_cm2_s must be >= 0")
    if area_cm2 <= 0:
        raise ValueError("area_cm2 must be > 0")
    return flux_cm2_s * area_cm2 * _HEMISPHERE_FACTOR


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

class ParticleContribution:
    """Per-population contribution to the sensor background."""

    def __init__(self, particle_type, deposited_mev, above_threshold, hit_rate_s):
        self.particle_type = particle_type
        self.deposited_mev = deposited_mev
        self.above_threshold = above_threshold
        # Zero when the population is below threshold.
        self.hit_rate_s = hit_rate_s

    def __repr__(self):
        return (
            f"ParticleContribution(type={self.particle_type!r}, "
            f"deposited_mev={self.deposited_mev:.4g}, "
            f"above_threshold={self.above_threshold}, "
            f"hit_rate_s={self.hit_rate_s:.4g})"
        )


class BackgroundResult:
    """Aggregate result of a direct-ionisation background assessment."""

    def __init__(self, contributions, total_background_s, budget_s, budget_exceeded):
        self.contributions = contributions        # list[ParticleContribution]
        self.total_background_s = total_background_s  # events/s
        self.budget_s = budget_s                 # None when no budget provided
        self.budget_exceeded = budget_exceeded   # None when no budget provided

    def __repr__(self):
        return (
            f"BackgroundResult(total={self.total_background_s:.4g} evt/s, "
            f"budget={self.budget_s}, exceeded={self.budget_exceeded})"
        )


# ---------------------------------------------------------------------------
# Assessment entry point
# ---------------------------------------------------------------------------

def assess_sensor_background(particles, sensor, budget_events_s=None):
    """
    Compute the sensor background rate from direct ionisation.

    Parameters
    ----------
    particles : list of dict
        Each dict: {type, flux_cm2_s, let_mev_cm2_mg}.
    sensor : dict
        Keys: area_cm2, thickness_cm, density_g_cm3, threshold_mev.
    budget_events_s : float or None
        Allowable background rate (events/s).  None when not yet allocated.

    Returns
    -------
    BackgroundResult

    Raises
    ------
    ValueError  : empty particle list, negative/zero dimensions, unknown type.
    KeyError    : missing required keys in particle or sensor dicts.
    """
    validate_sensor(sensor)
    if not particles:
        raise ValueError("Particle list must not be empty")
    if budget_events_s is not None and budget_events_s < 0:
        raise ValueError("budget_events_s must be >= 0")

    contributions = []
    for p in particles:
        validate_particle(p)
        dep_mev = compute_deposited_energy_mev(
            p["let_mev_cm2_mg"],
            sensor["density_g_cm3"],
            sensor["thickness_cm"],
        )
        above = particle_above_threshold(dep_mev, sensor["threshold_mev"])
        rate = compute_hit_rate(p["flux_cm2_s"], sensor["area_cm2"]) if above else 0.0
        contributions.append(
            ParticleContribution(p["type"], dep_mev, above, rate)
        )

    total = sum(c.hit_rate_s for c in contributions)
    exceeded = (total > budget_events_s) if budget_events_s is not None else None

    return BackgroundResult(contributions, total, budget_events_s, exceeded)
