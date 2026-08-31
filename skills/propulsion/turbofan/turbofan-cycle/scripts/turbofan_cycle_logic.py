#!/usr/bin/env python3
"""Turbofan cycle parameter logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, far-33: public domain
regulation context): FAR-33 sets the engine type-certification basis;
turbofan cycle performance work sits upstream of certification. The
bypass ratio, propulsive efficiency, net thrust, and specific thrust
are standard propulsion methodology. SI units throughout: mass flow
in kg/s, velocities in m/s, thrust in N, efficiency dimensionless.
"""


def bypass_ratio(m_dot_fan, m_dot_core):
    """Bypass ratio B = fan stream mass flow / core stream mass flow.

    Raises ValueError when either mass flow is <= 0.
    """
    if m_dot_fan <= 0:
        raise ValueError("fan mass flow must be > 0, got %r" % (m_dot_fan,))
    if m_dot_core <= 0:
        raise ValueError("core mass flow must be > 0, got %r" % (m_dot_core,))
    return m_dot_fan / float(m_dot_core)


def propulsive_efficiency(v0_ms, vj_ms):
    """Propulsive efficiency eta_p = 2*v0/(v0 + vj), dimensionless.

    Raises ValueError when flight velocity <= 0 or jet velocity
    <= flight velocity.
    """
    if v0_ms <= 0:
        raise ValueError("flight velocity must be > 0, got %r" % (v0_ms,))
    if vj_ms <= v0_ms:
        raise ValueError(
            "jet velocity must be > flight velocity, got %r <= %r" % (vj_ms, v0_ms)
        )
    return 2.0 * v0_ms / (v0_ms + vj_ms)


def thrust(m_dot_total, vj_ms, v0_ms):
    """Net thrust F = m_dot_total*(vj - v0) [N].

    Raises ValueError when total mass flow <= 0 or jet velocity
    <= flight velocity.
    """
    if m_dot_total <= 0:
        raise ValueError("total mass flow must be > 0, got %r" % (m_dot_total,))
    if vj_ms <= v0_ms:
        raise ValueError(
            "jet velocity must be > flight velocity, got %r <= %r" % (vj_ms, v0_ms)
        )
    return m_dot_total * (vj_ms - v0_ms)


def specific_thrust(thrust_n, m_dot_total):
    """Specific thrust F/m_dot_total [m/s].

    Raises ValueError when total mass flow <= 0 or net thrust < 0.
    """
    if m_dot_total <= 0:
        raise ValueError("total mass flow must be > 0, got %r" % (m_dot_total,))
    if thrust_n < 0:
        raise ValueError("net thrust must be >= 0, got %r" % (thrust_n,))
    return thrust_n / float(m_dot_total)
