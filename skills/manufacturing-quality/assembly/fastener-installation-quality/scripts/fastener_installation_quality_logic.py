"""Fastener installation quality logic (manufacturing-quality/assembly).

Pure stdlib, deterministic, offline. Implements the assembly-time
verification of aerospace structural fastener installations: grip
length selection for the clamped stack, thread protrusion check,
clamp load from applied torque with the torque coefficient, clamp
verdict against joint allowables, countersink flushness check for
flush head fasteners, swage collar engagement check for lock-bolts,
and the final installation verdict (pass, rework, scrap) with the
specific defect.

The protrusion band, minimum engaged threads, torque coefficient,
flushness tolerance and torque scatter band are documented typical
values, not standard reproductions; confirm each against the fastener
manufacturer data and the governing code before releasing an
installation.

Module constants carry the documented typical values.
"""

# Module constants (documented typical values).
PROTRUSION_MIN_MM = 0.5
PROTRUSION_MAX_MM = 3.0
THREADS_MIN = 2
K_TYPICAL = 0.2
SCATTER_BAND_PCT = 15.0
FLUSHNESS_TOLERANCE_DEFAULT_MM = 0.13
FASTENER_TYPES = ("bolt-nut", "lock-bolt", "rivet")
HEAD_STYLES = ("protruding", "flush")


def select_grip(stack_thicknesses_mm, available_grips_mm):
    """Select the smallest available grip at least as long as the stack.

    Returns a dict with stack_total_mm, grip_mm (None when no available
    grip reaches the total) and protrusion_mm (grip minus total when a
    grip is chosen, else None). Raises ValueError on an empty stack,
    negative thickness, an empty grip list, or grips not sorted
    ascending.
    """
    if not stack_thicknesses_mm:
        raise ValueError("stack must contain at least one thickness")
    if any(t < 0 for t in stack_thicknesses_mm):
        raise ValueError("stack thicknesses must be non-negative")
    if not available_grips_mm:
        raise ValueError("available grips must not be empty")
    if available_grips_mm != sorted(available_grips_mm):
        raise ValueError("available grips must be sorted ascending")
    total = sum(stack_thicknesses_mm)
    chosen = [g for g in available_grips_mm if g >= total]
    if not chosen:
        return {"stack_total_mm": total, "grip_mm": None,
                "protrusion_mm": None}
    grip = chosen[0]
    return {"stack_total_mm": total, "grip_mm": grip,
            "protrusion_mm": grip - total}


def protrusion_ok(protrusion_mm):
    """True when the thread protrusion sits inside the typical band.

    The documented typical band is PROTRUSION_MIN_MM to
    PROTRUSION_MAX_MM inclusive. A negative protrusion (grip shorter
    than the stack, a misfitted part) is out of band by the same check.
    """
    return PROTRUSION_MIN_MM <= protrusion_mm <= PROTRUSION_MAX_MM


def clamp_load_N(torque_Nm, k_factor, fastener_diameter_m):
    """Estimate the fastener clamp load from the applied torque.

    F = T / (k * D), with T the applied torque, k the torque
    coefficient and D the nominal fastener diameter. Raises ValueError
    on torque, k or diameter that are not positive.
    """
    if torque_Nm <= 0:
        raise ValueError("applied torque must be positive")
    if k_factor <= 0:
        raise ValueError("torque coefficient must be positive")
    if fastener_diameter_m <= 0:
        raise ValueError("fastener diameter must be positive")
    return torque_Nm / (k_factor * fastener_diameter_m)


def clamp_verdict(clamp_N, min_clamp_N, max_clamp_N):
    """Classify the clamp load against the joint allowables.

    Returns clamp-ok when min <= clamp <= max, under-clamp below the
    minimum required clamp and over-clamp above the allowable clamp.
    Raises ValueError on a non-positive minimum or a maximum below the
    minimum.
    """
    if min_clamp_N <= 0:
        raise ValueError("minimum clamp must be positive")
    if max_clamp_N < min_clamp_N:
        raise ValueError("maximum clamp must not be below minimum")
    if clamp_N < min_clamp_N:
        return "under-clamp"
    if clamp_N > max_clamp_N:
        return "over-clamp"
    return "clamp-ok"


def flushness_ok(measured_mm,
                 tolerance_mm=FLUSHNESS_TOLERANCE_DEFAULT_MM):
    """True when the measured flushness magnitude is within tolerance.

    Positive measured values are proud, negative values recessed; both
    directions are bounded by the tolerance (typical 0.13 mm default).
    """
    return abs(measured_mm) <= tolerance_mm


