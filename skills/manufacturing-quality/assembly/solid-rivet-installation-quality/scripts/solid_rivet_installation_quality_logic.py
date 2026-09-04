"""Solid rivet installation quality checks (manufacturing-quality/assembly).

Pure stdlib, deterministic. Implements the deformation-fastener checks:
rivet length selection from stack and head-style allowance, driven
shop-head geometry bands, squeeze force to upset, and hole-fill
clearance. Dimensions in mm, force in N, flow stress in MPa (N/mm2).
"""

import math

PROTRUDING_ALLOWANCE_D = 1.5   # protruding head allowance, diameters of shank
COUNTERSUNK_ALLOWANCE_D = 0.8  # countersunk head allowance, diameters of shank
SHOP_D_MIN_D = 1.4             # driven head diameter band lower edge, diameters
SHOP_D_MAX_D = 1.5             # driven head diameter band upper edge, diameters
SHOP_H_MIN_D = 0.4             # driven head height band lower edge, diameters
SHOP_H_MAX_D = 0.5             # driven head height band upper edge, diameters
SQUEEZE_FACTOR_DEFAULT = 1.5   # allowance factor over flow stress upset force
MAX_HOLE_CLEARANCE_MM = 0.1    # max hole fill clearance, mm

HEAD_STYLES = ("protruding", "countersunk")


def select_rivet_length(stack_mm, diameter_mm, head_style):
    """Select the rivet length: stack plus head-style allowance in diameters.

    allowance_mm = allowance_d * diameter; length_mm = stack + allowance_mm.
    """
    if stack_mm <= 0:
        raise ValueError("stack thickness must be positive")
    if diameter_mm <= 0:
        raise ValueError("rivet diameter must be positive")
    if head_style not in HEAD_STYLES:
        raise ValueError("head_style must be 'protruding' or 'countersunk'")
    allowance_d = (
        PROTRUDING_ALLOWANCE_D if head_style == "protruding"
        else COUNTERSUNK_ALLOWANCE_D
    )
    allowance_mm = allowance_d * diameter_mm
    return {"allowance_mm": allowance_mm, "length_mm": stack_mm + allowance_mm}


def shop_head_verdict(driven_diameter_mm, driven_height_mm, rivet_diameter_mm):
    """Judge the driven shop head against the workmanship ratio bands.

    ok when d_over_d in [SHOP_D_MIN_D, SHOP_D_MAX_D] and h_over_d in
    [SHOP_H_MIN_D, SHOP_H_MAX_D].
    """
    if driven_diameter_mm <= 0:
        raise ValueError("driven diameter must be positive")
    if driven_height_mm <= 0:
        raise ValueError("driven height must be positive")
    if rivet_diameter_mm <= 0:
        raise ValueError("rivet diameter must be positive")
    d_over_d = driven_diameter_mm / rivet_diameter_mm
    h_over_d = driven_height_mm / rivet_diameter_mm
    ok = (SHOP_D_MIN_D <= d_over_d <= SHOP_D_MAX_D
          and SHOP_H_MIN_D <= h_over_d <= SHOP_H_MAX_D)
    return {"d_over_d": d_over_d, "h_over_d": h_over_d, "ok": ok}


def squeeze_force(diameter_mm, flow_stress_mpa, factor=SQUEEZE_FACTOR_DEFAULT):
    """Force to upset the rivet: factor * flow_stress * (pi d^2 / 4)."""
    if diameter_mm <= 0:
        raise ValueError("rivet diameter must be positive")
    if flow_stress_mpa <= 0:
        raise ValueError("flow stress must be positive")
    if factor <= 0:
        raise ValueError("squeeze factor must be positive")
    area_mm2 = math.pi * diameter_mm ** 2 / 4.0
    force_n = factor * flow_stress_mpa * area_mm2
    return {"area_mm2": area_mm2, "force_n": force_n}


def hole_fill_check(hole_diameter_mm, rivet_diameter_mm,
                    max_clearance_mm=MAX_HOLE_CLEARANCE_MM):
    """Check the hole fill clearance: hole - rivet <= max clearance."""
    if hole_diameter_mm <= 0:
        raise ValueError("hole diameter must be positive")
    if rivet_diameter_mm <= 0:
        raise ValueError("rivet diameter must be positive")
    if rivet_diameter_mm > hole_diameter_mm:
        raise ValueError("interference fit is out of scope: rivet must not "
                         "exceed the hole diameter")
    if max_clearance_mm < 0:
        raise ValueError("max clearance must be non-negative")
    clearance_mm = hole_diameter_mm - rivet_diameter_mm
    return {"clearance_mm": clearance_mm,
            "ok": clearance_mm <= max_clearance_mm}


def installation_verdict(stack_mm, rivet_diameter_mm, head_style,
                         driven_diameter_mm, driven_height_mm,
                         squeeze_force_n, flow_stress_mpa, hole_diameter_mm,
                         factor=SQUEEZE_FACTOR_DEFAULT,
                         max_clearance_mm=MAX_HOLE_CLEARANCE_MM):
    """Combine the four sub-checks into one installation verdict.

    Keys: selected_length, shop_head, squeeze, hole_fill, overall_ok.
    The squeeze sub-dict carries the recomputed upset requirement (area_mm2,
    force_n) plus the applied force (applied_force_n); overall_ok is True
    only when the shop head and hole fill sub-checks both pass.
    """
    length = select_rivet_length(stack_mm, rivet_diameter_mm, head_style)
    head = shop_head_verdict(driven_diameter_mm, driven_height_mm,
                             rivet_diameter_mm)
    squeeze = squeeze_force(rivet_diameter_mm, flow_stress_mpa, factor)
    if squeeze_force_n <= 0:
        raise ValueError("applied squeeze force must be positive")
    fill = hole_fill_check(hole_diameter_mm, rivet_diameter_mm,
                           max_clearance_mm)
    squeeze["applied_force_n"] = squeeze_force_n
    overall_ok = head["ok"] and fill["ok"]
    return {"selected_length": length, "shop_head": head,
            "squeeze": squeeze, "hole_fill": fill,
            "overall_ok": overall_ok}
