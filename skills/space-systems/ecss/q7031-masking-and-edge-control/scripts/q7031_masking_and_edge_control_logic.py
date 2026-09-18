"""Masking, overspray containment and edge coverage for coating application.

Anchor: ECSS-Q-ST-70-31C, Application. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Size the overspray halo of the spray set-up from the gun stand-off and the
   fan angle, inflated by the fraction of atomised material that drifts
   outside the nominal pattern.
2. Turn that halo into a required masking margin for each keep-out zone,
   scaled by how unforgiving the zone is: an optical surface, a bonding or
   electrical contact face, a sealing land and a plain structural area do not
   earn the same clearance.
3. Compare the declared mask footprint margin of each zone with the required
   margin and name every zone whose mask is short.
4. Grade edge coverage separately, because a convex edge holds less film than
   the flat next to it. The retained fraction rises with edge radius from a
   sharp-edge floor toward the flat value, and where the retained thickness
   misses the edge minimum the number of stripe coats needed is derived.
5. Return one containment verdict with every finding named.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_MM",
    "CRITICALITY_SAFETY_FACTORS",
    "SHARP_EDGE_RETENTION",
    "CHARACTERISTIC_EDGE_RADIUS_MM",
    "validate_positive",
    "validate_fraction",
    "criticality_safety_factor",
    "overspray_halo_mm",
    "required_mask_margin_mm",
    "assess_zone",
    "edge_retention_factor",
    "edge_dry_thickness_um",
    "stripe_coats_required",
    "assess_edge",
    "assess_masking_plan",
]

# A mask margin can be drawn exactly on the required value. Absorb the
# representation error here, never by shaving the required margin.
MARGIN_TOLERANCE_MM = 1e-9

# How much clearance a keep-out zone earns, relative to the bare halo.
CRITICALITY_SAFETY_FACTORS = {
    "optical": 3.0,
    "bonding-electrical": 2.0,
    "sealing": 1.5,
    "general": 1.0,
}

# Fraction of the flat-surface film a perfectly sharp edge retains.
SHARP_EDGE_RETENTION = 0.30

# Edge radius at which half the shortfall to the flat value is recovered.
CHARACTERISTIC_EDGE_RADIUS_MM = 0.50


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_positive(value, label):
    """Return a validated strictly positive float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def validate_fraction(value, label, upper=1.0):
    """Return a validated fraction in [0, upper]."""
    out = _real(value, label)
    if out < 0.0 or out > upper:
        raise ValueError("%s must lie in [0, %g], got %g" % (label, upper, out))
    return out


def criticality_safety_factor(criticality):
    """Return the clearance multiplier for a keep-out zone category."""
    if not isinstance(criticality, str):
        raise ValueError("criticality must be a string, got %r" % (criticality,))
    key = criticality.strip().lower()
    if key not in CRITICALITY_SAFETY_FACTORS:
        raise ValueError(
            "unknown criticality '%s'; known categories: %s"
            % (criticality, ", ".join(sorted(CRITICALITY_SAFETY_FACTORS)))
        )
    return CRITICALITY_SAFETY_FACTORS[key]


def overspray_halo_mm(gun_distance_mm, fan_angle_deg, overspray_fraction=0.0):
    """Return the radius of the sprayed halo around the aimed pattern."""
    distance = validate_positive(gun_distance_mm, "gun_distance_mm")
    angle = _real(fan_angle_deg, "fan_angle_deg")
    if angle <= 0.0 or angle >= 180.0:
        raise ValueError("fan_angle_deg must lie in (0, 180), got %g" % angle)
    drift = validate_fraction(overspray_fraction, "overspray_fraction", upper=5.0)
    half_width = distance * math.tan(math.radians(angle) / 2.0)
    return half_width * (1.0 + drift)


def required_mask_margin_mm(halo_mm, criticality="general"):
    """Return the masking margin a zone of that criticality requires."""
    halo = validate_positive(halo_mm, "halo_mm")
    return halo * criticality_safety_factor(criticality)


def assess_zone(zone, halo_mm):
    """Grade one keep-out zone's declared mask footprint against the halo."""
    if not isinstance(zone, dict):
        raise ValueError("zone must be a mapping")
    for key in ("name", "criticality", "declared_mask_margin_mm"):
        if key not in zone:
            raise ValueError("zone missing required key '%s'" % key)
    name = str(zone["name"])
    required = required_mask_margin_mm(halo_mm, zone["criticality"])
    declared = _real(zone["declared_mask_margin_mm"], "declared_mask_margin_mm")
    if declared < 0.0:
        raise ValueError("declared_mask_margin_mm must be non-negative, got %g" % declared)
    adequate = declared >= required - MARGIN_TOLERANCE_MM
    findings = []
    if not adequate:
        findings.append(
            "%s: mask margin %.2f mm is short of the %.2f mm its category requires"
            % (name, declared, required)
        )
    return {
        "name": name,
        "criticality": str(zone["criticality"]).strip().lower(),
        "required_margin_mm": required,
        "declared_margin_mm": declared,
        "shortfall_mm": max(0.0, required - declared),
        "adequate": adequate,
        "findings": findings,
    }


