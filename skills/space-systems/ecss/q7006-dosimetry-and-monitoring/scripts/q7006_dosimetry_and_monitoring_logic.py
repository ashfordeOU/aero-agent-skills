"""Dosimetry and exposure monitoring for a radiation degradation test.

Anchor: ECSS-Q-ST-70-06C, facility clause -- measuring what the coupons
actually received while they were in the beam, with monitors whose
calibration is in date and traceable, and reconciling the delivered exposure
with the target. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate each monitor: which agent it reads, when it was last calibrated,
   how long that calibration is valid, whether the calibration is traceable,
   and the uncertainty it contributes.
2. Check the calibration is still in date on the run date, and that each
   measured agent is read by at least two independent monitors so that a
   drifting one can be detected at all.
3. Integrate the sampled flux over the run by the trapezoidal rule to get the
   delivered fluence or ultraviolet dose, refusing an unordered or
   single-point sample record.
4. Compare the redundant monitors against each other and raise a finding when
   they disagree by more than the agreement limit.
5. Combine the uncertainty contributions in quadrature and compare the
   delivered exposure with the target inside the acceptance tolerance,
   reporting short delivery and overshoot separately.
"""

import datetime
import math

__all__ = [
    "AGENTS",
    "MONITOR_AGREEMENT_LIMIT_PCT",
    "MINIMUM_MONITORS_PER_AGENT",
    "DEFAULT_DELIVERY_TOLERANCE_PCT",
    "validate_monitor",
    "calibration_expiry",
    "calibration_in_date",
    "accumulate_exposure",
    "combined_uncertainty_pct",
    "monitor_deviation_pct",
    "delivery_verdict",
    "assess_dosimetry",
]

AGENTS = ("particles", "ultraviolet")

# Two monitors reading the same agent must agree to this relative percentage;
# beyond it one of them has drifted and the delivered figure is unsupported.
MONITOR_AGREEMENT_LIMIT_PCT = 5.0

# A single monitor cannot be checked against anything, so a drift during the
# run would be invisible.
MINIMUM_MONITORS_PER_AGENT = 2

# Acceptance band on the delivered exposure against its target.
DEFAULT_DELIVERY_TOLERANCE_PCT = 10.0

_TOLERANCE = 1e-9


def _real(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or (number == 0.0 and not allow_zero):
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _date(value, label):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))


