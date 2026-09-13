"""Wire-category scheme and harness routing segregation.

Anchor: ECSS-E-ST-20-07C clause 4.2.13.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Assign every wire an electromagnetic category from its function,
   then adjust that assignment from its measured electrical behaviour:
   a fast-switching line is promoted to the interfering category, and
   a low-amplitude high-source-impedance line is demoted to the
   sensitive category.
2. Require a bundle to be uniform: every wire sharing a bundle must
   carry the same category, and a critical line may not share its
   bundle with a non-critical wire.
3. Derive the separation each bundle pair needs from the categories
   the two bundles carry, and compare it with the declared route
   separation.
4. Apply the extra treatment a critical line needs: twisted and
   shielded construction, and a routing path distinct from the one
   its redundant partner uses.

Stdlib only, offline, deterministic.
"""

CAT_SENSITIVE = "cat-1-sensitive"
CAT_SIGNAL = "cat-2-signal"
CAT_POWER = "cat-3-power"
CAT_INTERFERING = "cat-4-interfering"
CATEGORIES = (CAT_SENSITIVE, CAT_SIGNAL, CAT_POWER, CAT_INTERFERING)

FUNCTION_BASE_CATEGORY = {
    "low-level-analog-sensor": CAT_SENSITIVE,
    "detector-readout": CAT_SENSITIVE,
    "digital-data-bus": CAT_SIGNAL,
    "discrete-command": CAT_SIGNAL,
    "telemetry-acquisition": CAT_SIGNAL,
    "primary-power-distribution": CAT_POWER,
    "secondary-power-distribution": CAT_POWER,
    "power-return": CAT_POWER,
    "pyrotechnic-firing": CAT_INTERFERING,
    "motor-drive": CAT_INTERFERING,
    "heater-switching": CAT_INTERFERING,
    "radiofrequency-feed": CAT_INTERFERING,
}

# A line below this amplitude fed from above this source impedance is
# treated as sensitive whatever its nominal function family says.
SENSITIVE_AMPLITUDE_LIMIT_V = 0.1
SENSITIVE_SOURCE_IMPEDANCE_OHM = 1.0e4

# Switching rates above which a line is an interference source.
SWITCHING_DIDT_LIMIT_A_PER_US = 10.0
SWITCHING_DVDT_LIMIT_V_PER_US = 50.0

# Minimum bundle-to-bundle separation, in millimetres, keyed by the
# ordered category pair. Same-category bundles may run together.
SEPARATION_MATRIX_MM = {
    (CAT_SENSITIVE, CAT_SENSITIVE): 0.0,
    (CAT_SENSITIVE, CAT_SIGNAL): 50.0,
    (CAT_SENSITIVE, CAT_POWER): 100.0,
    (CAT_SENSITIVE, CAT_INTERFERING): 200.0,
    (CAT_SIGNAL, CAT_SIGNAL): 0.0,
    (CAT_SIGNAL, CAT_POWER): 50.0,
    (CAT_SIGNAL, CAT_INTERFERING): 150.0,
    (CAT_POWER, CAT_POWER): 0.0,
    (CAT_POWER, CAT_INTERFERING): 100.0,
    (CAT_INTERFERING, CAT_INTERFERING): 0.0,
}

# A declared separation is the sum of measured route offsets, so an
# exactly satisfied requirement can land a few ULPs short. This
# tolerance is far below any harness measurement resolution and
# absorbs that representation error without relaxing the requirement.
SEPARATION_TOLERANCE_MM = 1.0e-6

CRITICAL_CONSTRUCTION = "twisted-shielded-pair"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def validate_wire(wire):
    """Validate one wire record and return a normalized copy."""
    if not isinstance(wire, dict):
        raise ValueError("wire must be a mapping")
    wire_id = wire.get("id")
    if not isinstance(wire_id, str) or not wire_id.strip():
        raise ValueError("wire needs a non-empty string id")
    function = wire.get("function")
    if function not in FUNCTION_BASE_CATEGORY:
        raise ValueError(
            "wire %s has unknown function %r (expected one of %s)"
            % (wire_id, function, ", ".join(sorted(FUNCTION_BASE_CATEGORY)))
        )
    critical = wire.get("critical", False)
    if not isinstance(critical, bool):
        raise ValueError("wire %s field 'critical' must be a boolean" % wire_id)
    rise_time_us = _numeric("wire %s rise_time_us" % wire_id, wire.get("rise_time_us", 1.0))
    if rise_time_us <= 0:
        raise ValueError("wire %s rise_time_us must be positive" % wire_id)
    return {
        "id": wire_id,
        "function": function,
        "critical": critical,
        "amplitude_v": _numeric("wire %s amplitude_v" % wire_id, wire.get("amplitude_v", 0.0), 0.0),
        "peak_current_a": _numeric(
            "wire %s peak_current_a" % wire_id, wire.get("peak_current_a", 0.0), 0.0
        ),
        "rise_time_us": rise_time_us,
        "source_impedance_ohm": _numeric(
            "wire %s source_impedance_ohm" % wire_id, wire.get("source_impedance_ohm", 50.0), 0.0
        ),
        "construction": wire.get("construction", "single-wire"),
        "redundant_partner_id": wire.get("redundant_partner_id"),
    }


