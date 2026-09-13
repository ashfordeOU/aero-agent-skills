#!/usr/bin/env python3
"""Phase-nulling detection sensitivity tuning (ECSS-E-ST-20-01C clause 7.3.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A global multipactor detection method built on phase nulling cancels the
forward carrier against a reference arm and observes what survives. The
surviving residual carrier sets the detection floor: the deeper the null,
the smaller the perturbation a discharge has to produce to be seen. Null
depth is therefore the working expression of detection sensitivity.

For a two-arm cancellation with linear amplitude ratio ``a`` and residual
phase error ``phi`` the residual power fraction is

    r = 1 + a^2 - 2 a cos(phi)

and the null depth is ``-10 log10(r)``. Both the phase error and the
amplitude imbalance drift while the item is powered (cable electrical
length with chamber temperature, arm heating with applied power,
connector settling), so the null shallows monotonically after every
tuning. The elapsed time at which it reaches the floor committed in the
verification plan is the longest admissible re-tuning interval, and a
recorded tuning schedule is graded against that interval.
"""

import math

# Comparisons against a dB floor absorb representation error only; the
# engineering limit itself is never widened.
DB_ABS_TOL = 1e-9
TIME_ABS_TOL = 1e-9
# A residual fraction below this is numerically a perfect null.
PERFECT_NULL_FRACTION = 1e-300
# Default search horizon for the re-tuning interval solver (24 h).
DEFAULT_HORIZON_S = 86400.0
# Drift contributions within this many dB of each other read as balanced.
BALANCED_DRIVER_TOL_DB = 1.0

_REQUIRED_KEYS = (
    "required_null_depth_db",
    "phase_drift_rad_per_s",
    "amplitude_drift_db_per_s",
    "tuning_times_s",
    "run_duration_s",
)
_OPTIONAL_KEYS = (
    "initial_phase_error_rad",
    "initial_amplitude_imbalance_db",
    "horizon_s",
)


