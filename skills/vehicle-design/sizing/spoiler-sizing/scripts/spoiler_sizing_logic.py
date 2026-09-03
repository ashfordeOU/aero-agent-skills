#!/usr/bin/env python3
"""Spoiler sizing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): conceptual transport spoiler sizing splits the roll control
requirement between the primary roll channel and the roll spoilers,
sizes the flight spoiler panels from the roll assist share and the
roll damping derivative, sizes the ground spoilers (lift dumpers)
from the lift dump needed to unload the wing on touchdown, estimates
the speed brake and lift dump drag increments from the deployed
panel area and deflection, estimates the spoiler hinge moment for
the actuator, and checks the deflections and geometry against
typical limits.

The roll share model follows the control-surface-sizing convention:
the total steady roll authority coefficient at the design roll rate
is C_l_req = -p_req * b * C_l_p / (2 * V) from the roll damping
balance, the primary roll channel carries f_ail of it and the roll
spoilers carry f_spoil = 1 - f_ail. The flight spoiler area is sized
from the spoiler share of that coefficient: with the panel lift
loss per unit area ratio cl_delta_spoil (negative, lift loss, about
-0.3 to -0.5 per rad per unit area ratio), the rolling moment
coefficient of the deployed outboard set is C_l_spoil =
cl_delta_spoil * (A / S) * delta_eff * (y_arm / b), where A is the
total flight spoiler area of both wings, delta_eff is the effective
deflection (linear up to 45 deg, saturation beyond) in rad, and
y_arm the spanwise centroid of the outboard panels. Inverting gives
the area law A = C_l_spoil_req * S * b / (abs(cl_delta_spoil) *
delta_eff * y_arm), the same form as the compact roll spoiler sizing
law with the deflection term made explicit at the reference
deflection. The linear band model is conservative: separated flow at
high deflection destroys the local lift harder than the linear
slope, so sized areas come out larger than handbook panel areas.

Ground spoiler (lift dumper) sizing: the dumper must destroy a
fraction f_dump of the lift at the touchdown lift coefficient, so
the required wing lift loss is dCL_dump = -f_dump * C_L_td. The
lift loss from deployment is dCL_dump = -(A_dump / S) * k_dump *
sin(delta), with k_dump the lift loss coefficient of the deployed
belt (0 to 1.5) and delta the deployment deflection; A_dump is the
effective dump belt area, the spanwise run of the dump panels times
the local wing chord they unload. The panel planform is the belt
area times the panel chord fraction (module constant).

Speed brake and lift dump drag increments: dCD = (A_deployed / S) *
cd_spoil * sin(delta) * span_factor, summed over the deployed
panels, where A_deployed is the panel planform area that deploys,
cd_spoil the panel drag coefficient referenced to the panel area
(about 1.2), and span_factor the typical discrete panel loss
factor (module constant).

Hinge moment for the actuator: H = q * A_panel * c_bar_panel *
(c_h0 + c_h_alpha * alpha + c_h_delta * delta) with module-typical
hinge moment coefficients (reference-only, summary).

Limits checked: deflection 0 < delta <= delta_max (module constant
60 deg), panel aspect ratio within 1.5 to 4, and the panel span
fraction of the wing semi-span within 0.2 to 0.5.

Units are SI throughout: areas in m^2, lengths in m, speeds in m/s,
dynamic pressure in Pa, moments in N m, angles in rad (deg where
noted), derivatives per radian. Invalid inputs raise ValueError
throughout.
"""

import math

RHO_SL = 1.225
DELTA_MAX_DEG = 60.0
LINEAR_DELTA_DEG = 45.0
CL_DELTA_SPOIL_TYP = -0.40
CD_SPOIL_TYP = 1.2
K_DUMP_TYP = 1.5
SPAN_FACTOR_TYP = 0.9
ROLL_DAMPING_TYP = -0.45
DUMP_CHORD_FRACTION_TYP = 0.25
HINGE_COEFFS_TYP = (0.02, 0.03, 0.35)
G0 = 9.80665


def _check_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _deg2rad(deg):
    return deg * math.pi / 180.0


def roll_spoiler_share(f_aileron_share):
    """Roll spoiler share of the roll authority (unitless).

    f_spoil = 1 - f_aileron_share, with f_aileron_share the share of
    the roll control requirement carried by the primary roll channel
    (transport typical 0.6 to 0.7). Worked anchor: f_aileron_share =
    0.65 gives f_spoil = 0.35.

    Raises ValueError if f_aileron_share is not in (0, 1).
    """
    if not 0.0 < f_aileron_share < 1.0:
        raise ValueError(
            "f_aileron_share must be in (0, 1), got %r" % (f_aileron_share,)
        )
    return 1.0 - f_aileron_share