def switching_rates(wire):
    """Return (current-slew A/us, voltage-slew V/us) for one wire."""
    norm = validate_wire(wire)
    didt = norm["peak_current_a"] / norm["rise_time_us"]
    dvdt = norm["amplitude_v"] / norm["rise_time_us"]
    return didt, dvdt


def categorize_wire(wire):
    """Return the electromagnetic category of one wire."""
    norm = validate_wire(wire)
    base = FUNCTION_BASE_CATEGORY[norm["function"]]
    didt, dvdt = switching_rates(norm)
    if didt > SWITCHING_DIDT_LIMIT_A_PER_US or dvdt > SWITCHING_DVDT_LIMIT_V_PER_US:
        return CAT_INTERFERING
    if (
        base == CAT_SIGNAL
        and norm["amplitude_v"] <= SENSITIVE_AMPLITUDE_LIMIT_V
        and norm["source_impedance_ohm"] >= SENSITIVE_SOURCE_IMPEDANCE_OHM
    ):
        return CAT_SENSITIVE
    return base


def required_separation_mm(category_a, category_b):
    """Minimum route separation between two bundles, in millimetres."""
    for cat in (category_a, category_b):
        if cat not in CATEGORIES:
            raise ValueError("unknown wire category %r" % (cat,))
    key = (category_a, category_b)
    if key in SEPARATION_MATRIX_MM:
        return SEPARATION_MATRIX_MM[key]
    return SEPARATION_MATRIX_MM[(category_b, category_a)]


def separation_is_met(actual_mm, required_mm):
    """True when a declared separation satisfies the required one."""
    actual = _numeric("actual_mm", actual_mm, 0.0)
    required = _numeric("required_mm", required_mm, 0.0)
    return actual >= required - SEPARATION_TOLERANCE_MM