def _as_float(name, value):
    """Coerce to a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, out))
    return out


def _non_negative(name, value):
    out = _as_float(name, value)
    if out < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, out))
    return out


def meets_floor(value_db, floor_db):
    """True when ``value_db`` sits at or above ``floor_db``.

    The tolerance absorbs floating-point representation error in a value
    that arrived through logarithms and sums; it never relaxes the floor.
    """
    floor = _as_float("floor_db", floor_db)
    if isinstance(value_db, float) and math.isinf(value_db) and value_db > 0.0:
        return True  # a numerically perfect null clears every floor
    value = _as_float("value_db", value_db)
    return value > floor or math.isclose(
        value, floor, rel_tol=1e-12, abs_tol=DB_ABS_TOL
    )


def null_depth_db(incident_power_w, residual_power_w):
    """Null depth from measured incident and residual carrier power."""
    incident = _positive("incident_power_w", incident_power_w)
    residual = _positive("residual_power_w", residual_power_w)
    if residual > incident and not math.isclose(
        residual, incident, rel_tol=1e-12, abs_tol=0.0
    ):
        raise ValueError(
            "residual_power_w (%g W) exceeds incident_power_w (%g W): the "
            "nulling bridge cannot emit more than it receives" % (residual, incident)
        )
    return 10.0 * math.log10(incident / residual)


def residual_fraction(phase_error_rad, amplitude_imbalance_db):
    """Residual power fraction of a two-arm cancellation, 0 at a perfect null."""
    phi = _as_float("phase_error_rad", phase_error_rad)
    if abs(phi) > math.pi:
        raise ValueError(
            "phase_error_rad must lie within +/- pi (a larger residual phase "
            "error is the same null wrapped round), got %g" % phi
        )
    imbalance = _as_float("amplitude_imbalance_db", amplitude_imbalance_db)
    ratio = 10.0 ** (-imbalance / 20.0)
    fraction = 1.0 + ratio * ratio - 2.0 * ratio * math.cos(phi)
    return fraction if fraction > 0.0 else 0.0


def null_depth_from_imbalance(phase_error_rad, amplitude_imbalance_db):
    """Null depth implied by the residual phase error and amplitude imbalance."""
    fraction = residual_fraction(phase_error_rad, amplitude_imbalance_db)
    if fraction <= PERFECT_NULL_FRACTION:
        return float("inf")
    return -10.0 * math.log10(fraction)


def imbalance_at_elapsed(
    elapsed_s,
    phase_drift_rad_per_s,
    amplitude_drift_db_per_s,
    initial_phase_error_rad=0.0,
    initial_amplitude_imbalance_db=0.0,
):
    """Phase error and amplitude imbalance a given time after a tuning.

    Drift rates are magnitudes: both mismatches grow away from zero. The
    phase error is clamped at pi, beyond which the null is fully lost and
    further wrap adds nothing.
    """
    elapsed = _non_negative("elapsed_s", elapsed_s)
    phase_rate = _non_negative("phase_drift_rad_per_s", phase_drift_rad_per_s)
    amplitude_rate = _non_negative(
        "amplitude_drift_db_per_s", amplitude_drift_db_per_s
    )
    phi0 = _non_negative("initial_phase_error_rad", initial_phase_error_rad)
    imbalance0 = _non_negative(
        "initial_amplitude_imbalance_db", initial_amplitude_imbalance_db
    )
    if phi0 > math.pi:
        raise ValueError(
            "initial_phase_error_rad must lie within +/- pi, got %g" % phi0
        )
    phi = phi0 + phase_rate * elapsed
    if phi > math.pi:
        phi = math.pi
    return phi, imbalance0 + amplitude_rate * elapsed


def null_depth_at_elapsed(
    elapsed_s,
    phase_drift_rad_per_s,
    amplitude_drift_db_per_s,
    initial_phase_error_rad=0.0,
    initial_amplitude_imbalance_db=0.0,
):
    """Null depth a given elapsed time after the last tuning."""
    phi, imbalance = imbalance_at_elapsed(
        elapsed_s,
        phase_drift_rad_per_s,
        amplitude_drift_db_per_s,
        initial_phase_error_rad,
        initial_amplitude_imbalance_db,
    )
    return null_depth_from_imbalance(phi, imbalance)


def sensitivity_margin_db(achieved_null_depth_db, required_null_depth_db):
    """Signed margin of an achieved null depth over the required floor."""
    required = _positive("required_null_depth_db", required_null_depth_db)
    if isinstance(achieved_null_depth_db, float) and math.isinf(achieved_null_depth_db) and achieved_null_depth_db > 0.0:
        return float("inf")
    achieved = _as_float("achieved_null_depth_db", achieved_null_depth_db)
    return achieved - required


def max_tuning_interval_s(
    required_null_depth_db,
    phase_drift_rad_per_s,
    amplitude_drift_db_per_s,
    initial_phase_error_rad=0.0,
    initial_amplitude_imbalance_db=0.0,
    horizon_s=DEFAULT_HORIZON_S,
):
    """Longest elapsed time after a tuning for which the floor still holds.

    Null depth decays monotonically with elapsed time, so the crossing is
    unique and is found by bisection. Returns ``horizon_s`` when the floor
    still holds at the horizon, and infinity when neither mismatch drifts.
    """
    required = _positive("required_null_depth_db", required_null_depth_db)
    horizon = _positive("horizon_s", horizon_s)
    phase_rate = _non_negative("phase_drift_rad_per_s", phase_drift_rad_per_s)
    amplitude_rate = _non_negative(
        "amplitude_drift_db_per_s", amplitude_drift_db_per_s
    )

    def depth(elapsed):
        return null_depth_at_elapsed(
            elapsed,
            phase_rate,
            amplitude_rate,
            initial_phase_error_rad,
            initial_amplitude_imbalance_db,
        )

    fresh = depth(0.0)
    if not meets_floor(fresh, required):
        raise ValueError(
            "null depth immediately after tuning is %.3f dB, already below the "
            "required floor of %.3f dB: re-tuning cadence cannot repair the "
            "cancellation arm" % (fresh, required)
        )
    if phase_rate == 0.0 and amplitude_rate == 0.0:
        return float("inf")
    if meets_floor(depth(horizon), required):
        return horizon
    low, high = 0.0, horizon
    for _ in range(200):
        mid = 0.5 * (low + high)
        if meets_floor(depth(mid), required):
            low = mid
        else:
            high = mid
        if high - low <= TIME_ABS_TOL:
            break
    return low


def categorize_drift_driver(
    phase_drift_rad_per_s, amplitude_drift_db_per_s, interval_s
):
    """Name the mismatch that costs the most null depth over an interval."""
    interval = _positive("interval_s", interval_s)
    phase_rate = _non_negative("phase_drift_rad_per_s", phase_drift_rad_per_s)
    amplitude_rate = _non_negative(
        "amplitude_drift_db_per_s", amplitude_drift_db_per_s
    )
    if phase_rate == 0.0 and amplitude_rate == 0.0:
        return "no-drift"
    phase_only = null_depth_at_elapsed(interval, phase_rate, 0.0)
    amplitude_only = null_depth_at_elapsed(interval, 0.0, amplitude_rate)
    if math.isinf(phase_only) and math.isinf(amplitude_only):
        return "no-drift"
    if math.isinf(phase_only):
        return "amplitude-dominated"
    if math.isinf(amplitude_only):
        return "phase-dominated"
    if abs(phase_only - amplitude_only) <= BALANCED_DRIVER_TOL_DB:
        return "balanced"
    return "phase-dominated" if phase_only < amplitude_only else "amplitude-dominated"


def evaluate_tuning_schedule(tuning_times_s, run_duration_s, max_interval_s):
    """Grade recorded tuning epochs against the admissible interval."""
    if not isinstance(tuning_times_s, (list, tuple)):
        raise ValueError("tuning_times_s must be a list or tuple of epochs")
    if len(tuning_times_s) == 0:
        raise ValueError("tuning_times_s must hold at least one tuning epoch")
    duration = _positive("run_duration_s", run_duration_s)
    epochs = [_non_negative("tuning epoch", t) for t in tuning_times_s]
    for earlier, later in zip(epochs, epochs[1:]):
        if later <= earlier:
            raise ValueError(
                "tuning_times_s must increase strictly, got %g after %g"
                % (later, earlier)
            )
    if epochs[-1] > duration:
        raise ValueError(
            "tuning epoch %g s falls after the end of the %g s powered run"
            % (epochs[-1], duration)
        )
    if isinstance(max_interval_s, float) and math.isinf(max_interval_s):
        interval = float("inf")
    else:
        interval = _positive("max_interval_s", max_interval_s)

    def covered(gap):
        return gap < interval or math.isclose(
            gap, interval, rel_tol=1e-12, abs_tol=TIME_ABS_TOL
        )

    findings = []
    if epochs[0] > 0.0 and not covered(epochs[0]):
        findings.append(
            {
                "code": "no-tuning-at-run-start",
                "gap_s": epochs[0],
                "detail": "powered run began %g s before the first tuning" % epochs[0],
            }
        )
    for earlier, later in zip(epochs, epochs[1:]):
        gap = later - earlier
        if not covered(gap):
            findings.append(
                {
                    "code": "tuning-gap-exceeded",
                    "from_s": earlier,
                    "to_s": later,
                    "gap_s": gap,
                    "detail": "gap of %g s exceeds the %g s admissible interval"
                    % (gap, interval),
                }
            )
    tail = duration - epochs[-1]
    if not covered(tail):
        findings.append(
            {
                "code": "run-end-uncovered",
                "from_s": epochs[-1],
                "to_s": duration,
                "gap_s": tail,
                "detail": "last %g s of the powered run followed no tuning" % tail,
            }
        )
    return findings


def assess_detection_sensitivity_tuning(config):
    """Full clause 7.3.2 assessment of one powered run.

    Returns the fresh null depth, its margin, the admissible re-tuning
    interval, the dominant drift driver, the schedule findings and the
    overall verdict.
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping of assessment inputs")
    unknown = set(config) - set(_REQUIRED_KEYS) - set(_OPTIONAL_KEYS)
    if unknown:
        raise ValueError("unknown config keys: %s" % ", ".join(sorted(unknown)))
    missing = [key for key in _REQUIRED_KEYS if key not in config]
    if missing:
        raise ValueError("config missing required keys: %s" % ", ".join(missing))

    required = _positive("required_null_depth_db", config["required_null_depth_db"])
    phi0 = _non_negative(
        "initial_phase_error_rad", config.get("initial_phase_error_rad", 0.0)
    )
    imbalance0 = _non_negative(
        "initial_amplitude_imbalance_db",
        config.get("initial_amplitude_imbalance_db", 0.0),
    )
    horizon = _positive("horizon_s", config.get("horizon_s", DEFAULT_HORIZON_S))
    phase_rate = _non_negative(
        "phase_drift_rad_per_s", config["phase_drift_rad_per_s"]
    )
    amplitude_rate = _non_negative(
        "amplitude_drift_db_per_s", config["amplitude_drift_db_per_s"]
    )
    fresh = null_depth_from_imbalance(phi0, imbalance0)
    findings = []
    if not meets_floor(fresh, required):
        findings.append(
            {
                "code": "floor-unreachable-after-tuning",
                "null_depth_db": fresh,
                "required_null_depth_db": required,
                "detail": "cancellation arm cannot reach the committed floor even "
                "immediately after tuning",
            }
        )
        interval = None
        driver = "not-evaluated"
    else:
        interval = max_tuning_interval_s(
            required,
            phase_rate,
            amplitude_rate,
            phi0,
            imbalance0,
            horizon,
        )
        driver = categorize_drift_driver(
            phase_rate,
            amplitude_rate,
            interval if not math.isinf(interval) else horizon,
        )
        findings.extend(
            evaluate_tuning_schedule(
                config["tuning_times_s"], config["run_duration_s"], interval
            )
        )
    return {
        "null_depth_after_tuning_db": fresh,
        "sensitivity_margin_db": sensitivity_margin_db(fresh, required),
        "max_tuning_interval_s": interval,
        "drift_driver": driver,
        "findings": findings,
        "compliant": not findings,
    }
