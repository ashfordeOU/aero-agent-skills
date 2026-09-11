#!/usr/bin/env python3
"""ECSS-E-ST-10C §4.4.1 test conditions definition and validation
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
space engineering system test standard requires that test conditions be
defined and confirmed before any verification test begins. These
conditions span five areas: ambient environment (temperature, pressure,
humidity, EMI floor), cleanliness class per ISO 14644-1 for each test
area, electrostatic discharge (ESD) protection controls for each item
sensitive to ESD damage, the configuration state and interface
definitions for the unit under test, and the monitoring channel set
with recording rates and acceptance limits. Each condition element is
evaluated and categorized as compliant or non-compliant; a missing
mandatory condition is itself a finding; and the full set must be
confirmed before test execution begins. This module implements the
categorization and validation logic for all five areas.
"""

# Ambient environment condition status values
CONDITION_COMPLIANT = "compliant"
CONDITION_NON_COMPLIANT = "non_compliant"

# Recognized ISO 14644-1 cleanliness classes; lower number is stricter
VALID_CLEANLINESS_CLASSES = frozenset(
    {"ISO1", "ISO2", "ISO3", "ISO4", "ISO5", "ISO6", "ISO7", "ISO8", "ISO9"}
)

# ESD protection controls required in an ESD-controlled area
REQUIRED_ESD_CONTROLS = frozenset(
    {"esd_wrist_strap", "esd_mat", "esd_area_signage"}
)


def categorize_environment_condition(param_name, value, low_limit, high_limit):
    """Categorize an ambient environment parameter as CONDITION_COMPLIANT or
    CONDITION_NON_COMPLIANT.  value is compliant when
    low_limit <= value <= high_limit.  Raises ValueError for an empty
    param_name or for low_limit > high_limit."""
    if not param_name:
        raise ValueError("param_name must not be empty")
    if low_limit > high_limit:
        raise ValueError(
            "low_limit (%s) must not exceed high_limit (%s) for %r"
            % (low_limit, high_limit, param_name)
        )
    if low_limit <= value <= high_limit:
        return CONDITION_COMPLIANT
    return CONDITION_NON_COMPLIANT


def _iso_class_number(class_str):
    """Return the integer rank (1–9) of an ISO class string such as 'ISO5'.
    Raises ValueError for an unrecognized or out-of-range class label."""
    if class_str not in VALID_CLEANLINESS_CLASSES:
        raise ValueError(
            "unrecognized cleanliness class %r; expected one of %s"
            % (class_str, sorted(VALID_CLEANLINESS_CLASSES))
        )
    return int(class_str[3:])


def check_cleanliness_class(area_id, required_class, actual_class):
    """Violation list (empty if compliant) for a test area's cleanliness
    level.  actual_class is compliant when its ISO number is less than or
    equal to required_class's ISO number (lower number = stricter).
    Raises ValueError for an unrecognized class label."""
    req_rank = _iso_class_number(required_class)
    act_rank = _iso_class_number(actual_class)
    if act_rank <= req_rank:
        return []
    return [
        {
            "issue": "cleanliness_class_insufficient",
            "area": area_id,
            "required_class": required_class,
            "actual_class": actual_class,
        }
    ]


def check_esd_controls(item_id, esd_required, controls_present):
    """Violation list (empty if compliant) for ESD protection on a test item.
    When esd_required is True, every control in REQUIRED_ESD_CONTROLS must
    appear in controls_present (an iterable of control name strings).
    Returns [] when esd_required is False regardless of controls_present.
    Does not mutate controls_present."""
    if not esd_required:
        return []
    present = frozenset(controls_present)
    missing = REQUIRED_ESD_CONTROLS - present
    if not missing:
        return []
    return [
        {
            "issue": "esd_control_missing",
            "item": item_id,
            "missing_controls": sorted(missing),
        }
    ]


def check_configuration_completeness(config_id, required_fields, documented_fields):
    """Violation list (empty if compliant) for a test configuration record.
    Every string in required_fields must appear in documented_fields.
    Does not mutate either argument."""
    documented = frozenset(documented_fields)
    missing = [f for f in required_fields if f not in documented]
    if not missing:
        return []
    return [
        {
            "issue": "configuration_fields_missing",
            "config": config_id,
            "missing_fields": missing,
        }
    ]


