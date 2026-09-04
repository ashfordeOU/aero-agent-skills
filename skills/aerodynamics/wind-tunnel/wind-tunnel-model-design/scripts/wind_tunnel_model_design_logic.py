#!/usr/bin/env python3
"""Wind tunnel model and test setup design (stdlib only).

Reference implementation for the Aero Agent Skills leaf
skills/aerodynamics/wind-tunnel/wind-tunnel-model-design.

Designs the scale model and the test setup for a wind tunnel campaign on
an aircraft configuration before the test runs. The model scale is the
smaller of the scale set by the test section blockage limit and the
scale set by the span clearance, the model reference dimensions follow
from that scale, the model Reynolds number at the maximum tunnel speed
is compared with the full-scale flight Reynolds number, the maximum
test dynamic pressure and the model load at the maximum test lift
coefficient are estimated for the balance, the balance capacity is rated
against that load, and the model support sting is sized for the bending
moment of the load at the sting arm.

BLOCKAGE_MAX, SPAN_CLEARANCE and STING_ALLOWABLE_STRESS_PA are
documented typical values; they are program and test specific inputs
and every entry point accepts overrides. This leaf is the pre-test
design step: reducing raw balance readings into coefficients and
applying post-test wall or wake corrections belong to the sibling
leaves windtunnel-data-reduction and windtunnel-wall-corrections and
are not implemented here.

Every public function validates its inputs and raises ValueError on
non-physical values. Deterministic, offline, no third-party imports.
"""

import math

# Default maximum model-to-test-section area ratio, documented typical.
BLOCKAGE_MAX = 0.05
# Fraction of the test section width available to the model span,
# documented typical.
SPAN_CLEARANCE = 0.8
# Default sting allowable stress in Pa (steel, 800 MPa), input.
STING_ALLOWABLE_STRESS_PA = 800.0e6
# Sea level air dynamic viscosity in kg/(m s).
MU_AIR = 1.789e-5
# Sea level air density in kg/m^3.
RHO_SL = 1.225
# Standard gravity in m/s^2.
G0 = 9.80665
# Model-to-full Reynolds ratio at or above which the tunnel is
# reported as matching the full-scale flight condition.
REYNOLDS_MATCH_RATIO = 0.5