def validate_monitor(monitor):
    """Return a normalised record for one exposure monitor."""
    if not isinstance(monitor, dict):
        raise ValueError("monitor must be a mapping")
    for key in ("name", "agent", "calibration_date", "calibration_interval_days",
                "traceable", "uncertainty_pct"):
        if key not in monitor:
            raise ValueError("monitor missing required key '%s'" % key)
    name = monitor["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("monitor name must be a non-empty string")
    if monitor["agent"] not in AGENTS:
        raise ValueError("monitor '%s': agent must be one of %r" % (name, AGENTS))
    if not isinstance(monitor["traceable"], bool):
        raise ValueError("monitor '%s': traceable must be a boolean" % name)
    interval = monitor["calibration_interval_days"]
    if isinstance(interval, bool) or not isinstance(interval, int) or interval < 1:
        raise ValueError("monitor '%s': calibration_interval_days must be a positive integer" % name)
    return {
        "name": name.strip(),
        "agent": monitor["agent"],
        "calibration_date": _date(monitor["calibration_date"], "calibration_date"),
        "calibration_interval_days": interval,
        "traceable": monitor["traceable"],
        "uncertainty_pct": _real(monitor["uncertainty_pct"], "uncertainty_pct", True),
    }


def calibration_expiry(monitor):
    """Return the date the monitor's calibration stops being valid."""
    record = validate_monitor(monitor)
    return record["calibration_date"] + datetime.timedelta(
        days=record["calibration_interval_days"]
    )


def calibration_in_date(monitor, run_date):
    """Return True when the calibration still covers the run date."""
    when = _date(run_date, "run_date")
    record = validate_monitor(monitor)
    if when < record["calibration_date"]:
        raise ValueError(
            "run date %s precedes the calibration date %s"
            % (when.isoformat(), record["calibration_date"].isoformat())
        )
    return when <= calibration_expiry(monitor)


def accumulate_exposure(samples):
    """Integrate sampled flux over time and return the delivered exposure."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("samples needs at least two (time_s, flux) points")
    cleaned = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, (list, tuple)) or len(sample) != 2:
            raise ValueError("sample %d must be a (time_s, flux) pair" % index)
        time_s = _real(sample[0], "sample time at index %d" % index, allow_zero=True)
        flux = _real(sample[1], "sample flux at index %d" % index, allow_zero=True)
        if cleaned and time_s <= cleaned[-1][0]:
            raise ValueError(
                "sample times must strictly increase; %g follows %g" % (time_s, cleaned[-1][0])
            )
        cleaned.append((time_s, flux))
    total = 0.0
    for (t0, f0), (t1, f1) in zip(cleaned, cleaned[1:]):
        total += 0.5 * (f0 + f1) * (t1 - t0)
    return total


def combined_uncertainty_pct(components):
    """Combine independent percentage uncertainty contributions in quadrature."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError("components must be a non-empty sequence")
    total = 0.0
    for index, value in enumerate(components):
        contribution = _real(value, "uncertainty component %d" % index, allow_zero=True)
        total += contribution * contribution
    return math.sqrt(total)


def monitor_deviation_pct(reading_a, reading_b):
    """Return the relative deviation between two readings of the same agent."""
    first = _real(reading_a, "reading_a")
    second = _real(reading_b, "reading_b")
    mean = 0.5 * (first + second)
    return 100.0 * abs(first - second) / mean


def delivery_verdict(delivered, target, tolerance_pct=DEFAULT_DELIVERY_TOLERANCE_PCT):
    """Return 'within-tolerance', 'short-delivery' or 'overshoot'."""
    got = _real(delivered, "delivered", allow_zero=True)
    want = _real(target, "target")
    band = _real(tolerance_pct, "tolerance_pct", allow_zero=True)
    error_pct = 100.0 * (got - want) / want
    if abs(error_pct) <= band or math.isclose(
        abs(error_pct), band, rel_tol=_TOLERANCE, abs_tol=_TOLERANCE
    ):
        return "within-tolerance"
    return "short-delivery" if error_pct < 0.0 else "overshoot"


def assess_dosimetry(spec):
    """Reconcile a monitored exposure run against its target.

    spec keys: run_date, monitors, readings (monitor name -> sample list),
    targets (agent -> target exposure), optional tolerance_pct.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("run_date", "monitors", "readings", "targets"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    monitors = spec["monitors"]
    if not isinstance(monitors, (list, tuple)) or not monitors:
        raise ValueError("spec['monitors'] must be a non-empty sequence")
    readings = spec["readings"]
    targets = spec["targets"]
    if not isinstance(readings, dict) or not isinstance(targets, dict):
        raise ValueError("readings and targets must be mappings")
    tolerance = _real(
        spec.get("tolerance_pct", DEFAULT_DELIVERY_TOLERANCE_PCT), "tolerance_pct", True
    )
    run_date = _date(spec["run_date"], "run_date")
    records = [validate_monitor(monitor) for monitor in monitors]
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("monitor names must be unique within one run")
    findings = []
    per_monitor = []
    by_agent = {}
    for record in records:
        name = record["name"]
        if name not in readings:
            raise ValueError("no sample record for monitor '%s'" % name)
        in_date = calibration_in_date(record, run_date)
        delivered = accumulate_exposure(readings[name])
        if not in_date:
            findings.append(
                "monitor '%s' calibration expired on %s, before the run on %s"
                % (name, calibration_expiry(record).isoformat(), run_date.isoformat())
            )
        if not record["traceable"]:
            findings.append("monitor '%s' calibration is not traceable to a standard" % name)
        per_monitor.append(
            {
                "name": name,
                "agent": record["agent"],
                "delivered": delivered,
                "in_date": in_date,
                "uncertainty_pct": record["uncertainty_pct"],
            }
        )
        by_agent.setdefault(record["agent"], []).append(per_monitor[-1])
    per_agent = {}
    for agent, entries in sorted(by_agent.items()):
        if len(entries) < MINIMUM_MONITORS_PER_AGENT:
            findings.append(
                "%s is read by %d monitor(s); at least %d are needed to detect a drift"
                % (agent, len(entries), MINIMUM_MONITORS_PER_AGENT)
            )
        values = [entry["delivered"] for entry in entries]
        worst_deviation = 0.0
        for index, first in enumerate(values):
            for second in values[index + 1:]:
                worst_deviation = max(worst_deviation, monitor_deviation_pct(first, second))
        if worst_deviation > MONITOR_AGREEMENT_LIMIT_PCT and not math.isclose(
            worst_deviation, MONITOR_AGREEMENT_LIMIT_PCT, rel_tol=_TOLERANCE, abs_tol=0.0
        ):
            findings.append(
                "%s monitors disagree by %.2f%%, above the %.2f%% agreement limit"
                % (agent, worst_deviation, MONITOR_AGREEMENT_LIMIT_PCT)
            )
        delivered = sum(values) / len(values)
        uncertainty = combined_uncertainty_pct(
            [entry["uncertainty_pct"] for entry in entries]
        )
        if agent not in targets:
            raise ValueError("no target exposure declared for agent '%s'" % agent)
        verdict = delivery_verdict(delivered, targets[agent], tolerance)
        if verdict != "within-tolerance":
            findings.append(
                "%s delivered %.4g against a target of %.4g (%s)"
                % (agent, delivered, float(targets[agent]), verdict)
            )
        per_agent[agent] = {
            "delivered": delivered,
            "target": float(targets[agent]),
            "worst_deviation_pct": worst_deviation,
            "combined_uncertainty_pct": uncertainty,
            "verdict": verdict,
            "monitor_count": len(entries),
        }
    return {
        "run_date": run_date.isoformat(),
        "monitors": per_monitor,
        "agents": per_agent,
        "findings": findings,
        "dosimetry_accepted": not findings,
    }
