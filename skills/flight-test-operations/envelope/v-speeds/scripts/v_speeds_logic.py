#!/usr/bin/env python3
"""V-speeds logic module: vref, v2, and vr from stall speeds.

Contract: docs/harness-contract.md gate 3 (flight-test-operations/
envelope/v-speeds leaf). All speeds are in m/s.

The certification factors (vref = 1.3 * vs0, v2 = 1.2 * vs1,
vr = 1.1 * vs1) follow the FAR-25.107/25.125 context as common
certification practice; the exact basis comes from the flight test
program. Reference only, not reproduced.
"""


def reference_landing_speed(vs0):
    """Reference landing speed vref from the landing-configuration
    stalling speed vs0 in m/s. vref = 1.3 * vs0, output in m/s.
    Raises ValueError when vs0 is non-positive.
    """
    if vs0 <= 0:
        raise ValueError("vs0 must be positive, got %r" % (vs0,))
    return 1.3 * vs0


def takeoff_safety_speed(vs1):
    """Takeoff safety speed v2 from the takeoff-configuration
    stalling speed vs1 in m/s. v2 = 1.2 * vs1, output in m/s.
    Raises ValueError when vs1 is non-positive.
    """
    if vs1 <= 0:
        raise ValueError("vs1 must be positive, got %r" % (vs1,))
    return 1.2 * vs1


def rotation_speed(vs1):
    """Rotation speed vr from the takeoff-configuration stalling
    speed vs1 in m/s. vr = 1.1 * vs1, output in m/s.
    Raises ValueError when vs1 is non-positive.
    """
    if vs1 <= 0:
        raise ValueError("vs1 must be positive, got %r" % (vs1,))
    return 1.1 * vs1


def v_speeds(vs, vs0, vs1):
    """Assemble the validated v-speeds dict from the clean (vs),
    landing-configuration (vs0), and takeoff-configuration (vs1)
    stalling speeds in m/s.

    Returns {'vs': vs, 'vs0': vs0, 'vs1': vs1, 'vref': vref,
    'v2': v2, 'vr': vr} with vref = 1.3 * vs0, v2 = 1.2 * vs1,
    vr = 1.1 * vs1. Raises ValueError when any speed is
    non-positive, vs1 < vs (takeoff configuration stalls below
    clean), or vs0 > vs1 (landing configuration stalls above
    takeoff).
    """
    speeds = (vs, vs0, vs1)
    if any(s <= 0 for s in speeds):
        raise ValueError("all stalling speeds must be positive, got %r" % (speeds,))
    if vs1 < vs:
        raise ValueError(
            "vs1 must be >= vs (takeoff config stalls at or above clean), "
            "got vs1=%r vs=%r" % (vs1, vs)
        )
    if vs0 > vs1:
        raise ValueError(
            "vs0 must be <= vs1 (landing config stalls below takeoff), "
            "got vs0=%r vs1=%r" % (vs0, vs1)
        )
    return {
        "vs": vs,
        "vs0": vs0,
        "vs1": vs1,
        "vref": 1.3 * vs0,
        "v2": 1.2 * vs1,
        "vr": 1.1 * vs1,
    }


def vno_vne_guard(operating_speed, vne):
    """Verdict for an operating speed against the never exceed
    speed vne, all in m/s.

    Returns {'vne_exceeded': bool, 'margin_mps': vne -
    operating_speed}. Raises ValueError when vne is non-positive.
    """
    if vne <= 0:
        raise ValueError("vne must be positive, got %r" % (vne,))
    return {
        "vne_exceeded": operating_speed > vne,
        "margin_mps": vne - operating_speed,
    }
