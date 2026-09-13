#!/usr/bin/env python3
"""Launch-phase receiver overload demonstration.

Anchor: ECSS-E-ST-20-07C clause 4.2.2.2 (onboard receivers tolerate the
launch-site electromagnetic environment during prelaunch and launch,
fairing present or not). The clause is paraphrased into an implementable
procedure; no standard text is reproduced.

Coupling chain used throughout:
  field-strength (V/m) -> power-density (W/m2) -> intercepted power via
  the antenna effective-aperture (W) -> fairing shielding attenuation
  (dB, only while the fairing is on) -> front-end frequency-rejection
  (dB) -> linear sum at the antenna-port -> margin against the
  overload-threshold and the damage-threshold (dBm).

Stdlib only, deterministic, offline.
"""

import math

FREE_SPACE_IMPEDANCE_OHM = 376.730313668
SPEED_OF_LIGHT_M_PER_S = 299792458.0

PHASES = ("prelaunch", "liftoff", "ascent")
CONFIG_ENCLOSED = "fairing-enclosed"
CONFIG_JETTISONED = "fairing-jettisoned"
CONFIGURATIONS = (CONFIG_ENCLOSED, CONFIG_JETTISONED)

# Phase/configuration pairs the clause expects to see demonstrated.
REQUIRED_CASES = (
    ("prelaunch", CONFIG_ENCLOSED),
    ("liftoff", CONFIG_ENCLOSED),
    ("ascent", CONFIG_ENCLOSED),
    ("ascent", CONFIG_JETTISONED),
)

DEFAULT_REJECTION_SLOPE_DB_PER_OCTAVE = 20.0
DEFAULT_MAX_REJECTION_DB = 60.0

MARGIN_TOLERANCE_DB = 1e-9
BAND_EDGE_TOLERANCE_MHZ = 1e-9


# --- unit conversions -------------------------------------------------------


