#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 7.2.1.2.2 antenna engineering process steps
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical and electronic engineering standard lays out antenna
engineering as an ordered sequence that starts from the analysis of what
the mission must transmit and receive and ends at the antenna design
decision, passing through the derivation of the radio-frequency
requirements, the specification of the coverage and the radiation
pattern, the selection of an antenna concept and the definition of its
accommodation and interfaces. Each step consumes the output of the ones
before it: the required antenna gain is what the demanded radiated power
leaves after the transmitter output and the feeder attenuation, the
beamwidth follows from the coverage footprint seen at the orbit
altitude, the directivity follows from the beamwidth, and the concept
follows from the beamwidth together with the number of simultaneous
beams and the steering need.

This module implements step validation, sequence-order checking,
entry-data checking, next-step selection, required-gain derivation, the
edge-of-coverage half-angle, beamwidth and directivity conversion,
achievable-gain feasibility and the aggregate process review. It does
not size an aperture, synthesise a pattern or model a feed network.
"""

import math

# The clause sequence, in order. Position in this tuple is the
# prerequisite relation: every earlier step must be complete before a
# later one is entered.
PROCESS_STEPS = (
    "mission-transmission-reception-analysis",
    "radio-frequency-requirement-derivation",
    "coverage-and-pattern-specification",
    "antenna-concept-selection",
    "accommodation-and-interface-definition",
    "antenna-design-decision",
)

# Entry data each step consumes. A step whose entry data is incomplete is
# not enterable, however many predecessors are closed.
STEP_ENTRY_DATA = {
    "mission-transmission-reception-analysis": (
        "mission-link-set",
        "orbit-geometry",
        "ground-segment-definition",
    ),
    "radio-frequency-requirement-derivation": (
        "required-radiated-power",
        "transmitter-output",
        "feeder-attenuation",
    ),
    "coverage-and-pattern-specification": (
        "coverage-footprint-radius",
        "orbit-altitude",
        "polarization-plan",
    ),
    "antenna-concept-selection": (
        "required-antenna-gain",
        "half-power-beamwidth",
        "beam-count",
    ),
    "accommodation-and-interface-definition": (
        "mounting-envelope",
        "field-of-view-obstruction-map",
        "guided-wave-interface",
    ),
    "antenna-design-decision": (
        "selected-antenna-concept",
        "verification-approach",
    ),
}

REFLECTOR_ANTENNA = "reflector-antenna"
HORN_ANTENNA = "horn-antenna"
LOW_GAIN_ELEMENT_ANTENNA = "low-gain-element-antenna"
PHASED_ARRAY_ANTENNA = "phased-array-antenna"

# Concept band edges on the half-power beamwidth, degrees.
NARROW_BEAM_LIMIT_DEG = 10.0
INTERMEDIATE_BEAM_LIMIT_DEG = 60.0

# Directivity of a symmetric beam: the constant relates the product of
# the principal-plane beamwidths in degrees to the directivity a
# loss-free beam of that shape reaches.
BEAMWIDTH_DIRECTIVITY_CONSTANT = 31000.0

EARTH_MEAN_RADIUS_M = 6371000.0

# Default fraction of the geometric aperture that contributes to gain.
DEFAULT_APERTURE_EFFICIENCY = 0.6

# Angles and decibels here are built from trigonometric and logarithmic
# expressions, so a value that is physically exactly on a band edge can
# land a few units in the last place beyond it. The edges themselves are
# never moved -- only the representation error is absorbed.
ANGLE_TOLERANCE_DEG = 1e-9
DECIBEL_TOLERANCE_DB = 1e-9

REQUIRED_PROJECT_KEYS = (
    "completed_steps",
    "available_inputs",
    "required_radiated_power_dbw",
    "transmitter_power_dbw",
    "feeder_loss_db",
    "orbit_altitude_m",
    "coverage_radius_m",
)


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _at_or_below(value, limit, tolerance):
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=tolerance)


def validate_process_step(step):
    """Fold one step name into its canonical form, rejecting the unknown."""
    if not isinstance(step, str):
        raise ValueError("process step must be a string, got %r" % (step,))
    folded = step.strip().lower().replace("_", " ").replace("-", " ")
    parts = [part for part in folded.split() if part]
    if not parts:
        raise ValueError("process step must not be empty")
    key = "-".join(parts)
    if key not in PROCESS_STEPS:
        raise ValueError("unrecognised antenna engineering process step %r" % (step,))
    return key


def process_step_index(step):
    """Position of one step in the clause sequence, counting from zero."""
    return PROCESS_STEPS.index(validate_process_step(step))


def _normalise_completed(completed_steps):
    if isinstance(completed_steps, str) or not isinstance(
        completed_steps, (list, tuple, set, frozenset)
    ):
        raise ValueError("completed steps must be a list, tuple or set of step names")
    return set(validate_process_step(step) for step in completed_steps)


def check_step_order(completed_steps):
    """Report any completed step whose predecessors are still open."""
    completed = _normalise_completed(completed_steps)
    findings = []
    for step in PROCESS_STEPS:
        if step not in completed:
            continue
        for earlier in PROCESS_STEPS[: PROCESS_STEPS.index(step)]:
            if earlier not in completed:
                findings.append(
                    "%s is closed while %s is still open" % (step, earlier)
                )
    return {
        "completed": sorted(completed, key=PROCESS_STEPS.index),
        "findings": findings,
        "ordered": not findings,
    }


def check_step_prerequisites(step, completed_steps):
    """List the earlier steps that must close before this one is entered."""
    key = validate_process_step(step)
    completed = _normalise_completed(completed_steps)
    missing = [
        earlier
        for earlier in PROCESS_STEPS[: PROCESS_STEPS.index(key)]
        if earlier not in completed
    ]
    return {"step": key, "missing_prerequisites": missing, "ready": not missing}


def check_step_entry_data(step, available_inputs):
    """List the entry data one step consumes but the project does not hold."""
    key = validate_process_step(step)
    if isinstance(available_inputs, str) or not isinstance(
        available_inputs, (list, tuple, set, frozenset)
    ):
        raise ValueError("available inputs must be a list, tuple or set of data names")
    held = set()
    for item in available_inputs:
        if not isinstance(item, str):
            raise ValueError("entry data name must be a string, got %r" % (item,))
        folded = item.strip().lower().replace("_", "-").replace(" ", "-")
        if not folded:
            raise ValueError("entry data name must not be empty")
        held.add(folded)
    missing = [item for item in STEP_ENTRY_DATA[key] if item not in held]
    return {"step": key, "missing_entry_data": missing, "complete": not missing}


def next_process_step(completed_steps):
    """The first step of the sequence that is not yet closed, or None."""
    completed = _normalise_completed(completed_steps)
    for step in PROCESS_STEPS:
        if step not in completed:
            return step
    return None


def derive_required_antenna_gain_dbi(
    required_radiated_power_dbw, transmitter_power_dbw, feeder_loss_db
):
    """Gain the antenna must reach for the demanded radiated power."""
    required = _require_number("required_radiated_power_dbw", required_radiated_power_dbw)
    transmitter = _require_number("transmitter_power_dbw", transmitter_power_dbw)
    feeder = _require_non_negative("feeder_loss_db", feeder_loss_db)
    return required - transmitter + feeder


def edge_of_coverage_half_angle_deg(
    orbit_altitude_m, coverage_radius_m, body_radius_m=EARTH_MEAN_RADIUS_M
):
    """Half-angle the coverage footprint subtends at the spacecraft."""
    altitude = _require_positive("orbit_altitude_m", orbit_altitude_m)
    footprint = _require_positive("coverage_radius_m", coverage_radius_m)
    body = _require_positive("body_radius_m", body_radius_m)
    central_angle = footprint / body
    horizon_angle = math.acos(body / (body + altitude))
    if central_angle >= horizon_angle:
        raise ValueError(
            "coverage radius %r m reaches past the visible horizon at %r m altitude"
            % (coverage_radius_m, orbit_altitude_m)
        )
    across = body * math.sin(central_angle)
    along = (body + altitude) - body * math.cos(central_angle)
    return math.degrees(math.atan2(across, along))


def half_power_beamwidth_from_half_angle_deg(half_angle_deg):
    """Beamwidth that places the coverage edge at the half-power point."""
    half_angle = _require_positive("half_angle_deg", half_angle_deg)
    beamwidth = 2.0 * half_angle
    if beamwidth > 180.0:
        raise ValueError(
            "half-angle %r deg implies a beamwidth beyond a hemisphere" % (half_angle_deg,)
        )
    return beamwidth


def directivity_from_beamwidth_dbi(half_power_beamwidth_deg):
    """Directivity a symmetric beam of the given width reaches."""
    beamwidth = _require_positive("half_power_beamwidth_deg", half_power_beamwidth_deg)
    if beamwidth > 180.0:
        raise ValueError(
            "half-power beamwidth %r deg exceeds a hemisphere" % (half_power_beamwidth_deg,)
        )
    return 10.0 * math.log10(BEAMWIDTH_DIRECTIVITY_CONSTANT / (beamwidth * beamwidth))


def beamwidth_from_directivity_deg(directivity_dbi):
    """Beamwidth a symmetric beam of the given directivity implies."""
    directivity = _require_number("directivity_dbi", directivity_dbi)
    beamwidth = math.sqrt(
        BEAMWIDTH_DIRECTIVITY_CONSTANT / (10.0 ** (directivity / 10.0))
    )
    if beamwidth > 180.0:
        raise ValueError(
            "directivity %r dBi is below what a single beam holds" % (directivity_dbi,)
        )
    return beamwidth


def achievable_gain_dbi(directivity_dbi, aperture_efficiency=DEFAULT_APERTURE_EFFICIENCY):
    """Directivity reduced by the fraction of the aperture that contributes."""
    directivity = _require_number("directivity_dbi", directivity_dbi)
    efficiency = _require_number("aperture_efficiency", aperture_efficiency)
    if not 0.0 < efficiency <= 1.0:
        raise ValueError(
            "aperture efficiency must lie above 0 and at most 1, got %r"
            % (aperture_efficiency,)
        )
    return directivity + 10.0 * math.log10(efficiency)


def assess_gain_feasibility(required_gain_dbi, achievable_dbi):
    """Hold the gain the link demands against the gain the beam can reach."""
    required = _require_number("required_gain_dbi", required_gain_dbi)
    achievable = _require_number("achievable_dbi", achievable_dbi)
    feasible = _at_or_below(required, achievable, DECIBEL_TOLERANCE_DB)
    return {
        "required_gain_dbi": required,
        "achievable_gain_dbi": achievable,
        "feasible": feasible,
        "shortfall_db": 0.0 if feasible else required - achievable,
    }


def select_antenna_concept(
    half_power_beamwidth_deg, beam_count=1, electronic_steering=False
):
    """Branch from the pattern, the beam count and the steering need."""
    beamwidth = _require_positive("half_power_beamwidth_deg", half_power_beamwidth_deg)
    if beamwidth > 180.0:
        raise ValueError(
            "half-power beamwidth %r deg exceeds a hemisphere" % (half_power_beamwidth_deg,)
        )
    if isinstance(beam_count, bool) or not isinstance(beam_count, int):
        raise ValueError("beam_count must be an integer, got %r" % (beam_count,))
    if beam_count < 1:
        raise ValueError("beam_count must be at least 1, got %r" % (beam_count,))
    if not isinstance(electronic_steering, bool):
        raise ValueError(
            "electronic_steering must be a boolean, got %r" % (electronic_steering,)
        )
    if beam_count > 1 or electronic_steering:
        return PHASED_ARRAY_ANTENNA
    if _at_or_below(beamwidth, NARROW_BEAM_LIMIT_DEG, ANGLE_TOLERANCE_DEG):
        return REFLECTOR_ANTENNA
    if _at_or_below(beamwidth, INTERMEDIATE_BEAM_LIMIT_DEG, ANGLE_TOLERANCE_DEG):
        return HORN_ANTENNA
    return LOW_GAIN_ELEMENT_ANTENNA


def review_antenna_engineering_process(project):
    """Run the clause 7.2.1.2.2 sequence over one antenna engineering project."""
    if not isinstance(project, dict):
        raise ValueError("project record must be a mapping")
    missing_keys = [key for key in REQUIRED_PROJECT_KEYS if key not in project]
    if missing_keys:
        raise ValueError(
            "project record is missing required keys: %s" % ", ".join(missing_keys)
        )
    order = check_step_order(project["completed_steps"])
    findings = list(order["findings"])

    next_step = next_process_step(project["completed_steps"])
    if next_step is None:
        entry_data = {"step": None, "missing_entry_data": [], "complete": True}
    else:
        entry_data = check_step_entry_data(next_step, project["available_inputs"])
        for item in entry_data["missing_entry_data"]:
            findings.append("%s cannot be entered without %s" % (next_step, item))

    required_gain = derive_required_antenna_gain_dbi(
        project["required_radiated_power_dbw"],
        project["transmitter_power_dbw"],
        project["feeder_loss_db"],
    )
    half_angle = edge_of_coverage_half_angle_deg(
        project["orbit_altitude_m"],
        project["coverage_radius_m"],
        project.get("body_radius_m", EARTH_MEAN_RADIUS_M),
    )
    beamwidth = half_power_beamwidth_from_half_angle_deg(half_angle)
    directivity = directivity_from_beamwidth_dbi(beamwidth)
    achievable = achievable_gain_dbi(
        directivity, project.get("aperture_efficiency", DEFAULT_APERTURE_EFFICIENCY)
    )
    feasibility = assess_gain_feasibility(required_gain, achievable)
    if not feasibility["feasible"]:
        findings.append(
            "required antenna-gain %.3f dBi exceeds the %.3f dBi a %.3f deg beam reaches"
            % (required_gain, achievable, beamwidth)
        )
    concept = select_antenna_concept(
        beamwidth,
        project.get("beam_count", 1),
        project.get("electronic_steering", False),
    )
    return {
        "order": order,
        "next_step": next_step,
        "entry_data": entry_data,
        "required_gain_dbi": required_gain,
        "edge_of_coverage_half_angle_deg": half_angle,
        "half_power_beamwidth_deg": beamwidth,
        "directivity_dbi": directivity,
        "achievable_gain_dbi": achievable,
        "feasibility": feasibility,
        "selected_concept": concept,
        "findings": findings,
        "ready_for_design_decision": not findings,
    }
