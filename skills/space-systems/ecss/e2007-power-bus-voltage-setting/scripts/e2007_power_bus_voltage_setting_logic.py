"""Governing supply-voltage setting for a conducted emission measurement.

Anchor: ECSS-E-ST-20-07C clause 5.2.12 (conducted emission runs are performed
at the supply-voltage extreme that produces the worst result). Paraphrased into
an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalize the runs recorded at each supply setting: the setting label, the
   bus voltage it was held at, and the emission sweep obtained.
2. Align the sweeps on one frequency grid; two runs recorded on different
   grids cannot be compared point by point and the difference is an input
   error, not something to interpolate away.
3. Build the envelope: at every frequency the worst level obtained and the
   setting that produced it, ties going to the lower voltage so the answer is
   reproducible.
4. Rank the settings by the largest exceedance each one reaches above the
   declared limit line, falling back to the largest absolute level when no
   limit line was declared, and break ties on the count of frequencies where
   the setting holds the envelope, then on the lower voltage.
5. Report findings: an extreme that was never exercised, a run held at neither
   declared extreme, a reported setting other than the governing one, a
   governing run that is nevertheless not worst everywhere, and any envelope
   point above the limit.
"""

import math

__all__ = [
    "LEVEL_TOLERANCE_DB",
    "VOLTAGE_TOLERANCE_V",
    "GRID_RELATIVE_TOLERANCE",
    "validate_voltage",
    "validate_extremes",
    "validate_sweep",
    "validate_run",
    "common_grid",
    "interpolate_limit",
    "emission_envelope",
    "run_statistics",
    "select_governing_setting",
    "assess_bus_voltage_setting",
]

# Levels are compared as differences of decibel quantities; an exact equality
# can land a few units in the last place either way. Absorb the representation
# error here rather than by nudging a level or a limit.
LEVEL_TOLERANCE_DB = 1e-9
VOLTAGE_TOLERANCE_V = 1e-9
GRID_RELATIVE_TOLERANCE = 1e-9

_RUN_KEYS = ("setting", "voltage_v", "sweep")


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_voltage(value, label="voltage_v"):
    """Return a validated, strictly positive bus voltage."""
    voltage = _real(value, label)
    if voltage <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, voltage))
    return voltage


def validate_extremes(lower_v, upper_v):
    """Return the declared (lower, upper) supply extremes."""
    low = validate_voltage(lower_v, "lower extreme")
    high = validate_voltage(upper_v, "upper extreme")
    if high - low <= VOLTAGE_TOLERANCE_V:
        raise ValueError(
            "the upper extreme %g V must exceed the lower extreme %g V" % (high, low)
        )
    return (low, high)


def validate_sweep(points, name="sweep"):
    """Return a validated emission sweep as a list of (frequency, level) pairs."""
    if isinstance(points, dict) or not isinstance(points, (list, tuple)):
        raise ValueError("%s must be a sequence of (frequency_hz, level_dbuv) pairs" % name)
    if len(points) < 2:
        raise ValueError("%s needs at least two points to be a sweep" % name)
    validated = []
    for index, item in enumerate(points):
        if isinstance(item, (str, bytes)) or not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be a (frequency_hz, level_dbuv) pair" % (name, index))
        frequency = _real(item[0], "%s[%d] frequency_hz" % (name, index))
        level = _real(item[1], "%s[%d] level_dbuv" % (name, index))
        if frequency <= 0.0:
            raise ValueError("%s[%d] frequency_hz must be positive" % (name, index))
        if validated and frequency <= validated[-1][0]:
            raise ValueError(
                "%s must advance in frequency; point %d does not" % (name, index)
            )
        validated.append((frequency, level))
    return validated


