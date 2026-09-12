"""
insert_analysis_logic.py

Deterministic insert strength and margin-of-safety calculations for
metallic, honeycomb-sandwich, and composite substrates.
Reference clause: ECSS-E-ST-32C section 4.6.2.16.

No external dependencies — stdlib only.
"""
import math


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class InsertAnalysisError(ValueError):
    """Raised when input parameters are physically inadmissible."""


# ---------------------------------------------------------------------------
# Internal validation helpers
# ---------------------------------------------------------------------------

def _require_positive(**kwargs):
    for name, value in kwargs.items():
        if value <= 0:
            raise InsertAnalysisError(
                f"'{name}' must be positive (got {value!r})"
            )


def _require_non_negative(**kwargs):
    for name, value in kwargs.items():
        if value < 0:
            raise InsertAnalysisError(
                f"'{name}' must be non-negative (got {value!r})"
            )


# ---------------------------------------------------------------------------
# Substrate identifiers
# ---------------------------------------------------------------------------

SUBSTRATE_HONEYCOMB = "honeycomb"
SUBSTRATE_METAL = "metal"
SUBSTRATE_COMPOSITE = "composite"


# ---------------------------------------------------------------------------
# Honeycomb potted-insert — individual strength functions
# ---------------------------------------------------------------------------

def potted_insert_pullout_strength(
    potting_diameter_mm: float,
    core_thickness_mm: float,
    core_shear_strength_mpa: float,
) -> float:
    """
    Axial (pull-out) strength of a potted insert in honeycomb core.

    Governing failure: shear of the honeycomb core around the potting
    cylinder perimeter.

        F = pi * d_pot * t_core * tau_core

    Args:
        potting_diameter_mm: outer diameter of the potting cylinder [mm]
        core_thickness_mm: honeycomb core thickness [mm]
        core_shear_strength_mpa: core shear allowable [N/mm^2]

    Returns:
        Pull-out strength [N]
    """
    _require_positive(
        potting_diameter_mm=potting_diameter_mm,
        core_thickness_mm=core_thickness_mm,
        core_shear_strength_mpa=core_shear_strength_mpa,
    )
    shear_perimeter = math.pi * potting_diameter_mm
    return shear_perimeter * core_thickness_mm * core_shear_strength_mpa


def potted_insert_shear_strength(
    potting_diameter_mm: float,
    potting_shear_strength_mpa: float,
) -> float:
    """
    Lateral (shear) strength of a potted insert.

    The potting cross-section area resists the lateral load:

        F = (pi/4) * d_pot^2 * tau_pot

    Args:
        potting_diameter_mm: outer diameter of the potting cylinder [mm]
        potting_shear_strength_mpa: potting compound shear allowable [N/mm^2]

    Returns:
        Shear strength [N]
    """
    _require_positive(
        potting_diameter_mm=potting_diameter_mm,
        potting_shear_strength_mpa=potting_shear_strength_mpa,
    )
    area = math.pi * (potting_diameter_mm / 2.0) ** 2
    return area * potting_shear_strength_mpa


# ---------------------------------------------------------------------------
# Metal threaded-insert — individual strength functions
# ---------------------------------------------------------------------------

def metal_insert_pullout_strength(
    nominal_diameter_mm: float,
    engagement_length_mm: float,
    material_shear_strength_mpa: float,
) -> float:
    """
    Thread-stripping (pull-out) strength of a threaded insert in solid metal.

    Failure is shear of the engagement cylinder:

        F = pi * d_nom * L_engage * tau_allow

    Args:
        nominal_diameter_mm: nominal thread diameter [mm]
        engagement_length_mm: effective thread engagement length [mm]
        material_shear_strength_mpa: shear allowable of the weaker thread
            material (insert or parent) [N/mm^2]

    Returns:
        Pull-out strength [N]
    """
    _require_positive(
        nominal_diameter_mm=nominal_diameter_mm,
        engagement_length_mm=engagement_length_mm,
        material_shear_strength_mpa=material_shear_strength_mpa,
    )
    shear_area = math.pi * nominal_diameter_mm * engagement_length_mm
    return shear_area * material_shear_strength_mpa