def roll_coefficient_required(p_req, v, b, c_l_p):
    """Total steady roll authority coefficient C_l_req (unitless).

    C_l_req = -p_req * b * C_l_p / (2 * V), the balance of the
    required roll rate against the roll damping derivative, per the
    control-surface-sizing convention. p_req is the design roll rate
    (rad/s), V the reference speed (m/s), b the span (m), and C_l_p
    the roll damping derivative (negative, per rad). Worked anchor:
    p_req = 0.5 rad/s, V = 85 m/s, b = 34 m, C_l_p = -0.45 gives
    C_l_req = 0.5 * 34 * 0.45 / (2 * 85) = 0.045.

    Raises ValueError if p_req, v, b are not positive or c_l_p is
    not negative.
    """
    _check_positive(p_req, "p_req")
    _check_positive(v, "v")
    _check_positive(b, "b")
    if c_l_p >= 0:
        raise ValueError("c_l_p must be negative (roll damping), got %r" % (c_l_p,))
    return -p_req * b * c_l_p / (2.0 * v)


def spoiler_share_coefficient(c_l_req, f_spoil):
    """Rolling moment coefficient share of the roll spoilers."""
    _check_positive(c_l_req, "c_l_req")
    if not 0.0 < f_spoil < 1.0:
        raise ValueError("f_spoil must be in (0, 1), got %r" % (f_spoil,))
    return c_l_req * f_spoil


def roll_moment_share(c_l_spoil_req, q, s, b):
    """Required spoiler-share rolling moment (N m).

    L_share = C_l_spoil_req * q * S * b, the moment the roll
    spoilers must produce at the reference dynamic pressure.
    """
    _check_positive(c_l_spoil_req, "c_l_spoil_req")
    _check_positive(q, "q")
    _check_positive(s, "s")
    _check_positive(b, "b")
    return c_l_spoil_req * q * s * b


def deflection_effectiveness(delta_deg):
    """Effective deflection (rad) for lift loss bookkeeping.

    Linear up to LINEAR_DELTA_DEG (45 deg), saturated beyond: the
    returned value is min(delta, 45) in rad. Raises ValueError if
    delta_deg is outside (0, DELTA_MAX_DEG].
    """
    if not 0.0 < delta_deg <= DELTA_MAX_DEG:
        raise ValueError(
            "delta_deg must be in (0, %g], got %r" % (DELTA_MAX_DEG, delta_deg)
        )
    return _deg2rad(min(delta_deg, LINEAR_DELTA_DEG))


def flight_spoiler_area(roll_moment_share, q, s, b, cl_delta_spoil, y_arm):
    """Total flight spoiler area (m^2, both wings) for the roll share.

    Sizes the outboard flight spoiler panels that carry the roll
    assist share: A = C_l_spoil_req * S * b / (abs(cl_delta_spoil) *
    delta_eff * y_arm), with C_l_spoil_req = roll_moment_share /
    (q * S * b) recovered from the moment, delta_eff the effective
    deflection at the top of the linear band (45 deg), and y_arm the
    spanwise centroid of the outboard panels (m). cl_delta_spoil is
    negative (lift loss, per rad per unit area ratio). Worked
    anchor: roll_moment_share for C_l_spoil_req = 0.01575 at q =
    4425.3125 Pa, S = 122 m^2, b = 34 m, cl_delta_spoil = -0.4,
    y_arm = 13.5 m gives A = 15.404 m^2, about 3.851 m^2 per panel
    for 4 outboard panels.

    Raises ValueError if roll_moment_share, q, s, b, y_arm are not
    positive or cl_delta_spoil is not negative.
    """
    _check_positive(roll_moment_share, "roll_moment_share")
    _check_positive(q, "q")
    _check_positive(s, "s")
    _check_positive(b, "b")
    _check_positive(y_arm, "y_arm")
    if cl_delta_spoil >= 0:
        raise ValueError(
            "cl_delta_spoil must be negative (lift loss), got %r" % (cl_delta_spoil,)
        )
    c_l_spoil_req = roll_moment_share / (q * s * b)
    delta_eff = _deg2rad(LINEAR_DELTA_DEG)
    return c_l_spoil_req * s * b / (abs(cl_delta_spoil) * delta_eff * y_arm)