def declared_separation_mm(record):
    """Read a route-separation record, summing offset segments if given."""
    if not isinstance(record, dict):
        raise ValueError("route separation record must be a mapping")
    for key in ("route_a", "route_b"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError("route separation record needs a non-empty %s" % key)
    if record["route_a"] == record["route_b"]:
        raise ValueError("route separation record names the same route twice")
    segments = record.get("offset_segments_mm")
    if segments is not None:
        if not isinstance(segments, (list, tuple)) or not segments:
            raise ValueError("offset_segments_mm must be a non-empty sequence")
        total = 0.0
        for seg in segments:
            total += _numeric("offset segment", seg, 0.0)
        return total
    return _numeric("separation_mm", record.get("separation_mm"), 0.0)


def check_critical_line_treatment(wire, route_id, partner_route_id):
    """Findings for the extra treatment a critical line needs."""
    norm = validate_wire(wire)
    findings = []
    if not norm["critical"]:
        return findings
    if norm["construction"] != CRITICAL_CONSTRUCTION:
        findings.append("critical-line-not-twisted-shielded-pair")
    if norm["redundant_partner_id"] is None:
        findings.append("critical-line-has-no-redundant-partner")
    elif partner_route_id is None:
        findings.append("critical-line-redundant-partner-not-routed")
    elif partner_route_id == route_id:
        findings.append("critical-line-shares-route-with-redundant-partner")
    return findings


def check_bundle_composition(bundle, wire_index):
    """Findings for one bundle, plus the categories it carries."""
    if not isinstance(bundle, dict):
        raise ValueError("bundle must be a mapping")
    bundle_id = bundle.get("id")
    if not isinstance(bundle_id, str) or not bundle_id.strip():
        raise ValueError("bundle needs a non-empty string id")
    route_id = bundle.get("route_id")
    if not isinstance(route_id, str) or not route_id.strip():
        raise ValueError("bundle %s needs a non-empty route_id" % bundle_id)
    wire_ids = bundle.get("wire_ids")
    if not isinstance(wire_ids, list) or not wire_ids:
        raise ValueError("bundle %s needs a non-empty wire_ids list" % bundle_id)
    findings = []
    categories = set()
    criticality = set()
    for wid in wire_ids:
        if wid not in wire_index:
            raise ValueError("bundle %s names unknown wire %r" % (bundle_id, wid))
        categories.add(categorize_wire(wire_index[wid]))
        criticality.add(bool(wire_index[wid].get("critical", False)))
    if len(categories) > 1:
        findings.append("bundle-mixes-wire-categories")
    if len(criticality) > 1:
        findings.append("critical-line-bundled-with-noncritical-wire")
    return findings, categories


def check_route_separations(bundle_categories, separation_records):
    """Findings for every pair of bundles routed on different paths."""
    declared = {}
    for record in separation_records:
        value = declared_separation_mm(record)
        key = tuple(sorted((record["route_a"], record["route_b"])))
        declared[key] = value
    findings = []
    items = sorted(bundle_categories.items())
    for i, (bundle_a, info_a) in enumerate(items):
        for bundle_b, info_b in items[i + 1:]:
            route_a, route_b = info_a["route_id"], info_b["route_id"]
            required = 0.0
            for cat_a in info_a["categories"]:
                for cat_b in info_b["categories"]:
                    required = max(required, required_separation_mm(cat_a, cat_b))
            if route_a == route_b:
                if required > 0.0:
                    findings.append(
                        {
                            "bundles": (bundle_a, bundle_b),
                            "required_mm": required,
                            "actual_mm": 0.0,
                            "finding": "categories-share-one-route",
                        }
                    )
                continue
            if required <= 0.0:
                continue
            key = tuple(sorted((route_a, route_b)))
            if key not in declared:
                findings.append(
                    {
                        "bundles": (bundle_a, bundle_b),
                        "required_mm": required,
                        "actual_mm": None,
                        "finding": "route-separation-not-declared",
                    }
                )
                continue
            actual = declared[key]
            if not separation_is_met(actual, required):
                findings.append(
                    {
                        "bundles": (bundle_a, bundle_b),
                        "required_mm": required,
                        "actual_mm": actual,
                        "finding": "insufficient-route-separation",
                    }
                )
    return findings


def assess_harness_categorization(wires, bundles, separation_records=None):
    """Run the full clause 4.2.13.1 assessment over a harness definition."""
    if not isinstance(wires, list) or not wires:
        raise ValueError("wires must be a non-empty list")
    if not isinstance(bundles, list) or not bundles:
        raise ValueError("bundles must be a non-empty list")
    separation_records = separation_records or []
    if not isinstance(separation_records, list):
        raise ValueError("separation_records must be a list")
    wire_index = {}
    for wire in wires:
        norm = validate_wire(wire)
        if norm["id"] in wire_index:
            raise ValueError("duplicate wire id %r" % (norm["id"],))
        wire_index[norm["id"]] = wire
    categories = {wid: categorize_wire(w) for wid, w in wire_index.items()}
    bundle_categories = {}
    bundle_findings = {}
    wire_route = {}
    for bundle in bundles:
        findings, cats = check_bundle_composition(bundle, wire_index)
        if bundle["id"] in bundle_categories:
            raise ValueError("duplicate bundle id %r" % (bundle["id"],))
        bundle_categories[bundle["id"]] = {
            "route_id": bundle["route_id"],
            "categories": cats,
        }
        bundle_findings[bundle["id"]] = findings
        for wid in bundle["wire_ids"]:
            if wid in wire_route:
                raise ValueError("wire %r appears in more than one bundle" % (wid,))
            wire_route[wid] = bundle["route_id"]
    wire_findings = {}
    for wid, wire in wire_index.items():
        findings = []
        if wid not in wire_route:
            findings.append("wire-not-assigned-to-a-bundle")
        partner = wire.get("redundant_partner_id")
        findings.extend(
            check_critical_line_treatment(
                wire, wire_route.get(wid), wire_route.get(partner)
            )
        )
        wire_findings[wid] = findings
    route_findings = check_route_separations(bundle_categories, separation_records)
    compliant = (
        not route_findings
        and all(not f for f in bundle_findings.values())
        and all(not f for f in wire_findings.values())
    )
    return {
        "categories": categories,
        "wire_findings": wire_findings,
        "bundle_findings": bundle_findings,
        "route_findings": route_findings,
        "compliant": compliant,
    }
