#!/usr/bin/env python3
"""Single-carrier multipactor margin overview -- ECSS-E-ST-20-01C clause 4.6.1.

Deterministic, offline, standard-library-only implementation of the margin
scheme introduced by the clause:

* categorize an operating condition as continuous-wave or pulsed-carrier;
* reduce it to the governing carrier-power the multipactor-margin applies to
  (peak-envelope-power for a pulsed condition, derived from the duty-cycle
  when only the duty-averaged level is on record);
* screen a pulsed condition against the discharge-build-up-time so a
  build-up-limited short pulse is reported as a justification obligation and
  never as an automatic credit;
* convert a multipactor-threshold-power and a governing carrier-power into an
  achieved decibel multipactor-margin;
* compare that against the nominal value owed by the margin family and the
  carrier mode, taken from a declared project margin-policy table.

The numeric policy table below is a default that a project replaces with its
applicable clause 4.6 values; nothing in the module hard-codes a pass.

The clause is cited as the anchor only; no standard text is reproduced.
"""

import math

CONTINUOUS_WAVE = "continuous-wave"
PULSED_CARRIER = "pulsed-carrier"

CARRIER_MODES = (CONTINUOUS_WAVE, PULSED_CARRIER)

#: Accepted spellings for the two single-carrier envelope categories.
CARRIER_MODE_ALIASES = {
    "continuous-wave": CONTINUOUS_WAVE,
    "continuous_wave": CONTINUOUS_WAVE,
    "cw": CONTINUOUS_WAVE,
    "steady-carrier": CONTINUOUS_WAVE,
    "pulsed-carrier": PULSED_CARRIER,
    "pulsed_carrier": PULSED_CARRIER,
    "pulsed": PULSED_CARRIER,
    "duty-cycled": PULSED_CARRIER,
}

ANALYSIS_MARGIN = "analysis-margin"
TEST_MARGIN = "multipactor-test-margin"

MARGIN_FAMILIES = (ANALYSIS_MARGIN, TEST_MARGIN)

#: Project margin-policy table (decibel owed per margin family, per carrier
#: mode). Replace with the values declared for the programme.
DEFAULT_NOMINAL_MARGIN_DB = {
    ANALYSIS_MARGIN: {CONTINUOUS_WAVE: 6.0, PULSED_CARRIER: 6.0},
    TEST_MARGIN: {CONTINUOUS_WAVE: 3.0, PULSED_CARRIER: 4.0},
}

#: Decibel comparison tolerance. A margin is a base-ten logarithm, so an
#: exactly-met requirement can land a few units in the last place low; the
#: tolerance absorbs that representation error without widening the
#: engineering requirement.
MARGIN_TOLERANCE_DB = 1e-9

#: Relative tolerance for the pulse-width versus build-up-time comparison,
#: for the same reason (both sides are derived quantities).
TIME_TOLERANCE_REL = 1e-12

#: Default electron-multiplication model for the build-up screen: a single
#: seed electron growing to a detectable population.
DEFAULT_SEED_ELECTRONS = 1.0
DEFAULT_DETECTABLE_ELECTRONS = 1.0e6
DEFAULT_GROWTH_PER_CYCLE = 1.05


