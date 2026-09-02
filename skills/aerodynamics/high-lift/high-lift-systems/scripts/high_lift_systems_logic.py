#!/usr/bin/env python3
"""High-lift systems estimation logic (paraphrase, public-domain textbook correlations).

Conceptual-design correlations for trailing-edge flaps (plain, split,
slotted, Fowler) and leading-edge devices (slat, Krueger). Reference
increment values are widely cited textbook estimates (Raymer, Aircraft
Design: A Conceptual Approach, flap-type clmax increments for a flap
chord ratio near 0.25 at full span and full deflection). The model is
DATCOM-style: the section increment scales with deflection, flap chord
ratio, and flapped span fraction,

  Delta clmax = Delta clmax_ref * K_delta * K_chord * K_span
  K_delta = sin(delta) / sin(delta_max), clamped at delta_max
  K_chord = (c_f / c) / (c_f / c)_ref
  K_span = flapped span fraction

with leading-edge devices added by superposition. Wing-level CLmax
applies a three-dimensional and sweep reduction,

  CLmax_wing = 0.9 * clmax_section * cos(Lambda),

and the resulting stall speed is

  V_stall = sqrt(2 W / (rho S CLmax_wing)).

Drag and pitching moment increments:

  Delta CD0 = CD0_ref * sin(delta) / sin(delta_max)
  Delta CDi = Delta CL^2 / (pi AR e)
  Delta Cm  = -Delta CL * (x_cp - x_ac)

All inputs are validated; nonsense inputs raise ValueError.
"""

import math

# Reference flap data: full-deflection clmax increment (section level,
# flap chord ratio near 0.25, full span), typical maximum deflection in
# degrees, reference flap chord fraction, zero-lift drag coefficient at
# full deflection, and flap center-of-pressure fraction of chord.
FLAP_TYPES = {
    "plain": {
        "delta_clmax_ref": 0.9,
        "deflection_max_deg": 60.0,
        "chord_frac_ref": 0.20,
        "cd0_ref": 0.05,
        "cp_frac": 0.50,
    },
    "split": {
        "delta_clmax_ref": 0.9,
        "deflection_max_deg": 60.0,
        "chord_frac_ref": 0.20,
        "cd0_ref": 0.06,
        "cp_frac": 0.50,
    },
    "slotted": {
        "delta_clmax_ref": 1.3,
        "deflection_max_deg": 40.0,
        "chord_frac_ref": 0.25,
        "cd0_ref": 0.08,
        "cp_frac": 0.52,
    },
    "fowler": {
        "delta_clmax_ref": 1.7,
        "deflection_max_deg": 40.0,
        "chord_frac_ref": 0.30,
        "cd0_ref": 0.09,
        "cp_frac": 0.58,
    },
}

# Leading-edge devices: full-span reference clmax increment.
LEADING_EDGE_DEVICES = {
    "slat": 0.5,
    "krueger": 0.4,
}

WING_AC_FRAC = 0.25  # quarter chord


def _check_flap_type(flap_type):
    if flap_type not in FLAP_TYPES:
        raise ValueError(
            "unknown flap type %r; expected one of %s"
            % (flap_type, ", ".join(sorted(FLAP_TYPES)))
        )


def _check_deflection(deflection_deg):
    if deflection_deg < 0.0:
        raise ValueError("deflection must be >= 0 deg, got %r" % (deflection_deg,))


def _check_frac(value, name, allow_zero=True):
    if allow_zero:
        if not (0.0 <= value <= 1.0):
            raise ValueError("%s must be in [0, 1], got %r" % (name, value))
    else:
        if not (0.0 < value <= 1.0):
            raise ValueError("%s must be in (0, 1], got %r" % (name, value))


def _check_positive(value, name):
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def _deflection_factor(deflection_deg, deflection_max_deg):
    """sin(delta) / sin(delta_max), clamped at delta_max (flap stalls)."""
    if deflection_deg >= deflection_max_deg:
        return 1.0
    return math.sin(math.radians(deflection_deg)) / math.sin(
        math.radians(deflection_max_deg)
    )


