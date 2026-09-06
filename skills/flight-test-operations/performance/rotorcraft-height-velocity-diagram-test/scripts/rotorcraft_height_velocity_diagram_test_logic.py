"""Reduction of FAR 29 rotorcraft height-velocity (dead-man-curve)
demonstration flight tests (requirement named and framed only).

Pure stdlib arithmetic on measured marks and trace read-offs: per
demonstration the engine-failure recognition delay, the time to establish
autorotation and complete the flare or landing, the height lost to the
flare, the recovery altitude the flare consumes, the recognition-phase
height loss with the declared reaction time allowance, and the PASS or
FAIL touchdown verdict against the declared safe-touchdown sink limit.
Across the demonstrations of one speed, the height-velocity boundary
height where the measured height loss plus the recovery altitude equals
the starting height (linear crossing of the touchdown-sink versus
starting-height line through the bracketing pair at the sink limit), the
measured avoid-region map over the (height, speed) grid, and the
per-speed clearance verdict against the predicted height-velocity
diagram (quoted input from the flight-mechanics autorotative-descent
sink model).

Deterministic closed-form reduction, math only, no randomness.
"""

import math

# Module constants (representative demonstration rotorcraft; declared
# values, FAR 29 frames the height-velocity demonstration requirement by
# name only, no rule text reproduced).
SAFE_TOUCHDOWN_FPM = 600.0   # declared safe-touchdown sink limit, ft/min
REACTION_ALLOWANCE_S = 1.0   # declared reaction time allowance, s


def recognition_delay(t_reaction_s, t_failure_s):
    """Measured engine-failure recognition delay in seconds: the trace time
    of the first control input minus the trace time of the engine-failure
    event mark."""
    if t_failure_s < 0.0:
        raise ValueError("failure event time before the record start")
    if t_reaction_s <= t_failure_s:
        raise ValueError("first control input not after the failure event")
    return t_reaction_s - t_failure_s


def recognition_loss_with_allowance(h_rec_measured_ft, sink_end_recognition_fps,
                                    allowance_s=REACTION_ALLOWANCE_S):
    """Recognition-phase height loss in ft with the declared reaction time
    allowance applied: the measured height lost over the recognition window
    plus the additional height the rotorcraft sinks at the measured
    recognition-window end sink rate during the allowance seconds."""
    if h_rec_measured_ft < 0.0:
        raise ValueError("negative measured recognition height loss")
    if sink_end_recognition_fps < 0.0:
        raise ValueError("negative recognition-window end sink rate")
    if allowance_s < 0.0:
        raise ValueError("negative reaction time allowance")
    return h_rec_measured_ft + sink_end_recognition_fps * allowance_s


def time_to_establish_autorotation(t_flare_s, t_reaction_s):
    """Time in seconds from the first control input to the flare-initiation
    mark: the measured time to establish autorotation and set up the
    flare."""
    if t_reaction_s < 0.0:
        raise ValueError("reaction time before the record start")
    if t_flare_s <= t_reaction_s:
        raise ValueError("flare-initiation mark not after the first input")
    return t_flare_s - t_reaction_s


def height_lost_to_flare(h_start_ft, h_flare_ft):
    """Measured height lost in ft from the engine-failure starting height to
    the flare-initiation mark (the recognition and entry losses together,
    read off the baro/radar altitude trace)."""
    if h_start_ft <= 0.0:
        raise ValueError("non-positive demonstration starting height")
    if h_flare_ft <= 0.0 or h_flare_ft >= h_start_ft:
        raise ValueError("flare-initiation altitude not strictly inside the "
                         "recorded descent")
    return h_start_ft - h_flare_ft


def flare_recovery_altitude(h_flare_ft, h_contact_ft=0.0):
    """Recovery altitude in ft: the altitude consumed completing the flare
    and landing, the flare-initiation altitude above the touchdown
    altitude (0 ft for a touchdown)."""
    if h_flare_ft <= 0.0:
        raise ValueError("non-positive flare-initiation altitude")
    if h_contact_ft < 0.0 or h_contact_ft >= h_flare_ft:
        raise ValueError("touchdown altitude not below the flare-initiation "
                         "altitude")
    return h_flare_ft - h_contact_ft


