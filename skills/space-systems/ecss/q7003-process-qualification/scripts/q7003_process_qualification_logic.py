#!/usr/bin/env python3
"""Qualification of an anodizing line and its process.

Anchor: ECSS-Q-ST-70-03 quality-assurance clause on anodizing. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Qualification is a statement about a line, not about a part. What is
being demonstrated is that this tank, this rectifier, this rack pattern
and this declared parameter window together produce a coating that meets
every graded characteristic, repeatably, across the positions a part can
actually occupy.

Three things have to hold at once:

repeatability   several consecutive runs, not one. A single good run
                shows the line can do it once, which is not the claim.
coverage        coupons at the extremes of the rack as well as inside
                it. Current density, agitation and temperature all vary
                with position, so the ends of the rack are where the
                process fails first and a campaign that samples only the
                comfortable middle has not looked at the risk.
control         every recorded parameter inside the window being
                qualified. A run that drifted outside the window did not
                qualify the window; it qualified something else.

Qualification also expires. A bath rebuild, a rectifier change, a change
of alloy family or simple elapsed time all put the line back in front of
the same campaign.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

MIN_QUALIFICATION_RUNS = 3
RECOMMENDED_POSITION_FRACTION = 0.5

COUPON_OUTCOMES = ("pass", "fail")

QUALIFIED = "qualified"
CONDITIONALLY_QUALIFIED = "conditionally-qualified"
NOT_QUALIFIED = "not-qualified"

REQUALIFICATION_TRIGGERS = (
    "bath-rebuild",
    "rectifier-replacement",
    "alloy-family-change",
    "rack-design-change",
    "seal-chemistry-change",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _within(value, low, high):
    """low <= value <= high, absorbing floating-point representation error.

    A parameter that was set at a window edge is recorded through a unit
    conversion and a logger, so it can evaluate a few units in the last
    place outside its own bound. The window is never widened; only the
    comparison tolerates the representation error.
    """
    if value < low and not math.isclose(
        value, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return False
    if value > high and not math.isclose(
        value, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return False
    return True


def validate_parameter_windows(windows):
    """Check every declared parameter window is a real, ordered interval."""
    if not isinstance(windows, dict) or not windows:
        raise ValueError("windows must be a non-empty mapping of parameter to bounds")
    for name, bounds in windows.items():
        if not isinstance(name, str) or not name:
            raise ValueError("parameter names must be non-empty strings")
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("window for %s must be a (low, high) pair" % name)
        low = _require_number("%s low bound" % name, bounds[0])
        high = _require_number("%s high bound" % name, bounds[1])
        if high < low:
            raise ValueError(
                "window for %s is inverted: low %g above high %g" % (name, low, high)
            )
    return windows


def coupons_required(rack_positions_sampled, runs):
    """Coupons a campaign owes: one per sampled position per run."""
    positions = _require_count("rack_positions_sampled", rack_positions_sampled, 1)
    count = _require_count("runs", runs, minimum=1)
    return positions * count


def check_run_parameters(recorded, windows):
    """Grade one run's recorded parameters against the qualified window."""
    validate_parameter_windows(windows)
    if not isinstance(recorded, dict):
        raise ValueError("recorded parameters must be a mapping, got %r" % (recorded,))
    excursions = []
    missing = []
    for name, bounds in sorted(windows.items()):
        if name not in recorded:
            missing.append(name)
            continue
        value = _require_number(name, recorded[name])
        if not _within(value, float(bounds[0]), float(bounds[1])):
            excursions.append(
                "%s recorded %.4f outside the %.4f to %.4f window"
                % (name, value, bounds[0], bounds[1])
            )
    if missing:
        excursions.append(
            "parameters not recorded at all: %s" % ", ".join(missing)
        )
    return {
        "in_control": not excursions,
        "excursions": excursions,
        "unrecorded": missing,
    }


