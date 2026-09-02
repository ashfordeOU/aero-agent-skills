#!/usr/bin/env python3
"""Classical closed-wall wind tunnel wall corrections (stdlib only).

Reference implementation for the Aero Agent Skills leaf
skills/aerodynamics/wind-tunnel/windtunnel-wall-corrections.

Applies the classical low-speed wall corrections of a closed solid-wall
test section (Barlow, Rae and Pope, Low-Speed Wind Tunnel Testing,
boundary corrections chapter, method set summarized here) to measured
force and pressure coefficients. This leaf takes coefficients that were
already reduced from raw balance readings (the tare, Reynolds, Mach and
uncertainty steps belong to windtunnel-data-reduction) and corrects them
for the presence of the tunnel walls only.

Correction set:
  solid blockage    eps_sb = K1 * V_model / C^1.5,  K1 = 0.52 closed
  wake blockage     eps_wb = (S_model / (4 C)) * CDu
  total blockage    eps = eps_sb + eps_wb
  dynamic pressure  q_c = q_u * (1 + eps)^2
  velocity          V_c = V_u * (1 + eps)
  buoyancy drag     dCD_buoy = -(dP/dx) * V_model / (q * S_ref)
  lift interference delta_alpha = delta * (S_model / C) * CLu,  delta = pi/48
  lift factor       sigma = (pi^2 / 48) * (span / height)^2
  corrected CL      CLc = CLu * (1 - sigma - 2 * eps_sb)
  corrected CD      CDc = CDu * (1 - 3 * eps_sb - 2 * eps_wb) + dCD_buoy

K1, delta and the sigma coefficient are classical approximations for a
closed rectangular section; override them with the tunnel-specific
calibration when one is available. C is the test-section cross-sectional
area, C^1.5 its cubic scale (volume units). Every public function
validates its inputs and raises ValueError on non-physical values or a
model that does not fit inside the test section. Deterministic,
offline, no third-party imports.
"""

import math

# Solid blockage factor K1 for a closed rectangular test section,
# classical Barlow value (open sections use a smaller factor).
K1_CLOSED_RECTANGULAR = 0.52
# Wake blockage weight from the model wake filling the closed section.
WAKE_BLOCKAGE_FACTOR = 0.25
# Lift interference factor delta: classical closed-wall value pi/48.
DELTA_CLOSED = math.pi / 48.0
# Sigma lift factor coefficient: classical closed-wall pi^2/48.
SIGMA_CLOSED_COEFF = math.pi ** 2 / 48.0


def _require_positive(name, value):
    value = float(value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = float(value)
    if value < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (name, value))
    return value


def _require_finite(name, value):
    """Cast to float and reject NaN or infinite values (signed OK)."""
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _section_scale(test_section_area):
    """Cubic scale C^1.5 of the cross-sectional area (volume units)."""
    return float(test_section_area) ** 1.5


def solid_blockage(model_volume, test_section_area,
                   k1=K1_CLOSED_RECTANGULAR):
    """Solid blockage eps_sb = K1 * V_model / C^1.5.

    V_model is the model volume, C the test-section cross-sectional
    area, and C^1.5 the cubic scale of the section. K1 defaults to the
    classical closed-rectangular value 0.52 (Barlow); pass the
    tunnel-specific calibration when available.
    """
    vm = _require_non_negative("model_volume", model_volume)
    c = _require_positive("test_section_area", test_section_area)
    _require_positive("k1", k1)
    scale = _section_scale(c)
    if vm >= scale:
        raise ValueError(
            "model volume %g must be smaller than the test section "
            "volume scale C^1.5 = %g" % (vm, scale))
    return k1 * vm / scale


def wake_blockage(s_ref, test_section_area, cd_uncorrected):
    """Wake blockage eps_wb = (S_model / (4 C)) * CDu.

    S_model is the planform area, C the test-section cross-sectional
    area, CDu the uncorrected drag coefficient referenced to the
    uncorrected dynamic pressure.
    """
    s = _require_positive("s_ref", s_ref)
    c = _require_positive("test_section_area", test_section_area)
    cd = _require_non_negative("cd_uncorrected", cd_uncorrected)
    if s >= c:
        raise ValueError(
            "model planform area %g must be smaller than the test "
            "section cross-sectional area %g" % (s, c))
    return WAKE_BLOCKAGE_FACTOR * (s / c) * cd


def total_blockage(model_volume, test_section_area, s_ref,
                   cd_uncorrected, k1=K1_CLOSED_RECTANGULAR):
    """Total blockage eps = eps_sb + eps_wb."""
    eps_sb = solid_blockage(model_volume, test_section_area, k1)
    eps_wb = wake_blockage(s_ref, test_section_area, cd_uncorrected)
    return eps_sb + eps_wb