def validate_run(run):
    """Return a validated emission run record."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    unknown = sorted(set(run) - set(_RUN_KEYS))
    if unknown:
        raise ValueError("run has unknown key(s): %s" % ", ".join(unknown))
    for key in _RUN_KEYS:
        if key not in run:
            raise ValueError("run missing required key '%s'" % key)
    setting = run["setting"]
    if not isinstance(setting, str) or not setting.strip():
        raise ValueError("run setting must be a non-blank label")
    return {
        "setting": setting.strip(),
        "voltage_v": validate_voltage(run["voltage_v"]),
        "sweep": validate_sweep(run["sweep"], "sweep of %s" % setting.strip()),
    }


def _validated_runs(runs):
    if isinstance(runs, dict) or not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("runs must be a non-empty sequence of run records")
    validated = [validate_run(run) for run in runs]
    labels = [run["setting"] for run in validated]
    if len(set(labels)) != len(labels):
        raise ValueError("duplicate setting label among the runs")
    return validated


def common_grid(runs):
    """Return the frequency grid shared by every run, refusing a mismatch."""
    validated = _validated_runs(runs)
    reference = [point[0] for point in validated[0]["sweep"]]
    for run in validated[1:]:
        grid = [point[0] for point in run["sweep"]]
        if len(grid) != len(reference):
            raise ValueError(
                "run %s has %d sweep points against %d in run %s; the grids differ"
                % (run["setting"], len(grid), len(reference), validated[0]["setting"])
            )
        for index, (a, b) in enumerate(zip(grid, reference)):
            if not math.isclose(a, b, rel_tol=GRID_RELATIVE_TOLERANCE, abs_tol=0.0):
                raise ValueError(
                    "run %s departs from the common grid at point %d (%g Hz against %g Hz)"
                    % (run["setting"], index, a, b)
                )
    return tuple(reference)


def interpolate_limit(limit_line, frequency_hz):
    """Return the limit at a frequency, interpolated across the tabulated line."""
    if isinstance(limit_line, dict) or not isinstance(limit_line, (list, tuple)):
        raise ValueError("limit_line must be a sequence of (frequency_hz, limit_dbuv) pairs")
    table = validate_sweep(limit_line, "limit_line")
    frequency = _real(frequency_hz, "frequency_hz")
    if frequency <= 0.0:
        raise ValueError("frequency_hz must be positive")
    if frequency < table[0][0] or frequency > table[-1][0]:
        raise ValueError(
            "limit_line is tabulated over [%g, %g] Hz; %g Hz is outside it, "
            "extrapolation refused" % (table[0][0], table[-1][0], frequency)
        )
    for index in range(1, len(table)):
        f0, l0 = table[index - 1]
        f1, l1 = table[index]
        if frequency <= f1:
            if frequency == f0:
                return l0
            if frequency == f1:
                return l1
            span = math.log(f1) - math.log(f0)
            fraction = (math.log(frequency) - math.log(f0)) / span
            return l0 + fraction * (l1 - l0)
    return table[-1][1]


def emission_envelope(runs):
    """Return the worst level at every frequency and the setting that gave it."""
    validated = _validated_runs(runs)
    grid = common_grid(validated)
    envelope = []
    for index, frequency in enumerate(grid):
        worst = None
        for run in validated:
            level = run["sweep"][index][1]
            if worst is None:
                worst = (level, run)
                continue
            best_level, best_run = worst
            if level > best_level + LEVEL_TOLERANCE_DB:
                worst = (level, run)
            elif abs(level - best_level) <= LEVEL_TOLERANCE_DB:
                if run["voltage_v"] < best_run["voltage_v"]:
                    worst = (level, run)
        envelope.append({
            "frequency_hz": frequency,
            "level_dbuv": worst[0],
            "setting": worst[1]["setting"],
            "voltage_v": worst[1]["voltage_v"],
        })
    return envelope


def run_statistics(runs, limit_line=None):
    """Return the ranking statistics of every run."""
    validated = _validated_runs(runs)
    envelope = emission_envelope(validated)
    statistics = []
    for run in validated:
        levels = [point[1] for point in run["sweep"]]
        max_level = max(levels)
        exceedance = None
        worst_frequency = run["sweep"][levels.index(max_level)][0]
        if limit_line is not None:
            margins = []
            for frequency, level in run["sweep"]:
                margins.append(level - interpolate_limit(limit_line, frequency))
            exceedance = max(margins)
            worst_frequency = run["sweep"][margins.index(exceedance)][0]
        holds = 0
        for index, point in enumerate(envelope):
            if abs(run["sweep"][index][1] - point["level_dbuv"]) <= LEVEL_TOLERANCE_DB:
                holds += 1
        statistics.append({
            "setting": run["setting"],
            "voltage_v": run["voltage_v"],
            "max_level_dbuv": max_level,
            "max_exceedance_db": exceedance,
            "worst_frequency_hz": worst_frequency,
            "envelope_points": holds,
            "grid_points": len(envelope),
        })
    return statistics


def select_governing_setting(runs, limit_line=None):
    """Return the statistics of the setting the emission run is governed by."""
    statistics = run_statistics(runs, limit_line)
    governing = None
    for candidate in statistics:
        if governing is None:
            governing = candidate
            continue
        key = "max_exceedance_db" if limit_line is not None else "max_level_dbuv"
        if candidate[key] > governing[key] + LEVEL_TOLERANCE_DB:
            governing = candidate
        elif abs(candidate[key] - governing[key]) <= LEVEL_TOLERANCE_DB:
            if candidate["envelope_points"] > governing["envelope_points"]:
                governing = candidate
            elif candidate["envelope_points"] == governing["envelope_points"]:
                if candidate["voltage_v"] < governing["voltage_v"]:
                    governing = candidate
    return governing


def assess_bus_voltage_setting(spec):
    """Run the full clause 5.2.12 supply-extreme assessment.

    spec keys: runs, declared_extremes (lower, upper), optional limit_line,
    optional reported_setting.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("runs", "declared_extremes"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    extremes = spec["declared_extremes"]
    if isinstance(extremes, dict) or not isinstance(extremes, (list, tuple)) or len(extremes) != 2:
        raise ValueError("declared_extremes must be a (lower_v, upper_v) pair")
    lower, upper = validate_extremes(extremes[0], extremes[1])
    validated = _validated_runs(spec["runs"])
    limit_line = spec.get("limit_line")
    envelope = emission_envelope(validated)
    statistics = run_statistics(validated, limit_line)
    governing = select_governing_setting(validated, limit_line)
    findings = []
    for bound, label in ((lower, "lower"), (upper, "upper")):
        if not any(
            math.isclose(run["voltage_v"], bound, rel_tol=0.0, abs_tol=VOLTAGE_TOLERANCE_V)
            for run in validated
        ):
            findings.append(
                "the %s supply extreme %g V was never exercised, so the worst "
                "setting cannot be decided" % (label, bound)
            )
    for run in validated:
        at_extreme = any(
            math.isclose(run["voltage_v"], bound, rel_tol=0.0, abs_tol=VOLTAGE_TOLERANCE_V)
            for bound in (lower, upper)
        )
        if not at_extreme:
            findings.append(
                "run %s was held at %g V, which is neither declared extreme"
                % (run["setting"], run["voltage_v"])
            )
    off_envelope = [
        point for point in envelope if point["setting"] != governing["setting"]
    ]
    if off_envelope:
        findings.append(
            "the governing setting %s is not worst at %d of %d frequencies; the "
            "reported spectrum has to be the envelope of the settings"
            % (governing["setting"], len(off_envelope), len(envelope))
        )
    reported = spec.get("reported_setting")
    if reported is not None:
        if not isinstance(reported, str) or not reported.strip():
            raise ValueError("reported_setting must be a non-blank label")
        if reported.strip() != governing["setting"]:
            findings.append(
                "the campaign reported %s but %s is the governing setting"
                % (reported.strip(), governing["setting"])
            )
    over_limit = []
    if limit_line is not None:
        for point in envelope:
            margin = point["level_dbuv"] - interpolate_limit(limit_line, point["frequency_hz"])
            if margin > LEVEL_TOLERANCE_DB:
                over_limit.append((point["frequency_hz"], margin))
        if over_limit:
            worst = max(over_limit, key=lambda item: item[1])
            findings.append(
                "the envelope is above the limit at %d frequencies, worst %.3f dB "
                "at %g Hz" % (len(over_limit), worst[1], worst[0])
            )
    return {
        "envelope": envelope,
        "statistics": statistics,
        "governing": governing,
        "over_limit_count": len(over_limit),
        "findings": findings,
        "compliant": not findings,
    }
