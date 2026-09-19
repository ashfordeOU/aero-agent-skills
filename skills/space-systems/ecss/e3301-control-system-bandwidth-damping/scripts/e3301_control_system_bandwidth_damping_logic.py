"""Control-loop bandwidth placement and damping screen for a space mechanism.

Anchor: ECSS-E-ST-33-01C clauses 4.7.8.3 and 4.7.8.4 (mechanism control system
-- bandwidth set relative to the flexible structural modes it must not excite,
and the damping the closed loop has to retain). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the declared closed-loop bandwidth and the flexible-mode set of the
   driven structure (appendage, boom, harness-stiffened panel, gearbox torsion).
2. Derive the largest bandwidth the lowest flexible mode permits for the
   declared separation factor, and grade the declared bandwidth against it.
3. At every mode, turn the modal damping ratio into the resonant amplification
   the loop sees, add the required gain margin, and compare that demand with
   the attenuation the loop roll-off actually supplies an octave-count above
   the bandwidth.
4. Grade the closed-loop damping ratio -- declared, or recovered from a
   measured overshoot -- against the required minimum, and report the settling
   time that damping implies.
5. Report every finding: a mode inside the bandwidth, an insufficient
   separation, a mode the roll-off does not attenuate far enough, a
   closed-loop damping shortfall, and a modal damping assumption too
   optimistic to be credible without test evidence.
"""

import math

__all__ = [
    "COMPARISON_TOLERANCE",
    "CREDIBLE_MODAL_DAMPING_CAP",
    "validate_positive",
    "validate_damping_ratio",
    "validate_modes",
    "lowest_mode",
    "separation_ratio",
    "max_control_bandwidth_hz",
    "modal_amplification",
    "amplification_db",
    "required_attenuation_db",
    "rolloff_attenuation_db",
    "damping_from_overshoot",
    "overshoot_from_damping",
    "settling_time_s",
    "assess_mode_separation",
    "assess_closed_loop_damping",
    "assess_bandwidth_damping",
]

# Bandwidth and attenuation comparisons are differences of logarithms: a
# physically exact equality can land a few ULPs on the wrong side of the
# limit. Absorb the representation error here, never by relaxing the limit.
COMPARISON_TOLERANCE = 1e-9

# A flexible mode of a deployed space structure is lightly damped. A declared
# modal damping ratio above this cap makes the resonant amplification look
# small and is only admissible with measured evidence behind it.
CREDIBLE_MODAL_DAMPING_CAP = 0.05


def validate_positive(value, label):
    """Return value as a positive finite float, or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_damping_ratio(value, label, allow_unity=False):
    """Return a damping ratio in (0, 1) -- or (0, 1] when unity is allowed."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    zeta = float(value)
    if not math.isfinite(zeta):
        raise ValueError("%s must be finite" % label)
    if zeta <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    upper_ok = zeta <= 1.0 if allow_unity else zeta < 1.0
    if not upper_ok:
        raise ValueError("%s must stay below critical damping, got %r" % (label, value))
    return zeta


