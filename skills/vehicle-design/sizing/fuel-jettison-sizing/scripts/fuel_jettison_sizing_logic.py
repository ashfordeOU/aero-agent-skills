"""Fuel jettison system sizing logic (FAR 25.1001 context, reference-only).

Pure Python stdlib, deterministic, offline. Sizes the fuel jettison
system at the conceptual level: from the maximum takeoff weight (MTOW)
and the maximum landing weight (MLW), computes the fuel mass that must
be dumpable and the required average jettison rate to reach the landing
weight within the 15-minute (900 s) limit, applies the design margin to
the required rate, splits the design flow over the dump mast count, and
verifies the resulting time to landing weight against the 900 s limit.

Conventions: masses in kg, rates in kg/s, times in s. The required
average rate assumes the full excess fuel (MTOW - MLW) is dumped evenly
over the limit.

The FAR 25.1001 fuel jettison context is reference-only: no regulatory
text is reproduced here, only the standard engineering sizing method.
"""

# 15-minute rule limit for reaching the maximum landing weight, seconds.
JETTISON_LIMIT_S = 900.0

# Default design margin (10 percent) applied to the required average rate.
DESIGN_MARGIN_DEFAULT = 1.1


def _validate_masses(mtow_kg, mlw_kg):
    """Reject non-physical takeoff and landing mass inputs."""
    if mtow_kg <= 0:
        raise ValueError("mtow_kg must be positive")
    if mlw_kg <= 0:
        raise ValueError("mlw_kg must be positive")
    if mlw_kg > mtow_kg:
        raise ValueError("mlw_kg cannot exceed mtow_kg")


def dumpable_fuel_mass(mtow_kg, mlw_kg):
    """Return the fuel mass (kg) that must be dumpable to reach MLW.

    The excess weight (MTOW - MLW) is the fuel that must be jettisoned
    so the aircraft can land at or below the maximum landing weight.
    """
    _validate_masses(mtow_kg, mlw_kg)
    return mtow_kg - mlw_kg


def required_jettison_rate(mtow_kg, mlw_kg, limit_s=JETTISON_LIMIT_S):
    """Return the required average jettison rate (kg/s) over the limit.

    Assumes the full excess fuel (MTOW - MLW) is dumped evenly over the
    15-minute limit.
    """
    _validate_masses(mtow_kg, mlw_kg)
    if limit_s <= 0:
        raise ValueError("limit_s must be positive")
    return (mtow_kg - mlw_kg) / limit_s


def design_jettison_rate(required_rate_kg_s, margin=DESIGN_MARGIN_DEFAULT):
    """Return the design jettison rate (kg/s) with the design margin."""
    if required_rate_kg_s <= 0:
        raise ValueError("required_rate_kg_s must be positive")
    if margin < 1:
        raise ValueError("margin must be at least 1 (no undersizing)")
    return required_rate_kg_s * margin


def per_mast_flow(design_rate_kg_s, n_masts):
    """Return the design flow (kg/s) per dump mast."""
    if design_rate_kg_s <= 0:
        raise ValueError("design_rate_kg_s must be positive")
    if n_masts < 1:
        raise ValueError("n_masts must be at least 1")
    return design_rate_kg_s / n_masts


def time_to_landing_weight(dumpable_mass_kg, design_rate_kg_s):
    """Return {time_s, verdict} for reaching MLW at the design rate.

    Verdict is PASS when the time is within the 15-minute limit
    (<= JETTISON_LIMIT_S) and FAIL otherwise.
    """
    if dumpable_mass_kg < 0:
        raise ValueError("dumpable_mass_kg cannot be negative")
    if design_rate_kg_s <= 0:
        raise ValueError("design_rate_kg_s must be positive")
    time_s = dumpable_mass_kg / design_rate_kg_s
    return {"time_s": time_s, "verdict": "PASS" if time_s <= JETTISON_LIMIT_S else "FAIL"}


def jettison_summary(mtow_kg, mlw_kg, n_masts, margin=DESIGN_MARGIN_DEFAULT):
    """Return the complete jettison sizing summary dict.

    Keys: mtow_kg, mlw_kg, dumpable_mass_kg, required_rate_kg_s,
    design_rate_kg_s, margin, n_masts, per_mast_flow_kg_s, limit_s,
    time_s, verdict. The time and verdict are the design-time re-check
    of the time to landing weight at the design rate.
    """
    dumpable = dumpable_fuel_mass(mtow_kg, mlw_kg)
    required = required_jettison_rate(mtow_kg, mlw_kg)
    design = design_jettison_rate(required, margin)
    per_mast = per_mast_flow(design, n_masts)
    check = time_to_landing_weight(dumpable, design)
    return {
        "mtow_kg": mtow_kg,
        "mlw_kg": mlw_kg,
        "dumpable_mass_kg": dumpable,
        "required_rate_kg_s": required,
        "design_rate_kg_s": design,
        "margin": margin,
        "n_masts": n_masts,
        "per_mast_flow_kg_s": per_mast,
        "limit_s": JETTISON_LIMIT_S,
        "time_s": check["time_s"],
        "verdict": check["verdict"],
    }
