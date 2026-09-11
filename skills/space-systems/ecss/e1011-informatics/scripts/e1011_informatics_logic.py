#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.8 on-board informatics support for HFE (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
HFE standard's informatics clause covers on-board data systems, software
user interfaces, and automation support for crewed space systems. Display
elements are grouped by function (numerical readout, graphical trend,
status text, alert indicator, or crew control); each carries minimum
legibility requirements (luminance contrast ratio, character height). Alert
indicators are tiered by urgency — warning (immediate crew action, high
hazard within seconds), caution (timely action, moderate-to-high hazard
within minutes), and advisory (awareness only) — and the declared tier must
match the hazard severity and time-criticality pairing. Automation is
assigned one of four authority levels (advisory, shared_control, supervisory,
autonomous); at supervisory and autonomous levels the crew must retain an
override capability. This module implements display element type checking,
alert urgency determination, display format compliance, automation authority
assessment, and workstation-level aggregation; it does not define
human-performance limits, lighting environment models, or crew workload
budgets.
"""

DISPLAY_ELEMENT_TYPES = frozenset({
    "numerical", "graphical", "status_text", "alert", "control"
})

ALERT_LEVELS = frozenset({"advisory", "caution", "warning"})

AUTOMATION_AUTHORITY_LEVELS = frozenset({
    "advisory",       # system recommends; crew decides and acts
    "shared_control", # crew and system jointly execute
    "supervisory",    # crew sets goals; system executes steps
    "autonomous",     # system acts without crew input
})

_VALID_SEVERITIES = frozenset({"low", "medium", "high"})
_VALID_CRITICALITIES = frozenset({"seconds", "minutes", "hours", "none"})

MIN_CONTRAST_RATIO = 4.5   # minimum luminance contrast ratio for text legibility
MIN_CHAR_HEIGHT_MM = 3.5   # minimum character height at viewing distance up to 700 mm


def categorize_display_element(element_type):
    """Return element_type unchanged after confirming it is a recognized
    display element category under E-ST-10-11C §4.8. Raises ValueError
    for any type outside the known set."""
    if element_type in DISPLAY_ELEMENT_TYPES:
        return element_type
    raise ValueError(
        "unrecognized display element type %r under E-ST-10-11C §4.8" % (element_type,)
    )


def determine_alert_level(hazard_severity, time_criticality):
    """Map hazard severity and time criticality to an alert urgency tier.

    hazard_severity: "low" | "medium" | "high"
    time_criticality: "seconds" | "minutes" | "hours" | "none"

    Returns "warning", "caution", or "advisory". Raises ValueError for
    any unrecognized input.

    Mapping (paraphrased from E-ST-10-11C §4.8 alert-tier guidance):
    - warning  : high severity + action required within seconds
    - caution  : high or medium severity + action required within seconds or minutes
    - advisory : all other combinations
    """
    if hazard_severity not in _VALID_SEVERITIES:
        raise ValueError("unrecognized hazard_severity %r" % (hazard_severity,))
    if time_criticality not in _VALID_CRITICALITIES:
        raise ValueError("unrecognized time_criticality %r" % (time_criticality,))
    if hazard_severity == "high" and time_criticality == "seconds":
        return "warning"
    if hazard_severity in ("high", "medium") and time_criticality in ("seconds", "minutes"):
        return "caution"
    return "advisory"


def check_display_format(contrast_ratio, char_height_mm):
    """Return a list of format violations for a single display element.
    An empty list means the element meets both legibility thresholds.
    Raises ValueError for negative inputs."""
    if contrast_ratio < 0:
        raise ValueError("contrast_ratio must be >= 0")
    if char_height_mm < 0:
        raise ValueError("char_height_mm must be >= 0")
    violations = []
    if contrast_ratio < MIN_CONTRAST_RATIO:
        violations.append({
            "issue": "contrast_below_minimum",
            "contrast_ratio": contrast_ratio,
            "minimum": MIN_CONTRAST_RATIO,
        })
    if char_height_mm < MIN_CHAR_HEIGHT_MM:
        violations.append({
            "issue": "char_height_below_minimum",
            "char_height_mm": char_height_mm,
            "minimum_mm": MIN_CHAR_HEIGHT_MM,
        })
    return violations


def assess_automation_authority(authority_level, crew_override_available):
    """Return a list of violations for one automation function assignment.
    At supervisory and autonomous authority levels, a crew override
    capability is mandatory; its absence is flagged. Raises ValueError
    for an unrecognized authority level."""
    if authority_level not in AUTOMATION_AUTHORITY_LEVELS:
        raise ValueError(
            "unrecognized automation authority level %r under E-ST-10-11C §4.8"
            % (authority_level,)
        )
    violations = []
    if authority_level in ("supervisory", "autonomous") and not crew_override_available:
        violations.append({
            "issue": "missing_crew_override",
            "authority_level": authority_level,
        })
    return violations


def check_workstation_information(workstation):
    """Full §4.8 informatics review for one crew workstation.

    workstation dict keys:
      "workstation_id"   : str — unique identifier
      "display_elements" : list of {"type": str, "contrast_ratio": float,
                           "char_height_mm": float}
      "alerts"           : list of {"hazard_severity": str,
                           "time_criticality": str, "declared_level": str}
      "automation"       : list of {"authority_level": str,
                           "crew_override_available": bool}

    Returns:
      {"format_violations": [...], "alert_level_mismatches": [...],
       "automation_violations": [...]}

    Raises ValueError for an unrecognized display element type,
    hazard severity, time criticality, or automation authority level.
    Does not mutate the input dict.
    """
    wid = workstation["workstation_id"]

    format_violations = []
    for elem in workstation.get("display_elements", []):
        categorize_display_element(elem["type"])
        for v in check_display_format(elem["contrast_ratio"], elem["char_height_mm"]):
            entry = dict(v)
            entry["workstation"] = wid
            format_violations.append(entry)

    alert_level_mismatches = []
    for alert in workstation.get("alerts", []):
        expected = determine_alert_level(
            alert["hazard_severity"], alert["time_criticality"]
        )
        if expected != alert["declared_level"]:
            alert_level_mismatches.append({
                "issue": "alert_level_mismatch",
                "workstation": wid,
                "expected": expected,
                "declared": alert["declared_level"],
            })

    automation_violations = []
    for auto in workstation.get("automation", []):
        for v in assess_automation_authority(
            auto["authority_level"], auto["crew_override_available"]
        ):
            entry = dict(v)
            entry["workstation"] = wid
            automation_violations.append(entry)

    return {
        "format_violations": format_violations,
        "alert_level_mismatches": alert_level_mismatches,
        "automation_violations": automation_violations,
    }


def is_informatics_compliant(review):
    """True when all violation lists in a check_workstation_information
    result are empty — the workstation satisfies §4.8 for this assessment."""
    return all(len(v) == 0 for v in review.values())