def metal_insert_shear_strength(
    nominal_diameter_mm: float,
    material_shear_strength_mpa: float,
) -> float:
    """
    Cross-section shear strength of a threaded insert shank in solid metal.

    The gross cross-section carries the lateral load:

        F = (pi/4) * d_nom^2 * tau_allow

    Args:
        nominal_diameter_mm: nominal shank diameter [mm]
        material_shear_strength_mpa: shear allowable [N/mm^2]

    Returns:
        Shear strength [N]
    """
    _require_positive(
        nominal_diameter_mm=nominal_diameter_mm,
        material_shear_strength_mpa=material_shear_strength_mpa,
    )
    area = math.pi * (nominal_diameter_mm / 2.0) ** 2
    return area * material_shear_strength_mpa


# ---------------------------------------------------------------------------
# Composite insert — individual strength functions
# ---------------------------------------------------------------------------

def composite_insert_bearing_strength(
    bolt_diameter_mm: float,
    laminate_thickness_mm: float,
    bearing_strength_mpa: float,
) -> float:
    """
    Bearing (lateral) strength of an insert in a composite laminate.

    The projected bearing area resists the lateral load:

        F_bear = d_bolt * t_lam * sigma_bear

    Args:
        bolt_diameter_mm: fastener or insert shank diameter [mm]
        laminate_thickness_mm: total laminate thickness through the joint [mm]
        bearing_strength_mpa: laminate bearing allowable [N/mm^2]

    Returns:
        Bearing strength [N]
    """
    _require_positive(
        bolt_diameter_mm=bolt_diameter_mm,
        laminate_thickness_mm=laminate_thickness_mm,
        bearing_strength_mpa=bearing_strength_mpa,
    )
    bearing_area = bolt_diameter_mm * laminate_thickness_mm
    return bearing_area * bearing_strength_mpa


def composite_insert_pullthrough_strength(
    bolt_diameter_mm: float,
    laminate_thickness_mm: float,
    interlaminar_shear_mpa: float,
) -> float:
    """
    Pull-through (axial) strength of an insert in a composite laminate.

    Failure is shear of a laminate cylinder around the fastener perimeter:

        F_pull = pi * d_bolt * t_lam * tau_ILS

    Args:
        bolt_diameter_mm: fastener or insert shank diameter [mm]
        laminate_thickness_mm: laminate thickness through which pull-through
            occurs [mm]
        interlaminar_shear_mpa: interlaminar shear allowable [N/mm^2]

    Returns:
        Pull-through strength [N]
    """
    _require_positive(
        bolt_diameter_mm=bolt_diameter_mm,
        laminate_thickness_mm=laminate_thickness_mm,
        interlaminar_shear_mpa=interlaminar_shear_mpa,
    )
    shear_area = math.pi * bolt_diameter_mm * laminate_thickness_mm
    return shear_area * interlaminar_shear_mpa


# ---------------------------------------------------------------------------
# Combined-load interaction and margin of safety
# ---------------------------------------------------------------------------

def combined_load_ratio(
    axial_n: float,
    shear_n: float,
    pullout_strength_n: float,
    shear_strength_n: float,
) -> float:
    """
    Quadratic combined-load interaction ratio.

        R = (P / F_pullout)^2 + (V / F_shear)^2

    R <= 1.0 means the insert is within its combined-load envelope.

    Args:
        axial_n: applied axial (pull-out) load [N], non-negative
        shear_n: applied lateral (shear) load [N], non-negative
        pullout_strength_n: pull-out allowable [N], positive
        shear_strength_n: shear allowable [N], positive

    Returns:
        Dimensionless interaction ratio R
    """
    _require_positive(
        pullout_strength_n=pullout_strength_n,
        shear_strength_n=shear_strength_n,
    )
    _require_non_negative(axial_n=axial_n, shear_n=shear_n)
    r_axial = axial_n / pullout_strength_n
    r_shear = shear_n / shear_strength_n
    return r_axial ** 2 + r_shear ** 2


def margin_of_safety_from_ratio(interaction_ratio: float) -> float:
    """
    Margin of safety from a quadratic interaction ratio R.

        MS = 1 / sqrt(R) - 1

    MS >= 0 means the insert is structurally adequate.

    Args:
        interaction_ratio: value returned by combined_load_ratio, must be > 0

    Returns:
        Margin of safety (dimensionless)

    Raises:
        InsertAnalysisError: if interaction_ratio <= 0
    """
    if interaction_ratio <= 0:
        raise InsertAnalysisError(
            f"interaction_ratio must be > 0 (got {interaction_ratio!r})"
        )
    return 1.0 / math.sqrt(interaction_ratio) - 1.0


# ---------------------------------------------------------------------------
# High-level assessment functions
# ---------------------------------------------------------------------------

