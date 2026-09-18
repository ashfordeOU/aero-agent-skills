"""Layout and electrical rule checking of a drawn MMIC mask set.

Anchor: ECSS-Q-ST-60-12C clause 7.2.11 (automated verification that the drawn
layout obeys the foundry's geometry rules and that the drawn connectivity is the
intended one). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the rule deck and the drawn shapes. A shape is a rectangle on a
   named layer, carrying the net it belongs to; the deck carries, per layer, a
   minimum drawn width, a minimum spacing and a current-carrying capability per
   micron of metal width, plus the enclosure rules between layer pairs.
2. Run the geometry checks: minimum width on every shape, minimum spacing
   between same-layer shapes that belong to different nets, and enclosure of an
   inner-layer shape by an outer-layer shape on all four sides.
3. Run the electrical checks: every declared net must be drawn, every drawn
   shape must name a declared net, a net needs at least two connection points to
   be anything but a floating node, and the narrowest metal on a net must carry
   the current the net was declared to carry.
4. Move any finding whose rule and shapes match a documented waiver into a
   separate waived group. A waived finding is reported, never deleted, and the
   run is clean only when nothing unwaived remains.

Coordinates and dimensions are in microns, currents in milliamps.
"""

import math

__all__ = [
    "GEOMETRY_TOLERANCE",
    "validate_shape",
    "validate_rule_deck",
    "validate_net",
    "rectangle_separation_um",
    "enclosure_margin_um",
    "check_minimum_width",
    "check_minimum_spacing",
    "check_enclosure",
    "check_current_capacity",
    "check_connectivity",
    "apply_waivers",
    "group_findings",
    "run_rule_checks",
]

# Geometry comparisons are differences of floats that a shape drawn exactly on
# the rule lands on. Absorb the representation error here, never by shaving the
# foundry rule itself.
GEOMETRY_TOLERANCE = 1e-9

_SEVERITY_ORDER = ("error", "warning", "waived")


def _real(label, value):
    """Return value as a finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(label, value, allow_zero=False):
    """Return value as a positive finite float."""
    number = _real(label, value)
    if allow_zero:
        if number < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, number))
    elif number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _text(label, value):
    """Return a non-empty identifier string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def validate_shape(shape):
    """Return a normalised drawn rectangle.

    Keys: id, layer, net, x, y (lower-left corner), width_um, height_um.
    """
    if not isinstance(shape, dict):
        raise ValueError("shape must be a mapping")
    for key in ("id", "layer", "net", "x_um", "y_um", "width_um", "height_um"):
        if key not in shape:
            raise ValueError("shape missing required key '%s'" % key)
    return {
        "id": _text("shape['id']", shape["id"]),
        "layer": _text("shape['layer']", shape["layer"]),
        "net": _text("shape['net']", shape["net"]),
        "x_um": _real("shape['x_um']", shape["x_um"]),
        "y_um": _real("shape['y_um']", shape["y_um"]),
        "width_um": _positive("shape['width_um']", shape["width_um"]),
        "height_um": _positive("shape['height_um']", shape["height_um"]),
    }


def validate_rule_deck(deck):
    """Return a normalised foundry rule deck.

    Keys: layers (mapping of layer name to min_width_um, min_spacing_um and
    optional current_capacity_ma_per_um) and optional enclosures (a sequence of
    inner/outer/min_enclosure_um rules).
    """
    if not isinstance(deck, dict):
        raise ValueError("deck must be a mapping")
    if "layers" not in deck:
        raise ValueError("deck missing required key 'layers'")
    layers = deck["layers"]
    if not isinstance(layers, dict) or not layers:
        raise ValueError("deck['layers'] must be a non-empty mapping")
    out_layers = {}
    for name, rules in layers.items():
        layer = _text("layer name", name)
        if not isinstance(rules, dict):
            raise ValueError("deck['layers']['%s'] must be a mapping" % layer)
        for key in ("min_width_um", "min_spacing_um"):
            if key not in rules:
                raise ValueError(
                    "deck['layers']['%s'] missing rule '%s'" % (layer, key)
                )
        entry = {
            "min_width_um": _positive("%s min_width_um" % layer,
                                      rules["min_width_um"]),
            "min_spacing_um": _positive("%s min_spacing_um" % layer,
                                        rules["min_spacing_um"]),
        }
        capacity = rules.get("current_capacity_ma_per_um")
        if capacity is not None:
            entry["current_capacity_ma_per_um"] = _positive(
                "%s current_capacity_ma_per_um" % layer, capacity
            )
        out_layers[layer] = entry
    enclosures = deck.get("enclosures", [])
    if not isinstance(enclosures, (list, tuple)):
        raise ValueError("deck['enclosures'] must be a sequence")
    out_enclosures = []
    for index, rule in enumerate(enclosures):
        if not isinstance(rule, dict):
            raise ValueError("deck['enclosures'][%d] must be a mapping" % index)
        for key in ("inner", "outer", "min_enclosure_um"):
            if key not in rule:
                raise ValueError(
                    "deck['enclosures'][%d] missing '%s'" % (index, key)
                )
        inner = _text("enclosure inner", rule["inner"])
        outer = _text("enclosure outer", rule["outer"])
        if inner == outer:
            raise ValueError(
                "enclosure rule %d names '%s' as both inner and outer layer"
                % (index, inner)
            )
        out_enclosures.append({
            "inner": inner,
            "outer": outer,
            "min_enclosure_um": _positive("enclosure min_enclosure_um",
                                          rule["min_enclosure_um"]),
        })
    return {"layers": out_layers, "enclosures": out_enclosures}


