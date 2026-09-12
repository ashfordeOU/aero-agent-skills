"""
Stress spectrum derivation logic for fatigue analysis at the critical location.
Reference: ECSS-E-ST-32C clauses 7.2.3-7.2.4
"""

from typing import Dict, List, Optional, Tuple


def compute_stress(
    axial_load_N: float,
    section_area_m2: float,
    stress_concentration: float = 1.0,
) -> float:
    """Compute nominal stress at a cross-section with stress concentration factor."""
    if section_area_m2 <= 0.0:
        raise ValueError(
            f"Section area must be positive, got {section_area_m2}"
        )
    if stress_concentration < 1.0:
        raise ValueError(
            f"Stress concentration factor must be >= 1.0, got {stress_concentration}"
        )
    return (axial_load_N / section_area_m2) * stress_concentration


def compute_principal_stresses(
    sigma_x: float, sigma_y: float, tau_xy: float
) -> Tuple[float, float]:
    """Compute principal stresses from a 2-D stress state."""
    avg = (sigma_x + sigma_y) / 2.0
    radius = (((sigma_x - sigma_y) / 2.0) ** 2 + tau_xy ** 2) ** 0.5
    return avg + radius, avg - radius


def compute_von_mises(sigma_1: float, sigma_2: float) -> float:
    """Compute von Mises equivalent stress from two principal stresses."""
    return (sigma_1 ** 2 - sigma_1 * sigma_2 + sigma_2 ** 2) ** 0.5


def find_critical_location(locations: List[Dict]) -> Dict:
    """
    Return the location with the highest peak stress magnitude.
    Each entry must have 'id' and 'peak_stress_Pa' keys.
    """
    if not locations:
        raise ValueError("Location list is empty")
    for loc in locations:
        if "id" not in loc:
            raise ValueError("Location entry missing required key 'id'")
        if "peak_stress_Pa" not in loc:
            raise ValueError(
                f"Location '{loc['id']}' missing required key 'peak_stress_Pa'"
            )
    return max(locations, key=lambda loc: abs(loc["peak_stress_Pa"]))


def extract_turning_points(stress_history: List[float]) -> List[float]:
    """
    Reduce a stress history to its turning points (local maxima and minima).
    The first and last values are always retained.
    """
    if len(stress_history) < 2:
        return list(stress_history)

    turning = [stress_history[0]]
    for i in range(1, len(stress_history) - 1):
        prev = stress_history[i - 1]
        curr = stress_history[i]
        nxt = stress_history[i + 1]
        if (curr >= prev and curr >= nxt) or (curr <= prev and curr <= nxt):
            if curr != turning[-1]:
                turning.append(curr)
    last = stress_history[-1]
    if last != turning[-1]:
        turning.append(last)
    return turning


def rainflow_count(
    stress_history: List[float],
) -> List[Tuple[float, float, float]]:
    """
    Rainflow cycle counting per ECSS-E-ST-32C clause 7.2.4 / ASTM E1049.

    Returns a list of (stress_amplitude_Pa, mean_stress_Pa, count) tuples.
    Full cycles carry count = 1.0; residual half-cycles carry count = 0.5.
    """
    if len(stress_history) < 2:
        return []

    pts = extract_turning_points(stress_history)
    if len(pts) < 2:
        return []

    cycles: List[Tuple[float, float, float]] = []
    stack: List[float] = []

    for point in pts:
        stack.append(point)
        # Close full cycles while the stack allows
        while len(stack) >= 3:
            x = abs(stack[-2] - stack[-1])
            y = abs(stack[-3] - stack[-2])
            if x >= y:
                s_hi = max(stack[-3], stack[-2])
                s_lo = min(stack[-3], stack[-2])
                amplitude = (s_hi - s_lo) / 2.0
                mean = (s_hi + s_lo) / 2.0
                cycles.append((amplitude, mean, 1.0))
                # Remove the two inner points
                stack.pop(-2)
                stack.pop(-2)
            else:
                break

    # Remaining stack points form half-cycles
    for i in range(len(stack) - 1):
        s_hi = max(stack[i], stack[i + 1])
        s_lo = min(stack[i], stack[i + 1])
        amplitude = (s_hi - s_lo) / 2.0
        mean = (s_hi + s_lo) / 2.0
        cycles.append((amplitude, mean, 0.5))

    return cycles