def collar_engagement_ok(engaged_threads, min_threads=THREADS_MIN):
    """True when the engaged collar threads reach the minimum count.

    Returns None when engaged_threads is None (no measurement taken).
    Raises ValueError on a negative thread count.
    """
    if engaged_threads is None:
        return None
    if engaged_threads < 0:
        raise ValueError("engaged threads must not be negative")
    return engaged_threads >= min_threads


def installation_verdict(stack_thicknesses_mm, available_grips_mm,
                         fastener_diameter_m, applied_torque_Nm,
                         min_clamp_N, max_clamp_N,
                         fastener_type="bolt-nut",
                         head_style="protruding",
                         k_factor=K_TYPICAL,
                         measured_flushness_mm=None,
                         flushness_tolerance_mm=
                         FLUSHNESS_TOLERANCE_DEFAULT_MM,
                         collar_engaged_threads=None,
                         installed_torque_actual_Nm=None):
    """Classify the fastener installation as pass, rework or scrap.

    Decision order: no grip fits the stack (rework, no-grip-fits),
    thread protrusion out of the typical band (rework,
    protrusion-out-of-band), clamp outside the joint allowables
    (scrap, over-clamp or rework, under-clamp), flush head outside the
    flushness tolerance (rework, flushness-out-of-tolerance), and
    lock-bolt collar engagement below the minimum threads (rework,
    collar-engagement). A lock-bolt without a collar engagement
    measurement cannot pass, so it reports collar-engagement.

    The result always carries clamp_N, the clamp verdict string and,
    when installed_torque_actual_Nm is given, scatter_pct and
    scatter_ok for the typical 15 percent torque scatter band as an
    informational note. Raises ValueError on a non-positive diameter
    or torque, an unknown fastener_type or head_style, and a flush
    head without a measured flushness.
    """
    if fastener_diameter_m <= 0:
        raise ValueError("fastener diameter must be positive")
    if applied_torque_Nm <= 0:
        raise ValueError("applied torque must be positive")
    if fastener_type not in FASTENER_TYPES:
        raise ValueError("fastener_type must be bolt-nut, lock-bolt "
                         "or rivet")
    if head_style not in HEAD_STYLES:
        raise ValueError("head_style must be protruding or flush")

    grip = select_grip(stack_thicknesses_mm, available_grips_mm)
    clamp = clamp_load_N(applied_torque_Nm, k_factor,
                         fastener_diameter_m)
    clamp_v = clamp_verdict(clamp, min_clamp_N, max_clamp_N)

    if grip["grip_mm"] is not None:
        protrusion_ok_flag = protrusion_ok(grip["protrusion_mm"])
    else:
        protrusion_ok_flag = None

    if head_style == "flush":
        if measured_flushness_mm is None:
            raise ValueError("measured flushness is required for a "
                             "flush head fastener")
        flush_ok = flushness_ok(measured_flushness_mm,
                                flushness_tolerance_mm)
    else:
        flush_ok = None

    if fastener_type == "lock-bolt":
        collar_ok = collar_engagement_ok(collar_engaged_threads)
    else:
        collar_ok = None

    verdict = "pass"
    defect = None
    if grip["grip_mm"] is None:
        verdict = "rework"
        defect = "no-grip-fits"
    elif not protrusion_ok_flag:
        verdict = "rework"
        defect = "protrusion-out-of-band"
    elif clamp_v != "clamp-ok":
        verdict = "scrap" if clamp_v == "over-clamp" else "rework"
        defect = clamp_v
    elif flush_ok is False:
        verdict = "rework"
        defect = "flushness-out-of-tolerance"
    elif fastener_type == "lock-bolt" and collar_ok is not True:
        verdict = "rework"
        defect = "collar-engagement"

    if installed_torque_actual_Nm is not None:
        scatter_pct = (abs(installed_torque_actual_Nm -
                           applied_torque_Nm) / applied_torque_Nm
                       * 100.0)
        scatter_ok = scatter_pct <= SCATTER_BAND_PCT
    else:
        scatter_pct = None
        scatter_ok = None

    return {
        "stack_total_mm": grip["stack_total_mm"],
        "grip_mm": grip["grip_mm"],
        "protrusion_mm": grip["protrusion_mm"],
        "protrusion_ok": protrusion_ok_flag,
        "clamp_N": clamp,
        "clamp_verdict": clamp_v,
        "flushness_ok": flush_ok,
        "collar_engagement_ok": collar_ok,
        "scatter_pct": scatter_pct,
        "scatter_ok": scatter_ok,
        "verdict": verdict,
        "defect": defect,
    }
