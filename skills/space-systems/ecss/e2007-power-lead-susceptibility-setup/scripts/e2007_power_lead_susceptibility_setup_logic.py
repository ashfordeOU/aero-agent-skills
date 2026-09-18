#!/usr/bin/env python3
"""Power-lead susceptibility injection arrangement (ECSS-E-ST-20-07C, 5.4.7.3).

Offline, deterministic, standard-library only. The module checks the bench
arrangement a supply-lead susceptibility injection is built on:

* every supply lead terminated in its own stabilization network,
* the exposed run between the unit and that network, and the height that
  run is held at above the ground plane,
* where the series injection element sits along the lead, and how close
  the current monitor sits to it,
* the bond of the unit to the ground plane and the separation kept
  between an injected supply lead and any signal lead beside it,
* the arrangement as a whole: one lead injected at a time, a return lead
  that is not injected, and a plane the whole run is referenced to.

No standard text is reproduced; the clause is cited as an anchor only.
"""

import math

__all__ = [
    "REL_TOL",
    "LEAD_RUN_NOMINAL_M",
    "LEAD_RUN_TOLERANCE_FRACTION",
    "LEAD_HEIGHT_NOMINAL_M",
    "LEAD_HEIGHT_TOLERANCE_M",
    "INJECTION_WINDOW_M",
    "MONITOR_OFFSET_MAX_M",
    "BOND_RESISTANCE_LIMIT_OHM",
    "SIGNAL_LEAD_SEPARATION_MIN_M",
    "LEAD_POLARITIES",
    "check_lead_run",
    "check_lead_height",
    "check_injection_position",
    "check_monitor_position",
    "check_bond_resistance",
    "check_signal_lead_separation",
    "normalize_lead",
    "assess_bench_setup",
]

# Absorbs binary-representation error when a difference lands a few units in
# the last place outside an exactly-met bound. It never widens the bound.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Exposed run of supply lead between the unit and its stabilization network.
LEAD_RUN_NOMINAL_M = 2.0
LEAD_RUN_TOLERANCE_FRACTION = 0.10

# Height that run is held at above the ground plane, and its allowance.
LEAD_HEIGHT_NOMINAL_M = 0.05
LEAD_HEIGHT_TOLERANCE_M = 0.01

# Window, measured from the unit connector, the series injection element
# has to sit inside: close enough that the injected disturbance is not lost
# along the lead, far enough that the element does not load the connector.
INJECTION_WINDOW_M = (0.05, 0.20)

# The current monitor is clamped this close to the injection element.
MONITOR_OFFSET_MAX_M = 0.05

# Bond between the unit and the ground plane.
BOND_RESISTANCE_LIMIT_OHM = 2.5e-3

# Separation kept between an injected supply lead and any signal lead.
SIGNAL_LEAD_SEPARATION_MIN_M = 0.05

LEAD_POLARITIES = ("high", "return")

_LEAD_KEYS = (
    "id",
    "polarity",
    "stabilization_network",
    "run_length_m",
    "height_m",
    "injected",
    "injection_offset_m",
    "monitor_offset_m",
    "signal_lead_separation_m",
)

_REQUIRED_LEAD_KEYS = (
    "id",
    "polarity",
    "stabilization_network",
    "run_length_m",
    "height_m",
)

_SETUP_KEYS = ("leads", "bond_resistance_ohm", "ground_plane")


