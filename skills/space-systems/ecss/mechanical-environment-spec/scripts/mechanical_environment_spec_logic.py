"""
Mechanical environment specification logic — ECSS-E-ST-32C clauses 4.2.3-4.2.4.

Covers: microgravity, audible noise, human-induced vibration, random vibration
(PSD / Grms), and shock response spectrum (SRS).  All computations are
deterministic and offline; stdlib only.
"""

import math
from typing import Dict, List, Optional, Tuple

# ──────────────────────────── constants ────────────────────────────

RANDOM_VIB_FREQ_MIN_HZ: float = 20.0
RANDOM_VIB_FREQ_MAX_HZ: float = 2000.0

SRS_FREQ_MIN_HZ: float = 10.0
SRS_FREQ_MAX_HZ: float = 10000.0
SRS_DEFAULT_Q: int = 10

HUMAN_VIB_FREQ_MIN_HZ: float = 1.0
HUMAN_VIB_FREQ_MAX_HZ: float = 100.0

# All five environment types required by ECSS-E-ST-32C 4.2.3-4.2.4.
ENV_TYPES: frozenset = frozenset({
    "microgravity",
    "audible-noise",
    "human-vibration",
    "random-vibration",
    "shock-response",
})


class SpecificationError(ValueError):
    """Raised when a mechanical environment specification is invalid or incomplete."""


# ──────────────────────────── validation helpers ────────────────────────────

def _validate_psd_breakpoints(breakpoints: List[Tuple[float, float]]) -> None:
    """Raise SpecificationError if PSD breakpoint list is malformed."""
    if len(breakpoints) < 2:
        raise SpecificationError(
            "PSD definition requires at least 2 frequency-level breakpoints; "
            f"got {len(breakpoints)}"
        )
    prev_f = None
    for f, w in breakpoints:
        if f <= 0:
            raise SpecificationError(
                f"PSD breakpoint frequency must be positive; got {f} Hz"
            )
        if w <= 0:
            raise SpecificationError(
                f"PSD level must be positive g²/Hz; got {w}"
            )
        if prev_f is not None and f <= prev_f:
            raise SpecificationError(
                f"PSD frequencies must be strictly ascending; got {prev_f} Hz "
                f"followed by {f} Hz"
            )
        prev_f = f


def _validate_srs_breakpoints(breakpoints: List[Tuple[float, float]]) -> None:
    """Raise SpecificationError if SRS breakpoint list is malformed."""
    if len(breakpoints) < 2:
        raise SpecificationError(
            "SRS definition requires at least 2 frequency-acceleration breakpoints; "
            f"got {len(breakpoints)}"
        )
    prev_f = None
    for f, a in breakpoints:
        if f <= 0:
            raise SpecificationError(
                f"SRS breakpoint frequency must be positive; got {f} Hz"
            )
        if a <= 0:
            raise SpecificationError(
                f"SRS acceleration must be positive g; got {a}"
            )
        if prev_f is not None and f <= prev_f:
            raise SpecificationError(
                f"SRS frequencies must be strictly ascending; got {prev_f} Hz "
                f"followed by {f} Hz"
            )
        prev_f = f


# ──────────────────────────── random vibration (PSD / Grms) ────────────────────────────

def compute_grms_from_psd(breakpoints: List[Tuple[float, float]]) -> float:
    """
    Compute overall Grms from a piecewise log-log PSD definition.

    breakpoints: list of (frequency_Hz, psd_g2_per_Hz) in strictly ascending
                 frequency order.  At least two breakpoints required.

    Integration uses the exact log-log formula for each segment:
        area = (W2*f2 - W1*f1) / (m + 1)   when m != -1
        area = W1*f1 * ln(f2/f1)             when m == -1
    where m = log(W2/W1) / log(f2/f1) is the log-log slope.

    Returns overall Grms = sqrt(total area).
    """
    _validate_psd_breakpoints(breakpoints)
    total_mean_square = 0.0
    for i in range(len(breakpoints) - 1):
        f1, w1 = breakpoints[i]
        f2, w2 = breakpoints[i + 1]
        if w1 == w2:
            area = w1 * (f2 - f1)
        else:
            m = math.log(w2 / w1) / math.log(f2 / f1)
            if abs(m + 1.0) < 1e-9:
                area = w1 * f1 * math.log(f2 / f1)
            else:
                area = (w2 * f2 - w1 * f1) / (m + 1.0)
        if area < 0:
            raise SpecificationError(
                f"Negative PSD area in segment [{f1}, {f2}] Hz — verify breakpoint values"
            )
        total_mean_square += area
    return math.sqrt(total_mean_square)