def validate_net(net):
    """Return a normalised declared net.

    Keys: name, optional current_ma and connection_points.
    """
    if not isinstance(net, dict):
        raise ValueError("net must be a mapping")
    if "name" not in net:
        raise ValueError("net missing required key 'name'")
    points = net.get("connection_points", 2)
    if isinstance(points, bool) or not isinstance(points, int):
        raise ValueError("net['connection_points'] must be an integer")
    if points < 0:
        raise ValueError("net['connection_points'] must not be negative")
    return {
        "name": _text("net['name']", net["name"]),
        "current_ma": _positive("net['current_ma']", net.get("current_ma", 0.0),
                                allow_zero=True),
        "connection_points": points,
    }


def _finding(rule, severity, message, shapes):
    return {
        "rule": rule,
        "severity": severity,
        "message": message,
        "shapes": tuple(sorted(shapes)),
    }


def rectangle_separation_um(first, second):
    """Return the edge-to-edge separation of two rectangles; zero when they touch."""
    a = validate_shape(first)
    b = validate_shape(second)
    gap_x = max(a["x_um"] - (b["x_um"] + b["width_um"]),
                b["x_um"] - (a["x_um"] + a["width_um"]), 0.0)
    gap_y = max(a["y_um"] - (b["y_um"] + b["height_um"]),
                b["y_um"] - (a["y_um"] + a["height_um"]), 0.0)
    if gap_x == 0.0:
        return gap_y
    if gap_y == 0.0:
        return gap_x
    return math.hypot(gap_x, gap_y)


def enclosure_margin_um(inner, outer):
    """Return the smallest of the four enclosure margins; negative when uncovered."""
    a = validate_shape(inner)
    b = validate_shape(outer)
    left = a["x_um"] - b["x_um"]
    right = (b["x_um"] + b["width_um"]) - (a["x_um"] + a["width_um"])
    bottom = a["y_um"] - b["y_um"]
    top = (b["y_um"] + b["height_um"]) - (a["y_um"] + a["height_um"])
    return min(left, right, bottom, top)


def check_minimum_width(shapes, deck):
    """Return the findings for shapes drawn narrower than their layer allows."""
    rules = validate_rule_deck(deck)
    findings = []
    for raw in shapes:
        shape = validate_shape(raw)
        layer = rules["layers"].get(shape["layer"])
        if layer is None:
            findings.append(_finding(
                "unknown-layer", "error",
                "shape %s is drawn on layer '%s', which the deck does not define"
                % (shape["id"], shape["layer"]), [shape["id"]],
            ))
            continue
        drawn = min(shape["width_um"], shape["height_um"])
        limit = layer["min_width_um"]
        if drawn < limit - GEOMETRY_TOLERANCE * max(1.0, limit):
            findings.append(_finding(
                "min-width", "error",
                "shape %s is %.4f um wide on %s, below the %.4f um minimum"
                % (shape["id"], drawn, shape["layer"], limit), [shape["id"]],
            ))
    return findings


