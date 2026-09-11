#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.6.4 hardware ergonomics requirements check
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
human factors engineering standard's hardware ergonomics clause covers
four families of items -- controls (push-buttons, switches, rotary
knobs, pedals) with operating-force and torque limits; displays with
minimum and maximum character visual angle and minimum contrast ratio;
handles with payload-capacity limits per grip mode and a minimum grip
clearance; and maintenance access points with minimum opening diameters
by task type. Each item is assigned to a family, then its measured or
specified parameters are checked against the family's quantitative
thresholds. This module implements family assignment, force/torque limit
checking for controls, visual-angle and contrast checking for displays,
payload and grip-clearance checking for handles, and access-opening
diameter checking for maintenance access points; it does not implement
the inadvertent-activation guard assessment, the human factors
verification plan, or crew anthropometry limits.
"""

HARDWARE_ITEM_FAMILIES = frozenset(
    {"control", "display", "handle", "access_point"}
)

CONTROL_TYPES = frozenset(
    {
        "push_button",
        "toggle_switch",
        "rocker_switch",
        "rotary_knob",
        "handle_grip",
        "foot_pedal",
        "keyboard_key",
    }
)

# Maximum operating force (N) or torque (Nm) per control type.
# rotary_knob limit is in Nm; all others are in N.
CONTROL_FORCE_LIMIT = {
    "push_button": 22.2,
    "toggle_switch": 8.9,
    "rocker_switch": 8.9,
    "rotary_knob": 0.56,
    "handle_grip": 111.0,
    "foot_pedal": 89.0,
    "keyboard_key": 3.0,
}

DISPLAY_MIN_CHAR_VISUAL_ANGLE_ARCMIN = 20.0
DISPLAY_MAX_CHAR_VISUAL_ANGLE_ARCMIN = 80.0
DISPLAY_MIN_CONTRAST_RATIO = 3.0

HANDLE_ONE_HAND_MAX_PAYLOAD_N = 111.0
HANDLE_TWO_HAND_MAX_PAYLOAD_N = 222.0
HANDLE_MIN_GRIP_CLEARANCE_MM = 38.0

HANDLE_GRIP_MODES = frozenset({"one_hand", "two_hand"})

# Minimum access opening diameter (mm) by maintenance task type.
MAINTENANCE_ACCESS_MIN_DIAMETER_MM = {
    "finger": 38.0,
    "one_hand": 102.0,
    "two_hand": 152.0,
    "head_and_shoulders": 455.0,
}


def categorize_hardware_item(item_type):
    """Hardware ergonomics family for an item type: one of "control",
    "display", "handle", or "access_point". Raises ValueError for an
    item type outside the known set."""
    if item_type in HARDWARE_ITEM_FAMILIES:
        return item_type
    raise ValueError(
        "unrecognized hardware item type %r under E-ST-10-11C §4.6.4"
        % (item_type,)
    )


def check_control_force_limit(control_type, operating_force):
    """Violation list for a control's operating force or torque.
    operating_force must be >= 0. Returns [] when the value is at or
    below the limit for that control type. Raises ValueError for an
    unrecognized control type or a negative force value."""
    if operating_force < 0:
        raise ValueError("operating_force must be >= 0")
    if control_type not in CONTROL_FORCE_LIMIT:
        raise ValueError(
            "unrecognized control type %r under E-ST-10-11C §4.6.4"
            % (control_type,)
        )
    limit = CONTROL_FORCE_LIMIT[control_type]
    if operating_force > limit:
        return [
            {
                "issue": "control_force_limit_exceeded",
                "control_type": control_type,
                "operating_force": operating_force,
                "limit": limit,
            }
        ]
    return []


def check_display_visual_angle(char_visual_angle_arcmin):
    """Violation list for a display character visual angle (arcmin).
    Returns [] when the angle is within the range
    [DISPLAY_MIN_CHAR_VISUAL_ANGLE_ARCMIN,
    DISPLAY_MAX_CHAR_VISUAL_ANGLE_ARCMIN]. Raises ValueError for a
    negative angle."""
    if char_visual_angle_arcmin < 0:
        raise ValueError("char_visual_angle_arcmin must be >= 0")
    if char_visual_angle_arcmin < DISPLAY_MIN_CHAR_VISUAL_ANGLE_ARCMIN:
        return [
            {
                "issue": "display_char_visual_angle_below_minimum",
                "value_arcmin": char_visual_angle_arcmin,
                "minimum_arcmin": DISPLAY_MIN_CHAR_VISUAL_ANGLE_ARCMIN,
            }
        ]
    if char_visual_angle_arcmin > DISPLAY_MAX_CHAR_VISUAL_ANGLE_ARCMIN:
        return [
            {
                "issue": "display_char_visual_angle_above_maximum",
                "value_arcmin": char_visual_angle_arcmin,
                "maximum_arcmin": DISPLAY_MAX_CHAR_VISUAL_ANGLE_ARCMIN,
            }
        ]
    return []


def check_display_contrast(contrast_ratio):
    """Violation list for a display contrast ratio. Returns [] when
    contrast_ratio >= DISPLAY_MIN_CONTRAST_RATIO. Raises ValueError for
    a negative ratio."""
    if contrast_ratio < 0:
        raise ValueError("contrast_ratio must be >= 0")
    if contrast_ratio < DISPLAY_MIN_CONTRAST_RATIO:
        return [
            {
                "issue": "display_contrast_below_minimum",
                "value": contrast_ratio,
                "minimum": DISPLAY_MIN_CONTRAST_RATIO,
            }
        ]
    return []


def check_handle_requirements(payload_n, grip_mode, grip_clearance_mm):
    """Violation list for a handle: payload limit by grip mode and
    minimum grip clearance. grip_mode must be in HANDLE_GRIP_MODES.
    payload_n and grip_clearance_mm must be >= 0. Raises ValueError for
    an unrecognized grip mode or negative numeric values. Does not
    mutate inputs."""
    if payload_n < 0:
        raise ValueError("payload_n must be >= 0")
    if grip_clearance_mm < 0:
        raise ValueError("grip_clearance_mm must be >= 0")
    if grip_mode not in HANDLE_GRIP_MODES:
        raise ValueError(
            "unrecognized grip mode %r; expected one of %r"
            % (grip_mode, sorted(HANDLE_GRIP_MODES))
        )
    violations = []
    limit = (
        HANDLE_ONE_HAND_MAX_PAYLOAD_N
        if grip_mode == "one_hand"
        else HANDLE_TWO_HAND_MAX_PAYLOAD_N
    )
    if payload_n > limit:
        violations.append(
            {
                "issue": "handle_payload_limit_exceeded",
                "grip_mode": grip_mode,
                "payload_n": payload_n,
                "limit_n": limit,
            }
        )
    if grip_clearance_mm < HANDLE_MIN_GRIP_CLEARANCE_MM:
        violations.append(
            {
                "issue": "handle_grip_clearance_below_minimum",
                "grip_clearance_mm": grip_clearance_mm,
                "minimum_mm": HANDLE_MIN_GRIP_CLEARANCE_MM,
            }
        )
    return violations


def check_maintenance_access(task_type, opening_diameter_mm):
    """Violation list for a maintenance access point.
    opening_diameter_mm must be >= 0. Returns [] when the diameter
    meets or exceeds the minimum for the task type. Raises ValueError
    for an unrecognized task type or a negative diameter."""
    if opening_diameter_mm < 0:
        raise ValueError("opening_diameter_mm must be >= 0")
    if task_type not in MAINTENANCE_ACCESS_MIN_DIAMETER_MM:
        raise ValueError(
            "unrecognized maintenance task type %r under E-ST-10-11C §4.6.4"
            % (task_type,)
        )
    minimum = MAINTENANCE_ACCESS_MIN_DIAMETER_MM[task_type]
    if opening_diameter_mm < minimum:
        return [
            {
                "issue": "maintenance_access_opening_below_minimum",
                "task_type": task_type,
                "opening_diameter_mm": opening_diameter_mm,
                "minimum_mm": minimum,
            }
        ]
    return []


def hw_ergonomics_review(item):
    """Full §4.6.4 hardware ergonomics review for one item.

    item: {"item_id": str, "item_type": str, ...family-specific fields}.

    "control": "control_type" (str), "operating_force" (float >= 0).
    "display": "char_visual_angle_arcmin" (float >= 0),
               "contrast_ratio" (float >= 0).
    "handle":  "payload_n" (float >= 0), "grip_mode" (str),
               "grip_clearance_mm" (float >= 0).
    "access_point": "task_type" (str), "opening_diameter_mm" (float >= 0).

    Returns {"item_id": str, "findings": [...]}, findings empty when
    fully conformant. Raises ValueError for an unrecognized item_type."""
    item_id = item["item_id"]
    item_type = categorize_hardware_item(item["item_type"])
    findings = []
    if item_type == "control":
        findings.extend(
            check_control_force_limit(
                item["control_type"], item["operating_force"]
            )
        )
    elif item_type == "display":
        findings.extend(
            check_display_visual_angle(item["char_visual_angle_arcmin"])
        )
        findings.extend(
            check_display_contrast(item["contrast_ratio"])
        )
    elif item_type == "handle":
        findings.extend(
            check_handle_requirements(
                item["payload_n"], item["grip_mode"], item["grip_clearance_mm"]
            )
        )
    elif item_type == "access_point":
        findings.extend(
            check_maintenance_access(
                item["task_type"], item["opening_diameter_mm"]
            )
        )
    return {"item_id": item_id, "findings": findings}


def is_hw_ergonomics_compliant(review):
    """True when a hw_ergonomics_review result has no findings -- the
    item satisfies all §4.6.4 hardware ergonomics checks."""
    return len(review["findings"]) == 0