def _require_positive(name, value):
    """Return float(value) or raise ValueError when it is not > 0."""
    value = float(value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    """Return float(value) when in (0, 1], else raise ValueError."""
    value = float(value)
    if value <= 0.0 or value > 1.0:
        raise ValueError("%s must be in (0, 1], got %r" % (name, value))
    return value


def section_area(width, height):
    """Cross-sectional area of the test section, width * height."""
    w = _require_positive("width", width)
    h = _require_positive("height", height)
    return w * h


def scale_from_blockage(test_area, full_wing_area, blockage_max=BLOCKAGE_MAX):
    """Model scale that keeps the model area within the blockage limit.

    Scale by area: (blockage_max * test_area / full_wing_area) ** 0.5,
    so the model wing area equals blockage_max * test_area.
    """
    area = _require_positive("test_area", test_area)
    wing = _require_positive("full_wing_area", full_wing_area)
    block = _require_fraction("blockage_max", blockage_max)
    return math.sqrt(block * area / wing)


def scale_from_span(test_width, full_span, clearance=SPAN_CLEARANCE):
    """Model scale that leaves the span clearance to the section walls.

    Scale by span: (test_width * clearance) / full_span, the largest
    model that keeps the span inside the available fraction of width.
    """
    width = _require_positive("test_width", test_width)
    span = _require_positive("full_span", full_span)
    clear = _require_fraction("clearance", clearance)
    return width * clear / span


def choose_scale(
    test_area,
    full_wing_area,
    test_width,
    full_span,
    full_mac,
    blockage_max=BLOCKAGE_MAX,
    clearance=SPAN_CLEARANCE,
):
    """Select the model scale and derive the model reference dimensions.

    The chosen scale is the smaller of the blockage-limited scale and
    the span-limited scale; the model wing area, MAC and span scale
    with scale squared and scale respectively. Returns a dict with
    lambda_blockage, lambda_span, scale, model_wing_area, model_mac,
    model_span, blockage_ratio (model area over test area) and
    blocked_ok (blockage_ratio within the blockage limit). Raises
    ValueError on any non-positive dimension.
    """
    area = _require_positive("test_area", test_area)
    wing = _require_positive("full_wing_area", full_wing_area)
    width = _require_positive("test_width", test_width)
    span = _require_positive("full_span", full_span)
    mac = _require_positive("full_mac", full_mac)
    lambda_blockage = scale_from_blockage(area, wing, blockage_max)
    lambda_span = scale_from_span(width, span, clearance)
    scale = min(lambda_blockage, lambda_span)
    model_wing_area = wing * scale * scale
    model_mac = mac * scale
    model_span = span * scale
    blockage_ratio = model_wing_area / area
    # The blockage limit is inclusive: the blockage-limited scale lands
    # the model exactly on blockage_max up to float rounding, so compare
    # with a rounding tolerance instead of strict <=.
    blocked_ok = blockage_ratio <= blockage_max * (1.0 + 1e-12)
    return {
        "lambda_blockage": lambda_blockage,
        "lambda_span": lambda_span,
        "scale": scale,
        "model_wing_area": model_wing_area,
        "model_mac": model_mac,
        "model_span": model_span,
        "blockage_ratio": blockage_ratio,
        "blocked_ok": blocked_ok,
    }


def reynolds_model(tunnel_speed, model_mac, rho=RHO_SL, mu=MU_AIR):
    """Reynolds number of the model at the tunnel speed, rho*V*c/mu."""
    speed = _require_positive("tunnel_speed", tunnel_speed)
    mac = _require_positive("model_mac", model_mac)
    density = _require_positive("rho", rho)
    viscosity = _require_positive("mu", mu)
    return density * speed * mac / viscosity


def reynolds_ratio(model_re, full_re):
    """Model Reynolds over the full-scale flight Reynolds number."""
    model = _require_positive("model_re", model_re)
    full = _require_positive("full_re", full_re)
    return model / full


def model_load_N(q, model_wing_area, cl):
    """Aerodynamic load on the model at dynamic pressure q, q*S*cl."""
    pressure = _require_positive("q", q)
    area = _require_positive("model_wing_area", model_wing_area)
    lift = _require_positive("cl", cl)
    return pressure * area * lift


def balance_verdict(load_N, capacity_N):
    """Rate the balance against the model load.

    Returns "balance-ok" when the load does not exceed the capacity,
    else "balance-overload".
    """
    load = float(load_N)
    if load < 0.0:
        raise ValueError("load_N must be non-negative, got %r" % (load_N,))
    capacity = _require_positive("capacity_N", capacity_N)
    return "balance-ok" if load <= capacity else "balance-overload"


def sting_diameter_m(bending_moment_Nm, allowable_pa):
    """Sting diameter for a circular section bending moment.

    d = (32 * M / (pi * allowable)) ** (1/3), the solid circular shaft
    bending sizing relation.
    """
    moment = _require_positive("bending_moment_Nm", bending_moment_Nm)
    allowable = _require_positive("allowable_pa", allowable_pa)
    return (32.0 * moment / (math.pi * allowable)) ** (1.0 / 3.0)


def analyze(inputs):
    """Full wind tunnel model design pass over an inputs dict.

    Inputs: test_section_width_m, test_section_height_m (height may be
    omitted when test_section_area_m2 is given), test_section_area_m2
    (optional, computed from width and height otherwise), full_span_m,
    full_wing_area_m2, full_mac_m, full_reynolds, tunnel_max_speed_m_s,
    max_test_cl (default 1.4), balance_capacity_N, sting_arm_m,
    sting_allowable_stress_pa (default STING_ALLOWABLE_STRESS_PA),
    blockage_max (default BLOCKAGE_MAX).

    Returns a dict with the scale selection, model dimensions, blockage
    ratio, model Reynolds number at the maximum tunnel speed, the
    Reynolds ratio to the full-scale flight condition, the maximum
    dynamic pressure q = 0.5*rho*Vmax^2, the model load at the maximum
    test lift coefficient, the balance verdict, the sting bending
    moment and the sting diameter, and a reynolds_limitation string
    ("reynolds-matched" when the ratio is at least 0.5, else
    "reynolds-mismatch"; an engineering flag, not a pass/fail gate).
    Raises ValueError on non-positive dimensions, full_reynolds,
    tunnel_max_speed, balance capacity, sting arm, lift coefficient or
    allowable stress.
    """
    width = _require_positive("test_section_width_m", inputs["test_section_width_m"])
    height = inputs.get("test_section_height_m")
    area = inputs.get("test_section_area_m2")
    if area is None:
        if height is None:
            raise ValueError(
                "test_section_area_m2 or test_section_height_m required"
            )
        area = section_area(width, height)
    area = _require_positive("test_section_area_m2", area)
    full_span = _require_positive("full_span_m", inputs["full_span_m"])
    full_wing_area = _require_positive(
        "full_wing_area_m2", inputs["full_wing_area_m2"]
    )
    full_mac = _require_positive("full_mac_m", inputs["full_mac_m"])
    full_re = _require_positive("full_reynolds", inputs["full_reynolds"])
    vmax = _require_positive(
        "tunnel_max_speed_m_s", inputs["tunnel_max_speed_m_s"]
    )
    max_cl = float(inputs.get("max_test_cl", 1.4))
    if max_cl <= 0.0:
        raise ValueError("max_test_cl must be positive, got %r" % (max_cl,))
    balance_capacity = _require_positive(
        "balance_capacity_N", inputs["balance_capacity_N"]
    )
    sting_arm = _require_positive("sting_arm_m", inputs["sting_arm_m"])
    allowable = float(
        inputs.get(
            "sting_allowable_stress_pa", STING_ALLOWABLE_STRESS_PA
        )
    )
    if allowable <= 0.0:
        raise ValueError(
            "sting_allowable_stress_pa must be positive, got %r"
            % (allowable,)
        )
    blockage_max = float(inputs.get("blockage_max", BLOCKAGE_MAX))
    if not (0.0 < blockage_max <= 1.0):
        raise ValueError(
            "blockage_max must be in (0, 1], got %r" % (blockage_max,)
        )

    chosen = choose_scale(
        area,
        full_wing_area,
        width,
        full_span,
        full_mac,
        blockage_max=blockage_max,
        clearance=float(inputs.get("clearance", SPAN_CLEARANCE)),
    )
    model_re = reynolds_model(vmax, chosen["model_mac"])
    ratio = reynolds_ratio(model_re, full_re)
    q = 0.5 * RHO_SL * vmax * vmax
    load = model_load_N(q, chosen["model_wing_area"], max_cl)
    verdict = balance_verdict(load, balance_capacity)
    moment = load * sting_arm
    diameter = sting_diameter_m(moment, allowable)
    return {
        "lambda_blockage": chosen["lambda_blockage"],
        "lambda_span": chosen["lambda_span"],
        "scale": chosen["scale"],
        "model_wing_area": chosen["model_wing_area"],
        "model_mac": chosen["model_mac"],
        "model_span": chosen["model_span"],
        "blockage_ratio": chosen["blockage_ratio"],
        "blocked_ok": chosen["blocked_ok"],
        "model_reynolds": model_re,
        "reynolds_ratio": ratio,
        "reynolds_limitation": (
            "reynolds-matched" if ratio >= REYNOLDS_MATCH_RATIO
            else "reynolds-mismatch"
        ),
        "dynamic_pressure_pa": q,
        "model_load_N": load,
        "balance_verdict": verdict,
        "sting_bending_moment_Nm": moment,
        "sting_diameter_m": diameter,
    }


if __name__ == "__main__":
    # Smoke check mirroring the worked example of the spec.
    result = analyze(
        {
            "test_section_width_m": 2.44,
            "test_section_height_m": 2.44,
            "full_span_m": 34.0,
            "full_wing_area_m2": 122.6,
            "full_mac_m": 4.2,
            "full_reynolds": 3.0e7,
            "tunnel_max_speed_m_s": 80.0,
            "max_test_cl": 1.4,
            "balance_capacity_N": 5000.0,
            "sting_arm_m": 0.35,
            "sting_allowable_stress_pa": 800.0e6,
            "blockage_max": 0.05,
        }
    )
    print("scale=%.5f area=%.5f ratio=%.5f load=%.1f sting_mm=%.2f %s" % (
        result["scale"],
        result["model_wing_area"],
        result["reynolds_ratio"],
        result["model_load_N"],
        result["sting_diameter_m"] * 1000.0,
        result["balance_verdict"],
    ))
