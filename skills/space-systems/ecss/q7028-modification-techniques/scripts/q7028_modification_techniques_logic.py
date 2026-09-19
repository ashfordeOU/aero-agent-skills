"""Modification plan checks for a printed board assembly.

Anchor: ECSS-Q-ST-70-28 Methods (modification of a printed board assembly by
cutting tracks, adding wires and changing components). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every modification item in the plan and the board data it is
   graded against.
2. For a cut track, check the isolation actually left between the two cut
   ends against the gap the working voltage demands, and refuse a cut that
   left a copper bridge behind however wide the gap looks.
3. For an added wire, check the conductor carries its current, and work out
   how many intermediate supports the routed length needs so the wire cannot
   resonate or chafe.
4. For a component change, check the substitution is covered by an approved
   change record and that the replacement footprint matches the land pattern.
5. Draw the whole plan against the number of added wires the board may carry
   and against the requirement that every item is recorded, then return one
   verdict with the item-level findings kept separate.
"""

import math

__all__ = [
    "LENGTH_TOLERANCE_MM",
    "CURRENT_TOLERANCE_A",
    "SPAN_TOLERANCE",
    "WIRE_AMPACITY_A",
    "require_real",
    "require_count",
    "required_isolation_gap_mm",
    "assess_track_cut",
    "wire_ampacity_a",
    "support_points_required",
    "assess_added_wire",
    "added_wire_budget",
    "assess_component_change",
    "assess_modification_plan",
]

LENGTH_TOLERANCE_MM = 1e-9
CURRENT_TOLERANCE_A = 1e-9
# Absorbs the representation error in a length/span ratio that should land on
# a whole number, so a span dividing the length exactly does not buy a support.
SPAN_TOLERANCE = 1e-9

# Continuous current a single insulated hook-up conductor may carry when it is
# routed clear of a bundle, keyed by conductor gauge number.
WIRE_AMPACITY_A = {
    30: 0.86,
    28: 1.4,
    26: 2.2,
    24: 3.5,
    22: 5.0,
    20: 8.0,
    18: 12.0,
}


