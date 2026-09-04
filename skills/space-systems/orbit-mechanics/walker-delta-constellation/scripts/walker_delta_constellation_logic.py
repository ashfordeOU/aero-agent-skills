"""Walker-Delta constellation parameterization (pure geometry, stdlib only).

Implements the standard Walker-Delta t/p/f constellation model at the
conceptual level. Conventions (module contract):

- t: total satellites; p: number of orbital planes; f: phasing parameter.
- s = t / p satellites per plane (validated integer).
- RAAN of plane j (0-based): j * 360 / p degrees.
- Mean anomaly of slot k in plane j:
    (k * 360 / s + j * f * 360 / t) mod 360
  Each plane's first slot carries the inter-plane phase offset.
- Slot ids are (plane_index, slot_index).

The t/p/f triple is the Walker-Delta notation used for the Galileo-class
constellations: t satellites distributed over p equally spaced planes
with a phasing offset f between adjacent planes.

All functions raise ValueError on a non-physical t/p/f triple.
"""


def validate_walker(t, p, f):
    """Validate a Walker-Delta (t, p, f) triple; raise ValueError if invalid.

    Rules: t and p must be positive integers with t % p == 0, and the
    phasing parameter f must be an integer in [0, p - 1].
    """
    if not isinstance(t, int) or not isinstance(p, int) or not isinstance(f, int):
        raise ValueError("t, p and f must be integers")
    if t <= 0 or p <= 0:
        raise ValueError("t and p must be positive (got t=%r, p=%r)" % (t, p))
    if t % p != 0:
        raise ValueError("total satellites t must be divisible by the plane count p")
    if f < 0 or f >= p:
        raise ValueError("phasing parameter f must be in [0, p - 1]")


def walker_parameters(t, p, f):
    """Return the Walker-Delta geometry dict for (t, p, f).

    Returns dict with keys satellites_per_plane, raan_spacing_deg,
    mean_anomaly_spacing_deg and inter_plane_phase_deg.
    """
    validate_walker(t, p, f)
    s = t // p
    return {
        "satellites_per_plane": s,
        "raan_spacing_deg": 360.0 / p,
        "mean_anomaly_spacing_deg": 360.0 / s,
        "inter_plane_phase_deg": f * 360.0 / t,
    }


def walker_slots(t, p, f):
    """Enumerate the (plane, slot, raan_deg, mean_anomaly_deg) slot grid.

    Returns a list of t dicts, s = t/p entries per plane, ordered by
    plane then slot. RAAN of plane j is j * 360 / p; mean anomaly of
    slot k in plane j is (k * 360 / s + j * f * 360 / t) mod 360.
    """
    validate_walker(t, p, f)
    s = t // p
    slots = []
    for j in range(p):
        raan = j * 360.0 / p
        for k in range(s):
            ma = (k * 360.0 / s + j * f * 360.0 / t) % 360.0
            slots.append(
                {
                    "plane": j,
                    "slot": k,
                    "raan_deg": raan,
                    "mean_anomaly_deg": ma,
                }
            )
    return slots


def unique_slot_count(t, p, f):
    """Return the number of distinct (raan_deg, mean_anomaly_deg) pairs.

    For a valid Walker-Delta triple this equals t: planes carry distinct
    RAAN values and every slot pair is unique.
    """
    slots = walker_slots(t, p, f)
    return len({(s["raan_deg"], s["mean_anomaly_deg"]) for s in slots})
