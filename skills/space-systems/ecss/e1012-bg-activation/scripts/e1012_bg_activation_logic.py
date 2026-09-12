"""
Activation background prediction — ECSS-E-ST-10C §10.4.4.

Computes the radiation background from induced radioactive activation of
spacecraft materials: saturation activity, build-up during irradiation,
decay after irradiation, and conversion to detector count rate or dose rate.

stdlib only; no external dependencies.
"""

import math

AVOGADRO = 6.02214076e23
JOULES_PER_MEV = 1.60218e-13
FULL_SPHERE_SR = 4.0 * math.pi


class ActivationError(ValueError):
    """Raised for non-physical or missing input parameters."""


# ---------------------------------------------------------------------------
# Fundamental helpers
# ---------------------------------------------------------------------------

def decay_constant(half_life_s: float) -> float:
    """Return decay constant λ = ln2 / T½ [s⁻¹]."""
    if half_life_s <= 0.0:
        raise ActivationError(
            f"half_life_s must be positive, got {half_life_s}"
        )
    return math.log(2.0) / half_life_s


def n_atoms_from_mass(mass_g: float, atomic_mass_u: float) -> float:
    """
    Return number of target atoms N = (mass_g / atomic_mass_u) × N_A.

    mass_g        : sample mass [g]
    atomic_mass_u : atomic mass of the target isotope [u]
    """
    if mass_g <= 0.0:
        raise ActivationError(f"mass_g must be positive, got {mass_g}")
    if atomic_mass_u <= 0.0:
        raise ActivationError(
            f"atomic_mass_u must be positive, got {atomic_mass_u}"
        )
    return (mass_g / atomic_mass_u) * AVOGADRO


# ---------------------------------------------------------------------------
# Activation activity chain
# ---------------------------------------------------------------------------

def saturation_activity(
    flux_cm2_s: float,
    cross_section_cm2: float,
    n_atoms: float,
) -> float:
    """
    Return saturation activity A_sat = Φ · σ · N [Bq].

    flux_cm2_s       : incident particle flux [cm⁻² s⁻¹] (≥ 0)
    cross_section_cm2: reaction cross-section for the target isotope [cm²] (> 0)
    n_atoms          : number of target atoms (> 0)
    """
    if flux_cm2_s < 0.0:
        raise ActivationError(
            f"flux_cm2_s must be >= 0, got {flux_cm2_s}"
        )
    if cross_section_cm2 <= 0.0:
        raise ActivationError(
            f"cross_section_cm2 must be positive, got {cross_section_cm2}"
        )
    if n_atoms <= 0.0:
        raise ActivationError(f"n_atoms must be positive, got {n_atoms}")
    return flux_cm2_s * cross_section_cm2 * n_atoms


def buildup_activity(
    a_sat: float,
    lam: float,
    irr_time_s: float,
) -> float:
    """
    Return activity at end of irradiation [Bq].

    A(t_irr) = A_sat × (1 − exp(−λ · t_irr))

    a_sat     : saturation activity [Bq] (≥ 0)
    lam       : decay constant [s⁻¹] (> 0)
    irr_time_s: irradiation duration [s] (≥ 0)
    """
    if a_sat < 0.0:
        raise ActivationError(f"a_sat must be >= 0, got {a_sat}")
    if lam <= 0.0:
        raise ActivationError(f"lam must be positive, got {lam}")
    if irr_time_s < 0.0:
        raise ActivationError(
            f"irr_time_s must be >= 0, got {irr_time_s}"
        )
    return a_sat * (1.0 - math.exp(-lam * irr_time_s))


def decay_activity(
    a_eoi: float,
    lam: float,
    cool_time_s: float,
) -> float:
    """
    Return activity after a cooling interval [Bq].

    A(t_cool) = A_eoi × exp(−λ · t_cool)

    a_eoi      : end-of-irradiation activity [Bq] (≥ 0)
    lam        : decay constant [s⁻¹] (> 0)
    cool_time_s: elapsed time after end of irradiation [s] (≥ 0)
    """
    if a_eoi < 0.0:
        raise ActivationError(f"a_eoi must be >= 0, got {a_eoi}")
    if lam <= 0.0:
        raise ActivationError(f"lam must be positive, got {lam}")
    if cool_time_s < 0.0:
        raise ActivationError(
            f"cool_time_s must be >= 0, got {cool_time_s}"
        )
    return a_eoi * math.exp(-lam * cool_time_s)


# ---------------------------------------------------------------------------
# Background conversion
# ---------------------------------------------------------------------------