def check_minimum_spacing(shapes, deck):
    """Return the findings for same-layer shapes on different nets drawn too close."""
    rules = validate_rule_deck(deck)
    drawn = [validate_shape(s) for s in shapes]
    findings = []
    for i in range(len(drawn)):
        for j in range(i + 1, len(drawn)):
            a, b = drawn[i], drawn[j]
            if a["layer"] != b["layer"]:
                continue
            layer = rules["layers"].get(a["layer"])
            if layer is None:
                continue
            if a["net"] == b["net"]:
                # Same-net metal touching is connectivity, not a spacing error.
                continue
            separation = rectangle_separation_um(a, b)
            limit = layer["min_spacing_um"]
            if separation < limit - GEOMETRY_TOLERANCE * max(1.0, limit):
                findings.append(_finding(
                    "min-spacing", "error",
                    "shapes %s and %s on %s are %.4f um apart, below the %.4f um "
                    "minimum" % (a["id"], b["id"], a["layer"], separation, limit),
                    [a["id"], b["id"]],
                ))
    return findings


def check_enclosure(shapes, deck):
    """Return the findings for inner shapes not enclosed by their outer layer."""
    rules = validate_rule_deck(deck)
    drawn = [validate_shape(s) for s in shapes]
    findings = []
    for rule in rules["enclosures"]:
        inners = [s for s in drawn if s["layer"] == rule["inner"]]
        outers = [s for s in drawn if s["layer"] == rule["outer"]]
        for inner in inners:
            limit = rule["min_enclosure_um"]
            best = None
            for outer in outers:
                margin = enclosure_margin_um(inner, outer)
                if best is None or margin > best:
                    best = margin
            if best is None:
                findings.append(_finding(
                    "enclosure", "error",
                    "shape %s on %s has no %s shape to enclose it"
                    % (inner["id"], rule["inner"], rule["outer"]), [inner["id"]],
                ))
            elif best < limit - GEOMETRY_TOLERANCE * max(1.0, limit):
                findings.append(_finding(
                    "enclosure", "error",
                    "shape %s on %s is enclosed by only %.4f um of %s, below the "
                    "%.4f um minimum"
                    % (inner["id"], rule["inner"], best, rule["outer"], limit),
                    [inner["id"]],
                ))
    return findings


def check_current_capacity(shapes, nets, deck):
    """Return the findings for nets whose narrowest metal cannot carry their current."""
    rules = validate_rule_deck(deck)
    drawn = [validate_shape(s) for s in shapes]
    findings = []
    for raw in nets:
        net = validate_net(raw)
        if net["current_ma"] <= 0.0:
            continue
        narrowest = None
        capacity_per_um = None
        for shape in drawn:
            if shape["net"] != net["name"]:
                continue
            layer = rules["layers"].get(shape["layer"])
            if layer is None or "current_capacity_ma_per_um" not in layer:
                continue
            width = min(shape["width_um"], shape["height_um"])
            capacity = width * layer["current_capacity_ma_per_um"]
            if narrowest is None or capacity < narrowest[1]:
                narrowest = (shape, capacity)
                capacity_per_um = layer["current_capacity_ma_per_um"]
        if narrowest is None:
            findings.append(_finding(
                "current-capacity", "warning",
                "net %s is declared to carry %.4f mA but no metal on it has a "
                "declared capacity" % (net["name"], net["current_ma"]), [],
            ))
            continue
        shape, capacity = narrowest
        if net["current_ma"] > capacity + GEOMETRY_TOLERANCE * max(1.0, capacity):
            findings.append(_finding(
                "current-capacity", "error",
                "net %s carries %.4f mA through shape %s, which at %.4f mA per um "
                "supports only %.4f mA"
                % (net["name"], net["current_ma"], shape["id"], capacity_per_um,
                   capacity), [shape["id"]],
            ))
    return findings


def check_connectivity(shapes, nets):
    """Return the findings for undrawn nets, undeclared nets and floating nodes."""
    drawn = [validate_shape(s) for s in shapes]
    declared = {}
    for raw in nets:
        net = validate_net(raw)
        if net["name"] in declared:
            raise ValueError("net '%s' is declared twice" % net["name"])
        declared[net["name"]] = net
    findings = []
    drawn_nets = {}
    for shape in drawn:
        drawn_nets.setdefault(shape["net"], []).append(shape["id"])
    for name in sorted(declared):
        if name not in drawn_nets:
            findings.append(_finding(
                "connectivity", "error",
                "net %s is declared but nothing on the layout is drawn on it"
                % name, [],
            ))
        elif declared[name]["connection_points"] < 2:
            findings.append(_finding(
                "connectivity", "warning",
                "net %s reaches only %d connection point; it is a floating node"
                % (name, declared[name]["connection_points"]),
                drawn_nets[name],
            ))
    for name in sorted(drawn_nets):
        if name not in declared:
            findings.append(_finding(
                "connectivity", "error",
                "shapes are drawn on net %s, which the netlist does not declare"
                % name, drawn_nets[name],
            ))
    return findings