def goodman_equivalent_amplitude(
    amplitude_Pa: float,
    mean_Pa: float,
    ultimate_stress_Pa: float,
) -> float:
    """
    Apply the Goodman mean-stress correction to obtain the fully-reversed
    equivalent stress amplitude.

    Formula: S_eq = amplitude / (1 - mean / Su)

    Raises ValueError if mean stress magnitude >= ultimate stress (static failure).
    """
    if ultimate_stress_Pa <= 0.0:
        raise ValueError(
            f"Ultimate stress must be positive, got {ultimate_stress_Pa}"
        )
    if abs(mean_Pa) >= ultimate_stress_Pa:
        raise ValueError(
            f"Mean stress magnitude {abs(mean_Pa)} Pa >= ultimate stress "
            f"{ultimate_stress_Pa} Pa — this is a static failure case, not fatigue"
        )
    return amplitude_Pa / (1.0 - mean_Pa / ultimate_stress_Pa)


def aggregate_spectrum(
    cycles: List[Tuple[float, float, float]],
) -> List[Tuple[float, float, float]]:
    """
    Aggregate raw cycle list by (amplitude, mean) key and sum counts.
    Returns list sorted by descending stress amplitude.
    """
    bins: Dict[Tuple[float, float], float] = {}
    for amplitude, mean, count in cycles:
        key = (round(amplitude, 9), round(mean, 9))
        bins[key] = bins.get(key, 0.0) + count

    result = [(amp, mn, cnt) for (amp, mn), cnt in bins.items()]
    result.sort(key=lambda t: t[0], reverse=True)
    return result


def validate_spectrum(spectrum: List[Tuple[float, float, float]]) -> List[str]:
    """
    Check the stress spectrum for consistency.
    Returns a list of finding strings; an empty list means no findings.
    """
    findings: List[str] = []
    if not spectrum:
        findings.append("Stress spectrum is empty — no cycles were counted")
        return findings
    for i, (amp, mean, cnt) in enumerate(spectrum):
        if amp < 0.0:
            findings.append(f"Bin {i}: negative stress amplitude {amp} Pa")
        if cnt <= 0.0:
            findings.append(f"Bin {i}: non-positive cycle count {cnt}")
    return findings


def derive_stress_spectrum(
    load_events: List[Dict],
    section_area_m2: float,
    stress_concentration: float = 1.0,
    ultimate_stress_Pa: Optional[float] = None,
) -> Dict:
    """
    Derive the stress spectrum from a sequence of load events.

    Parameters
    ----------
    load_events : list of dicts with 'id' (str) and 'load_N' (float) keys,
                  ordered as they appear in the mission load sequence.
    section_area_m2 : net section area at the fatigue-critical location (m²).
    stress_concentration : stress concentration factor Kt >= 1.0.
    ultimate_stress_Pa : if provided, a Goodman-corrected spectrum is also returned.

    Returns
    -------
    dict with keys:
        'stress_history'  : list of (id, stress_Pa) tuples
        'cycles'          : raw rainflow output [(amplitude, mean, count), ...]
        'spectrum'        : aggregated spectrum sorted by descending amplitude
        'findings'        : validation findings (list of strings)
        'goodman_spectrum': Goodman-corrected spectrum (only if ultimate_stress_Pa given)
    """
    if section_area_m2 <= 0.0:
        raise ValueError("Section area must be positive")
    if not load_events:
        raise ValueError("Load event list is empty")

    stress_history: List[Tuple[str, float]] = []
    stress_values: List[float] = []

    for event in load_events:
        eid = event.get("id", "unknown")
        load = event.get("load_N")
        if load is None:
            raise ValueError(f"Load event '{eid}' is missing required key 'load_N'")
        s = compute_stress(load, section_area_m2, stress_concentration)
        stress_history.append((eid, s))
        stress_values.append(s)

    cycles = rainflow_count(stress_values)
    spectrum = aggregate_spectrum(cycles)
    findings = validate_spectrum(spectrum)

    result: Dict = {
        "stress_history": stress_history,
        "cycles": cycles,
        "spectrum": spectrum,
        "findings": findings,
    }

    if ultimate_stress_Pa is not None:
        goodman: List[Tuple[float, float, float]] = []
        for amp, mean, cnt in spectrum:
            try:
                eq_amp = goodman_equivalent_amplitude(amp, mean, ultimate_stress_Pa)
            except ValueError as exc:
                raise ValueError(
                    f"Goodman correction failed for amplitude={amp} mean={mean}: {exc}"
                ) from exc
            goodman.append((eq_amp, 0.0, cnt))
        goodman.sort(key=lambda t: t[0], reverse=True)
        result["goodman_spectrum"] = goodman

    return result