def background_count_rate(
    activity_bq: float,
    solid_angle_sr: float,
    detection_efficiency: float,
) -> float:
    """
    Return background count rate at a detector [counts s⁻¹].

    CR = A × (Ω / 4π) × ε

    activity_bq        : residual activity of the source [Bq] (≥ 0)
    solid_angle_sr     : solid angle subtended by detector aperture [sr]
                         in (0, 4π]
    detection_efficiency: fraction of particles that produce a count
                         in (0, 1]
    """
    if activity_bq < 0.0:
        raise ActivationError(
            f"activity_bq must be >= 0, got {activity_bq}"
        )
    if not (0.0 < solid_angle_sr <= FULL_SPHERE_SR):
        raise ActivationError(
            f"solid_angle_sr must be in (0, 4π], got {solid_angle_sr}"
        )
    if not (0.0 < detection_efficiency <= 1.0):
        raise ActivationError(
            f"detection_efficiency must be in (0, 1], got {detection_efficiency}"
        )
    return activity_bq * (solid_angle_sr / FULL_SPHERE_SR) * detection_efficiency


def dose_rate_from_activity(
    activity_bq: float,
    gamma_energy_mev: float,
    mass_g: float,
    geometry_factor: float = 1.0,
) -> float:
    """
    Return absorbed dose rate in a target mass [Gy s⁻¹].

    D˙ = A × E_γ × 1.602×10⁻¹³ × geometry_factor / mass_kg

    Simplified point-source formula; geometry_factor accounts for
    attenuation or build-up (1.0 = no attenuation, < 1 = shielded).

    activity_bq    : residual activity [Bq] (≥ 0)
    gamma_energy_mev: mean gamma energy per disintegration [MeV] (> 0)
    mass_g         : target (detector) mass [g] (> 0)
    geometry_factor: dimensionless attenuation/build-up correction (> 0)
    """
    if activity_bq < 0.0:
        raise ActivationError(f"activity_bq must be >= 0, got {activity_bq}")
    if gamma_energy_mev <= 0.0:
        raise ActivationError(
            f"gamma_energy_mev must be positive, got {gamma_energy_mev}"
        )
    if mass_g <= 0.0:
        raise ActivationError(f"mass_g must be positive, got {mass_g}")
    if geometry_factor <= 0.0:
        raise ActivationError(
            f"geometry_factor must be positive, got {geometry_factor}"
        )
    mass_kg = mass_g * 1e-3
    return (
        activity_bq * gamma_energy_mev * JOULES_PER_MEV * geometry_factor / mass_kg
    )


# ---------------------------------------------------------------------------
# Higher-level objects
# ---------------------------------------------------------------------------

class ActivationProduct:
    """Single activation product from an irradiated target isotope."""

    def __init__(
        self,
        name: str,
        half_life_s: float,
        flux_cm2_s: float,
        cross_section_cm2: float,
        n_atoms: float,
    ) -> None:
        if not name or not isinstance(name, str):
            raise ActivationError("name must be a non-empty string")
        self.name = name
        self.lam = decay_constant(half_life_s)
        self.a_sat = saturation_activity(flux_cm2_s, cross_section_cm2, n_atoms)

    def activity_at(self, irr_time_s: float, cool_time_s: float = 0.0) -> float:
        """Return activity [Bq] after irr_time_s irradiation and cool_time_s cooling."""
        a_eoi = buildup_activity(self.a_sat, self.lam, irr_time_s)
        return decay_activity(a_eoi, self.lam, cool_time_s)


class ActivationBackground:
    """
    Aggregate activation background from a collection of activation products.

    Products are added one at a time; total activity and dominant-source
    fraction are derived on demand.
    """

    def __init__(self) -> None:
        self._products: list = []

    def add_product(self, product: ActivationProduct) -> None:
        if not isinstance(product, ActivationProduct):
            raise ActivationError("product must be an ActivationProduct instance")
        self._products.append(product)

    def product_count(self) -> int:
        return len(self._products)

    def total_activity(self, irr_time_s: float, cool_time_s: float = 0.0) -> float:
        """Return summed activity [Bq] from all registered products."""
        return sum(p.activity_at(irr_time_s, cool_time_s) for p in self._products)

    def dominant_products(
        self,
        irr_time_s: float,
        cool_time_s: float = 0.0,
        threshold: float = 0.10,
    ) -> list:
        """
        Return names of products whose individual activity exceeds
        `threshold` fraction of the total (default 10 %).
        Returns an empty list when total activity is zero.
        """
        total = self.total_activity(irr_time_s, cool_time_s)
        if total == 0.0:
            return []
        return [
            p.name
            for p in self._products
            if p.activity_at(irr_time_s, cool_time_s) / total > threshold
        ]