def require_real(label, value, minimum=None, allow_equal=True):
    """Return value as a float, raising ValueError on anything unusable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if allow_equal and out < minimum:
            raise ValueError("%s must be at least %g, got %g" % (label, minimum, out))
        if not allow_equal and out <= minimum:
            raise ValueError("%s must exceed %g, got %g" % (label, minimum, out))
    return out


def require_count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def required_isolation_gap_mm(gap_table, working_voltage_v):
    """Interpolate the isolation gap a working voltage demands."""
    if not isinstance(gap_table, (list, tuple)) or len(gap_table) < 2:
        raise ValueError("gap_table needs at least two (volts, gap_mm) points")
    points = []
    for i, item in enumerate(gap_table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("gap_table[%d] must be a (volts, gap_mm) pair" % i)
        volts = require_real("gap_table[%d] volts" % i, item[0], minimum=0.0,
                             allow_equal=False)
        gap = require_real("gap_table[%d] gap_mm" % i, item[1], minimum=0.0,
                           allow_equal=False)
        points.append((volts, gap))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError("gap_table voltages must strictly increase (index %d)" % i)
    voltage = require_real("working_voltage_v", working_voltage_v, minimum=0.0,
                           allow_equal=False)
    low_v, high_v = points[0][0], points[-1][0]
    if voltage < low_v or voltage > high_v:
        raise ValueError(
            "gap_table is tabulated over [%g, %g] V; %g V is outside it, "
            "extrapolation refused" % (low_v, high_v, voltage)
        )
    for i in range(1, len(points)):
        v0, g0 = points[i - 1]
        v1, g1 = points[i]
        if voltage <= v1:
            if voltage == v0:
                return g0
            if voltage == v1:
                return g1
            fraction = (voltage - v0) / (v1 - v0)
            return g0 + fraction * (g1 - g0)
    return points[-1][1]


def assess_track_cut(gap_mm, working_voltage_v, gap_table, residual_copper_mm=0.0):
    """Grade one cut track on its isolation gap and on any copper left bridging it."""
    gap = require_real("gap_mm", gap_mm, minimum=0.0)
    residual = require_real("residual_copper_mm", residual_copper_mm, minimum=0.0)
    required = required_isolation_gap_mm(gap_table, working_voltage_v)
    bridged = residual > LENGTH_TOLERANCE_MM
    short = gap < required - LENGTH_TOLERANCE_MM
    return {
        "gap_mm": gap,
        "required_gap_mm": required,
        "residual_copper_mm": residual,
        "bridged": bridged,
        "gap_short": short,
        "acceptable": not (bridged or short),
    }


def wire_ampacity_a(gauge):
    """Return the continuous current a conductor gauge may carry."""
    if not isinstance(gauge, int) or isinstance(gauge, bool):
        raise ValueError("gauge must be an integer gauge number, got %r" % (gauge,))
    if gauge not in WIRE_AMPACITY_A:
        raise ValueError(
            "gauge must be one of %s, got %d"
            % (", ".join(str(g) for g in sorted(WIRE_AMPACITY_A)), gauge)
        )
    return WIRE_AMPACITY_A[gauge]


def support_points_required(length_mm, max_unsupported_span_mm):
    """Return the intermediate supports a routed wire length needs."""
    length = require_real("length_mm", length_mm, minimum=0.0, allow_equal=False)
    span = require_real("max_unsupported_span_mm", max_unsupported_span_mm,
                        minimum=0.0, allow_equal=False)
    segments = math.ceil(length / span - SPAN_TOLERANCE)
    return max(0, segments - 1)


def assess_added_wire(gauge, current_a, length_mm, max_unsupported_span_mm,
                      supports_planned):
    """Grade one added wire on conductor rating and on how it is supported."""
    ampacity = wire_ampacity_a(gauge)
    current = require_real("current_a", current_a, minimum=0.0)
    needed = support_points_required(length_mm, max_unsupported_span_mm)
    planned = require_count("supports_planned", supports_planned)
    over_current = current > ampacity + CURRENT_TOLERANCE_A
    under_supported = planned < needed
    return {
        "gauge": gauge,
        "ampacity_a": ampacity,
        "current_a": current,
        "over_current": over_current,
        "supports_required": needed,
        "supports_planned": planned,
        "under_supported": under_supported,
        "acceptable": not (over_current or under_supported),
    }


def added_wire_budget(wires_already_fitted, wires_in_this_plan, max_added_wires):
    """Return the added-wire budget state for the board."""
    fitted = require_count("wires_already_fitted", wires_already_fitted)
    planned = require_count("wires_in_this_plan", wires_in_this_plan)
    maximum = require_count("max_added_wires", max_added_wires)
    total = fitted + planned
    return {
        "wires_already_fitted": fitted,
        "wires_in_this_plan": planned,
        "total_after_plan": total,
        "max_added_wires": maximum,
        "over_budget": total > maximum,
        "at_budget": total == maximum,
    }


def assess_component_change(reference, approved_change_ref, footprint_matches):
    """Grade one component substitution on its approval and its land pattern."""
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("reference must be a non-empty designator string")
    if approved_change_ref is not None and not isinstance(approved_change_ref, str):
        raise ValueError("approved_change_ref must be a string or None")
    if not isinstance(footprint_matches, bool):
        raise ValueError("footprint_matches must be a bool, got %r"
                         % (footprint_matches,))
    unapproved = approved_change_ref is None or not approved_change_ref.strip()
    return {
        "reference": reference,
        "approved_change_ref": approved_change_ref,
        "unapproved": unapproved,
        "footprint_matches": footprint_matches,
        "acceptable": not unapproved and footprint_matches,
    }


def assess_modification_plan(spec):
    """Grade a whole board modification plan and return one verdict.

    spec keys: gap_table, max_unsupported_span_mm, wires_already_fitted,
    max_added_wires, optional track_cuts, added_wires, component_changes and
    recorded (a bool saying every item carries a modification record).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("gap_table", "max_unsupported_span_mm", "wires_already_fitted",
                "max_added_wires"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    cuts_in = spec.get("track_cuts", [])
    wires_in = spec.get("added_wires", [])
    changes_in = spec.get("component_changes", [])
    for label, seq in (("track_cuts", cuts_in), ("added_wires", wires_in),
                       ("component_changes", changes_in)):
        if not isinstance(seq, (list, tuple)):
            raise ValueError("spec['%s'] must be a sequence of mappings" % label)
    if not cuts_in and not wires_in and not changes_in:
        raise ValueError("a modification plan must carry at least one item")

    findings = []

    cuts = []
    for index, item in enumerate(cuts_in):
        if not isinstance(item, dict):
            raise ValueError("track_cuts[%d] must be a mapping" % index)
        for key in ("reference", "gap_mm", "working_voltage_v"):
            if key not in item:
                raise ValueError("track_cuts[%d] missing key '%s'" % (index, key))
        record = assess_track_cut(
            item["gap_mm"], item["working_voltage_v"], spec["gap_table"],
            item.get("residual_copper_mm", 0.0),
        )
        record["reference"] = item["reference"]
        cuts.append(record)
        if record["bridged"]:
            findings.append(
                "cut %s still has %.3f mm of copper bridging it"
                % (record["reference"], record["residual_copper_mm"])
            )
        if record["gap_short"]:
            findings.append(
                "cut %s leaves %.3f mm against the %.3f mm its working voltage demands"
                % (record["reference"], record["gap_mm"], record["required_gap_mm"])
            )

    wires = []
    for index, item in enumerate(wires_in):
        if not isinstance(item, dict):
            raise ValueError("added_wires[%d] must be a mapping" % index)
        for key in ("reference", "gauge", "current_a", "length_mm",
                    "supports_planned"):
            if key not in item:
                raise ValueError("added_wires[%d] missing key '%s'" % (index, key))
        record = assess_added_wire(
            item["gauge"], item["current_a"], item["length_mm"],
            spec["max_unsupported_span_mm"], item["supports_planned"],
        )
        record["reference"] = item["reference"]
        wires.append(record)
        if record["over_current"]:
            findings.append(
                "wire %s carries %.3f A on a conductor rated %.3f A"
                % (record["reference"], record["current_a"], record["ampacity_a"])
            )
        if record["under_supported"]:
            findings.append(
                "wire %s is planned with %d supports against the %d its routing needs"
                % (record["reference"], record["supports_planned"],
                   record["supports_required"])
            )

    changes = []
    for index, item in enumerate(changes_in):
        if not isinstance(item, dict):
            raise ValueError("component_changes[%d] must be a mapping" % index)
        for key in ("reference", "footprint_matches"):
            if key not in item:
                raise ValueError("component_changes[%d] missing key '%s'"
                                 % (index, key))
        record = assess_component_change(
            item["reference"], item.get("approved_change_ref"),
            item["footprint_matches"],
        )
        changes.append(record)
        if record["unapproved"]:
            findings.append(
                "component change %s carries no approved change reference"
                % record["reference"]
            )
        if not record["footprint_matches"]:
            findings.append(
                "component change %s does not match the land pattern"
                % record["reference"]
            )

    budget = added_wire_budget(spec["wires_already_fitted"], len(wires),
                               spec["max_added_wires"])
    if budget["over_budget"]:
        findings.append(
            "the plan takes the board to %d added wires against a limit of %d"
            % (budget["total_after_plan"], budget["max_added_wires"])
        )
    elif budget["at_budget"]:
        findings.append(
            "the plan takes the board to its limit of %d added wires"
            % budget["max_added_wires"]
        )

    recorded = spec.get("recorded", True)
    if not isinstance(recorded, bool):
        raise ValueError("spec['recorded'] must be a bool, got %r" % (recorded,))
    if not recorded:
        findings.append("not every modification item carries a modification record")

    rejected = budget["over_budget"] or not recorded
    for record in cuts:
        if not record["acceptable"]:
            rejected = True
    for record in wires:
        if not record["acceptable"]:
            rejected = True
    for record in changes:
        if not record["acceptable"]:
            rejected = True

    if rejected:
        verdict = "reject"
    elif findings:
        verdict = "plan-with-actions"
    else:
        verdict = "approve"

    return {
        "track_cuts": cuts,
        "added_wires": wires,
        "component_changes": changes,
        "wire_budget": budget,
        "recorded": recorded,
        "verdict": verdict,
        "findings": findings,
    }
