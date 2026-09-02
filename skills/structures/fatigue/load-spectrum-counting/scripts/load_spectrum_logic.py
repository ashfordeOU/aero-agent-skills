#!/usr/bin/env python3
"""Fatigue load spectrum logic (paraphrase, common methodology).

Common-knowledge summary: a fatigue load spectrum reduces a mission
load history to cycles and aggregates them by level. Rainflow cycle
counting (ASTM E1049-85 section 5.4.4 practice) extracts cycles from
the turning points of a history: an excursion becomes a full cycle
when the following excursion in the opposite direction is at least as
large, and the residual stream forms half cycles. Level-crossing and
exceedance spectra count how often a load level is crossed or
exceeded. A mission spectrum aggregates per-phase (level, cycles)
blocks; spectrum truncation removes cycles below a cutoff level that
contribute little damage. Cumulative damage uses Miner's rule (sum of
n/N) with cycles to failure N from a Basquin S-N curve. Standards
context: FAR-25.571 damage tolerance practice for transport aeroplanes
(public domain regulation); the counting rules are common fatigue
methodology.
"""

from collections import deque


def turning_points(values):
    """Reduce a load history to its turning points (local extrema).

    Consecutive equal samples collapse; monotonic runs collapse to
    their endpoints. The first and last samples are kept.
    """
    pts = []
    for v in values:
        if not pts or v != pts[-1]:
            pts.append(v)
    if len(pts) < 3:
        return pts
    out = [pts[0], pts[1]]
    for v in pts[2:]:
        if (out[-1] - out[-2]) * (v - out[-1]) < 0:
            out.append(v)
        else:
            out[-1] = v
    return out


def rainflow_cycles(values):
    """Count cycles in a load history by the ASTM E1049 rainflow method.

    Returns a list of (range, mean, count) tuples. count is 1.0 for a
    full cycle and 0.5 for a half cycle; two half cycles at the same
    range and mean merge into one full cycle when summed.
    """
    pts = turning_points(values)
    points = deque()
    cycles = []
    for v in pts:
        points.append(v)
        while len(points) >= 3:
            x1, x2, x3 = points[-3], points[-2], points[-1]
            x_rng = abs(x3 - x2)
            y_rng = abs(x2 - x1)
            if x_rng < y_rng:
                break
            elif len(points) == 3:
                cycles.append((y_rng, (points[0] + points[1]) / 2.0, 0.5))
                points.popleft()
            else:
                cycles.append((y_rng, (points[-3] + points[-2]) / 2.0, 1.0))
                last = points.pop()
                points.pop()
                points.pop()
                points.append(last)
    while len(points) > 1:
        cycles.append(
            (abs(points[1] - points[0]), (points[0] + points[1]) / 2.0, 0.5)
        )
        points.popleft()
    return cycles


def rainflow_spectrum(values):
    """Rainflow cycle counts merged by range: {range: total count}."""
    merged = {}
    for rng, mean, count in rainflow_cycles(values):
        merged[rng] = merged.get(rng, 0.0) + count
    return merged


def exceedance_counts(peaks, levels):
    """Exceedance count per level: number of peaks with value >= level.

    A peak equal to the level counts as exceeded (closed interval), the
    common convention for spectrum building.
    """
    return [sum(1 for p in peaks if p >= level) for level in levels]


def upcrossing_count(history, level):
    """Number of upward crossings of a level in the load history.

    An upcrossing is a segment whose start is below the level and whose
    end is at or above it.
    """
    count = 0
    if not history:
        return 0
    prev = history[0]
    for v in history[1:]:
        if prev < level <= v:
            count += 1
        prev = v
    return count


def mission_spectrum(phases):
    """Aggregate per-phase (level, cycles) blocks into a level spectrum.

    Returns {level: total_cycles}; repeated levels across phases sum.
    """
    spec = {}
    for level, cycles in phases:
        spec[level] = spec.get(level, 0) + cycles
    return spec


def truncate_spectrum(spectrum, cutoff):
    """Drop spectrum levels strictly below the cutoff (truncation level).

    Small cycles below the truncation level contribute little damage
    and are removed; the spectrum is re-reported at the remaining
    levels.
    """
    return {level: count for level, count in spectrum.items() if level >= cutoff}


def basquin_life(alt_stress, c=2.0e10, b=3.0):
    """Cycles to failure N = C * S_a**(-b) (Basquin S-N relation).

    S_a is the alternating stress (half the load range). Raises
    ValueError on a non-positive stress or coefficient.
    """
    if alt_stress <= 0:
        raise ValueError("alternating stress must be > 0, got %r" % (alt_stress,))
    if c <= 0:
        raise ValueError("S-N coefficient must be > 0, got %r" % (c,))
    return c * alt_stress ** (-b)


def spectrum_damage(blocks, c=2.0e10, b=3.0):
    """Miner cumulative damage over (alt_stress, cycles) spectrum blocks.

    Sums n/N over the blocks with N from the Basquin curve. Raises
    ValueError on a negative cycle count or a non-positive stress.
    """
    total = 0.0
    for alt_stress, cycles in blocks:
        if cycles < 0:
            raise ValueError("cycles must be >= 0, got %r" % (cycles,))
        total += cycles / basquin_life(alt_stress, c, b)
    return total
