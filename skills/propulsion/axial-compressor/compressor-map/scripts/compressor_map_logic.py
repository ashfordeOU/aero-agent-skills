#!/usr/bin/env python3
"""Axial compressor operating map logic.

The compressor map plots total pressure ratio against corrected mass
flow with iso-speed lines. The stable operating region is bounded on
the left by the surge line (peak pressure ratio per speed) and on the
right by the choke line (blocked flow). The operating line is the
design locus of running points below the surge line.

Standard-day correction (theta/delta method), SI units throughout:
- theta = Tt / T_ref with T_ref = 288.15 K (dimensionless)
- delta = Pt / P_ref with P_ref = 101325 Pa (dimensionless)
- corrected mass flow m_corr = m_actual * sqrt(theta) / delta in kg/s
- corrected rotor speed N_corr = N_actual / sqrt(theta) in rpm
- flow-basis surge margin (q_operating - q_surge) / q_operating * 100
  in percent: at constant corrected speed the surge point sits at
  lower flow than the running point, so a positive margin means the
  running point is to the right of (safer than) surge
- pressure-ratio operating-line clearance
  (pr_surge - pr_operating) / pr_operating * 100 in percent: at the
  same corrected flow the surge line sits above the operating line
- map verdict: "on-map", "approaching-surge", or "on-surge-line"
  from the fractional pressure-ratio distance to the surge line

FAR-33 is referenced, not reproduced; the map conventions and
correction relations are common turbomachinery methodology summarized
per standards-map.yaml.

Functions raise ValueError on non-physical inputs (zero or negative
flows, speeds, temperatures, or pressures; surge pressure ratio at or
below unity) instead of returning nonsense or dividing by zero.
"""

import math


def corrected_flow(m_actual, theta, delta):
    """Corrected mass flow m_corr = m_actual*sqrt(theta)/delta in kg/s.

    theta = Tt/288.15 and delta = Pt/101325 are the standard-day
    correction factors (dimensionless); m_actual is the measured mass
    flow in kg/s.
    """
    if m_actual <= 0:
        raise ValueError("m_actual must be > 0, got %r" % (m_actual,))
    if theta <= 0:
        raise ValueError("theta must be > 0, got %r" % (theta,))
    if delta <= 0:
        raise ValueError("delta must be > 0, got %r" % (delta,))
    return m_actual * math.sqrt(theta) / delta


def corrected_speed(n_actual, theta):
    """Corrected rotor speed N_corr = n_actual/sqrt(theta) in rpm.

    n_actual is the measured rotor speed in rpm; theta is the
    standard-day temperature correction factor (dimensionless).
    """
    if n_actual <= 0:
        raise ValueError("n_actual must be > 0, got %r" % (n_actual,))
    if theta <= 0:
        raise ValueError("theta must be > 0, got %r" % (theta,))
    return n_actual / math.sqrt(theta)


def surge_margin_flow(q_surge, q_operating):
    """Flow-basis surge margin in percent.

    SM = (q_operating - q_surge) / q_operating * 100 at the same
    corrected speed: the horizontal clearance from the surge point to
    the running point. Positive means the running point is at higher
    flow than the surge point (safe side); negative means it is left
    of surge (unstable).
    """
    if q_surge <= 0:
        raise ValueError("q_surge must be > 0, got %r" % (q_surge,))
    if q_operating <= 0:
        raise ValueError("q_operating must be > 0, got %r" % (q_operating,))
    return (q_operating - q_surge) / q_operating * 100.0


def operating_line_clearance(pr_operating, pr_surge):
    """Pressure-ratio operating-line clearance in percent.

    CL = (pr_surge - pr_operating) / pr_operating * 100 at the same
    corrected flow: the vertical clearance from the operating line to
    the surge line. Positive means the operating line is below surge
    (safe side); negative means it is above surge (unstable).
    """
    if pr_operating <= 0:
        raise ValueError("pr_operating must be > 0, got %r" % (pr_operating,))
    if pr_surge <= 0:
        raise ValueError("pr_surge must be > 0, got %r" % (pr_surge,))
    return (pr_surge - pr_operating) / pr_operating * 100.0


def map_verdict(pr, q_corr, surge_pr, threshold=0.05):
    """Classify an operating point against the surge line.

    pr is the operating pressure ratio, q_corr the corrected mass flow
    in kg/s, surge_pr the surge-line pressure ratio at that flow.
    Returns "on-surge-line" when pr >= surge_pr, "approaching-surge"
    when the fractional gap (surge_pr - pr)/surge_pr is within the
    threshold (default 0.05, i.e. 5%), else "on-map".
    """
    if pr <= 0:
        raise ValueError("pr must be > 0, got %r" % (pr,))
    if q_corr <= 0:
        raise ValueError("q_corr must be > 0, got %r" % (q_corr,))
    if surge_pr <= 1.0:
        raise ValueError("surge_pr must be > 1, got %r" % (surge_pr,))
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be in (0, 1), got %r" % (threshold,))
    if pr >= surge_pr:
        return "on-surge-line"
    if (surge_pr - pr) / surge_pr <= threshold:
        return "approaching-surge"
    return "on-map"


def map_point(n_corr, m_corr):
    """Identify a map point by its corrected speed and corrected flow.

    Returns a dict with corrected_speed (rpm) and corrected_flow
    (kg/s); the canonical way to locate a point on the map before
    querying the surge line at that flow.
    """
    if n_corr <= 0:
        raise ValueError("n_corr must be > 0, got %r" % (n_corr,))
    if m_corr <= 0:
        raise ValueError("m_corr must be > 0, got %r" % (m_corr,))
    return {"corrected_speed": n_corr, "corrected_flow": m_corr}