def flight_spoiler_deflection(required_lift_increment, area, s, cl_delta_spoil):
    """Flight spoiler deflection (deg) for a required lift loss.

    The wing lift loss coefficient needed from the deployed outboard
    set is required_lift_increment (positive magnitude). The
    deflection in the linear band solves
    required_lift_increment = abs(cl_delta_spoil) * (area / S) *
    delta_eff, so delta = required * S / (abs(cl_delta_spoil) *
    area) in rad, converted to deg. When the required loss exceeds
    the 45 deg linear band capacity the deflection saturates at
    DELTA_MAX_DEG travel and the effectiveness stays flat, so the
    returned deflection saturates at DELTA_MAX_DEG.

    Raises ValueError if required_lift_increment, area, s are not
    positive or cl_delta_spoil is not negative.
    """
    _check_positive(required_lift_increment, "required_lift_increment")
    _check_positive(area, "area")
    _check_positive(s, "s")
    if cl_delta_spoil >= 0:
        raise ValueError(
            "cl_delta_spoil must be negative (lift loss), got %r" % (cl_delta_spoil,)
        )
    needed = required_lift_increment * s / (abs(cl_delta_spoil) * area)
    needed_deg = needed * 180.0 / math.pi
    return min(needed_deg, DELTA_MAX_DEG)


def ground_spoiler_area(f_dump, cl_touchdown, s, k_dump, delta_max):
    """Ground spoiler (lift dumper) belt area (m^2) for the lift dump.

    The dumper must destroy f_dump of the lift at the touchdown lift
    coefficient, dCL_dump = -f_dump * C_L_td. With the deployment
    lift loss dCL_dump = -(A / S) * k_dump * sin(delta_max), the
    required effective dump belt area is A = f_dump * C_L_td * S /
    (k_dump * sin(delta_max)), where delta_max is the deployment
    deflection in deg and A is the belt area, the spanwise run of
    the dump panels times the local wing chord they unload. Worked
    anchor: f_dump = 0.6, C_L_td = 1.0, S = 122 m^2, k_dump = 1.5,
    delta_max = 60 deg gives A = 0.6 * 122 / (1.5 * 0.8660) = 56.35
    m^2, a belt run of about 8.05 m per wing at a 3.5 m local chord.

    Raises ValueError if f_dump or cl_touchdown, s are not positive
    in (0, 1) for f_dump, k_dump outside (0, 1.5), or delta_max
    outside (0, 90].
    """
    if not 0.0 < f_dump < 1.0:
        raise ValueError("f_dump must be in (0, 1), got %r" % (f_dump,))
    _check_positive(cl_touchdown, "cl_touchdown")
    _check_positive(s, "s")
    if not 0.0 < k_dump <= 1.5:
        raise ValueError("k_dump must be in (0, 1.5], got %r" % (k_dump,))
    if not 0.0 < delta_max <= 90.0:
        raise ValueError("delta_max must be in (0, 90], got %r" % (delta_max,))
    return f_dump * cl_touchdown * s / (k_dump * math.sin(_deg2rad(delta_max)))


def _drag_increment(area_deployed, s, cd_spoil, delta, name):
    _check_positive(area_deployed, "area_deployed")
    _check_positive(s, "s")
    _check_positive(cd_spoil, "cd_spoil")
    if not 0.0 < delta <= 90.0:
        raise ValueError("%s delta must be in (0, 90], got %r" % (name, delta))
    return (area_deployed / s) * cd_spoil * math.sin(_deg2rad(delta)) * SPAN_FACTOR_TYP


def lift_dump_drag_increment(area_deployed, s, cd_spoil, delta):
    """Lift dump drag increment dCD (unitless) on the ground.

    dCD = (A_deployed / S) * cd_spoil * sin(delta) * span_factor with
    A_deployed the dump panel planform area that deploys and delta in
    deg; the drag rise accompanies the lift dump on touchdown and
    adds to the braking deceleration. Worked anchor: 14.09 m^2 of
    dump planform on S = 122 m^2, cd_spoil = 1.2, delta = 60 deg
    gives dCD = 0.1080.

    Raises ValueError on invalid inputs (delta outside (0, 90]).
    """
    return _drag_increment(area_deployed, s, cd_spoil, delta, "lift dump")


