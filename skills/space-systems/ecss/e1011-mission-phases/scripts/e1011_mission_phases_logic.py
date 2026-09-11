"""
e1011_mission_phases_logic.py

Mission-phase mapping and human-in-the-loop activity identification for
Human Factors Engineering (HFE) requirements capture.

Anchor: ECSS-E-ST-10-11C §4.3.6
"""

# Canonical mission phases in lifecycle order with short codes
CANONICAL_PHASES = [
    "GRD",  # Ground / pre-launch operations
    "LCH",  # Launch
    "ASC",  # Ascent
    "DEP",  # Deployment / separation
    "CHK",  # On-orbit checkout
    "NOM",  # Nominal operations
    "CTG",  # Contingency / off-nominal operations
    "DPS",  # Disposal / decommissioning
]

PHASE_LABELS = {
    "GRD": "Ground Operations",
    "LCH": "Launch",
    "ASC": "Ascent",
    "DEP": "Deployment",
    "CHK": "On-orbit Checkout",
    "NOM": "Nominal Operations",
    "CTG": "Contingency Operations",
    "DPS": "Disposal",
}

# Phases where critical activities must carry human-in-the-loop oversight
MANDATORY_HUMAN_PHASES = {"LCH", "ASC", "CTG"}

VALID_ACTIVITY_TYPES = {
    "commanding",
    "monitoring",
    "maintenance",
    "procedure_execution",
    "decision_making",
    "communication",
    "emergency_response",
    "configuration",
}

VALID_CRITICALITY_LEVELS = {"critical", "routine", "monitoring"}

# Deterministic mapping from activity type to primary HFE driver category
ACTIVITY_TYPE_TO_HFE_DRIVER = {
    "commanding": "workload",
    "monitoring": "cognitive",
    "maintenance": "anthropometry",
    "procedure_execution": "workload",
    "decision_making": "cognitive",
    "communication": "communication",
    "emergency_response": "safety",
    "configuration": "workload",
}

HFE_REQ_ID_PREFIX = "HFE"


def validate_phase_code(phase_code):
    """Raise ValueError if phase_code is not in the canonical phase list."""
    if phase_code not in CANONICAL_PHASES:
        raise ValueError(
            "Unknown phase code '{}'; must be one of {}".format(
                phase_code, CANONICAL_PHASES
            )
        )


def validate_activity_type(activity_type):
    """Raise ValueError if activity_type is not in the controlled vocabulary."""
    if activity_type not in VALID_ACTIVITY_TYPES:
        raise ValueError(
            "Unknown activity_type '{}'; must be one of {}".format(
                activity_type, sorted(VALID_ACTIVITY_TYPES)
            )
        )


def validate_criticality(criticality):
    """Raise ValueError if criticality is not in the controlled vocabulary."""
    if criticality not in VALID_CRITICALITY_LEVELS:
        raise ValueError(
            "Unknown criticality '{}'; must be one of {}".format(
                criticality, sorted(VALID_CRITICALITY_LEVELS)
            )
        )


def categorize_activity(activity_type, is_human_in_loop):
    """
    Return 'human_in_loop' when a human actively executes the activity,
    'automated' otherwise. Raises ValueError for unrecognized activity_type.
    """
    validate_activity_type(activity_type)
    return "human_in_loop" if is_human_in_loop else "automated"


def determine_hfe_driver(activity_type):
    """
    Map an activity type to its primary HFE driver category.
    Raises ValueError for unrecognized activity_type.
    """
    validate_activity_type(activity_type)
    return ACTIVITY_TYPE_TO_HFE_DRIVER[activity_type]


def generate_hfe_req_id(phase_code, activity_id):
    """
    Return a structured HFE requirement ID for a phase + activity.
    Format: HFE-<PHASE_CODE>-<ACTIVITY_ID>
    Raises ValueError if phase_code is not canonical.
    """
    validate_phase_code(phase_code)
    return "{}-{}-{}".format(HFE_REQ_ID_PREFIX, phase_code, activity_id)