def _build_result(
    f_pull: float,
    f_shear: float,
    p_factored: float,
    v_factored: float,
    substrate: str,
) -> dict:
    """Shared result-building logic for all three assess_* functions."""
    if p_factored == 0.0 and v_factored == 0.0:
        return {
            "pullout_strength_n": f_pull,
            "shear_strength_n": f_shear,
            "interaction_ratio": 0.0,
            "margin_of_safety": float("inf"),
            "is_acceptable": True,
            "failure_mode": "acceptable",
            "substrate": substrate,
        }
    r = combined_load_ratio(p_factored, v_factored, f_pull, f_shear)
    ms = margin_of_safety_from_ratio(r)
    acceptable = ms >= 0.0
    if acceptable:
        mode = "acceptable"
    elif (p_factored / f_pull) >= (v_factored / f_shear):
        mode = "pullout"
    else:
        mode = "shear"
    return {
        "pullout_strength_n": f_pull,
        "shear_strength_n": f_shear,
        "interaction_ratio": r,
        "margin_of_safety": ms,
        "is_acceptable": acceptable,
        "failure_mode": mode,
        "substrate": substrate,
    }


def assess_potted_insert(
    axial_load_n: float,
    shear_load_n: float,
    potting_diameter_mm: float,
    core_thickness_mm: float,
    core_shear_strength_mpa: float,
    potting_shear_strength_mpa: float,
    factor_of_safety: float = 1.5,
) -> dict:
    """
    Full strength assessment for a potted insert in honeycomb core.

    Applies the project factor of safety to the applied loads, computes
    pull-out and shear allowables, evaluates the quadratic interaction,
    and returns a result dict.

    Returns dict with keys:
        pullout_strength_n, shear_strength_n, interaction_ratio,
        margin_of_safety, is_acceptable, failure_mode, substrate
    """
    _require_positive(factor_of_safety=factor_of_safety)
    _require_non_negative(axial_load_n=axial_load_n, shear_load_n=shear_load_n)
    f_pull = potted_insert_pullout_strength(
        potting_diameter_mm, core_thickness_mm, core_shear_strength_mpa
    )
    f_shear = potted_insert_shear_strength(
        potting_diameter_mm, potting_shear_strength_mpa
    )
    return _build_result(
        f_pull, f_shear,
        axial_load_n * factor_of_safety,
        shear_load_n * factor_of_safety,
        SUBSTRATE_HONEYCOMB,
    )


def assess_metal_insert(
    axial_load_n: float,
    shear_load_n: float,
    nominal_diameter_mm: float,
    engagement_length_mm: float,
    material_shear_strength_mpa: float,
    factor_of_safety: float = 1.5,
) -> dict:
    """
    Full strength assessment for a threaded insert in solid metal.

    Same return structure as assess_potted_insert.
    """
    _require_positive(factor_of_safety=factor_of_safety)
    _require_non_negative(axial_load_n=axial_load_n, shear_load_n=shear_load_n)
    f_pull = metal_insert_pullout_strength(
        nominal_diameter_mm, engagement_length_mm, material_shear_strength_mpa
    )
    f_shear = metal_insert_shear_strength(
        nominal_diameter_mm, material_shear_strength_mpa
    )
    return _build_result(
        f_pull, f_shear,
        axial_load_n * factor_of_safety,
        shear_load_n * factor_of_safety,
        SUBSTRATE_METAL,
    )


def assess_composite_insert(
    axial_load_n: float,
    shear_load_n: float,
    bolt_diameter_mm: float,
    laminate_thickness_mm: float,
    interlaminar_shear_mpa: float,
    bearing_strength_mpa: float,
    factor_of_safety: float = 1.5,
) -> dict:
    """
    Full strength assessment for an insert in a composite laminate.

    Pull-through governs axial load; bearing governs lateral load.
    Same return structure as assess_potted_insert.
    """
    _require_positive(factor_of_safety=factor_of_safety)
    _require_non_negative(axial_load_n=axial_load_n, shear_load_n=shear_load_n)
    f_pull = composite_insert_pullthrough_strength(
        bolt_diameter_mm, laminate_thickness_mm, interlaminar_shear_mpa
    )
    f_shear = composite_insert_bearing_strength(
        bolt_diameter_mm, laminate_thickness_mm, bearing_strength_mpa
    )
    return _build_result(
        f_pull, f_shear,
        axial_load_n * factor_of_safety,
        shear_load_n * factor_of_safety,
        SUBSTRATE_COMPOSITE,
    )