def assess_position_coverage(positions_sampled, positions_available):
    """Grade which rack positions the coupons actually came from.

    The ends of a rack see a different current density and a different
    flow than the middle, so a campaign that never hung a coupon at an
    extreme has not sampled where the process fails first.
    """
    available = _require_count("positions_available", positions_available, 1)
    if not isinstance(positions_sampled, (list, tuple, set)) or not positions_sampled:
        raise ValueError("positions_sampled must be a non-empty sequence")
    sampled = set()
    for position in positions_sampled:
        index = _require_count("rack position", position, minimum=1)
        if index > available:
            raise ValueError(
                "rack position %d is beyond the %d positions available"
                % (index, available)
            )
        sampled.add(index)
    extremes = {1, available}
    missing_extremes = sorted(extremes - sampled)
    fraction = len(sampled) / available
    findings = []
    if missing_extremes:
        findings.append(
            "no coupon at rack position(s) %s; the ends of the rack are where "
            "current density and flow depart most from the middle"
            % ", ".join(str(index) for index in missing_extremes)
        )
    elif fraction < RECOMMENDED_POSITION_FRACTION and not math.isclose(
        fraction, RECOMMENDED_POSITION_FRACTION, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        findings.append(
            "only %d of %d rack positions sampled; the extremes are covered but "
            "the interior spread is thin" % (len(sampled), available)
        )
    return {
        "sampled_positions": sorted(sampled),
        "positions_available": available,
        "coverage_fraction": fraction,
        "extremes_covered": not missing_extremes,
        "findings": findings,
    }


def assess_coupon_results(results, required_characteristics):
    """Check every required characteristic was measured and passed."""
    if not isinstance(results, dict):
        raise ValueError("results must be a mapping of characteristic to outcome")
    required = list(required_characteristics or [])
    if not required:
        raise ValueError("required_characteristics must name at least one")
    missing = [name for name in required if name not in results]
    failed = []
    for name in required:
        if name in results:
            outcome = results[name]
            if outcome not in COUPON_OUTCOMES:
                raise ValueError(
                    "outcome for %s must be one of %s, got %r"
                    % (name, ", ".join(COUPON_OUTCOMES), outcome)
                )
            if outcome == "fail":
                failed.append(name)
    findings = []
    if missing:
        findings.append(
            "characteristic(s) never measured on a coupon: %s" % ", ".join(missing)
        )
    if failed:
        findings.append("coupon failure on: %s" % ", ".join(failed))
    return {
        "missing": missing,
        "failed": failed,
        "complete": not missing,
        "all_passed": not failed,
        "findings": findings,
    }


def requalification_required(changes, days_since_qualification, validity_days):
    """Whether the line owes a fresh campaign before it runs again."""
    if changes is None:
        changes = []
    if not isinstance(changes, (list, tuple, set)):
        raise ValueError("changes must be a sequence of trigger names")
    days = _require_count("days_since_qualification", days_since_qualification)
    validity = _require_count("validity_days", validity_days, minimum=1)
    reasons = []
    for change in sorted(set(changes)):
        if change not in REQUALIFICATION_TRIGGERS:
            raise ValueError(
                "unknown change %r; expected one of %s"
                % (change, ", ".join(REQUALIFICATION_TRIGGERS))
            )
        reasons.append("%s invalidates the standing qualification" % change)
    if days >= validity:
        reasons.append(
            "%d days since qualification reaches the %d day validity"
            % (days, validity)
        )
    return {"required": bool(reasons), "reasons": reasons}


def qualify_process(case):
    """Full qualification verdict for an anodizing line campaign."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    windows = validate_parameter_windows(case.get("parameter_windows"))
    runs = case.get("runs")
    if not isinstance(runs, (list, tuple)) or not runs:
        raise ValueError("runs must be a non-empty sequence of recorded runs")
    coverage = assess_position_coverage(
        case.get("positions_sampled"), case.get("positions_available")
    )
    coupons = assess_coupon_results(
        case.get("coupon_results"), case.get("required_characteristics")
    )
    findings = list(coverage["findings"]) + list(coupons["findings"])
    excursion_runs = []
    for index, recorded in enumerate(runs, start=1):
        control = check_run_parameters(recorded, windows)
        if not control["in_control"]:
            excursion_runs.append(index)
            findings.extend("run %d: %s" % (index, text) for text in control["excursions"])
    enough_runs = len(runs) >= MIN_QUALIFICATION_RUNS
    if not enough_runs:
        findings.append(
            "%d run(s) recorded; repeatability needs at least %d consecutive runs"
            % (len(runs), MIN_QUALIFICATION_RUNS)
        )
    fatal = (
        not enough_runs
        or excursion_runs
        or not coverage["extremes_covered"]
        or not coupons["complete"]
        or not coupons["all_passed"]
    )
    if fatal:
        verdict = NOT_QUALIFIED
    elif findings:
        verdict = CONDITIONALLY_QUALIFIED
    else:
        verdict = QUALIFIED
    return {
        "verdict": verdict,
        "runs_recorded": len(runs),
        "runs_with_excursions": excursion_runs,
        "coupons_required": coupons_required(
            len(coverage["sampled_positions"]), len(runs)
        ),
        "coverage": coverage,
        "coupon_results": coupons,
        "findings": findings,
    }