def analyse_phase(phase_code, activities):
    """
    Analyse a mission phase for human-in-the-loop coverage and derive
    HFE requirements.

    Each entry in `activities` must be a dict with:
      - activity_id   (str): unique identifier within this phase
      - activity_type (str): one of VALID_ACTIVITY_TYPES
      - is_human_in_loop (bool)
      - criticality   (str): one of VALID_CRITICALITY_LEVELS

    Returns a dict:
      {
        "phase_code": str,
        "hfe_requirements": [
            {"req_id": str, "phase": str, "activity_id": str,
             "driver": str, "criticality": str}, ...
        ],
        "findings": [str, ...],
      }

    Raises ValueError if phase_code is unknown or any activity field is invalid.
    """
    validate_phase_code(phase_code)

    hfe_requirements = []
    findings = []
    human_activities = []

    for act in activities:
        act_type = act["activity_type"]
        criticality = act["criticality"]
        validate_activity_type(act_type)
        validate_criticality(criticality)

        is_human = bool(act["is_human_in_loop"])
        act_id = act["activity_id"]

        if is_human:
            human_activities.append(act)
            driver = determine_hfe_driver(act_type)
            req_id = generate_hfe_req_id(phase_code, act_id)
            hfe_requirements.append({
                "req_id": req_id,
                "phase": phase_code,
                "activity_id": act_id,
                "driver": driver,
                "criticality": criticality,
            })
        else:
            if criticality == "critical" and phase_code in MANDATORY_HUMAN_PHASES:
                findings.append(
                    "PHASE {} ACT {}: critical activity type '{}' has no "
                    "human-in-the-loop assignment in a mandatory-human phase; "
                    "HFE review required".format(phase_code, act_id, act_type)
                )

    if not human_activities:
        findings.append(
            "PHASE {}: no human-in-the-loop activities recorded; "
            "verify whether this phase is within the HFE assessment scope".format(
                phase_code
            )
        )

    return {
        "phase_code": phase_code,
        "hfe_requirements": hfe_requirements,
        "findings": findings,
    }


def check_phase_completeness(phase_activity_map):
    """
    Check that every canonical phase is represented in phase_activity_map.
    Return a finding string for each absent phase.
    """
    findings = []
    for phase in CANONICAL_PHASES:
        if phase not in phase_activity_map:
            findings.append(
                "PHASE {} ({}): not present in the mission-phase inventory; "
                "confirm scope or add a no-activity entry".format(
                    phase, PHASE_LABELS[phase]
                )
            )
    return findings


def map_mission_phases(phase_activity_map):
    """
    Map all canonical mission phases, producing per-phase analysis results.

    `phase_activity_map` is a dict of {phase_code: [activity_dict, ...]}.
    Phases in CANONICAL_PHASES but absent from the map are included in the
    output with a finding flagging their absence.

    Returns:
      {
        "phase_results": {phase_code: analyse_phase result dict, ...},
        "completeness_findings": [str, ...],
        "all_findings": [str, ...],
      }

    Raises ValueError if any supplied phase_code is not canonical.
    """
    phase_results = {}

    for phase_code, activities in phase_activity_map.items():
        validate_phase_code(phase_code)
        phase_results[phase_code] = analyse_phase(phase_code, activities)

    for phase in CANONICAL_PHASES:
        if phase not in phase_results:
            phase_results[phase] = {
                "phase_code": phase,
                "hfe_requirements": [],
                "findings": [
                    "PHASE {} ({}): no activities supplied; phase is absent "
                    "from the mission-phase inventory".format(
                        phase, PHASE_LABELS[phase]
                    )
                ],
            }

    completeness_findings = check_phase_completeness(phase_activity_map)

    all_findings = []
    for phase in CANONICAL_PHASES:
        all_findings.extend(phase_results[phase]["findings"])
    all_findings.extend(completeness_findings)

    return {
        "phase_results": phase_results,
        "completeness_findings": completeness_findings,
        "all_findings": all_findings,
    }


def summarise_hfe_coverage(mapping_result):
    """Return per-phase count of HFE requirements from a map_mission_phases result."""
    return {
        phase: len(result["hfe_requirements"])
        for phase, result in mapping_result["phase_results"].items()
    }
