#!/usr/bin/env python3
"""Device layout generation (ECSS-E-ST-20-40C 5.6.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
Layout generation turns the closed detailed design into a physical
implementation -- a placed and routed database for a digital device, a
drawn layout for an analogue one -- and documents what was done to get
there. A run is judged on four numbers and one list:

* utilisation, the placed cell area over the core area available to it. A
  run above its utilisation ceiling has no room left for the routing and
  the engineering-change cells that always follow;
* timing, the achieved critical-path period against the target period.
  The slack is the difference, and a run landing exactly on target has met
  it -- the comparison absorbs representation error rather than failing an
  implementation that is precisely on the number;
* routing completion, the routed nets over the total nets. Any unrouted
  net is a finding, because the figure rounds to a clean-looking
  percentage long before the last net is connected;
* the open geometry violations the run left behind;
* the documentation the clause asks for -- floorplan, layer stack, pin
  assignment, deviations taken and the tool and version that produced the
  database. An undocumented layout cannot be reproduced or reviewed, and
  the tool version is the item most often left out.

Areas and periods are positive quantities, so a zero or negative figure is
an input defect rather than a finding.
"""

import math

# Implementation styles the clause covers.
IMPLEMENTATION_STYLES = ("place-and-route", "full-custom", "structured-array")

# Documentation the layout record has to carry.
REQUIRED_DOCUMENTATION = (
    "floorplan-description",
    "layer-stack",
    "pin-assignment",
    "layout-rule-deviations",
    "tool-and-version",
)

REL_TOL = 1e-12
ABS_TOL = 1e-18

_RUN_KEYS = (
    "style",
    "core_area_mm2",
    "placed_cell_area_mm2",
    "target_period_ns",
    "achieved_period_ns",
    "total_nets",
    "unrouted_nets",
    "open_geometry_violations",
    "documentation",
)