def buoyancy_drag_increment(dpdx, model_volume, q, s_ref):
    """Horizontal buoyancy drag increment dCD_buoy.

    dCD_buoy = -(dP/dx) * V_model / (q * S_ref), with dP/dx the
    streamwise static pressure gradient of the empty test section in
    Pa/m. Sign convention: in a closed solid-wall section the core flow
    accelerates downstream so dP/dx is negative and the increment is
    positive (drag added); a positive dP/dx reduces drag.
    """
    grad = _require_finite("dpdx", dpdx)
    vm = _require_non_negative("model_volume", model_volume)
    qv = _require_positive("q", q)
    s = _require_positive("s_ref", s_ref)
    return -grad * vm / (qv * s)


def sigma_lift_factor(span, test_section_height,
                      coefficient=SIGMA_CLOSED_COEFF):
    """Lift factor sigma = (pi^2 / 48) * (span / height)^2.

    Classical closed-wall result (Barlow); valid while the span is
    smaller than the test-section height. Override the coefficient with
    the tunnel-specific calibration when available.
    """
    b = _require_positive("span", span)
    h = _require_positive("test_section_height", test_section_height)
    _require_positive("coefficient", coefficient)
    if b >= h:
        raise ValueError(
            "model span %g must be smaller than the test section "
            "height %g" % (b, h))
    return coefficient * (b / h) ** 2


def lift_interference_delta_alpha(alpha_u_deg, s_ref, test_section_area,
                                  cl_uncorrected, delta=DELTA_CLOSED):
    """Lift interference angle of attack correction.

    delta_alpha = delta * (S_model / C) * CLu (radians), converted to
    degrees and added to the geometric angle. delta is the classical
    closed-wall value pi/48 by default. Returns (delta_alpha_deg,
    alpha_corrected_deg).
    """
    a = _require_finite("alpha_u_deg", alpha_u_deg)
    s = _require_positive("s_ref", s_ref)
    c = _require_positive("test_section_area", test_section_area)
    cl = _require_finite("cl_uncorrected", cl_uncorrected)
    _require_positive("delta", delta)
    delta_alpha = delta * (s / c) * cl
    delta_alpha_deg = math.degrees(delta_alpha)
    return delta_alpha_deg, a + delta_alpha_deg


def corrected_lift_coefficient(cl_uncorrected, sigma, eps_sb):
    """First-order corrected lift CLc = CLu * (1 - sigma - 2 eps_sb)."""
    cl = _require_finite("cl_uncorrected", cl_uncorrected)
    _require_non_negative("sigma", sigma)
    _require_non_negative("eps_sb", eps_sb)
    return cl * (1.0 - sigma - 2.0 * eps_sb)


def corrected_drag_coefficient(cd_uncorrected, eps_sb, eps_wb,
                               buoyancy_increment=0.0):
    """First-order corrected drag.

    CDc = CDu * (1 - 3 eps_sb - 2 eps_wb) + buoyancy_increment, where
    the buoyancy increment is the horizontal buoyancy term computed by
    buoyancy_drag_increment when a pressure gradient was measured.
    """
    cd = _require_non_negative("cd_uncorrected", cd_uncorrected)
    _require_non_negative("eps_sb", eps_sb)
    _require_non_negative("eps_wb", eps_wb)
    _require_finite("buoyancy_increment", buoyancy_increment)
    return cd * (1.0 - 3.0 * eps_sb - 2.0 * eps_wb) + buoyancy_increment


def corrected_dynamic_pressure(q_uncorrected, eps):
    """Blockage corrected dynamic pressure q_c = q_u * (1 + eps)^2."""
    q = _require_positive("q_uncorrected", q_uncorrected)
    _require_non_negative("eps", eps)
    return q * (1.0 + eps) ** 2


def corrected_velocity(v_uncorrected, eps):
    """Blockage corrected tunnel speed V_c = V_u * (1 + eps)."""
    v = _require_positive("v_uncorrected", v_uncorrected)
    _require_non_negative("eps", eps)
    return v * (1.0 + eps)


def _validate_geometry(s_ref, model_volume, test_section_area,
                       test_section_height, span):
    """Shared checks: model geometry must fit inside the test section."""
    _require_positive("s_ref", s_ref)
    _require_positive("test_section_area", test_section_area)
    _require_positive("test_section_height", test_section_height)
    _require_positive("span", span)
    # Exercise the per-quantity checks and their fit constraints.
    solid_blockage(model_volume, test_section_area)
    wake_blockage(s_ref, test_section_area, 0.0)
    sigma_lift_factor(span, test_section_height)


