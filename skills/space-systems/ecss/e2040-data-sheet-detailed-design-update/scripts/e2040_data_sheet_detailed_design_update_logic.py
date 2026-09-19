#!/usr/bin/env python3
"""Data sheet refresh at the end of detailed design (ECSS-E-ST-20-40C 5.5.4).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A preliminary data sheet is written when the device is still an intent: the
figures in it are estimates carried from the architecture. Detailed design
replaces those estimates with figures the implementation actually produces --
timing extracted from the synthesised paths, power from the switching
estimate, area from the placed cells. The refresh is the activity that folds
the new figures back into the sheet, and three things go wrong in it:

* a parameter is simply never refreshed. The sheet then ships a mixture of
  measured and guessed figures with nothing marking which is which, and the
  next phase budgets against the guess;
* a refreshed figure quietly breaks a budget the requirement set fixed. The
  parameter is newer and therefore looks better, so the budget comparison has
  to be redone against the refreshed value rather than assumed;
* the figures arrive in whatever unit the tool that produced them printed.
  Nanoseconds against seconds and milliwatts against watts compare fine
  numerically and wrongly physically, so every figure is folded onto the
  canonical unit of its kind before anything is compared.

A figure landing exactly on its budget meets it. The comparison therefore
absorbs representation error instead of failing a device that is exactly on
target, which is what a strict comparison against a converted figure does.
"""

import math

# Parameter kinds a device data sheet carries, and the canonical unit each
# one is folded onto before comparison.
CANONICAL_UNITS = {
    "timing": "s",
    "power": "W",
    "area": "mm2",
    "mass": "g",
    "voltage": "V",
    "frequency": "Hz",
}
PARAMETER_KINDS = tuple(sorted(CANONICAL_UNITS))

# Unit spellings folded onto a canonical unit and its scale factor. The
# factors are decimal literals, not computed powers, so they are identical
# on every platform.
_UNIT_SCALES = {
    "timing": {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12},
    "power": {"w": 1.0, "mw": 1e-3, "uw": 1e-6, "kw": 1e3},
    "area": {"mm2": 1.0, "um2": 1e-6, "cm2": 100.0},
    "mass": {"g": 1.0, "mg": 1e-3, "kg": 1e3},
    "voltage": {"v": 1.0, "mv": 1e-3, "kv": 1e3},
    "frequency": {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9},
}

# Which way a budget is written.
DIRECTIONS = ("not-to-exceed", "at-least")

# How a refreshed figure compares with the estimate it replaces.
MOVEMENTS = ("confirmed", "increased", "decreased")

REL_TOL = 1e-12
ABS_TOL = 1e-18

_SHEET_KEYS = ("id", "kind", "preliminary", "unit", "budget", "direction")
_FIGURE_KEYS = ("id", "value", "unit", "source", "provisional")
_SOURCES = ("synthesis", "extraction", "simulation", "measurement", "estimate")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _number(name, value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if positive and out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (name, out))
    return out


def _fraction(name, value):
    out = _number(name, value)
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_kind(value):
    """Fold a parameter kind onto one of the kinds the data sheet carries."""
    key = " ".join(_text("kind", value).lower().split())
    aliases = {
        "timing": "timing",
        "delay": "timing",
        "power": "power",
        "dissipation": "power",
        "area": "area",
        "mass": "mass",
        "weight": "mass",
        "voltage": "voltage",
        "frequency": "frequency",
        "clock": "frequency",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown parameter kind %r; use one of %s"
        % (value, ", ".join(PARAMETER_KINDS))
    )


def canonical_unit(kind):
    """The unit every figure of this kind is folded onto."""
    return CANONICAL_UNITS[normalize_kind(kind)]


def to_canonical(kind, value, unit):
    """Fold one figure onto the canonical unit of its kind."""
    resolved = normalize_kind(kind)
    key = _text("unit", unit).lower().replace("^", "")
    key = key.replace("µ", "u").replace("μ", "u")
    scales = _UNIT_SCALES[resolved]
    if key not in scales:
        raise ValueError(
            "unit %r is not a %s unit; use one of %s"
            % (unit, resolved, ", ".join(sorted(scales)))
        )
    return _number("value", value) * scales[key]