def touchdown_verdict(touchdown_sink_fpm, limit_fpm=SAFE_TOUCHDOWN_FPM):
    """PASS or FAIL touchdown verdict of one demonstration: PASS when the
    measured touchdown sink rate is at or below the declared limit,
    inclusive at the limit."""
    if touchdown_sink_fpm < 0.0:
        raise ValueError("negative touchdown sink rate")
    if limit_fpm <= 0.0:
        raise ValueError("non-positive touchdown sink limit")
    return "PASS" if touchdown_sink_fpm <= limit_fpm else "FAIL"


def interpolate_boundary_height(fail_h0_ft, pass_h0_ft, fail_sink_fpm,
                                pass_sink_fpm, limit_fpm=SAFE_TOUCHDOWN_FPM):
    """Reduced height-velocity boundary height in ft at one speed: the
    linear crossing of the touchdown-sink-versus-starting-height line
    through the bracketing demonstration pair (highest FAILING starting
    height, lowest PASSING starting height) at the declared touchdown sink
    limit."""
    if fail_h0_ft <= 0.0 or pass_h0_ft <= 0.0:
        raise ValueError("non-positive bracketing starting height")
    if pass_h0_ft <= fail_h0_ft:
        raise ValueError("no FAIL to PASS verdict flip in the swept heights")
    if fail_sink_fpm <= limit_fpm:
        raise ValueError("highest failing demonstration at or under the limit")
    if pass_sink_fpm > limit_fpm:
        raise ValueError("lowest passing demonstration above the limit")
    if limit_fpm <= 0.0:
        raise ValueError("non-positive touchdown sink limit")
    if math.isclose(pass_sink_fpm, fail_sink_fpm):
        raise ValueError("flat touchdown-sink line across the bracket")
    frac = (limit_fpm - fail_sink_fpm) / (pass_sink_fpm - fail_sink_fpm)
    return fail_h0_ft + (pass_h0_ft - fail_h0_ft) * frac


def build_avoid_map(heights_ft, speeds_kt, boundary_ft):
    """Measured avoid-region map over the (height AGL, speed KTAS) grid:
    one cell per grid point, region AVOID when the height is strictly
    below the reduced boundary at that speed (inside the dead-man-curve
    region), SAFE at or above it. Returns the cells as a list of dicts."""
    if not heights_ft or not speeds_kt:
        raise ValueError("empty height or speed grid")
    if len(boundary_ft) != len(speeds_kt):
        raise ValueError("boundary table length differs from the speed grid")
    if any(h <= 0.0 for h in heights_ft):
        raise ValueError("non-positive grid height")
    if any(b < 0.0 for b in boundary_ft):
        raise ValueError("negative boundary height")
    cells = []
    for i, v in enumerate(speeds_kt):
        for h in heights_ft:
            cells.append({"height_ft": h, "speed_kt": v,
                          "region": "AVOID" if h < boundary_ft[i] else "SAFE"})
    return cells


def clearance_verdict(measured_boundary_ft, predicted_boundary_ft):
    """Clearance of the measured height-velocity boundary against the
    predicted height-velocity diagram at one speed: margin_ft is the
    predicted boundary height minus the measured boundary height; verdict
    PASS when the measured avoid region does not extend above the predicted
    boundary (margin at or above zero, inclusive)."""
    if measured_boundary_ft < 0.0 or predicted_boundary_ft < 0.0:
        raise ValueError("negative boundary height")
    margin = predicted_boundary_ft - measured_boundary_ft
    return {"measured_boundary_ft": measured_boundary_ft,
            "predicted_boundary_ft": predicted_boundary_ft,
            "margin_ft": margin,
            "verdict": "PASS" if margin >= 0.0 else "FAIL"}