def apply_wall_corrections(alpha_u_deg, cl_uncorrected, cd_uncorrected,
                           s_ref, model_volume, test_section_area,
                           test_section_height, span, q_uncorrected,
                           v_uncorrected=None, dpdx=None,
                           k1=K1_CLOSED_RECTANGULAR,
                           delta=DELTA_CLOSED,
                           sigma_coefficient=SIGMA_CLOSED_COEFF):
    """Full closed-wall correction chain for one measured point.

    Computes solid and wake blockage, the lift factor sigma, the lift
    interference angle increment, the horizontal buoyancy drag increment
    (only when dpdx is supplied), and the corrected lift and drag
    coefficients with corrected dynamic pressure and velocity. Returns a
    dict of corrected values with a correction ledger.
    """
    a = _require_finite("alpha_u_deg", alpha_u_deg)
    cl = _require_finite("cl_uncorrected", cl_uncorrected)
    cd = _require_non_negative("cd_uncorrected", cd_uncorrected)
    _validate_geometry(s_ref, model_volume, test_section_area,
                       test_section_height, span)
    q = _require_positive("q_uncorrected", q_uncorrected)

    eps_sb = solid_blockage(model_volume, test_section_area, k1)
    eps_wb = wake_blockage(s_ref, test_section_area, cd)
    eps = eps_sb + eps_wb
    q_c = corrected_dynamic_pressure(q, eps)

    sigma = sigma_lift_factor(span, test_section_height, sigma_coefficient)
    delta_alpha_deg, alpha_c = lift_interference_delta_alpha(
        a, s_ref, test_section_area, cl, delta)

    buoy = 0.0
    if dpdx is not None:
        buoy = buoyancy_drag_increment(dpdx, model_volume, q, s_ref)

    cl_c = corrected_lift_coefficient(cl, sigma, eps_sb)
    cd_c = corrected_drag_coefficient(cd, eps_sb, eps_wb, buoy)

    v_c = None
    if v_uncorrected is not None:
        v_c = corrected_velocity(v_uncorrected, eps)

    ledger = [
        {"step": "solid-blockage", "value": eps_sb,
         "note": "K1 * V_model / C^1.5 with K1 %g" % k1},
        {"step": "wake-blockage", "value": eps_wb,
         "note": "(S_model / (4 C)) * CDu"},
        {"step": "total-blockage", "value": eps,
         "note": "eps_sb + eps_wb"},
        {"step": "dynamic-pressure", "value": q_c,
         "note": "q_u * (1 + eps)^2"},
        {"step": "sigma-lift-factor", "value": sigma,
         "note": "(pi^2 / 48) * (span / height)^2"},
        {"step": "lift-interference-alpha", "value": delta_alpha_deg,
         "note": "delta * (S_model / C) * CLu in degrees"},
    ]
    if dpdx is not None:
        ledger.append({"step": "buoyancy-drag", "value": buoy,
                       "note": "-(dP/dx) * V_model / (q * S_ref)"})
    else:
        ledger.append({"step": "buoyancy-drag", "value": 0.0,
                       "note": "not applied, dpdx not supplied"})
    ledger.append({"step": "coefficients-corrected", "value": cd_c,
                   "note": "CDu * (1 - 3 eps_sb - 2 eps_wb) + buoyancy"})

    return {
        "alpha_uncorrected_deg": a,
        "alpha_corrected_deg": alpha_c,
        "delta_alpha_deg": delta_alpha_deg,
        "cl_uncorrected": cl,
        "cl_corrected": cl_c,
        "cd_uncorrected": cd,
        "cd_corrected": cd_c,
        "eps_sb": eps_sb,
        "eps_wb": eps_wb,
        "eps": eps,
        "sigma": sigma,
        "buoyancy_increment": buoy,
        "q_uncorrected": q,
        "q_corrected": q_c,
        "velocity_ratio": 1.0 + eps,
        "v_corrected": v_c,
        "ledger": ledger,
    }


def correct_measured_polar(points, s_ref, model_volume, test_section_area,
                           test_section_height, span, q_uncorrected,
                           v_uncorrected=None, dpdx=None,
                           k1=K1_CLOSED_RECTANGULAR,
                           delta=DELTA_CLOSED,
                           sigma_coefficient=SIGMA_CLOSED_COEFF):
    """Correct every point of a measured polar for the tunnel walls.

    points is a non-empty list of dicts with keys alpha_deg, cl, cd (the
    uncorrected measured values). Common tunnel and model geometry is
    validated once, then each point runs apply_wall_corrections. Returns
    a list of corrected point dicts in the same order.
    """
    _validate_geometry(s_ref, model_volume, test_section_area,
                       test_section_height, span)
    if not points:
        raise ValueError("points must not be empty")
    return [
        apply_wall_corrections(
            p["alpha_deg"], p["cl"], p["cd"], s_ref, model_volume,
            test_section_area, test_section_height, span, q_uncorrected,
            v_uncorrected, dpdx, k1, delta, sigma_coefficient)
        for p in points
    ]