def apply_waivers(findings, waivers=None):
    """Split findings into the unwaived ones and the ones a waiver covers.

    A waiver names a rule and, optionally, the shape ids it covers. A waiver
    with no shape ids covers every finding of that rule.
    """
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    if waivers is None:
        waivers = []
    if not isinstance(waivers, (list, tuple)):
        raise ValueError("waivers must be a sequence")
    checked = []
    for index, waiver in enumerate(waivers):
        if not isinstance(waiver, dict):
            raise ValueError("waivers[%d] must be a mapping" % index)
        if "rule" not in waiver:
            raise ValueError("waivers[%d] missing 'rule'" % index)
        ids = waiver.get("shapes", [])
        if not isinstance(ids, (list, tuple)):
            raise ValueError("waivers[%d]['shapes'] must be a sequence" % index)
        checked.append({
            "rule": _text("waiver rule", waiver["rule"]),
            "shapes": tuple(sorted(_text("waiver shape id", s) for s in ids)),
            "reference": waiver.get("reference", ""),
        })
    open_findings = []
    waived = []
    for finding in findings:
        if not isinstance(finding, dict) or "rule" not in finding:
            raise ValueError("each finding must be a mapping carrying 'rule'")
        cover = None
        for waiver in checked:
            if waiver["rule"] != finding["rule"]:
                continue
            if waiver["shapes"] and waiver["shapes"] != tuple(finding["shapes"]):
                continue
            cover = waiver
            break
        if cover is None:
            open_findings.append(finding)
        else:
            entry = dict(finding)
            entry["severity"] = "waived"
            entry["waiver_reference"] = cover["reference"]
            waived.append(entry)
    return open_findings, waived


def group_findings(findings):
    """Return finding counts grouped by severity and by rule."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    by_severity = {}
    by_rule = {}
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("each finding must be a mapping")
        for key in ("severity", "rule"):
            if key not in finding:
                raise ValueError("finding missing '%s'" % key)
        by_severity[finding["severity"]] = by_severity.get(finding["severity"], 0) + 1
        by_rule[finding["rule"]] = by_rule.get(finding["rule"], 0) + 1
    ordered = {}
    for key in _SEVERITY_ORDER:
        if key in by_severity:
            ordered[key] = by_severity[key]
    for key in sorted(by_severity):
        if key not in ordered:
            ordered[key] = by_severity[key]
    return {"by_severity": ordered,
            "by_rule": {k: by_rule[k] for k in sorted(by_rule)}}


def run_rule_checks(layout, deck, waivers=None):
    """Run the clause 7.2.11 geometry and connectivity checks over a layout.

    layout keys: shapes (sequence of rectangles), optional nets (netlist).
    """
    if not isinstance(layout, dict):
        raise ValueError("layout must be a mapping")
    if "shapes" not in layout:
        raise ValueError("layout missing required key 'shapes'")
    shapes = layout["shapes"]
    if not isinstance(shapes, (list, tuple)) or not shapes:
        raise ValueError("layout['shapes'] must be a non-empty sequence")
    nets = layout.get("nets", [])
    if not isinstance(nets, (list, tuple)):
        raise ValueError("layout['nets'] must be a sequence")
    seen = set()
    for raw in shapes:
        shape = validate_shape(raw)
        if shape["id"] in seen:
            raise ValueError("shape id '%s' is drawn twice" % shape["id"])
        seen.add(shape["id"])
    findings = []
    findings.extend(check_minimum_width(shapes, deck))
    findings.extend(check_minimum_spacing(shapes, deck))
    findings.extend(check_enclosure(shapes, deck))
    findings.extend(check_current_capacity(shapes, nets, deck))
    findings.extend(check_connectivity(shapes, nets))
    open_findings, waived = apply_waivers(findings, waivers)
    open_findings.sort(key=lambda f: (f["rule"], f["shapes"]))
    waived.sort(key=lambda f: (f["rule"], f["shapes"]))
    errors = [f for f in open_findings if f["severity"] == "error"]
    return {
        "findings": open_findings,
        "waived": waived,
        "grouped": group_findings(open_findings + waived),
        "error_count": len(errors),
        "clean": not open_findings,
    }
