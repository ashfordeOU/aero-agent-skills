"""Bonded scarf composite repair sizing logic (pure stdlib, deterministic).

Implements the uniform-stress scarf joint model used to size a bonded
scarf repair for a damaged composite laminate: scarf length from parent
thickness and scarf angle, average adhesive shear stress at the parent
laminate stress, required scarf angle for an adhesive shear allowable,
and the external patch thickness that restores the parent in-plane
stiffness.

Angles are degrees for callers and converted internally. There are no
material constants; every input is explicit so the model works for any
carbon/epoxy or glass/epoxy parent and patch system.

Model relations (uniform stress scarf joint):
- L = thickness / tan(theta)
- tau = sigma * sin(theta) * cos(theta), equivalently
  tau = (sigma / 2) * sin(2 * theta)
- theta_req = 0.5 * asin(2 * tau_a / sigma)
- t_patch = t_parent * E_parent / E_patch
"""

import math

DEG2RAD = math.pi / 180.0


def scarf_length(thickness, scarf_angle_deg):
    """Scarf length L = thickness / tan(angle) for a full-depth scarf.

    thickness is the parent laminate thickness and scarf_angle_deg the
    scarf angle measured from the laminate plane. The return value is in
    the same length unit as thickness. Raises ValueError when thickness
    is not positive or the angle is outside (0, 90) degrees.
    """
    if thickness <= 0:
        raise ValueError("thickness must be > 0")
    if scarf_angle_deg <= 0 or scarf_angle_deg >= 90:
        raise ValueError("scarf_angle_deg must be in (0, 90)")
    return thickness / math.tan(scarf_angle_deg * DEG2RAD)


def adhesive_shear_stress(parent_stress, scarf_angle_deg):
    """Average adhesive shear stress tau = sigma * sin(theta) * cos(theta).

    Uniform-stress scarf model: the adhesive carries the parent laminate
    stress projected onto the scarf plane. parent_stress is the far-field
    laminate stress and the return value is in the same stress unit.
    Raises ValueError when parent_stress is negative or the angle is
    outside (0, 90) degrees.
    """
    if parent_stress < 0:
        raise ValueError("parent_stress must be >= 0")
    if scarf_angle_deg <= 0 or scarf_angle_deg >= 90:
        raise ValueError("scarf_angle_deg must be in (0, 90)")
    theta = scarf_angle_deg * DEG2RAD
    return parent_stress * math.sin(theta) * math.cos(theta)


def required_scarf_angle(parent_stress, allowable_shear):
    """Required scarf angle in degrees for an adhesive shear allowable.

    From tau = (sigma / 2) * sin(2 * theta) with tau set to the
    allowable: theta = 0.5 * asin(2 * allowable / sigma). Returns
    degrees. Raises ValueError when parent_stress or allowable_shear is
    not positive, or when 2 * allowable / sigma exceeds 1.0, which means
    no real scarf angle can carry the load at that stress.
    """
    if parent_stress <= 0:
        raise ValueError("parent_stress must be > 0")
    if allowable_shear <= 0:
        raise ValueError("allowable_shear must be > 0")
    ratio = 2.0 * allowable_shear / parent_stress
    if ratio > 1.0:
        raise ValueError(
            "2 * allowable_shear / parent_stress > 1: no real scarf angle "
            "can carry the load at this stress"
        )
    return 0.5 * math.asin(ratio) / DEG2RAD


def patch_thickness_for_stiffness(parent_thickness, parent_modulus,
                                  patch_modulus):
    """External patch thickness matching the parent in-plane stiffness.

    t_patch = t_parent * E_parent / E_patch keeps the repaired section
    stiffness equal to the undamaged parent. All arguments must be
    positive; the return value is in the same length unit as
    parent_thickness.
    """
    if parent_thickness <= 0:
        raise ValueError("parent_thickness must be > 0")
    if parent_modulus <= 0:
        raise ValueError("parent_modulus must be > 0")
    if patch_modulus <= 0:
        raise ValueError("patch_modulus must be > 0")
    return parent_thickness * parent_modulus / patch_modulus


def repair_sizing(parent_thickness, parent_stress, parent_modulus,
                  patch_modulus, scarf_angle_deg, allowable_shear):
    """Complete bonded scarf repair sizing summary (SI inputs).

    parent_thickness in m, parent_stress in Pa, moduli in Pa,
    scarf_angle_deg in degrees, allowable_shear in Pa. Returns a dict
    with scarf_length_m, scarf_angle_deg, adhesive_shear_Pa,
    required_scarf_angle_deg (for the allowable; may be steeper than the
    chosen angle, both are reported), patch_thickness_m and margin =
    allowable_shear / adhesive_shear - 1. A negative margin means the
    chosen scarf angle does not clear the allowable. ValueErrors from
    the component functions propagate.
    """
    length = scarf_length(parent_thickness, scarf_angle_deg)
    shear = adhesive_shear_stress(parent_stress, scarf_angle_deg)
    required = required_scarf_angle(parent_stress, allowable_shear)
    patch = patch_thickness_for_stiffness(parent_thickness,
                                          parent_modulus, patch_modulus)
    margin = allowable_shear / shear - 1.0
    return {
        "scarf_length_m": length,
        "scarf_angle_deg": scarf_angle_deg,
        "adhesive_shear_Pa": shear,
        "required_scarf_angle_deg": required,
        "patch_thickness_m": patch,
        "margin": margin,
    }