def edge_retention_factor(edge_radius_mm):
    """Return the fraction of the flat film a convex edge of that radius holds."""
    radius = _real(edge_radius_mm, "edge_radius_mm")
    if radius < 0.0:
        raise ValueError("edge_radius_mm must be non-negative, got %g" % radius)
    recovered = radius / (radius + CHARACTERISTIC_EDGE_RADIUS_MM)
    return SHARP_EDGE_RETENTION + (1.0 - SHARP_EDGE_RETENTION) * recovered


def edge_dry_thickness_um(nominal_dft_um, edge_radius_mm):
    """Return the dry film thickness retained on an edge of that radius."""
    nominal = validate_positive(nominal_dft_um, "nominal_dft_um")
    return nominal * edge_retention_factor(edge_radius_mm)


def stripe_coats_required(nominal_dft_um, edge_radius_mm, min_edge_dft_um):
    """Return how many extra stripe coats the edge needs to reach its minimum."""
    nominal = validate_positive(nominal_dft_um, "nominal_dft_um")
    minimum = validate_positive(min_edge_dft_um, "min_edge_dft_um")
    per_coat = edge_dry_thickness_um(nominal, edge_radius_mm)
    if per_coat >= minimum - MARGIN_TOLERANCE_MM:
        return 0
    deficit = minimum - per_coat
    return int(math.ceil(deficit / per_coat - MARGIN_TOLERANCE_MM))


def assess_edge(edge, nominal_dft_um, min_edge_dft_um):
    """Grade one edge feature for retained coverage."""
    if not isinstance(edge, dict):
        raise ValueError("edge must be a mapping")
    for key in ("name", "edge_radius_mm"):
        if key not in edge:
            raise ValueError("edge missing required key '%s'" % key)
    name = str(edge["name"])
    retained = edge_dry_thickness_um(nominal_dft_um, edge["edge_radius_mm"])
    minimum = validate_positive(min_edge_dft_um, "min_edge_dft_um")
    covered = retained >= minimum - MARGIN_TOLERANCE_MM
    stripes = stripe_coats_required(nominal_dft_um, edge["edge_radius_mm"], minimum)
    findings = []
    if not covered:
        findings.append(
            "%s: edge retains %.2f um against a %.2f um minimum; %d stripe coat(s) needed"
            % (name, retained, minimum, stripes)
        )
    return {
        "name": name,
        "edge_radius_mm": _real(edge["edge_radius_mm"], "edge_radius_mm"),
        "retention_factor": edge_retention_factor(edge["edge_radius_mm"]),
        "retained_dft_um": retained,
        "min_edge_dft_um": minimum,
        "stripe_coats_required": stripes,
        "covered": covered,
        "findings": findings,
    }


def assess_masking_plan(spec):
    """Run the full masking, overspray and edge-coverage assessment.

    spec keys: gun_distance_mm, fan_angle_deg, zones; optional
    overspray_fraction, edges, nominal_dft_um, min_edge_dft_um.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("gun_distance_mm", "fan_angle_deg", "zones"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    zones = spec["zones"]
    if not isinstance(zones, (list, tuple)) or not zones:
        raise ValueError("spec['zones'] must be a non-empty sequence of keep-out zones")
    halo = overspray_halo_mm(
        spec["gun_distance_mm"], spec["fan_angle_deg"], spec.get("overspray_fraction", 0.0)
    )
    findings = []
    zone_records = []
    seen = set()
    for zone in zones:
        record = assess_zone(zone, halo)
        if record["name"] in seen:
            raise ValueError("duplicate keep-out zone name '%s'" % record["name"])
        seen.add(record["name"])
        zone_records.append(record)
        findings.extend(record["findings"])

    edge_records = []
    edges = spec.get("edges")
    if edges:
        if "nominal_dft_um" not in spec or "min_edge_dft_um" not in spec:
            raise ValueError(
                "edge grading needs both 'nominal_dft_um' and 'min_edge_dft_um'"
            )
        for edge in edges:
            record = assess_edge(edge, spec["nominal_dft_um"], spec["min_edge_dft_um"])
            edge_records.append(record)
            findings.extend(record["findings"])

    return {
        "overspray_halo_mm": halo,
        "zones": zone_records,
        "edges": edge_records,
        "findings": findings,
        "contained": not findings,
    }
