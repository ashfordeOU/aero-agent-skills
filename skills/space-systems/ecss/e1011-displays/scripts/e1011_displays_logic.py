"""
ECSS-E-ST-10-11C §4.9.4 — Display design compliance logic.

Deterministic, offline, stdlib only.
Implements display format validation, information-density checks, and
alarm-presentation verification per the HFE display design rules.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_FONT_SIZE_PT = 10          # minimum readable font size (points)
MIN_CONTRAST_RATIO = 4.5       # minimum luminance contrast ratio (WCAG AA floor)
MAX_PARAMETERS_DEFAULT = 15    # default maximum parameters per display
MAX_VISIBLE_ALARMS_DEFAULT = 12  # default maximum simultaneously visible alarms

# Approved display layout types
_APPROVED_LAYOUT_TYPES = frozenset([
    "list",
    "graphical",
    "schematic",
    "alphanumeric",
    "combined",
])

# Alarm priority levels (ordered from least to most severe)
_ALARM_PRIORITIES = ("advisory", "caution", "warning", "emergency")

# Alarm state machine states
_ALARM_STATES = frozenset(["normal", "active", "acknowledged", "suppressed"])

# Priority levels requiring both visual and auditory cues when active
_HIGH_PRIORITY_THRESHOLD = frozenset(["warning", "emergency"])


# ---------------------------------------------------------------------------
# Display format validation
# ---------------------------------------------------------------------------

def validate_display_format(display):
    """
    Verify a single display entry against HFE §4.9.4 format requirements.

    Parameters
    ----------
    display : dict with required keys:
        display_id    : str   — unique display identifier
        layout_type   : str   — one of the approved layout types
        font_size_pt  : int or float  — rendered font size in points
        contrast_ratio: float — luminance contrast ratio (text vs background)

    Returns
    -------
    dict with keys:
        display_id  : str
        layout_type : str
        compliant   : bool
        findings    : list[str]

    Raises
    ------
    TypeError  if field types are wrong
    ValueError if required keys are missing
    """
    required_keys = {"display_id", "layout_type", "font_size_pt", "contrast_ratio"}
    missing = required_keys - set(display.keys())
    if missing:
        raise ValueError(f"display dict missing required keys: {sorted(missing)}")

    display_id = display["display_id"]
    layout_type = display["layout_type"]
    font_size_pt = display["font_size_pt"]
    contrast_ratio = display["contrast_ratio"]

    if not isinstance(display_id, str):
        raise TypeError(f"display_id must be str, got {type(display_id).__name__}")
    if not isinstance(layout_type, str):
        raise TypeError(f"layout_type must be str, got {type(layout_type).__name__}")
    if not isinstance(font_size_pt, (int, float)):
        raise TypeError(
            f"font_size_pt must be int or float, got {type(font_size_pt).__name__}"
        )
    if not isinstance(contrast_ratio, (int, float)):
        raise TypeError(
            f"contrast_ratio must be int or float, got {type(contrast_ratio).__name__}"
        )

    findings = []

    if not display_id.strip():
        findings.append("display_id is empty")

    if layout_type.lower().strip() not in _APPROVED_LAYOUT_TYPES:
        findings.append(
            f"layout_type '{layout_type}' is not in the approved set: "
            f"{sorted(_APPROVED_LAYOUT_TYPES)}"
        )

    if font_size_pt < MIN_FONT_SIZE_PT:
        findings.append(
            f"font_size_pt {font_size_pt} is below the HFE minimum of {MIN_FONT_SIZE_PT} pt"
        )

    if contrast_ratio < MIN_CONTRAST_RATIO:
        findings.append(
            f"contrast_ratio {contrast_ratio} is below the HFE minimum of {MIN_CONTRAST_RATIO}"
        )

    return {
        "display_id": display_id,
        "layout_type": layout_type,
        "compliant": len(findings) == 0,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Display density validation
# ---------------------------------------------------------------------------

def validate_display_density(
    display_id,
    parameter_count,
    alarm_count_visible,
    max_parameters=MAX_PARAMETERS_DEFAULT,
    max_visible_alarms=MAX_VISIBLE_ALARMS_DEFAULT,
):
    """
    Verify that a display's information density does not exceed HFE limits.

    Parameters
    ----------
    display_id          : str  — display identifier
    parameter_count     : int  — number of simultaneously shown parameters
    alarm_count_visible : int  — number of simultaneously visible alarms
    max_parameters      : int  — project parameter limit (default 15)
    max_visible_alarms  : int  — project visible-alarm limit (default 12)

    Returns
    -------
    dict with keys:
        display_id          : str
        parameter_count     : int
        alarm_count_visible : int
        compliant           : bool
        findings            : list[str]

    Raises
    ------
    TypeError  if types are wrong
    ValueError if counts or limits are negative
    """
    if not isinstance(display_id, str):
        raise TypeError(f"display_id must be str, got {type(display_id).__name__}")
    if not isinstance(parameter_count, int):
        raise TypeError(
            f"parameter_count must be int, got {type(parameter_count).__name__}"
        )
    if not isinstance(alarm_count_visible, int):
        raise TypeError(
            f"alarm_count_visible must be int, got {type(alarm_count_visible).__name__}"
        )
    if not isinstance(max_parameters, int) or max_parameters <= 0:
        raise ValueError(
            f"max_parameters must be a positive int, got {max_parameters!r}"
        )
    if not isinstance(max_visible_alarms, int) or max_visible_alarms <= 0:
        raise ValueError(
            f"max_visible_alarms must be a positive int, got {max_visible_alarms!r}"
        )
    if parameter_count < 0:
        raise ValueError(
            f"parameter_count must be >= 0, got {parameter_count}"
        )
    if alarm_count_visible < 0:
        raise ValueError(
            f"alarm_count_visible must be >= 0, got {alarm_count_visible}"
        )

    findings = []

    if parameter_count > max_parameters:
        findings.append(
            f"parameter_count {parameter_count} exceeds the project limit of "
            f"{max_parameters}"
        )

    if alarm_count_visible > max_visible_alarms:
        findings.append(
            f"alarm_count_visible {alarm_count_visible} exceeds the project limit of "
            f"{max_visible_alarms}"
        )

    return {
        "display_id": display_id,
        "parameter_count": parameter_count,
        "alarm_count_visible": alarm_count_visible,
        "compliant": len(findings) == 0,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Alarm presentation validation
# ---------------------------------------------------------------------------

def validate_alarm_entry(alarm):
    """
    Verify an alarm entry against HFE §4.9.4 alarm presentation requirements.

    Parameters
    ----------
    alarm : dict with required keys:
        alarm_id           : str  — unique alarm identifier
        priority           : str  — one of 'advisory', 'caution', 'warning', 'emergency'
        state              : str  — one of 'normal', 'active', 'acknowledged', 'suppressed'
        visual_distinct    : bool — whether the alarm is visually distinct from nominal
        auditory_distinct  : bool — whether an auditory signal is present
        suppression_visible: bool — whether a suppression indicator is visible

    Returns
    -------
    dict with keys:
        alarm_id  : str
        priority  : str
        state     : str
        compliant : bool
        findings  : list[str]

    Raises
    ------
    TypeError  if field types are wrong
    ValueError if required keys are missing or priority/state is unknown
    """
    required_keys = {
        "alarm_id", "priority", "state",
        "visual_distinct", "auditory_distinct", "suppression_visible",
    }
    missing = required_keys - set(alarm.keys())
    if missing:
        raise ValueError(f"alarm dict missing required keys: {sorted(missing)}")

    alarm_id = alarm["alarm_id"]
    priority = alarm["priority"]
    state = alarm["state"]
    visual_distinct = alarm["visual_distinct"]
    auditory_distinct = alarm["auditory_distinct"]
    suppression_visible = alarm["suppression_visible"]

    if not isinstance(alarm_id, str):
        raise TypeError("alarm['alarm_id'] must be str")
    if not isinstance(priority, str):
        raise TypeError("alarm['priority'] must be str")
    if not isinstance(state, str):
        raise TypeError("alarm['state'] must be str")
    if not isinstance(visual_distinct, bool):
        raise TypeError("alarm['visual_distinct'] must be bool")
    if not isinstance(auditory_distinct, bool):
        raise TypeError("alarm['auditory_distinct'] must be bool")
    if not isinstance(suppression_visible, bool):
        raise TypeError("alarm['suppression_visible'] must be bool")

    if priority not in _ALARM_PRIORITIES:
        raise ValueError(
            f"priority '{priority}' is not valid; must be one of {_ALARM_PRIORITIES}"
        )
    if state not in _ALARM_STATES:
        raise ValueError(
            f"state '{state}' is not valid; must be one of {sorted(_ALARM_STATES)}"
        )

    findings = []

    if state == "active" and priority in _HIGH_PRIORITY_THRESHOLD:
        if not visual_distinct:
            findings.append(
                f"active '{priority}' alarm requires visual_distinct=True"
            )
        if not auditory_distinct:
            findings.append(
                f"active '{priority}' alarm requires auditory_distinct=True"
            )

    if priority == "emergency" and state == "suppressed":
        findings.append(
            "emergency alarms cannot enter the suppressed state; "
            "they must remain visible at all times"
        )

    if state == "suppressed" and not suppression_visible:
        findings.append(
            "suppressed alarm requires suppression_visible=True "
            "so operators are aware the condition is masked"
        )

    return {
        "alarm_id": alarm_id,
        "priority": priority,
        "state": state,
        "compliant": len(findings) == 0,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Aggregate assessment
# ---------------------------------------------------------------------------

def assess_display(format_spec, density_spec, alarms):
    """
    Run the full §4.9.4 assessment over one display's format, density, and alarms.

    Parameters
    ----------
    format_spec  : dict  — as required by validate_display_format
    density_spec : dict  — as required by validate_display_density (positional args
                           are passed as keyword args extracted from the dict)
    alarms       : list[dict]  — each dict as required by validate_alarm_entry

    Returns
    -------
    dict with keys:
        format_result    : dict
        density_result   : dict
        alarm_results    : list[dict]
        overall_compliant: bool
        total_findings   : int
    """
    if not isinstance(format_spec, dict):
        raise TypeError("format_spec must be a dict")
    if not isinstance(density_spec, dict):
        raise TypeError("density_spec must be a dict")
    if not isinstance(alarms, list):
        raise TypeError("alarms must be a list")

    format_result = validate_display_format(format_spec)

    density_result = validate_display_density(
        display_id=density_spec["display_id"],
        parameter_count=density_spec["parameter_count"],
        alarm_count_visible=density_spec["alarm_count_visible"],
        max_parameters=density_spec.get("max_parameters", MAX_PARAMETERS_DEFAULT),
        max_visible_alarms=density_spec.get("max_visible_alarms", MAX_VISIBLE_ALARMS_DEFAULT),
    )

    alarm_results = [validate_alarm_entry(a) for a in alarms]

    total = (
        len(format_result["findings"])
        + len(density_result["findings"])
        + sum(len(r["findings"]) for r in alarm_results)
    )

    return {
        "format_result": format_result,
        "density_result": density_result,
        "alarm_results": alarm_results,
        "overall_compliant": total == 0,
        "total_findings": total,
    }