def _require_real(name, value):
    """Return value as a float, raising ValueError when it is not finite."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    """Return value as a strictly positive float or raise ValueError."""
    value = _require_real(name, value)
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return value


def normalize_carrier_mode(mode):
    """Map a carrier-mode spelling onto its canonical category.

    Raises ValueError for an unrecognized mode -- a condition whose envelope
    category is unknown cannot be reduced to a governing carrier-power.
    """
    if not isinstance(mode, str):
        raise ValueError("carrier mode must be a string, got %r" % (mode,))
    key = mode.strip().lower()
    if key not in CARRIER_MODE_ALIASES:
        raise ValueError(
            "unrecognized carrier mode %r; expected one of %s"
            % (mode, ", ".join(sorted(set(CARRIER_MODE_ALIASES))))
        )
    return CARRIER_MODE_ALIASES[key]


def governing_carrier_power_w(condition):
    """Reduce an operating condition to the carrier-power the margin is taken
    against.

    Continuous-wave: the steady carrier level.
    Pulsed-carrier: the peak-envelope-power, either stated directly or
    recovered from the duty-averaged level and the duty-cycle.

    Returns a mapping with the canonical mode, the governing power in watt
    and the basis used. Raises ValueError on a missing or invalid level.
    """
    if not isinstance(condition, dict):
        raise ValueError("condition must be a mapping, got %r" % (condition,))
    mode = normalize_carrier_mode(condition.get("mode"))
    if mode == CONTINUOUS_WAVE:
        if "carrier_power_w" not in condition:
            raise ValueError(
                "continuous-wave condition requires 'carrier_power_w'"
            )
        power = _require_positive("carrier_power_w", condition["carrier_power_w"])
        basis = "steady-carrier-power"
        return {"mode": mode, "governing_power_w": power, "basis": basis}

    if "peak_power_w" in condition:
        power = _require_positive("peak_power_w", condition["peak_power_w"])
        return {
            "mode": mode,
            "governing_power_w": power,
            "basis": "stated-peak-envelope-power",
        }
    if "average_power_w" in condition:
        average = _require_positive("average_power_w", condition["average_power_w"])
        duty = _require_real("duty_cycle", condition.get("duty_cycle"))
        if duty <= 0.0 or duty > 1.0:
            raise ValueError(
                "duty_cycle must lie in (0, 1], got %r" % (condition.get("duty_cycle"),)
            )
        return {
            "mode": mode,
            "governing_power_w": average / duty,
            "basis": "peak-recovered-from-duty-cycle",
        }
    raise ValueError(
        "pulsed-carrier condition requires 'peak_power_w' or "
        "'average_power_w' together with 'duty_cycle'"
    )


def discharge_build_up_time_s(
    frequency_hz,
    growth_per_cycle=DEFAULT_GROWTH_PER_CYCLE,
    seed_electrons=DEFAULT_SEED_ELECTRONS,
    detectable_electrons=DEFAULT_DETECTABLE_ELECTRONS,
):
    """Time for a seed electron population to multiply to a detectable level.

    The population grows by a constant factor per radio-frequency cycle; the
    cycle count needed is the logarithm of the population ratio divided by the
    logarithm of the per-cycle growth, and the time follows by dividing by the
    carrier frequency.
    """
    frequency_hz = _require_positive("frequency_hz", frequency_hz)
    growth_per_cycle = _require_positive("growth_per_cycle", growth_per_cycle)
    if growth_per_cycle <= 1.0:
        raise ValueError(
            "growth_per_cycle must exceed 1.0 for a discharge to build up, got %r"
            % (growth_per_cycle,)
        )
    seed_electrons = _require_positive("seed_electrons", seed_electrons)
    detectable_electrons = _require_positive(
        "detectable_electrons", detectable_electrons
    )
    if detectable_electrons <= seed_electrons:
        raise ValueError(
            "detectable_electrons (%r) must exceed seed_electrons (%r)"
            % (detectable_electrons, seed_electrons)
        )
    cycles = math.log(detectable_electrons / seed_electrons) / math.log(
        growth_per_cycle
    )
    return cycles / frequency_hz


def pulse_supports_build_up(pulse_width_s, build_up_time_s):
    """True when the pulse is long enough for the discharge to develop.

    A pulse exactly as long as the build-up-time supports it; the comparison
    absorbs the representation error of two derived quantities rather than
    widening the physical criterion.
    """
    pulse_width_s = _require_positive("pulse_width_s", pulse_width_s)
    build_up_time_s = _require_positive("build_up_time_s", build_up_time_s)
    if math.isclose(pulse_width_s, build_up_time_s, rel_tol=TIME_TOLERANCE_REL):
        return True
    return pulse_width_s > build_up_time_s


def achieved_margin_db(threshold_power_w, operating_power_w):
    """Decibel distance from the operating point up to the multipactor
    threshold. Negative when the gap already runs above its threshold."""
    threshold_power_w = _require_positive("threshold_power_w", threshold_power_w)
    operating_power_w = _require_positive("operating_power_w", operating_power_w)
    return 10.0 * math.log10(threshold_power_w / operating_power_w)


def power_limit_for_margin_w(threshold_power_w, required_margin_db):
    """Highest carrier-power that still holds the required decibel margin."""
    threshold_power_w = _require_positive("threshold_power_w", threshold_power_w)
    required_margin_db = _require_real("required_margin_db", required_margin_db)
    if required_margin_db < 0.0:
        raise ValueError(
            "required_margin_db must not be negative, got %r" % (required_margin_db,)
        )
    return threshold_power_w / (10.0 ** (required_margin_db / 10.0))


def nominal_margin_requirement_db(margin_family, carrier_mode, policy=None):
    """Nominal decibel value owed by a margin family for a carrier mode."""
    if margin_family not in MARGIN_FAMILIES:
        raise ValueError(
            "unrecognized margin family %r; expected one of %s"
            % (margin_family, ", ".join(MARGIN_FAMILIES))
        )
    mode = normalize_carrier_mode(carrier_mode)
    table = DEFAULT_NOMINAL_MARGIN_DB if policy is None else policy
    if margin_family not in table:
        raise ValueError(
            "margin policy declares no entry for family %r" % (margin_family,)
        )
    family_table = table[margin_family]
    if mode not in family_table:
        raise ValueError(
            "margin policy declares no %r entry for carrier mode %r"
            % (margin_family, mode)
        )
    return _require_real("nominal margin", family_table[mode])


def assess_single_carrier_condition(condition, policy=None):
    """Grade one operating condition against its nominal multipactor-margin.

    Returns a record carrying the governing carrier-power, the achieved and
    required decibel values, the shortfall, the compliance verdict and any
    build-up finding raised by a pulsed condition.
    """
    reduced = governing_carrier_power_w(condition)
    threshold = _require_positive(
        "threshold_power_w", condition.get("threshold_power_w")
    )
    family = condition.get("margin_family", ANALYSIS_MARGIN)
    required = nominal_margin_requirement_db(family, reduced["mode"], policy)
    achieved = achieved_margin_db(threshold, reduced["governing_power_w"])

    findings = []
    build_up_status = "not-screened"
    if reduced["mode"] == PULSED_CARRIER and "pulse_width_s" in condition:
        if "frequency_hz" not in condition:
            raise ValueError(
                "pulsed build-up screen requires 'frequency_hz' alongside "
                "'pulse_width_s'"
            )
        build_up = discharge_build_up_time_s(
            condition["frequency_hz"],
            condition.get("growth_per_cycle", DEFAULT_GROWTH_PER_CYCLE),
            condition.get("seed_electrons", DEFAULT_SEED_ELECTRONS),
            condition.get("detectable_electrons", DEFAULT_DETECTABLE_ELECTRONS),
        )
        if pulse_supports_build_up(condition["pulse_width_s"], build_up):
            build_up_status = "build-up-supported"
        else:
            build_up_status = "build-up-limited"
            findings.append(
                "build-up-limited short pulse: the discharge cannot reach a "
                "detectable level within the pulse, but the seeding and "
                "yield assumptions owe a justification before any credit"
            )

    compliant = achieved >= required - MARGIN_TOLERANCE_DB
    shortfall = 0.0 if compliant else required - achieved
    if not compliant:
        findings.append(
            "multipactor-margin shortfall of %.3f decibel against the %s "
            "nominal value" % (shortfall, family)
        )
    return {
        "identifier": condition.get("identifier", "unnamed-condition"),
        "mode": reduced["mode"],
        "power_basis": reduced["basis"],
        "governing_power_w": reduced["governing_power_w"],
        "threshold_power_w": threshold,
        "margin_family": family,
        "achieved_margin_db": achieved,
        "required_margin_db": required,
        "shortfall_db": shortfall,
        "allowed_power_w": power_limit_for_margin_w(threshold, required),
        "build_up_status": build_up_status,
        "compliant": compliant,
        "findings": findings,
    }


def summarize_margin_overview(conditions, policy=None):
    """Roll a unit's operating conditions up into one margin-overview record."""
    if not isinstance(conditions, (list, tuple)) or not conditions:
        raise ValueError("conditions must be a non-empty list of mappings")
    records = [assess_single_carrier_condition(c, policy) for c in conditions]
    non_compliant = [r["identifier"] for r in records if not r["compliant"]]
    build_up_limited = [
        r["identifier"] for r in records if r["build_up_status"] == "build-up-limited"
    ]
    worst = max(r["shortfall_db"] for r in records)
    return {
        "condition_count": len(records),
        "compliant_count": sum(1 for r in records if r["compliant"]),
        "non_compliant": non_compliant,
        "build_up_limited": build_up_limited,
        "worst_shortfall_db": worst,
        "unit_compliant": not non_compliant,
        "records": records,
    }