def check_random_vibration_coverage(breakpoints: List[Tuple[float, float]]) -> Dict:
    """
    Check that the PSD breakpoints span the minimum required frequency range
    (RANDOM_VIB_FREQ_MIN_HZ to RANDOM_VIB_FREQ_MAX_HZ).

    Returns:
        {"compliant": bool, "findings": [str, ...]}
    """
    _validate_psd_breakpoints(breakpoints)
    findings: List[str] = []
    f_low = breakpoints[0][0]
    f_high = breakpoints[-1][0]
    if f_low > RANDOM_VIB_FREQ_MIN_HZ:
        findings.append(
            f"PSD lower bound {f_low} Hz exceeds minimum required "
            f"{RANDOM_VIB_FREQ_MIN_HZ} Hz — extend the spectrum downward"
        )
    if f_high < RANDOM_VIB_FREQ_MAX_HZ:
        findings.append(
            f"PSD upper bound {f_high} Hz is below required "
            f"{RANDOM_VIB_FREQ_MAX_HZ} Hz — extend the spectrum upward"
        )
    return {"compliant": len(findings) == 0, "findings": findings}


# ──────────────────────────── shock response spectrum ────────────────────────────

def check_srs_coverage(
    breakpoints: List[Tuple[float, float]],
    q: int = SRS_DEFAULT_Q,
) -> Dict:
    """
    Check that the SRS breakpoints span the minimum required frequency range
    (SRS_FREQ_MIN_HZ to SRS_FREQ_MAX_HZ) and that Q is positive.

    Returns:
        {"compliant": bool, "findings": [str, ...], "q_factor": int}
    """
    _validate_srs_breakpoints(breakpoints)
    if q <= 0:
        raise SpecificationError(f"Q factor must be a positive integer; got {q}")
    findings: List[str] = []
    f_low = breakpoints[0][0]
    f_high = breakpoints[-1][0]
    if f_low > SRS_FREQ_MIN_HZ:
        findings.append(
            f"SRS lower bound {f_low} Hz exceeds minimum required "
            f"{SRS_FREQ_MIN_HZ} Hz — extend the spectrum downward"
        )
    if f_high < SRS_FREQ_MAX_HZ:
        findings.append(
            f"SRS upper bound {f_high} Hz is below required "
            f"{SRS_FREQ_MAX_HZ} Hz — extend the spectrum upward"
        )
    return {"compliant": len(findings) == 0, "findings": findings, "q_factor": q}


def interpolate_srs_acceleration(
    breakpoints: List[Tuple[float, float]],
    query_hz: float,
) -> float:
    """
    Interpolate SRS acceleration at query_hz using log-log interpolation.

    query_hz must lie within the breakpoint range (inclusive).
    Uses the formula: a = a1 * (a2/a1)^[log(f/f1)/log(f2/f1)]

    Returns interpolated acceleration in g.
    """
    _validate_srs_breakpoints(breakpoints)
    freqs = [bp[0] for bp in breakpoints]
    accs = [bp[1] for bp in breakpoints]
    if query_hz < freqs[0] or query_hz > freqs[-1]:
        raise SpecificationError(
            f"Query frequency {query_hz} Hz is outside the SRS range "
            f"[{freqs[0]}, {freqs[-1]}] Hz — extrapolation is not permitted"
        )
    if query_hz == freqs[0]:
        return accs[0]
    if query_hz == freqs[-1]:
        return accs[-1]
    for i in range(len(freqs) - 1):
        if freqs[i] <= query_hz <= freqs[i + 1]:
            f1, a1 = freqs[i], accs[i]
            f2, a2 = freqs[i + 1], accs[i + 1]
            if a1 == a2:
                return a1
            t = math.log(query_hz / f1) / math.log(f2 / f1)
            return a1 * (a2 / a1) ** t
    raise SpecificationError(
        f"Could not locate segment containing {query_hz} Hz"
    )


# ──────────────────────────── audible noise ────────────────────────────

def check_audible_noise_spec(
    band_levels_db: Dict[float, float],
    limit_db: float,
) -> Dict:
    """
    Check octave-band SPL values against a flat dB limit.

    band_levels_db: mapping of {center_frequency_Hz: spl_dB}
    limit_db: maximum allowable SPL per octave band (must be positive).

    Returns:
        {"compliant": bool, "exceedances": [{"freq_hz": f, "level_db": l, "excess_db": e}, ...]}
    """
    if limit_db <= 0:
        raise SpecificationError(
            f"Noise limit must be a positive dB value; got {limit_db}"
        )
    exceedances = []
    for freq, spl in sorted(band_levels_db.items()):
        if spl > limit_db:
            exceedances.append({
                "freq_hz": freq,
                "level_db": spl,
                "excess_db": round(spl - limit_db, 4),
            })
    return {"compliant": len(exceedances) == 0, "exceedances": exceedances}