def validate_modes(modes):
    """Return the flexible-mode set sorted by frequency, validated."""
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError("modes must be a non-empty sequence of mode mappings")
    seen = set()
    validated = []
    for index, mode in enumerate(modes):
        if not isinstance(mode, dict):
            raise ValueError("modes[%d] must be a mapping" % index)
        for key in ("name", "frequency_hz", "damping_ratio"):
            if key not in mode:
                raise ValueError("modes[%d] missing key '%s'" % (index, key))
        name = mode["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("modes[%d] name must be a non-empty string" % index)
        if name in seen:
            raise ValueError("duplicate mode name %r" % name)
        seen.add(name)
        validated.append(
            {
                "name": name,
                "frequency_hz": validate_positive(
                    mode["frequency_hz"], "modes[%d] frequency_hz" % index
                ),
                "damping_ratio": validate_damping_ratio(
                    mode["damping_ratio"], "modes[%d] damping_ratio" % index
                ),
                "damping_measured": bool(mode.get("damping_measured", False)),
            }
        )
    validated.sort(key=lambda item: (item["frequency_hz"], item["name"]))
    return validated


def lowest_mode(modes):
    """Return the lowest-frequency flexible mode of a validated mode set."""
    return validate_modes(modes)[0]


def separation_ratio(mode_frequency_hz, bandwidth_hz):
    """Return how many times the mode frequency exceeds the loop bandwidth."""
    mode_hz = validate_positive(mode_frequency_hz, "mode_frequency_hz")
    band_hz = validate_positive(bandwidth_hz, "bandwidth_hz")
    return mode_hz / band_hz


def max_control_bandwidth_hz(lowest_mode_hz, separation_factor):
    """Return the largest bandwidth the lowest mode admits at this separation."""
    mode_hz = validate_positive(lowest_mode_hz, "lowest_mode_hz")
    factor = validate_positive(separation_factor, "separation_factor")
    if factor < 1.0:
        raise ValueError("separation_factor below unity places the mode inside the loop")
    return mode_hz / factor


def modal_amplification(damping_ratio):
    """Return the resonant amplification a lightly damped mode presents."""
    zeta = validate_damping_ratio(damping_ratio, "damping_ratio")
    return 1.0 / (2.0 * zeta)


def amplification_db(damping_ratio):
    """Return the resonant amplification of a mode expressed in decibels."""
    return 20.0 * math.log10(modal_amplification(damping_ratio))


def required_attenuation_db(damping_ratio, required_gain_margin_db):
    """Return the loop attenuation a mode demands: its peak plus the margin."""
    if not isinstance(required_gain_margin_db, (int, float)) or isinstance(
        required_gain_margin_db, bool
    ):
        raise ValueError("required_gain_margin_db must be a real number")
    margin = float(required_gain_margin_db)
    if not math.isfinite(margin):
        raise ValueError("required_gain_margin_db must be finite")
    if margin < 0.0:
        raise ValueError("required_gain_margin_db must be non-negative")
    return amplification_db(damping_ratio) + margin


def rolloff_attenuation_db(bandwidth_hz, mode_frequency_hz, slope_db_per_octave):
    """Return the attenuation the loop roll-off supplies at the mode frequency."""
    band_hz = validate_positive(bandwidth_hz, "bandwidth_hz")
    mode_hz = validate_positive(mode_frequency_hz, "mode_frequency_hz")
    slope = validate_positive(slope_db_per_octave, "slope_db_per_octave")
    if mode_hz <= band_hz:
        return 0.0
    octaves = math.log(mode_hz / band_hz) / math.log(2.0)
    return slope * octaves


def damping_from_overshoot(overshoot_fraction):
    """Recover the second-order damping ratio from a measured step overshoot."""
    if not isinstance(overshoot_fraction, (int, float)) or isinstance(
        overshoot_fraction, bool
    ):
        raise ValueError("overshoot_fraction must be a real number")
    overshoot = float(overshoot_fraction)
    if not math.isfinite(overshoot):
        raise ValueError("overshoot_fraction must be finite")
    if overshoot <= 0.0 or overshoot >= 1.0:
        raise ValueError(
            "overshoot_fraction must lie strictly between 0 and 1, got %r"
            % (overshoot_fraction,)
        )
    log_overshoot = math.log(overshoot)
    return -log_overshoot / math.sqrt(math.pi * math.pi + log_overshoot * log_overshoot)


def overshoot_from_damping(damping_ratio):
    """Return the step overshoot fraction a second-order damping ratio gives."""
    zeta = validate_damping_ratio(damping_ratio, "damping_ratio")
    return math.exp(-math.pi * zeta / math.sqrt(1.0 - zeta * zeta))


def settling_time_s(damping_ratio, natural_frequency_hz, band_fraction=0.02):
    """Return the settling time into a band around the commanded position."""
    zeta = validate_damping_ratio(damping_ratio, "damping_ratio")
    freq = validate_positive(natural_frequency_hz, "natural_frequency_hz")
    if not isinstance(band_fraction, (int, float)) or isinstance(band_fraction, bool):
        raise ValueError("band_fraction must be a real number")
    band = float(band_fraction)
    if not math.isfinite(band) or band <= 0.0 or band >= 1.0:
        raise ValueError("band_fraction must lie strictly between 0 and 1")
    omega_n = 2.0 * math.pi * freq
    envelope = band * math.sqrt(1.0 - zeta * zeta)
    return -math.log(envelope) / (zeta * omega_n)


def assess_mode_separation(
    modes,
    bandwidth_hz,
    separation_factor,
    slope_db_per_octave,
    required_gain_margin_db,
):
    """Grade every flexible mode against the declared bandwidth and roll-off."""
    validated = validate_modes(modes)
    band_hz = validate_positive(bandwidth_hz, "bandwidth_hz")
    factor = validate_positive(separation_factor, "separation_factor")
    if factor < 1.0:
        raise ValueError("separation_factor below unity places the mode inside the loop")
    records = []
    for mode in validated:
        mode_hz = mode["frequency_hz"]
        ratio = mode_hz / band_hz
        supplied = rolloff_attenuation_db(band_hz, mode_hz, slope_db_per_octave)
        demanded = required_attenuation_db(
            mode["damping_ratio"], required_gain_margin_db
        )
        inside_loop = mode_hz < band_hz or math.isclose(
            mode_hz, band_hz, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0
        )
        separated = ratio > factor or math.isclose(
            ratio, factor, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0
        )
        attenuated = supplied > demanded or math.isclose(
            supplied, demanded, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE
        )
        records.append(
            {
                "name": mode["name"],
                "frequency_hz": mode_hz,
                "damping_ratio": mode["damping_ratio"],
                "separation_ratio": ratio,
                "inside_bandwidth": inside_loop,
                "separation_met": separated and not inside_loop,
                "amplification_db": amplification_db(mode["damping_ratio"]),
                "required_attenuation_db": demanded,
                "supplied_attenuation_db": supplied,
                "attenuation_met": attenuated and not inside_loop,
                "damping_assumption_credible": (
                    mode["damping_ratio"] <= CREDIBLE_MODAL_DAMPING_CAP
                    or mode["damping_measured"]
                ),
            }
        )
    return records


def assess_closed_loop_damping(spec):
    """Grade the closed-loop damping ratio against the required minimum."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = spec.get("required_closed_loop_damping")
    required_zeta = validate_damping_ratio(
        required, "required_closed_loop_damping", allow_unity=True
    )
    declared = spec.get("closed_loop_damping")
    overshoot = spec.get("measured_overshoot")
    if declared is None and overshoot is None:
        raise ValueError(
            "spec needs closed_loop_damping or measured_overshoot to grade damping"
        )
    if declared is not None:
        achieved = validate_damping_ratio(
            declared, "closed_loop_damping", allow_unity=True
        )
        source = "declared"
    else:
        achieved = damping_from_overshoot(overshoot)
        source = "recovered-from-overshoot"
    met = achieved > required_zeta or math.isclose(
        achieved, required_zeta, rel_tol=0.0, abs_tol=COMPARISON_TOLERANCE
    )
    record = {
        "achieved_damping_ratio": achieved,
        "required_damping_ratio": required_zeta,
        "damping_source": source,
        "damping_met": met,
    }
    natural = spec.get("closed_loop_natural_frequency_hz")
    if natural is not None:
        record["settling_time_s"] = settling_time_s(
            achieved, natural, spec.get("settling_band_fraction", 0.02)
        )
    return record


def assess_bandwidth_damping(spec):
    """Run the full clause 4.7.8.3-4.7.8.4 bandwidth and damping assessment.

    spec keys: bandwidth_hz, structural_modes, separation_factor,
    rolloff_db_per_octave, required_gain_margin_db,
    required_closed_loop_damping, and one of closed_loop_damping or
    measured_overshoot; optional closed_loop_natural_frequency_hz and
    settling_band_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "bandwidth_hz",
        "structural_modes",
        "separation_factor",
        "rolloff_db_per_octave",
        "required_gain_margin_db",
        "required_closed_loop_damping",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    band_hz = validate_positive(spec["bandwidth_hz"], "bandwidth_hz")
    modes = validate_modes(spec["structural_modes"])
    factor = validate_positive(spec["separation_factor"], "separation_factor")
    records = assess_mode_separation(
        modes,
        band_hz,
        factor,
        spec["rolloff_db_per_octave"],
        spec["required_gain_margin_db"],
    )
    damping = assess_closed_loop_damping(spec)
    ceiling = max_control_bandwidth_hz(modes[0]["frequency_hz"], factor)
    bandwidth_ok = band_hz < ceiling or math.isclose(
        band_hz, ceiling, rel_tol=COMPARISON_TOLERANCE, abs_tol=0.0
    )
    findings = []
    if not bandwidth_ok:
        findings.append(
            "bandwidth %.4f Hz exceeds the %.4f Hz ceiling the %s mode sets at a "
            "separation factor of %.2f" % (band_hz, ceiling, modes[0]["name"], factor)
        )
    for record in records:
        if record["inside_bandwidth"]:
            findings.append(
                "mode %s at %.4f Hz sits inside the control bandwidth"
                % (record["name"], record["frequency_hz"])
            )
            continue
        if not record["separation_met"]:
            findings.append(
                "mode %s is only %.2f times the bandwidth, below the required %.2f"
                % (record["name"], record["separation_ratio"], factor)
            )
        if not record["attenuation_met"]:
            findings.append(
                "roll-off gives %.2f dB at mode %s but its peak plus margin demands "
                "%.2f dB"
                % (
                    record["supplied_attenuation_db"],
                    record["name"],
                    record["required_attenuation_db"],
                )
            )
        if not record["damping_assumption_credible"]:
            findings.append(
                "mode %s assumes a damping ratio of %.4f without measured evidence"
                % (record["name"], record["damping_ratio"])
            )
    if not damping["damping_met"]:
        findings.append(
            "closed-loop damping %.4f is below the required %.4f"
            % (damping["achieved_damping_ratio"], damping["required_damping_ratio"])
        )
    return {
        "bandwidth_hz": band_hz,
        "bandwidth_ceiling_hz": ceiling,
        "bandwidth_within_ceiling": bandwidth_ok,
        "separation_factor": factor,
        "mode_records": records,
        "damping": damping,
        "compliant": not findings,
        "findings": findings,
    }