def _finite_number(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric" % label)
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite" % label)
    return value


def watts_to_dbm(power_w):
    """Convert a power in watts to dBm."""
    power_w = _finite_number(power_w, "power")
    if power_w <= 0.0:
        raise ValueError("power must be positive to express it in dBm")
    return 10.0 * math.log10(power_w * 1000.0)


def dbm_to_watts(power_dbm):
    """Convert a power in dBm to watts."""
    power_dbm = _finite_number(power_dbm, "power level")
    return 10.0 ** (power_dbm / 10.0) / 1000.0


def power_density_w_per_m2(field_v_per_m):
    """Far-field power-density of a plane wave of the given field-strength."""
    field = _finite_number(field_v_per_m, "field strength")
    if field <= 0.0:
        raise ValueError("field strength must be positive")
    return field * field / FREE_SPACE_IMPEDANCE_OHM


def wavelength_m(frequency_mhz):
    """Free-space wavelength at the given frequency."""
    freq = _finite_number(frequency_mhz, "frequency")
    if freq <= 0.0:
        raise ValueError("frequency must be positive")
    return SPEED_OF_LIGHT_M_PER_S / (freq * 1.0e6)


def effective_aperture_m2(frequency_mhz, gain_dbi):
    """Antenna effective-aperture at the illuminating frequency."""
    gain_dbi = _finite_number(gain_dbi, "antenna gain")
    lam = wavelength_m(frequency_mhz)
    gain_linear = 10.0 ** (gain_dbi / 10.0)
    return gain_linear * lam * lam / (4.0 * math.pi)


# --- record normalization ---------------------------------------------------


def normalize_emitter(raw):
    """Normalize one launch-site emitter record."""
    if not isinstance(raw, dict):
        raise ValueError("emitter record must be a mapping")
    ident = str(raw.get("id", "")).strip()
    if not ident:
        raise ValueError("emitter needs a non-blank id")
    freq = _finite_number(raw.get("frequency_mhz"), "emitter %s frequency" % ident)
    if freq <= 0.0:
        raise ValueError("emitter %s frequency must be positive" % ident)
    field = _finite_number(
        raw.get("field_strength_v_per_m"), "emitter %s field strength" % ident
    )
    if field <= 0.0:
        raise ValueError("emitter %s field strength must be positive" % ident)
    raw_phases = raw.get("phases")
    if not isinstance(raw_phases, (list, tuple, set, frozenset)):
        raise ValueError("emitter %s needs a phase list" % ident)
    phases = []
    for phase in raw_phases:
        key = str(phase).strip().lower()
        if key not in PHASES:
            raise ValueError("emitter %s has unrecognised phase %r" % (ident, phase))
        if key not in phases:
            phases.append(key)
    if not phases:
        raise ValueError("emitter %s radiates in no declared phase" % ident)
    return {
        "id": ident,
        "frequency_mhz": freq,
        "field_strength_v_per_m": field,
        "phases": tuple(phases),
    }


def normalize_receiver(raw):
    """Normalize one onboard receiver record."""
    if not isinstance(raw, dict):
        raise ValueError("receiver record must be a mapping")
    ident = str(raw.get("id", "")).strip()
    if not ident:
        raise ValueError("receiver needs a non-blank id")
    centre = _finite_number(
        raw.get("center_frequency_mhz"), "receiver %s centre frequency" % ident
    )
    if centre <= 0.0:
        raise ValueError("receiver %s centre frequency must be positive" % ident)
    bandwidth = _finite_number(
        raw.get("bandwidth_mhz"), "receiver %s bandwidth" % ident
    )
    if bandwidth <= 0.0:
        raise ValueError("receiver %s bandwidth must be positive" % ident)
    gain = _finite_number(raw.get("gain_dbi"), "receiver %s antenna gain" % ident)
    overload = _finite_number(
        raw.get("overload_threshold_dbm"), "receiver %s overload threshold" % ident
    )
    damage = _finite_number(
        raw.get("damage_threshold_dbm"), "receiver %s damage threshold" % ident
    )
    if damage < overload:
        raise ValueError(
            "receiver %s damage threshold sits below its overload threshold" % ident
        )
    margin = _finite_number(
        raw.get("required_margin_db", 0.0), "receiver %s required margin" % ident
    )
    if margin < 0.0:
        raise ValueError("receiver %s required margin must not be negative" % ident)
    slope = _finite_number(
        raw.get("rejection_slope_db_per_octave", DEFAULT_REJECTION_SLOPE_DB_PER_OCTAVE),
        "receiver %s rejection slope" % ident,
    )
    if slope < 0.0:
        raise ValueError("receiver %s rejection slope must not be negative" % ident)
    floor = _finite_number(
        raw.get("max_rejection_db", DEFAULT_MAX_REJECTION_DB),
        "receiver %s maximum rejection" % ident,
    )
    if floor < 0.0:
        raise ValueError("receiver %s maximum rejection must not be negative" % ident)
    return {
        "id": ident,
        "center_frequency_mhz": centre,
        "bandwidth_mhz": bandwidth,
        "gain_dbi": gain,
        "overload_threshold_dbm": overload,
        "damage_threshold_dbm": damage,
        "required_margin_db": margin,
        "rejection_slope_db_per_octave": slope,
        "max_rejection_db": floor,
    }


# --- coupling ---------------------------------------------------------------


def fairing_attenuation_db(configuration, fairing_shielding_db):
    """Shielding attenuation credited for the given configuration."""
    config = str(configuration).strip().lower()
    if config not in CONFIGURATIONS:
        raise ValueError("unrecognised configuration: %r" % (configuration,))
    shielding = _finite_number(fairing_shielding_db, "fairing shielding")
    if shielding < 0.0:
        raise ValueError("fairing shielding attenuation must not be negative")
    return shielding if config == CONFIG_ENCLOSED else 0.0


def front_end_rejection_db(emitter_frequency_mhz, receiver):
    """Front-end selectivity applied to an emitter at a frequency offset.

    In-band emitters are rejected by nothing. Out-of-band emitters are
    attenuated on a decibel-per-octave slope measured from the passband
    edge, saturating at the stopband floor of the filter.
    """
    freq = _finite_number(emitter_frequency_mhz, "emitter frequency")
    if freq <= 0.0:
        raise ValueError("emitter frequency must be positive")
    half_band = receiver["bandwidth_mhz"] / 2.0
    offset = abs(freq - receiver["center_frequency_mhz"])
    if offset <= half_band + BAND_EDGE_TOLERANCE_MHZ:
        return 0.0
    octaves = math.log(offset / half_band, 2.0)
    raw = receiver["rejection_slope_db_per_octave"] * octaves
    return min(raw, receiver["max_rejection_db"])


def coupled_power_dbm(emitter, receiver, configuration, fairing_shielding_db):
    """Level coupled into the receiver antenna-port by one emitter."""
    density = power_density_w_per_m2(emitter["field_strength_v_per_m"])
    aperture = effective_aperture_m2(emitter["frequency_mhz"], receiver["gain_dbi"])
    incident_dbm = watts_to_dbm(density * aperture)
    attenuation = fairing_attenuation_db(configuration, fairing_shielding_db)
    rejection = front_end_rejection_db(emitter["frequency_mhz"], receiver)
    return incident_dbm - attenuation - rejection


def aggregate_dbm(levels_dbm):
    """Sum decibel levels in linear power and return the total in dBm."""
    if not isinstance(levels_dbm, (list, tuple)):
        raise ValueError("levels must be given as a list or tuple")
    if not levels_dbm:
        raise ValueError("cannot aggregate an empty level list")
    total_w = 0.0
    for level in levels_dbm:
        total_w += dbm_to_watts(level)
    return watts_to_dbm(total_w)


def meets_margin(actual_margin_db, required_margin_db, tolerance=MARGIN_TOLERANCE_DB):
    """True when the achieved margin reaches the requirement.

    The margin is a difference of decibel quantities built from
    logarithms, so an exactly compliant case can land a few units in the
    last place below the requirement. That representation error is
    absorbed here; the required margin itself is never relaxed.
    """
    actual = _finite_number(actual_margin_db, "achieved margin")
    required = _finite_number(required_margin_db, "required margin")
    if tolerance < 0.0:
        raise ValueError("tolerance must not be negative")
    return actual > required or math.isclose(
        actual, required, rel_tol=0.0, abs_tol=tolerance
    )


# --- case evaluation --------------------------------------------------------


def emitters_in_phase(emitters, phase):
    """Select the normalized emitters radiating in a given launch phase."""
    key = str(phase).strip().lower()
    if key not in PHASES:
        raise ValueError("unrecognised launch phase: %r" % (phase,))
    return tuple(e for e in emitters if key in e["phases"])


def evaluate_receiver_case(
    receiver, emitters, phase, configuration, fairing_shielding_db
):
    """Evaluate one receiver against one phase/configuration pair."""
    active = emitters_in_phase(emitters, phase)
    if not active:
        raise ValueError("no emitter radiates in phase %r" % (phase,))
    contributions = []
    for emitter in active:
        level = coupled_power_dbm(
            emitter, receiver, configuration, fairing_shielding_db
        )
        contributions.append((emitter["id"], level))
    total_dbm = aggregate_dbm([level for _, level in contributions])
    overload_margin = receiver["overload_threshold_dbm"] - total_dbm
    damage_margin = receiver["damage_threshold_dbm"] - total_dbm
    required = receiver["required_margin_db"]
    driver = max(contributions, key=lambda item: item[1])[0]
    return {
        "receiver": receiver["id"],
        "phase": str(phase).strip().lower(),
        "configuration": str(configuration).strip().lower(),
        "port_level_dbm": total_dbm,
        "contributions": tuple(contributions),
        "driving_emitter": driver,
        "overload_margin_db": overload_margin,
        "damage_margin_db": damage_margin,
        "overload_ok": meets_margin(overload_margin, required),
        "damage_ok": meets_margin(damage_margin, required),
    }


def assess_launch_campaign(receivers, emitters, fairing_shielding_db):
    """Run every required phase/configuration pair for every receiver."""
    if not isinstance(receivers, (list, tuple)) or not receivers:
        raise ValueError("at least one receiver record is required")
    if not isinstance(emitters, (list, tuple)):
        raise ValueError("emitters must be given as a list or tuple")
    norm_receivers = [normalize_receiver(r) for r in receivers]
    norm_emitters = [normalize_emitter(e) for e in emitters]
    cases = []
    findings = []
    for phase, configuration in REQUIRED_CASES:
        active = emitters_in_phase(norm_emitters, phase)
        if not active:
            findings.append("no-emitter-environment-declared:%s" % phase)
            continue
        for receiver in norm_receivers:
            case = evaluate_receiver_case(
                receiver, norm_emitters, phase, configuration, fairing_shielding_db
            )
            cases.append(case)
            if not case["overload_ok"]:
                findings.append(
                    "overload-margin-shortfall:%s:%s:%s"
                    % (receiver["id"], phase, configuration)
                )
            if not case["damage_ok"]:
                findings.append(
                    "damage-margin-shortfall:%s:%s:%s"
                    % (receiver["id"], phase, configuration)
                )
    return {
        "cases": tuple(cases),
        "findings": tuple(findings),
        "demonstrated": not findings,
    }
