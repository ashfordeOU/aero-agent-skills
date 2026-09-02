#!/usr/bin/env python3
"""Feedback control design logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, arp4754a: gated,
reference-only): ARP4754A frames the development process for aircraft
and systems functions including control laws; the frequency-domain
margins here (gain margin >= 6 dB, phase margin >= 45 degrees) and the
Ziegler-Nichols PID tuning rule are textbook control engineering
practice, not standard text.
"""


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def gain_margin_ok(gm_db, min_db=6.0):
    """True when the gain margin (dB) meets the acceptance minimum."""
    return gm_db >= min_db


def phase_margin_ok(pm_deg, min_deg=45.0):
    """True when the phase margin (deg) meets the acceptance minimum."""
    return pm_deg >= min_deg


def stability_from_margins(gm_db, pm_deg):
    """Classify closed-loop stability from the margins.

    'stable' when both margins are positive; 'unstable' when either is
    zero or negative; non-numeric inputs raise ValueError.
    """
    if not (_is_number(gm_db) and _is_number(pm_deg)):
        raise ValueError("margins must be numeric, got %r, %r" % (gm_db, pm_deg))
    if gm_db > 0 and pm_deg > 0:
        return "stable"
    return "unstable"


def ziegler_nichols_pid(ku, tu):
    """Classic Ziegler-Nichols PID gains (kp, ki, kd) from ultimate
    gain ku and ultimate period tu (continuous-cycling method)."""
    if ku <= 0 or tu <= 0:
        raise ValueError("ultimate gain and period must be > 0, got %r, %r" % (ku, tu))
    kp = 0.6 * ku
    ki = 2.0 * kp / tu
    kd = kp * tu / 8.0
    return (kp, ki, kd)


def controller_sanity(kp, ki, kd):
    """True when the gains are structurally sane: positive proportional
    gain, non-negative integral and derivative gains."""
    return kp > 0 and ki >= 0 and kd >= 0