def flap_clmax_increment(flap_type, deflection_deg, chord_frac=None, span_frac=1.0):
    """Section clmax increment for a trailing-edge flap.

    flap_type: plain, split, slotted, or fowler.
    deflection_deg: flap deflection, clamped at the type maximum.
    chord_frac: flap chord ratio; defaults to the type reference value.
    span_frac: flapped fraction of the span in (0, 1].
    """
    _check_flap_type(flap_type)
    _check_deflection(deflection_deg)
    data = FLAP_TYPES[flap_type]
    if chord_frac is None:
        chord_frac = data["chord_frac_ref"]
    _check_frac(chord_frac, "chord_frac", allow_zero=False)
    _check_frac(span_frac, "span_frac", allow_zero=False)
    k_delta = _deflection_factor(deflection_deg, data["deflection_max_deg"])
    k_chord = chord_frac / data["chord_frac_ref"]
    return data["delta_clmax_ref"] * k_delta * k_chord * span_frac


def fowler_chord_ratio(extension_frac):
    """Chord ratio c_ext / c = 1 + (Delta c / c) for a Fowler flap.

    The extension fraction is the added chord as a fraction of the
    clean chord, valid in [0, 1): zero means unextended (ratio 1.0),
    one would mean a doubled chord and is rejected.
    """
    if not (0.0 <= extension_frac < 1.0):
        raise ValueError(
            "extension_frac must be in [0, 1), got %r" % (extension_frac,)
        )
    return 1.0 + extension_frac


def slat_clmax_increment(device, span_frac=1.0):
    """Section clmax increment from a leading-edge device.

    device: slat or krueger; span_frac is the covered span fraction.
    """
    if device not in LEADING_EDGE_DEVICES:
        raise ValueError(
            "unknown leading-edge device %r; expected slat or krueger" % (device,)
        )
    _check_frac(span_frac, "span_frac", allow_zero=False)
    return LEADING_EDGE_DEVICES[device] * span_frac


def combined_clmax_increment(flap_increment, slat_increment):
    """Total section clmax increment, flap plus slat superposition."""
    if flap_increment < 0.0 or slat_increment < 0.0:
        raise ValueError("increments must be >= 0, got %r, %r" % (flap_increment, slat_increment))
    return flap_increment + slat_increment


def wing_clmax(clmax_section, sweep_deg=0.0):
    """Wing-level CLmax: 0.9 * clmax_section * cos(Lambda)."""
    _check_positive(clmax_section, "clmax_section")
    if not (0.0 <= sweep_deg < 90.0):
        raise ValueError("sweep must be in [0, 90) deg, got %r" % (sweep_deg,))
    return 0.9 * clmax_section * math.cos(math.radians(sweep_deg))


def stall_speed(weight, wing_area, rho, clmax_wing):
    """Stall speed in m/s: sqrt(2 W / (rho S CLmax))."""
    _check_positive(weight, "weight")
    _check_positive(wing_area, "wing_area")
    _check_positive(rho, "rho")
    _check_positive(clmax_wing, "clmax_wing")
    return math.sqrt(2.0 * weight / (rho * wing_area * clmax_wing))


def flap_drag_increment(flap_type, deflection_deg, delta_cl, aspect_ratio, oswald_e=0.8):
    """Drag rise from flaps: zero-lift term plus induced term.

    Returns (delta_cd0, delta_cdi, total).
    """
    _check_flap_type(flap_type)
    _check_deflection(deflection_deg)
    _check_positive(delta_cl, "delta_cl")
    _check_positive(aspect_ratio, "aspect_ratio")
    if not (0.0 < oswald_e <= 1.0):
        raise ValueError("oswald_e must be in (0, 1], got %r" % (oswald_e,))
    data = FLAP_TYPES[flap_type]
    k_delta = _deflection_factor(deflection_deg, data["deflection_max_deg"])
    cd0 = data["cd0_ref"] * k_delta
    cdi = (delta_cl * delta_cl) / (math.pi * aspect_ratio * oswald_e)
    return (cd0, cdi, cd0 + cdi)


def flap_pitch_moment_increment(flap_type, delta_cl, ac_frac=WING_AC_FRAC):
    """Wing-level pitching moment increment: -Delta CL * (x_cp - x_ac).

    Uses the flap type center-of-pressure fraction of chord.
    """
    _check_flap_type(flap_type)
    _check_positive(delta_cl, "delta_cl")
    if not (0.0 <= ac_frac <= 1.0):
        raise ValueError("ac_frac must be in [0, 1], got %r" % (ac_frac,))
    data = FLAP_TYPES[flap_type]
    return -delta_cl * (data["cp_frac"] - ac_frac)