def _text(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out:
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


def _count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def _fraction(name, value):
    out = _number(name, value)
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def normalize_style(value):
    """Fold an implementation style onto one of the recognised styles."""
    key = " ".join(_text("style", value).lower().replace("_", " ").split())
    key = key.replace(" ", "-")
    aliases = {
        "place-and-route": "place-and-route",
        "pnr": "place-and-route",
        "p-and-r": "place-and-route",
        "digital": "place-and-route",
        "full-custom": "full-custom",
        "custom": "full-custom",
        "analogue": "full-custom",
        "analog": "full-custom",
        "structured-array": "structured-array",
        "sea-of-gates": "structured-array",
    }
    if key in aliases:
        return aliases[key]
    raise ValueError(
        "unknown implementation style %r; use one of %s"
        % (value, ", ".join(IMPLEMENTATION_STYLES))
    )


def utilization(placed_cell_area, core_area):
    """Placed cell area over the core area available to it."""
    placed = _number("placed_cell_area_mm2", placed_cell_area)
    core = _number("core_area_mm2", core_area, positive=True)
    if placed < 0.0:
        raise ValueError("placed_cell_area_mm2 must not be negative")
    return placed / core


def within_utilization_ceiling(value, ceiling):
    """True when utilisation sits at or under its ceiling."""
    value = _number("utilization", value)
    ceiling = _fraction("ceiling", ceiling)
    return value < ceiling or math.isclose(
        value, ceiling, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def setup_slack_ns(target_period_ns, achieved_period_ns):
    """Slack of the critical path against the target period, in nanoseconds."""
    target = _number("target_period_ns", target_period_ns, positive=True)
    achieved = _number("achieved_period_ns", achieved_period_ns, positive=True)
    return target - achieved


def timing_is_met(target_period_ns, achieved_period_ns):
    """True when the run meets its target period, an exact landing included."""
    target = _number("target_period_ns", target_period_ns, positive=True)
    achieved = _number("achieved_period_ns", achieved_period_ns, positive=True)
    if math.isclose(achieved, target, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return True
    return achieved < target


def routing_completion(total_nets, unrouted_nets):
    """Fraction of the net list the run actually connected."""
    total = _count("total_nets", total_nets, minimum=1)
    unrouted = _count("unrouted_nets", unrouted_nets)
    if unrouted > total:
        raise ValueError(
            "unrouted_nets (%d) cannot exceed total_nets (%d)" % (unrouted, total)
        )
    return (total - unrouted) / total


def missing_documentation(documentation):
    """Documentation items the clause asks for and the record does not carry."""
    if not isinstance(documentation, (list, tuple, set)):
        raise ValueError("documentation must be a list, tuple or set")
    present = set()
    for index, item in enumerate(sorted(documentation)):
        name = " ".join(
            _text("documentation[%d]" % index, item).lower().replace("_", " ").split()
        ).replace(" ", "-")
        if name not in REQUIRED_DOCUMENTATION:
            raise ValueError(
                "unknown documentation item %r; use one of %s"
                % (item, ", ".join(REQUIRED_DOCUMENTATION))
            )
        present.add(name)
    return [item for item in REQUIRED_DOCUMENTATION if item not in present]


def validate_run(run):
    """Check the layout run record and return it resolved."""
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping describing the layout run")
    unknown = sorted(set(run) - set(_RUN_KEYS))
    if unknown:
        raise ValueError("run has unknown keys: %s" % ", ".join(unknown))
    required = (
        "core_area_mm2",
        "placed_cell_area_mm2",
        "target_period_ns",
        "achieved_period_ns",
        "total_nets",
    )
    missing = [key for key in required if key not in run]
    if missing:
        raise ValueError("run missing required keys: %s" % ", ".join(missing))
    return {
        "style": normalize_style(run.get("style", "place-and-route")),
        "core_area_mm2": _number("core_area_mm2", run["core_area_mm2"], positive=True),
        "placed_cell_area_mm2": _number(
            "placed_cell_area_mm2", run["placed_cell_area_mm2"]
        ),
        "target_period_ns": _number(
            "target_period_ns", run["target_period_ns"], positive=True
        ),
        "achieved_period_ns": _number(
            "achieved_period_ns", run["achieved_period_ns"], positive=True
        ),
        "total_nets": _count("total_nets", run["total_nets"], minimum=1),
        "unrouted_nets": _count("unrouted_nets", run.get("unrouted_nets", 0)),
        "open_geometry_violations": _count(
            "open_geometry_violations", run.get("open_geometry_violations", 0)
        ),
        "documentation": list(run.get("documentation", [])),
    }


def evaluate_layout_generation(run, utilization_ceiling=0.75):
    """Full 5.6.2 assessment of one device layout generation run.

    Returns the utilisation, slack and routing figures, the documentation
    gaps, the findings and the verdict.
    """
    resolved = validate_run(run)
    ceiling = _fraction("utilization_ceiling", utilization_ceiling)

    used = utilization(
        resolved["placed_cell_area_mm2"], resolved["core_area_mm2"]
    )
    slack = setup_slack_ns(
        resolved["target_period_ns"], resolved["achieved_period_ns"]
    )
    met = timing_is_met(
        resolved["target_period_ns"], resolved["achieved_period_ns"]
    )
    completion = routing_completion(
        resolved["total_nets"], resolved["unrouted_nets"]
    )
    gaps = missing_documentation(resolved["documentation"])

    findings = []
    if not within_utilization_ceiling(used, ceiling):
        findings.append(
            {
                "code": "utilization-over-ceiling",
                "achieved": used,
                "ceiling": ceiling,
                "detail": "the core is %.1f %% utilised against a %.1f %% ceiling, "
                "leaving no room for routing and later change cells"
                % (100.0 * used, 100.0 * ceiling),
            }
        )
    if not met:
        findings.append(
            {
                "code": "target-period-not-met",
                "slack_ns": slack,
                "detail": "the critical path closes at %g ns against a %g ns "
                "target, a slack of %g ns"
                % (
                    resolved["achieved_period_ns"],
                    resolved["target_period_ns"],
                    slack,
                ),
            }
        )
    if resolved["unrouted_nets"] > 0:
        findings.append(
            {
                "code": "nets-left-unrouted",
                "unrouted": resolved["unrouted_nets"],
                "detail": "%d of %d nets are unrouted, so the implementation is "
                "incomplete however high the completion figure reads"
                % (resolved["unrouted_nets"], resolved["total_nets"]),
            }
        )
    if resolved["open_geometry_violations"] > 0:
        findings.append(
            {
                "code": "geometry-violations-open",
                "violations": resolved["open_geometry_violations"],
                "detail": "%d geometry violations are still open on the generated "
                "layout" % resolved["open_geometry_violations"],
            }
        )
    for item in gaps:
        findings.append(
            {
                "code": "documentation-item-missing",
                "item": item,
                "detail": "the layout record carries no %s, so the implementation "
                "cannot be reproduced or reviewed" % item,
            }
        )

    return {
        "style": resolved["style"],
        "utilization": used,
        "utilization_ceiling": ceiling,
        "setup_slack_ns": slack,
        "timing_met": met,
        "routing_completion": completion,
        "unrouted_nets": resolved["unrouted_nets"],
        "missing_documentation": gaps,
        "findings": findings,
        "releasable": not findings,
    }