def speed_brake_drag_increment(area_deployed, s, cd_spoil, delta):
    """Speed brake drag increment dCD (unitless) in flight.

    dCD = (A_deployed / S) * cd_spoil * sin(delta) * span_factor with
    A_deployed the flight spoiler planform deployed as a speed brake
    and delta in deg. Worked anchor: 15.404 m^2 of flight spoiler
    planform on S = 122 m^2, cd_spoil = 1.2, delta = 45 deg gives
    dCD = 0.09642.

    Raises ValueError on invalid inputs (delta outside (0, 90]).
    """
    return _drag_increment(area_deployed, s, cd_spoil, delta, "speed brake")


def hinge_moment(q, area, c_bar, alpha, delta, coeffs):
    """Spoiler hinge moment H (N m) for the actuator.

    H = q * A_panel * c_bar_panel * (c_h0 + c_h_alpha * alpha +
    c_h_delta * delta), with alpha and delta in rad and coeffs the
    tuple (c_h0, c_h_alpha, c_h_delta) of module-typical hinge
    moment coefficients (reference-only). The sign follows the load
    convention of the coefficients. Worked anchor: q = 4425.3125 Pa,
    A_panel = 3.851 m^2, c_bar = 1.0 m, alpha = 4 deg, delta = 45
    deg, coeffs = (0.02, 0.03, 0.35) gives H = 5060.9 N m.

    Raises ValueError if q, area, c_bar are not positive or coeffs
    is not a 3-tuple of numbers.
    """
    _check_positive(q, "q")
    _check_positive(area, "area")
    _check_positive(c_bar, "c_bar")
    if not isinstance(coeffs, (tuple, list)) or len(coeffs) != 3:
        raise ValueError("coeffs must be a (c_h0, c_h_alpha, c_h_delta) 3-tuple")
    c_h0, c_h_alpha, c_h_delta = (float(c) for c in coeffs)
    bracket = c_h0 + c_h_alpha * alpha + c_h_delta * delta
    return q * area * c_bar * bracket


def deflection_limits_check(delta_deg, delta_max_deg=DELTA_MAX_DEG):
    """Deflection check against the travel limit (deg).

    Returns {"within": bool, "margin_deg": float, "verdict": str};
    the spoiler band is 0 < delta <= delta_max (module typical 60
    deg). Raises ValueError if delta_max_deg is not positive.
    """
    _check_positive(delta_max_deg, "delta_max_deg")
    within = 0.0 < delta_deg <= delta_max_deg
    margin = delta_max_deg - delta_deg
    if within:
        verdict = "deflection within limit, margin %g deg" % margin
    else:
        verdict = "deflection outside limit by %g deg" % (-margin)
    return {"within": within, "margin_deg": margin, "verdict": verdict}


def geometry_limits_check(area_panel, chord_panel, b):
    """Panel geometry check against the typical bands.

    Returns a dict with the panel aspect ratio (span / chord, must
    fall in 1.5 to 4) and the single-side span fraction of the wing
    semi-span (typical 0.2 to 0.5), with within flags and a verdict
    string. area_panel is the per-panel area (m^2), chord_panel the
    panel chord (m), b the span (m). Raises ValueError if inputs
    are not positive.
    """
    _check_positive(area_panel, "area_panel")
    _check_positive(chord_panel, "chord_panel")
    _check_positive(b, "b")
    semi_span = b / 2.0
    panel_span = area_panel / chord_panel
    aspect_ratio = panel_span / chord_panel
    span_fraction = panel_span / semi_span
    ar_ok = 1.5 <= aspect_ratio <= 4.0
    sf_ok = 0.2 <= span_fraction <= 0.5
    notes = []
    if not ar_ok:
        notes.append("aspect ratio %g outside 1.5-4 band" % aspect_ratio)
    if not sf_ok:
        notes.append("span fraction %g outside 0.2-0.5 band" % span_fraction)
    if notes:
        verdict = "geometry outside typical band: " + "; ".join(notes)
    else:
        verdict = "panel geometry within typical bands"
    return {
        "aspect_ratio": aspect_ratio,
        "aspect_ratio_ok": ar_ok,
        "span_fraction": span_fraction,
        "span_fraction_ok": sf_ok,
        "verdict": verdict,
    }