def compute_overall_spl(band_levels_db: List[float]) -> float:
    """
    Compute the overall sound pressure level from a list of octave-band SPL values
    using energy summation: L_total = 10 * log10(sum(10^(Li/10))).

    Returns overall SPL in dB.
    """
    if not band_levels_db:
        raise SpecificationError(
            "band_levels_db must contain at least one SPL value"
        )
    total_power = sum(10.0 ** (spl / 10.0) for spl in band_levels_db)
    return 10.0 * math.log10(total_power)


# ──────────────────────────── human-induced vibration ────────────────────────────

def check_human_vibration_spec(freq_hz: float, amplitude_g: float) -> Dict:
    """
    Check a human-induced vibration event against the applicable frequency range
    (ECSS-E-ST-32C 4.2.4: 1-100 Hz) and confirm amplitude is positive.

    Returns:
        {"compliant": bool, "findings": [str, ...], "freq_hz": float, "amplitude_g": float}
    """
    if amplitude_g <= 0:
        raise SpecificationError(
            f"Vibration amplitude must be positive g; got {amplitude_g}"
        )
    findings: List[str] = []
    if freq_hz < HUMAN_VIB_FREQ_MIN_HZ or freq_hz > HUMAN_VIB_FREQ_MAX_HZ:
        findings.append(
            f"Human-induced vibration frequency {freq_hz} Hz is outside the "
            f"applicable range [{HUMAN_VIB_FREQ_MIN_HZ}, {HUMAN_VIB_FREQ_MAX_HZ}] Hz"
        )
    return {
        "compliant": len(findings) == 0,
        "findings": findings,
        "freq_hz": freq_hz,
        "amplitude_g": amplitude_g,
    }


# ──────────────────────────── microgravity ────────────────────────────

def check_microgravity_spec(
    steady_state_micro_g: float,
    transient_micro_g: Optional[float] = None,
) -> Dict:
    """
    Validate a microgravity environment specification.

    steady_state_micro_g: quasi-static acceleration level in micro-g (>= 0).
    transient_micro_g: peak transient acceleration in micro-g (optional).

    A zero steady-state value triggers a warning (the zero-g assumption should
    be explicit).  A transient value lower than the steady-state value is
    flagged as a likely transposition error.

    Returns:
        {"compliant": bool, "findings": [str, ...],
         "steady_state_micro_g": float, "transient_micro_g": float | None}
    """
    if steady_state_micro_g < 0:
        raise SpecificationError(
            f"Steady-state micro-g must be non-negative; got {steady_state_micro_g}"
        )
    findings: List[str] = []
    if steady_state_micro_g == 0.0:
        findings.append(
            "Steady-state micro-g level is zero — confirm the zero-g assumption "
            "is intentional and documented"
        )
    if transient_micro_g is not None:
        if transient_micro_g < steady_state_micro_g:
            findings.append(
                f"Transient micro-g ({transient_micro_g}) is less than steady-state "
                f"({steady_state_micro_g}) — verify the values are not transposed"
            )
    return {
        "compliant": len(findings) == 0,
        "findings": findings,
        "steady_state_micro_g": steady_state_micro_g,
        "transient_micro_g": transient_micro_g,
    }


# ──────────────────────────── environment completeness ────────────────────────────

def check_environment_completeness(env_types_provided: List[str]) -> Dict:
    """
    Verify that all five required environment types are included in the
    mechanical environment specification.

    env_types_provided: list of type strings; each must be a member of ENV_TYPES.
    Unrecognized entries raise SpecificationError.

    Returns:
        {"compliant": bool, "missing": [str, ...], "provided": [str, ...]}
    """
    unknown = [e for e in env_types_provided if e not in ENV_TYPES]
    if unknown:
        raise SpecificationError(
            f"Unrecognized environment type(s): {sorted(unknown)}. "
            f"Accepted values: {sorted(ENV_TYPES)}"
        )
    provided_set = set(env_types_provided)
    missing = sorted(ENV_TYPES - provided_set)
    return {
        "compliant": len(missing) == 0,
        "missing": missing,
        "provided": sorted(provided_set),
    }