def _finding(code, subject, detail):
    """Build one arrangement finding record."""
    return {"code": code, "subject": subject, "detail": detail}


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %s" % (label, type(value).__name__))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _as_positive_float(value, label):
    number = _as_float(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _as_nonnegative_float(value, label):
    number = _as_float(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def _as_flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _as_identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _within(value, allowed):
    """Bound comparison that absorbs binary-representation error."""
    return value <= allowed or math.isclose(
        value, allowed, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _at_least(value, required):
    """Lower-bound comparison that absorbs binary-representation error."""
    return value >= required or math.isclose(
        value, required, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def check_lead_run(
    run_length_m,
    nominal_m=LEAD_RUN_NOMINAL_M,
    tolerance_fraction=LEAD_RUN_TOLERANCE_FRACTION,
):
    """Check the exposed run between the unit and its stabilization network."""
    run = _as_positive_float(run_length_m, "run_length_m")
    nominal = _as_positive_float(nominal_m, "nominal_m")
    fraction = _as_nonnegative_float(tolerance_fraction, "tolerance_fraction")
    if fraction >= 1.0:
        raise ValueError(
            "tolerance_fraction must stay below one, got %r" % (tolerance_fraction,)
        )
    allowed = nominal * fraction
    deviation = abs(run - nominal)
    return {
        "quantity": "lead-run",
        "nominal_m": nominal,
        "actual_m": run,
        "deviation_m": deviation,
        "allowed_m": allowed,
        "within": _within(deviation, allowed),
    }


def check_lead_height(
    height_m,
    nominal_m=LEAD_HEIGHT_NOMINAL_M,
    tolerance_m=LEAD_HEIGHT_TOLERANCE_M,
):
    """Check the height the lead run is held at above the ground plane."""
    height = _as_positive_float(height_m, "height_m")
    nominal = _as_positive_float(nominal_m, "nominal_m")
    allowed = _as_nonnegative_float(tolerance_m, "tolerance_m")
    deviation = abs(height - nominal)
    return {
        "quantity": "lead-height",
        "nominal_m": nominal,
        "actual_m": height,
        "deviation_m": deviation,
        "allowed_m": allowed,
        "within": _within(deviation, allowed),
    }


def check_injection_position(offset_m, window_m=INJECTION_WINDOW_M):
    """Check where the series injection element sits along the lead."""
    offset = _as_positive_float(offset_m, "offset_m")
    if not isinstance(window_m, (tuple, list)) or len(window_m) != 2:
        raise ValueError("window_m must be a pair of distances, got %r" % (window_m,))
    near = _as_positive_float(window_m[0], "window lower bound")
    far = _as_positive_float(window_m[1], "window upper bound")
    if far <= near:
        raise ValueError("the injection window does not widen: %r" % (window_m,))
    return {
        "quantity": "injection-position",
        "offset_m": offset,
        "window_m": (near, far),
        "too_near": not _at_least(offset, near),
        "too_far": not _within(offset, far),
        "within": _at_least(offset, near) and _within(offset, far),
    }


def check_monitor_position(
    injection_offset_m, monitor_offset_m, allowed_m=MONITOR_OFFSET_MAX_M
):
    """Check how close the current monitor is clamped to the injection."""
    injection = _as_positive_float(injection_offset_m, "injection_offset_m")
    monitor = _as_positive_float(monitor_offset_m, "monitor_offset_m")
    allowed = _as_nonnegative_float(allowed_m, "allowed_m")
    separation = abs(monitor - injection)
    return {
        "quantity": "monitor-position",
        "injection_offset_m": injection,
        "monitor_offset_m": monitor,
        "separation_m": separation,
        "allowed_m": allowed,
        "within": _within(separation, allowed),
    }


def check_bond_resistance(resistance_ohm, limit_ohm=BOND_RESISTANCE_LIMIT_OHM):
    """Check the bond between the unit and the ground plane."""
    resistance = _as_nonnegative_float(resistance_ohm, "resistance_ohm")
    limit = _as_positive_float(limit_ohm, "limit_ohm")
    return {
        "quantity": "bond-resistance",
        "actual_ohm": resistance,
        "limit_ohm": limit,
        "milliohm": resistance * 1.0e3,
        "within": _within(resistance, limit),
    }


def check_signal_lead_separation(
    separation_m, minimum_m=SIGNAL_LEAD_SEPARATION_MIN_M
):
    """Check the separation kept from an injected lead to a signal lead."""
    separation = _as_nonnegative_float(separation_m, "separation_m")
    minimum = _as_positive_float(minimum_m, "minimum_m")
    return {
        "quantity": "signal-lead-separation",
        "actual_m": separation,
        "minimum_m": minimum,
        "within": _at_least(separation, minimum),
    }


def normalize_lead(lead):
    """Validate one supply lead record and return it with numbers coerced."""
    if not isinstance(lead, dict):
        raise ValueError("a lead must be a mapping, got %r" % (lead,))
    unknown = sorted(set(lead) - set(_LEAD_KEYS))
    if unknown:
        raise ValueError("unknown key(s) %s on a lead" % (unknown,))
    missing = sorted(set(_REQUIRED_LEAD_KEYS) - set(lead))
    if missing:
        raise ValueError("missing key(s) %s on a lead" % (missing,))
    identifier = _as_identifier(lead["id"], "id")
    polarity = lead["polarity"]
    if polarity not in LEAD_POLARITIES:
        raise ValueError(
            "unknown lead polarity %r, expected one of %s"
            % (polarity, list(LEAD_POLARITIES))
        )
    injected = _as_flag(lead.get("injected", False), "injected")
    normalized = {
        "id": identifier,
        "polarity": polarity,
        "stabilization_network": _as_flag(
            lead["stabilization_network"], "stabilization_network"
        ),
        "run_length_m": _as_positive_float(lead["run_length_m"], "run_length_m"),
        "height_m": _as_positive_float(lead["height_m"], "height_m"),
        "injected": injected,
        "injection_offset_m": None,
        "monitor_offset_m": None,
        "signal_lead_separation_m": None,
    }
    if injected:
        if "injection_offset_m" not in lead:
            raise ValueError(
                "lead %s is injected but carries no injection offset" % identifier
            )
        normalized["injection_offset_m"] = _as_positive_float(
            lead["injection_offset_m"], "injection_offset_m"
        )
        if "monitor_offset_m" in lead:
            normalized["monitor_offset_m"] = _as_positive_float(
                lead["monitor_offset_m"], "monitor_offset_m"
            )
    else:
        for key in ("injection_offset_m", "monitor_offset_m"):
            if key in lead:
                raise ValueError(
                    "lead %s declares %s but is not injected" % (identifier, key)
                )
    if "signal_lead_separation_m" in lead:
        normalized["signal_lead_separation_m"] = _as_nonnegative_float(
            lead["signal_lead_separation_m"], "signal_lead_separation_m"
        )
    return normalized


def assess_bench_setup(setup):
    """Assess the whole injection arrangement lead by lead.

    Returns the per-lead checks, every finding raised against the
    arrangement and whether the bench is fit for the run.
    """
    if not isinstance(setup, dict):
        raise ValueError("the setup must be a mapping, got %r" % (setup,))
    unknown = sorted(set(setup) - set(_SETUP_KEYS))
    if unknown:
        raise ValueError("unknown setup key(s) %s" % (unknown,))
    leads = setup.get("leads")
    if isinstance(leads, (str, bytes)) or not hasattr(leads, "__iter__"):
        raise ValueError("leads must be an iterable of lead records")
    normalized = [normalize_lead(lead) for lead in leads]
    if len(normalized) < 2:
        raise ValueError(
            "a supply pair needs at least two leads, got %d" % len(normalized)
        )
    seen = set()
    for lead in normalized:
        if lead["id"] in seen:
            raise ValueError("lead %r appears twice" % lead["id"])
        seen.add(lead["id"])
    polarities = set(lead["polarity"] for lead in normalized)
    if polarities != set(LEAD_POLARITIES):
        raise ValueError(
            "the arrangement needs a high lead and a return lead, got %s"
            % sorted(polarities)
        )
    ground_plane = _as_flag(setup.get("ground_plane", True), "ground_plane")
    findings = []
    records = []
    for lead in normalized:
        checks = {
            "run": check_lead_run(lead["run_length_m"]),
            "height": check_lead_height(lead["height_m"]),
        }
        if not checks["run"]["within"]:
            findings.append(
                _finding(
                    "lead-run-out-of-tolerance",
                    lead["id"],
                    "runs %.4f m against a nominal %.4f m (allowed %.4f m)"
                    % (
                        checks["run"]["actual_m"],
                        checks["run"]["nominal_m"],
                        checks["run"]["allowed_m"],
                    ),
                )
            )
        if not checks["height"]["within"]:
            findings.append(
                _finding(
                    "lead-height-out-of-tolerance",
                    lead["id"],
                    "sits %.4f m above the plane against a nominal %.4f m "
                    "(allowed %.4f m)"
                    % (
                        checks["height"]["actual_m"],
                        checks["height"]["nominal_m"],
                        checks["height"]["allowed_m"],
                    ),
                )
            )
        if not lead["stabilization_network"]:
            findings.append(
                _finding(
                    "stabilization-network-missing",
                    lead["id"],
                    "the lead is not terminated in its own stabilization network",
                )
            )
        if lead["injected"]:
            checks["injection"] = check_injection_position(lead["injection_offset_m"])
            if not checks["injection"]["within"]:
                where = "nearer than" if checks["injection"]["too_near"] else "beyond"
                findings.append(
                    _finding(
                        "injection-position-outside-window",
                        lead["id"],
                        "the element sits %.4f m from the connector, %s the "
                        "%.4f to %.4f m window"
                        % (
                            checks["injection"]["offset_m"],
                            where,
                            checks["injection"]["window_m"][0],
                            checks["injection"]["window_m"][1],
                        ),
                    )
                )
            if lead["monitor_offset_m"] is not None:
                checks["monitor"] = check_monitor_position(
                    lead["injection_offset_m"], lead["monitor_offset_m"]
                )
                if not checks["monitor"]["within"]:
                    findings.append(
                        _finding(
                            "monitor-too-far-from-injection",
                            lead["id"],
                            "clamped %.4f m from the element against a %.4f m "
                            "allowance"
                            % (
                                checks["monitor"]["separation_m"],
                                checks["monitor"]["allowed_m"],
                            ),
                        )
                    )
            if lead["signal_lead_separation_m"] is not None:
                checks["separation"] = check_signal_lead_separation(
                    lead["signal_lead_separation_m"]
                )
                if not checks["separation"]["within"]:
                    findings.append(
                        _finding(
                            "signal-lead-too-close",
                            lead["id"],
                            "runs %.4f m from a signal lead against a %.4f m "
                            "minimum"
                            % (
                                checks["separation"]["actual_m"],
                                checks["separation"]["minimum_m"],
                            ),
                        )
                    )
        records.append({"lead": lead, "checks": checks})
    injected = [lead for lead in normalized if lead["injected"]]
    if not injected:
        findings.append(
            _finding(
                "no-lead-injected",
                "arrangement",
                "no supply lead carries the series injection element",
            )
        )
    elif len(injected) > 1:
        findings.append(
            _finding(
                "several-leads-injected",
                "arrangement",
                "%d leads carry an injection element at once" % len(injected),
            )
        )
    for lead in injected:
        if lead["polarity"] == "return":
            findings.append(
                _finding(
                    "return-lead-injected",
                    lead["id"],
                    "the return lead carries the injection element",
                )
            )
    if not ground_plane:
        findings.append(
            _finding(
                "ground-plane-missing",
                "arrangement",
                "the arrangement declares no ground plane to reference the run to",
            )
        )
    bond = None
    if "bond_resistance_ohm" in setup:
        bond = check_bond_resistance(setup["bond_resistance_ohm"])
        if not bond["within"]:
            findings.append(
                _finding(
                    "bond-resistance-high",
                    "arrangement",
                    "bonded at %.4f milliohm against a %.4f milliohm limit"
                    % (bond["milliohm"], bond["limit_ohm"] * 1.0e3),
                )
            )
    else:
        findings.append(
            _finding(
                "bond-resistance-undeclared",
                "arrangement",
                "the bond of the unit to the plane was not measured",
            )
        )
    fit = not findings
    return {
        "verdict": "setup-fit" if fit else "setup-not-fit",
        "fit": fit,
        "lead_count": len(normalized),
        "injected_lead_count": len(injected),
        "ground_plane": ground_plane,
        "bond": bond,
        "leads": records,
        "findings": findings,
        "conforming_fraction": sum(
            1
            for record in records
            if not any(
                finding["subject"] == record["lead"]["id"] for finding in findings
            )
        )
        / float(len(records)),
    }