def spoiler_verdict(
    p_req,
    v,
    s,
    b,
    q,
    f_aileron_share,
    y_arm,
    f_dump,
    cl_touchdown,
    cl_delta_spoil=CL_DELTA_SPOIL_TYP,
    c_l_p=ROLL_DAMPING_TYP,
    k_dump=K_DUMP_TYP,
    delta_max_deg=DELTA_MAX_DEG,
    n_flight_panels=4,
    flight_panel_chord=1.0,
    dump_local_chord=3.5,
    alpha_deg=4.0,
    cd_spoil=CD_SPOIL_TYP,
    coeffs=HINGE_COEFFS_TYP,
    dump_chord_fraction=DUMP_CHORD_FRACTION_TYP,
):
    """Complete spoiler sizing verdict dict for a transport.

    Orchestrates the share split, the flight spoiler area and
    deflection from the roll damping requirement, the ground spoiler
    belt area from the touchdown lift dump, the speed brake and lift
    dump drag increments, the flight panel hinge moment, and the
    deflection and geometry limit checks. Returns a dict with the
    areas, deflections, drag increments, hinge moments, limits, and
    a sized verdict string.
    """
    _check_positive(p_req, "p_req")
    _check_positive(v, "v")
    _check_positive(s, "s")
    _check_positive(b, "b")
    _check_positive(q, "q")
    _check_positive(y_arm, "y_arm")
    _check_positive(cl_touchdown, "cl_touchdown")
    _check_positive(alpha_deg, "alpha_deg")
    f_spoil = roll_spoiler_share(f_aileron_share)
    c_l_req = roll_coefficient_required(p_req, v, b, c_l_p)
    c_l_spoil_req = c_l_req * f_spoil
    l_share = roll_moment_share(c_l_spoil_req, q, s, b)
    a_flight = flight_spoiler_area(l_share, q, s, b, cl_delta_spoil, y_arm)
    a_per_panel = a_flight / n_flight_panels
    delta_eff_deg = _deg2rad(LINEAR_DELTA_DEG)
    lift_increment = c_l_spoil_req * b / y_arm
    deflection_deg = flight_spoiler_deflection(
        lift_increment, a_flight, s, cl_delta_spoil
    )
    alpha_rad = _deg2rad(alpha_deg)
    h_flight = hinge_moment(
        q, a_per_panel, flight_panel_chord, alpha_rad, delta_eff_deg, coeffs
    )
    dcd_speed = speed_brake_drag_increment(a_flight, s, cd_spoil, LINEAR_DELTA_DEG)
    a_dump = ground_spoiler_area(f_dump, cl_touchdown, s, k_dump, delta_max_deg)
    dump_planform = a_dump * dump_chord_fraction
    dcd_dump = lift_dump_drag_increment(
        dump_planform, s, cd_spoil, delta_max_deg
    )
    limits = deflection_limits_check(deflection_deg, delta_max_deg)
    geometry = geometry_limits_check(a_per_panel, flight_panel_chord, b)
    semi_span = b / 2.0
    dump_run_per_side = (a_dump / 2.0) / dump_local_chord
    dump_span_fraction = dump_run_per_side / semi_span
    dump_span_ok = 0.2 <= dump_span_fraction <= 0.5
    checks = [limits["within"], geometry["aspect_ratio_ok"],
              geometry["span_fraction_ok"], dump_span_ok]
    if all(checks):
        verdict_text = (
            "sized: flight spoiler total %g m^2, per panel %g m^2, "
            "dump belt %g m^2, deflection %g deg within travel, "
            "geometry within typical bands"
            % (a_flight, a_per_panel, a_dump, deflection_deg)
        )
    else:
        verdict_text = (
            "sized with limit findings: check deflection and "
            "geometry entries for the out-of-band item"
        )
    return {
        "roll_spoiler_share": f_spoil,
        "c_l_required_total": c_l_req,
        "c_l_spoiler_share": c_l_spoil_req,
        "roll_moment_share_nm": l_share,
        "flight_spoiler_area_m2": a_flight,
        "flight_panels": n_flight_panels,
        "flight_area_per_panel_m2": a_per_panel,
        "flight_deflection_deg": deflection_deg,
        "flight_hinge_moment_nm_per_panel": h_flight,
        "speed_brake_drag_increment": dcd_speed,
        "ground_spoiler_area_m2": a_dump,
        "ground_deflection_deg": delta_max_deg,
        "lift_dump_drag_increment": dcd_dump,
        "limits": limits,
        "geometry": geometry,
        "dump_span_fraction": dump_span_fraction,
        "dump_span_ok": dump_span_ok,
        "verdict": verdict_text,
    }
