#!/usr/bin/env python3
"""Finite element contact analysis logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml: far-25 and cs-25 public
domain, referenced by name only): contact in finite element analysis
is enforced either by the penalty method (a normal force proportional
to penetration, F_n = k_pen * p) or by the Lagrange multiplier method
(the zero penetration constraint is enforced exactly with the contact
pressure as an unknown). The penalty stiffness is estimated from the
softer contacting member as k_pen = alpha * E * A / L, and penetration
control raises the stiffness until the penetration p = F / k_pen
falls under the accepted tolerance. Coulomb friction caps the
tangential force at mu * |F_n|, categorizing the interface as sticking
or slipping. Master-slave (node-to-surface) contact computes a signed
gap by projecting slave nodes onto the master surface along its
normal. Tie constraints rigidly bond surfaces within a relative
displacement tolerance. All functions are deterministic, stdlib only,
offline, and use N/mm units.
"""

import math


def contact_stiffness_estimate(young_modulus, contact_area,
                               characteristic_length, alpha=100.0):
    """Penalty stiffness estimate: k_pen = alpha * E * A / L.

    young_modulus in N/mm^2, contact_area in mm^2,
    characteristic_length in mm; returns stiffness in N/mm. alpha is
    the multiplier on the underlying element stiffness scale (10 to
    1000 in practice). All inputs must be strictly positive.
    """
    for name, value in (("young_modulus", young_modulus),
                        ("contact_area", contact_area),
                        ("characteristic_length", characteristic_length),
                        ("alpha", alpha)):
        if value <= 0.0:
            raise ValueError("%s must be strictly positive: %r"
                             % (name, value))
    return alpha * young_modulus * contact_area / characteristic_length


def penalty_contact_force(stiffness, gap):
    """Penalty normal contact force from a signed gap.

    gap >= 0 means separation: no contact, zero force. gap < 0 means
    penetration p = -gap: force = stiffness * p (compression
    positive). Returns a dict with in_contact, gap, penetration, and
    force. Negative stiffness raises ValueError.
    """
    if stiffness < 0.0:
        raise ValueError("stiffness must be non-negative: %r" % (stiffness,))
    if gap >= 0.0:
        return {"in_contact": False, "gap": gap,
                "penetration": 0.0, "force": 0.0}
    penetration = -gap
    return {"in_contact": True, "gap": gap,
            "penetration": penetration, "force": stiffness * penetration}


def lagrange_contact_check(gap, tolerance=1e-9):
    """Lagrange multiplier enforcement check for a signed gap.

    The Lagrange method enforces zero penetration exactly: the
    constraint is active when the gap is at or below zero, and it is
    enforced when the resulting penetration is within tolerance.
    Returns a dict with in_contact, gap, penetration, and enforced.
    """
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative: %r" % (tolerance,))
    penetration = max(0.0, -gap)
    return {"in_contact": gap <= 0.0, "gap": gap,
            "penetration": penetration,
            "enforced": penetration <= tolerance}


def friction_force(normal_force, mu, tangential_trial):
    """Coulomb friction: cap the shear at mu * |normal_force|.

    When |tangential_trial| <= f_max the interface sticks and the
    friction force equals the trial shear; otherwise it slips and the
    friction force saturates at f_max in the trial direction. The
    result is categorized as 'sticking' or 'slipping'. normal_force
    must be non-negative (a negative normal force means separation,
    which carries no friction) and mu must be non-negative.
    """
    if normal_force < 0.0:
        raise ValueError(
            "normal force must be non-negative (contact is compressive): %r"
            % (normal_force,))
    if mu < 0.0:
        raise ValueError("friction coefficient must be non-negative: %r"
                         % (mu,))
    f_max = mu * abs(normal_force)
    if abs(tangential_trial) <= f_max:
        return {"state": "sticking", "friction_force": tangential_trial,
                "max_friction": f_max}
    direction = 0.0 if tangential_trial == 0.0 \
        else (1.0 if tangential_trial > 0.0 else -1.0)
    return {"state": "slipping", "friction_force": direction * f_max,
            "max_friction": f_max}


def penetration_control(applied_force, stiffness, tolerance,
                        factor=10.0, max_iterations=10):
    """Penetration control: raise stiffness until p = F / k is under
    tolerance.

    With an applied normal load, the equilibrium penetration is
    p = applied_force / stiffness. Each iteration multiplies the
    stiffness by factor (must be > 1) and re-checks. Returns a dict
    with stiffness, penetration, iterations, and converged; reports
    converged False with the final stiffness when the loop runs out.
    """
    if applied_force < 0.0:
        raise ValueError("applied_force must be non-negative: %r"
                         % (applied_force,))
    if stiffness <= 0.0:
        raise ValueError("stiffness must be strictly positive: %r"
                         % (stiffness,))
    if tolerance <= 0.0:
        raise ValueError("tolerance must be strictly positive: %r"
                         % (tolerance,))
    if factor <= 1.0:
        raise ValueError("factor must be strictly greater than 1: %r"
                         % (factor,))
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1: %r"
                         % (max_iterations,))
    current = stiffness
    for i in range(1, max_iterations + 1):
        penetration = applied_force / current
        if penetration <= tolerance:
            return {"stiffness": current, "penetration": penetration,
                    "iterations": i, "converged": True}
        current *= factor
    return {"stiffness": current,
            "penetration": applied_force / current,
            "iterations": max_iterations, "converged": False}


def node_to_surface_gap(master_p1, master_p2, slave_point):
    """Signed gap of a slave node against a 2D master segment.

    master_p1, master_p2: (x, y) endpoints of the master surface
    segment; slave_point: (x, y) slave node. The gap is the
    projection of the slave node onto the segment's left normal
    (outward for a segment oriented counter-clockwise around the
    master body). Positive gap is separation, negative gap is
    penetration. A zero-length master segment raises ValueError.
    """
    x1, y1 = master_p1
    x2, y2 = master_p2
    xs, ys = slave_point
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0.0:
        raise ValueError("zero-length master segment: %r, %r"
                         % (master_p1, master_p2))
    nx = -dy / length
    ny = dx / length
    return (xs - x1) * nx + (ys - y1) * ny


def tie_constraint_check(relative_displacement, tolerance):
    """Tied interface check: relative displacement within tolerance.

    A tie constraint rigidly bonds two surfaces (no separation, no
    sliding); the bond holds when the relative displacement magnitude
    stays within tolerance. Returns a dict with tied,
    relative_displacement, and tolerance.
    """
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative: %r"
                         % (tolerance,))
    return {"tied": abs(relative_displacement) <= tolerance,
            "relative_displacement": relative_displacement,
            "tolerance": tolerance}