def relative_change(preliminary, refreshed):
    """Signed change of a refreshed figure against the estimate it replaces."""
    base = _number("preliminary", preliminary)
    new = _number("refreshed", refreshed)
    if base == 0.0:
        raise ValueError("relative change is undefined against a zero estimate")
    return (new - base) / abs(base)


def categorize_movement(preliminary, refreshed, tolerance=0.05):
    """Group a refreshed figure as confirmed, increased or decreased.

    A movement landing exactly on the tolerance counts as confirmed, so the
    comparison absorbs representation error rather than reporting a figure
    that is exactly on tolerance as a change.
    """
    tolerance = _number("tolerance", tolerance)
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative, got %g" % tolerance)
    change = relative_change(preliminary, refreshed)
    magnitude = abs(change)
    if magnitude < tolerance or math.isclose(
        magnitude, tolerance, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        return "confirmed"
    return "increased" if change > 0.0 else "decreased"


def normalize_direction(value):
    """Fold the way a budget is written onto a recognised direction."""
    key = " ".join(_text("direction", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "not-to-exceed": "not-to-exceed",
        "max": "not-to-exceed",
        "maximum": "not-to-exceed",
        "upper": "not-to-exceed",
        "at-least": "at-least",
        "min": "at-least",
        "minimum": "at-least",
        "lower": "at-least",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown budget direction %r; use one of %s" % (value, ", ".join(DIRECTIONS))
    )


def meets_budget(value, budget, direction):
    """True when a refreshed figure satisfies its budget, exact landings included."""
    value = _number("value", value)
    budget = _number("budget", budget)
    direction = normalize_direction(direction)
    if math.isclose(value, budget, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return True
    return value < budget if direction == "not-to-exceed" else value > budget


def budget_margin(value, budget, direction):
    """Fractional margin of a figure against its budget, positive when met."""
    value = _number("value", value)
    budget = _number("budget", budget)
    direction = normalize_direction(direction)
    if budget == 0.0:
        raise ValueError("margin is undefined against a zero budget")
    if direction == "not-to-exceed":
        return (budget - value) / abs(budget)
    return (value - budget) / abs(budget)


def validate_data_sheet(entries):
    """Check the preliminary data sheet and return it resolved in order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("data sheet must be a list of parameters")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("parameters[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_SHEET_KEYS))
        if unknown:
            raise ValueError(
                "parameters[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "kind", "preliminary", "unit"):
            if key not in entry:
                raise ValueError("parameters[%d] missing key: %s" % (index, key))
        param_id = _text("parameters[%d].id" % index, entry["id"])
        if param_id in seen:
            raise ValueError("duplicate parameter id %r" % param_id)
        seen.add(param_id)
        kind = normalize_kind(entry["kind"])
        preliminary = to_canonical(kind, entry["preliminary"], entry["unit"])
        record = {
            "id": param_id,
            "kind": kind,
            "unit": CANONICAL_UNITS[kind],
            "preliminary": preliminary,
            "budget": None,
            "direction": None,
        }
        if entry.get("budget") is not None:
            record["budget"] = to_canonical(kind, entry["budget"], entry["unit"])
            record["direction"] = normalize_direction(
                entry.get("direction", "not-to-exceed")
            )
        elif entry.get("direction") is not None:
            raise ValueError(
                "parameter %r declares a direction with no budget" % param_id
            )
        resolved.append(record)
    return resolved


def validate_figures(entries):
    """Check the detailed-design figures and return them keyed by parameter."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("figures must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("figures[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_FIGURE_KEYS))
        if unknown:
            raise ValueError(
                "figures[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "value", "unit"):
            if key not in entry:
                raise ValueError("figures[%d] missing key: %s" % (index, key))
        figure_id = _text("figures[%d].id" % index, entry["id"])
        if figure_id in resolved:
            raise ValueError("duplicate figure for parameter %r" % figure_id)
        source = _text("figures[%d].source" % index, entry.get("source", "extraction"))
        if source not in _SOURCES:
            raise ValueError(
                "unknown figure source %r; use one of %s"
                % (source, ", ".join(_SOURCES))
            )
        provisional = entry.get("provisional", False)
        if not isinstance(provisional, bool):
            raise ValueError("figures[%d].provisional must be true or false" % index)
        resolved[figure_id] = {
            "id": figure_id,
            "value": _number("figures[%d].value" % index, entry["value"]),
            "unit": _text("figures[%d].unit" % index, entry["unit"]),
            "source": source,
            "provisional": provisional,
        }
    return resolved


def refresh_data_sheet(sheet, figures, tolerance=0.05, refresh_goal=1.0):
    """Fold detailed-design figures into the preliminary data sheet.

    Returns the refreshed parameter records, the refresh fraction reached,
    the findings and the verdict.
    """
    parameters = validate_data_sheet(sheet)
    if not parameters:
        raise ValueError("the data sheet must carry at least one parameter")
    supplied = validate_figures(figures)
    tolerance = _number("tolerance", tolerance)
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative, got %g" % tolerance)
    refresh_goal = _fraction("refresh_goal", refresh_goal)

    findings = []
    records = []
    refreshed_count = 0
    known = {p["id"] for p in parameters}
    for stray in sorted(set(supplied) - known):
        findings.append(
            {
                "code": "figure-without-parameter",
                "parameter": stray,
                "detail": "a detailed-design figure was supplied for %r, which the "
                "data sheet does not carry" % stray,
            }
        )

    for parameter in parameters:
        record = dict(parameter)
        figure = supplied.get(parameter["id"])
        if figure is None:
            record["refreshed"] = None
            record["movement"] = None
            record["change"] = None
            record["source"] = None
            record["meets_budget"] = None
            record["margin"] = None
            findings.append(
                {
                    "code": "parameter-not-refreshed",
                    "parameter": parameter["id"],
                    "detail": "%s still carries its preliminary estimate after "
                    "detailed design" % parameter["id"],
                }
            )
            records.append(record)
            continue

        refreshed_count += 1
        value = to_canonical(parameter["kind"], figure["value"], figure["unit"])
        record["refreshed"] = value
        record["source"] = figure["source"]
        record["change"] = relative_change(parameter["preliminary"], value)
        record["movement"] = categorize_movement(
            parameter["preliminary"], value, tolerance
        )
        if figure["provisional"]:
            findings.append(
                {
                    "code": "figure-still-provisional",
                    "parameter": parameter["id"],
                    "detail": "the figure refreshing %s is marked provisional, so "
                    "the sheet is not closed on it" % parameter["id"],
                }
            )
        if figure["source"] == "estimate":
            findings.append(
                {
                    "code": "figure-still-an-estimate",
                    "parameter": parameter["id"],
                    "detail": "%s was refreshed from an estimate rather than from "
                    "the detailed design" % parameter["id"],
                }
            )
        if parameter["budget"] is None:
            record["meets_budget"] = None
            record["margin"] = None
        else:
            record["meets_budget"] = meets_budget(
                value, parameter["budget"], parameter["direction"]
            )
            record["margin"] = budget_margin(
                value, parameter["budget"], parameter["direction"]
            )
            if not record["meets_budget"]:
                findings.append(
                    {
                        "code": "budget-broken-by-refreshed-figure",
                        "parameter": parameter["id"],
                        "value": value,
                        "budget": parameter["budget"],
                        "detail": "%s refreshes to %g %s against a %s budget of "
                        "%g %s"
                        % (
                            parameter["id"],
                            value,
                            parameter["unit"],
                            parameter["direction"],
                            parameter["budget"],
                            parameter["unit"],
                        ),
                    }
                )
        records.append(record)

    fraction = refreshed_count / len(parameters)
    if not (
        fraction > refresh_goal
        or math.isclose(fraction, refresh_goal, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    ):
        findings.append(
            {
                "code": "refresh-goal-missed",
                "achieved": fraction,
                "goal": refresh_goal,
                "detail": "%.1f %% of the sheet was refreshed against a %.1f %% goal"
                % (100.0 * fraction, 100.0 * refresh_goal),
            }
        )

    return {
        "parameters": records,
        "parameter_count": len(parameters),
        "refreshed_count": refreshed_count,
        "refresh_fraction": fraction,
        "not_refreshed": sorted(
            r["id"] for r in records if r["refreshed"] is None
        ),
        "findings": findings,
        "acceptable": not findings,
    }
