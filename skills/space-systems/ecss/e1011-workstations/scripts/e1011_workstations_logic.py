#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.7.6 workstation design assessment
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human-factors standard's workstation clause requires each display and
control to be categorized into an access-frequency zone (primary,
secondary, or tertiary) and verified against that zone's viewing-angle
limits from the Eye Reference Point (ERP), reach-radius limits from the
Shoulder Reference Point (SRP), and each access path to the workstation
verified against ingress/egress clearance minimums (clear width and clear
height, varying by access mode). Primary zone elements must lie within
functional reach and the preferred viewing field; secondary zone elements
extend to maximum reach and the acceptable viewing field; tertiary zone
elements require crew repositioning and carry no fixed reach radius.
Access paths are checked for three modes: normal operational, maintenance,
and emergency egress, each with its own minimum width and height.
"""

VALID_ZONES = frozenset({"primary", "secondary", "tertiary"})
VALID_ACCESS_MODES = frozenset(
    {"normal_operational", "maintenance", "emergency_egress"}
)

# Viewing-angle and viewing-distance limits per zone (degrees / mm).
# h_max: maximum absolute horizontal deviation from straight ahead.
# v_min/v_max: vertical range; 0 = horizontal, negative = below horizontal.
# dist_min_mm/dist_max_mm: minimum and maximum acceptable viewing distance.
VIEWING_LIMITS = {
    "primary": {
        "h_max": 30.0,
        "v_min": -30.0,
        "v_max": 0.0,
        "dist_min_mm": 300.0,
        "dist_max_mm": 750.0,
    },
    "secondary": {
        "h_max": 60.0,
        "v_min": -60.0,
        "v_max": 10.0,
        "dist_min_mm": 300.0,
        "dist_max_mm": 750.0,
    },
    "tertiary": {
        "h_max": 90.0,
        "v_min": -90.0,
        "v_max": 30.0,
        "dist_min_mm": 200.0,
        "dist_max_mm": 1000.0,
    },
}

# Maximum reach radius per zone (mm from Shoulder Reference Point).
# None for tertiary: repositioning is accepted, no radius cap applies.
REACH_LIMIT_MM = {
    "primary": 400.0,
    "secondary": 650.0,
    "tertiary": None,
}

# Minimum clear dimensions per ingress/egress access mode (mm).
ACCESS_CLEARANCE_MM = {
    "normal_operational": {"width": 550, "height": 1800},
    "maintenance": {"width": 500, "height": 1500},
    "emergency_egress": {"width": 450, "height": 1400},
}


def categorize_zone(zone):
    """Return zone if it is a recognized access-frequency zone string,
    otherwise raise ValueError. Valid: 'primary', 'secondary', 'tertiary'."""
    if zone not in VALID_ZONES:
        raise ValueError(
            "unrecognized workstation zone %r; expected one of %s"
            % (zone, sorted(VALID_ZONES))
        )
    return zone


def check_display_viewing(zone, h_angle_deg, v_angle_deg, distance_mm):
    """Check a display's viewing geometry against §4.7.6 zone limits.

    zone: 'primary' | 'secondary' | 'tertiary'.
    h_angle_deg: horizontal deviation from straight ahead (sign ignored, absolute
        value is compared to limit).
    v_angle_deg: vertical deviation from horizontal (0 = horizontal,
        negative = below, positive = above).
    distance_mm: distance from Eye Reference Point to display surface (mm).
    Returns a list of finding dicts (empty = compliant). Raises ValueError
    for an unrecognized zone or negative distance."""
    categorize_zone(zone)
    if distance_mm < 0:
        raise ValueError("distance_mm must be >= 0, got %r" % distance_mm)
    limits = VIEWING_LIMITS[zone]
    findings = []
    if abs(h_angle_deg) > limits["h_max"]:
        findings.append(
            {
                "issue": "horizontal_viewing_angle_exceeded",
                "zone": zone,
                "h_angle_deg": h_angle_deg,
                "limit_deg": limits["h_max"],
            }
        )
    if v_angle_deg < limits["v_min"] or v_angle_deg > limits["v_max"]:
        findings.append(
            {
                "issue": "vertical_viewing_angle_exceeded",
                "zone": zone,
                "v_angle_deg": v_angle_deg,
                "v_min_deg": limits["v_min"],
                "v_max_deg": limits["v_max"],
            }
        )
    if distance_mm < limits["dist_min_mm"]:
        findings.append(
            {
                "issue": "viewing_distance_below_minimum",
                "zone": zone,
                "distance_mm": distance_mm,
                "min_mm": limits["dist_min_mm"],
            }
        )
    if distance_mm > limits["dist_max_mm"]:
        findings.append(
            {
                "issue": "viewing_distance_above_maximum",
                "zone": zone,
                "distance_mm": distance_mm,
                "max_mm": limits["dist_max_mm"],
            }
        )
    return findings


def check_control_reach(zone, reach_mm):
    """Check a control's reach distance against §4.7.6 zone limits.

    zone: 'primary' | 'secondary' | 'tertiary'.
    reach_mm: distance from Shoulder Reference Point to control actuation
        point (mm).
    Returns a list of finding dicts (empty = compliant). Tertiary zone
    always returns [] because crew repositioning is expected and accepted.
    Raises ValueError for an unrecognized zone or negative distance."""
    categorize_zone(zone)
    if reach_mm < 0:
        raise ValueError("reach_mm must be >= 0, got %r" % reach_mm)
    limit = REACH_LIMIT_MM[zone]
    if limit is None:
        return []
    if reach_mm > limit:
        return [
            {
                "issue": "reach_envelope_exceeded",
                "zone": zone,
                "reach_mm": reach_mm,
                "limit_mm": limit,
            }
        ]
    return []


def check_access_path(mode, width_mm, height_mm):
    """Check an ingress/egress access path against §4.7.6 clearance minimums.

    mode: 'normal_operational' | 'maintenance' | 'emergency_egress'.
    width_mm: clear width of the access path (mm).
    height_mm: clear height of the access path (mm).
    Returns a list of finding dicts (empty = compliant). Raises ValueError
    for an unrecognized mode or negative dimension."""
    if mode not in VALID_ACCESS_MODES:
        raise ValueError(
            "unrecognized access mode %r; expected one of %s"
            % (mode, sorted(VALID_ACCESS_MODES))
        )
    if width_mm < 0:
        raise ValueError("width_mm must be >= 0, got %r" % width_mm)
    if height_mm < 0:
        raise ValueError("height_mm must be >= 0, got %r" % height_mm)
    mins = ACCESS_CLEARANCE_MM[mode]
    findings = []
    if width_mm < mins["width"]:
        findings.append(
            {
                "issue": "access_width_below_minimum",
                "mode": mode,
                "width_mm": width_mm,
                "min_mm": mins["width"],
            }
        )
    if height_mm < mins["height"]:
        findings.append(
            {
                "issue": "access_height_below_minimum",
                "mode": mode,
                "height_mm": height_mm,
                "min_mm": mins["height"],
            }
        )
    return findings


def workstation_review(workstation):
    """Full §4.7.6 workstation design review.

    workstation: {
      "workstation_id": str,
      "displays": [
        {"display_id": str, "zone": str, "h_angle_deg": float,
         "v_angle_deg": float, "distance_mm": float},
        ...
      ],
      "controls": [
        {"control_id": str, "zone": str, "reach_mm": float},
        ...
      ],
      "access_paths": [
        {"path_id": str, "mode": str, "width_mm": float, "height_mm": float},
        ...
      ],
    }
    Returns {
      "workstation_id": str,
      "display_findings": [...],
      "reach_findings": [...],
      "access_findings": [...],
    }.
    Raises ValueError for any unrecognized zone or access mode.
    Does not mutate the input workstation dict."""
    ws_id = workstation["workstation_id"]

    display_findings = []
    for disp in workstation.get("displays", []):
        found = check_display_viewing(
            disp["zone"],
            disp["h_angle_deg"],
            disp["v_angle_deg"],
            disp["distance_mm"],
        )
        for f in found:
            display_findings.append(dict(f, display_id=disp["display_id"]))

    reach_findings = []
    for ctrl in workstation.get("controls", []):
        found = check_control_reach(ctrl["zone"], ctrl["reach_mm"])
        for f in found:
            reach_findings.append(dict(f, control_id=ctrl["control_id"]))

    access_findings = []
    for path in workstation.get("access_paths", []):
        found = check_access_path(path["mode"], path["width_mm"], path["height_mm"])
        for f in found:
            access_findings.append(dict(f, path_id=path["path_id"]))

    return {
        "workstation_id": ws_id,
        "display_findings": display_findings,
        "reach_findings": reach_findings,
        "access_findings": access_findings,
    }


def is_workstation_compliant(review):
    """True when all three finding lists in a workstation_review result are
    empty — the workstation satisfies §4.7.6 for this assessment."""
    return (
        len(review.get("display_findings", [])) == 0
        and len(review.get("reach_findings", [])) == 0
        and len(review.get("access_findings", [])) == 0
    )