def check_monitoring_channel(channel_id, recording_rate_hz, limits):
    """Violation list (empty if compliant) for a single monitoring channel
    definition.  recording_rate_hz must be > 0 and limits must not be None.
    Raises ValueError for a negative recording rate."""
    if recording_rate_hz < 0:
        raise ValueError(
            "recording_rate_hz must be >= 0 for channel %r" % (channel_id,)
        )
    findings = []
    if recording_rate_hz == 0:
        findings.append(
            {
                "issue": "monitoring_channel_rate_zero",
                "channel": channel_id,
            }
        )
    if limits is None:
        findings.append(
            {
                "issue": "monitoring_channel_limits_undefined",
                "channel": channel_id,
            }
        )
    return findings


def check_monitoring_coverage(monitor_id, required_channels, defined_channels):
    """Violation list (empty if compliant) for monitoring coverage.
    Every channel name in required_channels must appear as a key in
    defined_channels (a dict mapping channel name to a definition dict with
    keys 'recording_rate_hz' and 'limits').  Missing channels are flagged;
    present channels are validated via check_monitoring_channel.
    Does not mutate defined_channels."""
    findings = []
    for ch in required_channels:
        if ch not in defined_channels:
            findings.append(
                {
                    "issue": "monitoring_channel_not_defined",
                    "monitor_id": monitor_id,
                    "channel": ch,
                }
            )
        else:
            defn = defined_channels[ch]
            findings.extend(
                check_monitoring_channel(
                    ch,
                    defn.get("recording_rate_hz", 0),
                    defn.get("limits"),
                )
            )
    return findings


def validate_test_conditions(conditions):
    """Full test conditions validation per ECSS-E-ST-10C §4.4.1.

    conditions: {
        "environment": [
            {"param": str, "value": float,
             "low_limit": float, "high_limit": float}
        ],
        "cleanliness_areas": [
            {"area_id": str, "required_class": str, "actual_class": str}
        ],
        "esd_items": [
            {"item_id": str, "esd_required": bool,
             "controls_present": [str]}
        ],
        "configurations": [
            {"config_id": str, "required_fields": [str],
             "documented_fields": [str]}
        ],
        "monitoring": [
            {"monitor_id": str, "required_channels": [str],
             "defined_channels": dict}
        ]
    }

    Returns {"findings": [...]}, where each finding is a dict with at least
    "category" and "issue" keys.  An empty findings list means all conditions
    are compliant.  Raises ValueError for malformed inputs."""
    findings = []

    for env in conditions.get("environment", []):
        status = categorize_environment_condition(
            env["param"], env["value"], env["low_limit"], env["high_limit"]
        )
        if status == CONDITION_NON_COMPLIANT:
            findings.append(
                {
                    "category": "environment",
                    "issue": "environment_condition_out_of_range",
                    "param": env["param"],
                    "value": env["value"],
                    "low_limit": env["low_limit"],
                    "high_limit": env["high_limit"],
                }
            )

    for area in conditions.get("cleanliness_areas", []):
        for v in check_cleanliness_class(
            area["area_id"], area["required_class"], area["actual_class"]
        ):
            findings.append({"category": "cleanliness", **v})

    for item in conditions.get("esd_items", []):
        for v in check_esd_controls(
            item["item_id"],
            item["esd_required"],
            item.get("controls_present", []),
        ):
            findings.append({"category": "esd", **v})

    for cfg in conditions.get("configurations", []):
        for v in check_configuration_completeness(
            cfg["config_id"],
            cfg.get("required_fields", []),
            cfg.get("documented_fields", []),
        ):
            findings.append({"category": "configuration", **v})

    for mon in conditions.get("monitoring", []):
        for v in check_monitoring_coverage(
            mon["monitor_id"],
            mon.get("required_channels", []),
            mon.get("defined_channels", {}),
        ):
            findings.append({"category": "monitoring", **v})

    return {"findings": findings}


def is_test_conditions_compliant(validation_result):
    """True when all test conditions are compliant (no findings)."""
    return len(validation_result["findings"]) == 0
