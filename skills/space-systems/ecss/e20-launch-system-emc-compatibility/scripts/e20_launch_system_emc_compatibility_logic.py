#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 6.3.2.2 launch system electromagnetic
environment and compatibility (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard places a duty on the spacecraft to be
compatible with the electromagnetic environment of the launch system
throughout the prelaunch and launch phases, not only in orbit. This
module implements the checkable part of that clause: categorization of
a campaign phase and of an environment source, the free-space
far-field relation between an emitter and the field it puts on the
spacecraft, the far-field validity boundary, the fairing shielding
attenuation that applies while the vehicle is encapsulated, the lookup
of the radiated-susceptibility level the spacecraft was qualified to
at a given frequency, the resulting margin against a requirement, and
the aggregated campaign finding lists. It does not model near-field
coupling, does not compute a lightning transient waveform, and does
not replace a range electromagnetic survey.
"""

import math

PRELAUNCH_PHASES = frozenset(
    {
        "payload_processing",
        "spacecraft_fuelling",
        "encapsulation",
        "transfer_to_pad",
        "on_pad_standby",
        "final_countdown",
    }
)
LAUNCH_PHASES = frozenset(
    {
        "liftoff",
        "atmospheric_ascent",
        "fairing_jettison",
        "upper_stage_flight",
        "spacecraft_separation",
    }
)

# Phases in which the fairing is closed around the spacecraft, so the
# incident field reaches it reduced by the fairing shielding
# effectiveness. Jettison and everything after it is exposed again.
ENCAPSULATED_PHASES = frozenset(
    {
        "encapsulation",
        "transfer_to_pad",
        "on_pad_standby",
        "final_countdown",
        "liftoff",
        "atmospheric_ascent",
    }
)

MANDATORY_CAMPAIGN_PHASES = frozenset(
    {
        "payload_processing",
        "encapsulation",
        "on_pad_standby",
        "final_countdown",
        "liftoff",
        "atmospheric_ascent",
        "spacecraft_separation",
    }
)

GROUND_FIXED_EMITTERS = frozenset(
    {
        "range_tracking_radar",
        "range_safety_command_transmitter",
        "ground_telemetry_transmitter",
        "weather_radar",
        "airport_surveillance_radar",
    }
)
LAUNCHER_BORNE_EMITTERS = frozenset(
    {
        "launcher_telemetry_transmitter",
        "launcher_radar_transponder",
        "launcher_receiver_local_oscillator",
    }
)
FACILITY_EMITTERS = frozenset(
    {
        "cleanroom_handheld_radio",
        "facility_wireless_network",
        "overhead_crane_drive",
    }
)
ELECTROSTATIC_SOURCES = frozenset(
    {
        "triboelectric_charging",
        "lightning_induced_transient",
        "precipitation_static",
    }
)

EMITTER_CATEGORIES = frozenset({"ground_fixed", "launcher_borne", "facility"})

SPEED_OF_LIGHT_M_PER_S = 299792458.0

# E = sqrt(30 * P_eirp) / d is the free-space far-field relation for an
# equivalent isotropically radiated power in watts at a distance in
# metres, giving volts per metre.
FREE_SPACE_FIELD_CONSTANT = 30.0

DEFAULT_REQUIRED_MARGIN_DB = 6.0

# Absorbs the representation error of a ratio that is mathematically
# on the requirement; it never widens the requirement itself.
MARGIN_TOLERANCE_DB = 1.0e-9


def categorize_launch_phase(phase):
    """Campaign half a phase belongs to: "prelaunch" or "launch".
    Raises ValueError for a phase that is in neither set."""
    if phase in PRELAUNCH_PHASES:
        return "prelaunch"
    if phase in LAUNCH_PHASES:
        return "launch"
    raise ValueError(
        "unrecognized campaign phase %r under "
        "E-ST-20C clause 6.3.2.2" % (phase,)
    )


def categorize_environment_source(source_kind):
    """Source category: "ground_fixed", "launcher_borne", "facility" or
    "electrostatic". Raises ValueError for a kind that is not part of
    the launch electromagnetic environment."""
    if source_kind in GROUND_FIXED_EMITTERS:
        return "ground_fixed"
    if source_kind in LAUNCHER_BORNE_EMITTERS:
        return "launcher_borne"
    if source_kind in FACILITY_EMITTERS:
        return "facility"
    if source_kind in ELECTROSTATIC_SOURCES:
        return "electrostatic"
    raise ValueError("unrecognized environment source kind %r" % (source_kind,))


def is_encapsulated(phase):
    """True when the fairing is closed around the spacecraft in this
    phase. Raises ValueError through categorize_launch_phase for an
    unrecognized phase."""
    categorize_launch_phase(phase)
    return phase in ENCAPSULATED_PHASES


def free_space_field_strength(eirp_w, distance_m):
    """Incident field in volts per metre from an equivalent
    isotropically radiated power at a separation distance, under the
    free-space far-field relation. Raises ValueError for a negative
    power or a non-positive distance."""
    if eirp_w < 0:
        raise ValueError("eirp_w must be >= 0")
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    return math.sqrt(FREE_SPACE_FIELD_CONSTANT * eirp_w) / distance_m


def wavelength_m(frequency_hz):
    """Free-space wavelength in metres. Raises ValueError for a
    non-positive frequency."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    return SPEED_OF_LIGHT_M_PER_S / frequency_hz


def far_field_distance_m(frequency_hz, aperture_m):
    """Distance beyond which the free-space far-field relation is
    usable: the larger of twice the squared aperture over the
    wavelength and three wavelengths, so a small aperture is still
    bounded by the wavelength term. Raises ValueError for a negative
    aperture or through wavelength_m for a bad frequency."""
    if aperture_m < 0:
        raise ValueError("aperture_m must be >= 0")
    lam = wavelength_m(frequency_hz)
    return max(2.0 * aperture_m * aperture_m / lam, 3.0 * lam)


def attenuated_field(field_v_per_m, shielding_db):
    """Field remaining after a shielding barrier of the given
    effectiveness in decibels. Raises ValueError for a negative field
    or a negative shielding effectiveness, which would amplify."""
    if field_v_per_m < 0:
        raise ValueError("field_v_per_m must be >= 0")
    if shielding_db < 0:
        raise ValueError("shielding_db must be >= 0")
    return field_v_per_m / (10.0 ** (shielding_db / 20.0))


def incident_field_at_spacecraft(source, phase, fairing_shielding_db):
    """Field in volts per metre an emitter puts on the spacecraft in
    one campaign phase.

    source: {"source_kind", "eirp_w", "distance_m", ...}. Raises
    ValueError for an electrostatic source, which carries no radiated
    field model, and through the helpers for a bad phase or a bad
    electrical input."""
    category = categorize_environment_source(source["source_kind"])
    if category not in EMITTER_CATEGORIES:
        raise ValueError(
            "source kind %r is an electrostatic source and has no "
            "radiated field model" % (source["source_kind"],)
        )
    field = free_space_field_strength(source["eirp_w"], source["distance_m"])
    if is_encapsulated(phase):
        return attenuated_field(field, fairing_shielding_db)
    return field


def qualification_level_at(frequency_hz, qualification_levels):
    """Radiated-susceptibility level in volts per metre the spacecraft
    was qualified to at this frequency, or None when the frequency
    falls outside every tested band. The first band that contains the
    frequency wins, so the result is deterministic. Raises ValueError
    for a non-positive frequency or a band whose edges are inverted."""
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be > 0")
    for band in qualification_levels:
        if band["f_min_hz"] > band["f_max_hz"]:
            raise ValueError(
                "qualification band edges inverted: %r > %r"
                % (band["f_min_hz"], band["f_max_hz"])
            )
        if band["f_min_hz"] <= frequency_hz <= band["f_max_hz"]:
            return band["level_v_per_m"]
    return None


def radiated_susceptibility_margin_db(qualification_v_per_m, incident_v_per_m):
    """Separation in decibels between the level the spacecraft was
    qualified to and the field it sees. Raises ValueError for a
    non-positive level or incident field."""
    if qualification_v_per_m <= 0:
        raise ValueError("qualification_v_per_m must be > 0")
    if incident_v_per_m <= 0:
        raise ValueError("incident_v_per_m must be > 0")
    return 20.0 * math.log10(qualification_v_per_m / incident_v_per_m)


def missing_campaign_phases(declared_phases, mandatory_phases=None):
    """Sorted list of mandatory campaign phases that carry no
    assessment. mandatory_phases defaults to
    MANDATORY_CAMPAIGN_PHASES. Raises ValueError when the mandatory
    set is empty."""
    required = set(
        MANDATORY_CAMPAIGN_PHASES if mandatory_phases is None else mandatory_phases
    )
    if not required:
        raise ValueError("the mandatory campaign phase set must not be empty")
    return sorted(required - set(declared_phases))


def source_findings(
    phase,
    source,
    qualification_levels,
    fairing_shielding_db,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
    tolerance_db=MARGIN_TOLERANCE_DB,
):
    """Findings for one source in one phase, keyed by check:
    {"near_field": [...], "frequency_coverage": [...],
    "field_margin": [...], "electrostatic_control": [...]}.

    An electrostatic source is checked for a declared dissipation
    provision and never for a field. An emitter inside the far-field
    boundary is reported and its field is not scored, because the
    free-space relation does not apply there. A frequency outside every
    tested band is reported instead of being scored against an
    extrapolated level. Raises ValueError for a negative tolerance or
    through the helpers."""
    if tolerance_db < 0:
        raise ValueError("tolerance_db must be >= 0")
    result = {
        "near_field": [],
        "frequency_coverage": [],
        "field_margin": [],
        "electrostatic_control": [],
    }
    source_id = source["source_id"]
    category = categorize_environment_source(source["source_kind"])
    categorize_launch_phase(phase)
    if category not in EMITTER_CATEGORIES:
        if not source.get("dissipation_provision"):
            result["electrostatic_control"].append(
                {
                    "issue": "missing_electrostatic_dissipation_provision",
                    "phase": phase,
                    "source": source_id,
                }
            )
        return result
    boundary_m = far_field_distance_m(source["frequency_hz"], source["aperture_m"])
    if source["distance_m"] < boundary_m:
        result["near_field"].append(
            {
                "issue": "source_inside_far_field_boundary",
                "phase": phase,
                "source": source_id,
                "distance_m": source["distance_m"],
                "far_field_distance_m": boundary_m,
            }
        )
        return result
    level = qualification_level_at(source["frequency_hz"], qualification_levels)
    if level is None:
        result["frequency_coverage"].append(
            {
                "issue": "frequency_outside_tested_susceptibility_envelope",
                "phase": phase,
                "source": source_id,
                "frequency_hz": source["frequency_hz"],
            }
        )
        return result
    incident = incident_field_at_spacecraft(source, phase, fairing_shielding_db)
    margin_db = radiated_susceptibility_margin_db(level, incident)
    if margin_db < required_margin_db and not math.isclose(
        margin_db, required_margin_db, rel_tol=0.0, abs_tol=tolerance_db
    ):
        result["field_margin"].append(
            {
                "issue": "radiated_susceptibility_margin_below_requirement",
                "phase": phase,
                "source": source_id,
                "incident_v_per_m": incident,
                "qualification_v_per_m": level,
                "margin_db": margin_db,
                "required_margin_db": required_margin_db,
            }
        )
    return result


def launch_campaign_review(campaign):
    """Full clause 6.3.2.2 review for one launch campaign.

    campaign: {"campaign_id": str, "fairing_shielding_db": float,
    "qualification_levels": [{"f_min_hz", "f_max_hz",
    "level_v_per_m"}, ...], "phases": [{"phase": str, "sources":
    [source, ...]}, ...], "required_margin_db": float (optional),
    "mandatory_phases": iterable (optional), "tolerance_db": float
    (optional)}.

    Returns {"phase_coverage": [...], "near_field": [...],
    "frequency_coverage": [...], "field_margin": [...],
    "electrostatic_control": [...]}. Raises ValueError through the
    helpers for an unrecognized phase or source or a bad input. Does
    not mutate campaign."""
    declared = [entry["phase"] for entry in campaign["phases"]]
    review = {
        "phase_coverage": [
            {
                "issue": "campaign_phase_not_assessed",
                "campaign": campaign["campaign_id"],
                "phase": phase,
            }
            for phase in missing_campaign_phases(
                declared, campaign.get("mandatory_phases")
            )
        ],
        "near_field": [],
        "frequency_coverage": [],
        "field_margin": [],
        "electrostatic_control": [],
    }
    for entry in campaign["phases"]:
        for source in entry["sources"]:
            findings = source_findings(
                entry["phase"],
                source,
                campaign["qualification_levels"],
                campaign["fairing_shielding_db"],
                campaign.get("required_margin_db", DEFAULT_REQUIRED_MARGIN_DB),
                campaign.get("tolerance_db", MARGIN_TOLERANCE_DB),
            )
            for key, items in findings.items():
                review[key].extend(items)
    return review


def is_campaign_compatible(review):
    """True when every finding list in a launch_campaign_review result
    is empty -- every mandatory phase was assessed and every source in
    every phase is compatible with the qualified design."""
    return all(len(findings) == 0 for findings in review.values())
