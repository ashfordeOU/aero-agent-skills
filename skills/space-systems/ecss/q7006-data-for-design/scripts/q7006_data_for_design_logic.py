"""Particle and UV radiation testing: degradation data into the design.

Anchor: ECSS-Q-ST-70-06C, the data clause of particle and UV radiation
testing for space materials (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A radiation campaign ends with beginning-of-life and end-of-life
   values of solar absorptance and infrared emittance. The thermal and
   optical design needs them as a design case, not as a table: a hot
   case and a cold case, each built from the combination that hurts.
2. The hot case takes the worst absorptance the surface ever has and the
   worst emittance it ever has -- the degraded absorptance raised by its
   uncertainty against the lowest emittance lowered by its own. The cold
   case takes the opposite corner. Mixing a beginning-of-life
   absorptance with an end-of-life emittance produces a case the
   spacecraft never sees.
3. Both cases are read through the absorptance over emittance ratio,
   which is what actually sets the equilibrium temperature of a
   sun-facing surface; the temperature itself follows from the ratio and
   the solar flux through a fourth root.
4. Design data may only be issued where the test enveloped the mission.
   A fluence, an ultraviolet dose or a temperature extreme the test
   never reached is an extrapolation, and a design value issued on one
   silently converts a modelling assumption into a qualified number.
5. Where the programme has allocated an end-of-life absorptance, an
   emittance floor or a ratio, the measured data is graded against the
   allocation so the thermal budget learns immediately that it moved.

Stdlib only, offline, deterministic.
"""

STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8

# Emittance below this cannot carry a ratio; a surface this black in the
# infrared is a modelling error, not a coating.
MIN_EMITTANCE = 1.0e-3

# Envelope axes the test has to reach at least as far as the mission.
ENVELOPE_AT_LEAST = (
    "particle_fluence_cm2",
    "uv_dose_esh",
    "max_temperature_c",
)

# Envelope axes the test has to reach at least as low as the mission.
ENVELOPE_AT_MOST = ("min_temperature_c",)

DESIGN_CASES = ("hot", "cold")

# Ratios and envelope comparisons are built from decimal literals, so a
# value sitting exactly on a bound can land a few units in the last place
# past it. This tolerance absorbs that representation error only; no
# envelope is ever widened.
DESIGN_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if minimum is not None and val < minimum - DESIGN_TOLERANCE:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and val > maximum + DESIGN_TOLERANCE:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return val


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _absorptance(label, value):
    return _numeric(label, value, 0.0, 1.0)


def _emittance(label, value):
    emittance = _numeric(label, value, 0.0, 1.0)
    if emittance < MIN_EMITTANCE:
        raise ValueError("%s must be at least %r" % (label, MIN_EMITTANCE))
    return emittance


def clamp_absorptance(value):
    """Keep an absorptance inside the physically available range."""
    return min(1.0, max(0.0, _numeric("absorptance", value)))


def clamp_emittance(value):
    """Keep an emittance inside the physically available range."""
    return min(1.0, max(MIN_EMITTANCE, _numeric("emittance", value)))


def alpha_over_epsilon(absorptance, emittance):
    """Ratio that sets the equilibrium temperature of a sun-facing surface."""
    alpha = _absorptance("absorptance", absorptance)
    epsilon = _emittance("emittance", emittance)
    return alpha / epsilon


def equilibrium_temperature_k(absorptance, emittance, solar_flux_w_m2):
    """Equilibrium temperature of a flat sun-facing radiating surface."""
    ratio = alpha_over_epsilon(absorptance, emittance)
    flux = _numeric("solar_flux_w_m2", solar_flux_w_m2, 0.0)
    if flux <= 0.0:
        raise ValueError("solar_flux_w_m2 must be greater than zero")
    return (ratio * flux / STEFAN_BOLTZMANN_W_M2_K4) ** 0.25


def envelope_ratio(test_value, mission_value):
    """How far the tested exposure reaches relative to the mission one."""
    tested = _numeric("test_value", test_value, 0.0)
    mission = _numeric("mission_value", mission_value, 0.0)
    if mission <= 0.0:
        raise ValueError("mission_value must be greater than zero")
    return tested / mission


def envelope_shortfalls(test_envelope, mission_envelope):
    """Envelope axes on which the test did not reach the mission."""
    if not isinstance(test_envelope, dict) or not isinstance(mission_envelope, dict):
        raise ValueError("envelopes must be mappings")
    shortfalls = []
    for axis in ENVELOPE_AT_LEAST:
        if axis not in test_envelope or axis not in mission_envelope:
            shortfalls.append(axis)
            continue
        tested = _numeric("test %s" % axis, test_envelope[axis])
        mission = _numeric("mission %s" % axis, mission_envelope[axis])
        if tested + DESIGN_TOLERANCE < mission:
            shortfalls.append(axis)
    for axis in ENVELOPE_AT_MOST:
        if axis not in test_envelope or axis not in mission_envelope:
            shortfalls.append(axis)
            continue
        tested = _numeric("test %s" % axis, test_envelope[axis])
        mission = _numeric("mission %s" % axis, mission_envelope[axis])
        if tested > mission + DESIGN_TOLERANCE:
            shortfalls.append(axis)
    return sorted(shortfalls)


def design_pair(record, case):
    """Absorptance and emittance for the hot or the cold design case."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    which = _text("case", case)
    if which not in DESIGN_CASES:
        raise ValueError("unknown design case %r" % (which,))

    alpha_bol = _absorptance("bol_absorptance", record.get("bol_absorptance"))
    alpha_eol = _absorptance("eol_absorptance", record.get("eol_absorptance"))
    eps_bol = _emittance("bol_emittance", record.get("bol_emittance"))
    eps_eol = _emittance("eol_emittance", record.get("eol_emittance"))
    alpha_unc = _numeric(
        "absorptance_uncertainty", record.get("absorptance_uncertainty", 0.0), 0.0
    )
    eps_unc = _numeric(
        "emittance_uncertainty", record.get("emittance_uncertainty", 0.0), 0.0
    )

    if which == "hot":
        alpha = clamp_absorptance(max(alpha_bol, alpha_eol) + alpha_unc)
        epsilon = clamp_emittance(min(eps_bol, eps_eol) - eps_unc)
    else:
        alpha = clamp_absorptance(min(alpha_bol, alpha_eol) - alpha_unc)
        epsilon = clamp_emittance(max(eps_bol, eps_eol) + eps_unc)
    return alpha, epsilon


def build_design_data(record):
    """Turn a radiation degradation record into issuable thermal design data."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")

    material = _text("material", record.get("material"))
    solar_flux = _numeric("solar_flux_w_m2", record.get("solar_flux_w_m2", 1361.0), 0.0)

    findings = []

    alpha_unc = _numeric(
        "absorptance_uncertainty", record.get("absorptance_uncertainty", 0.0), 0.0
    )
    eps_unc = _numeric(
        "emittance_uncertainty", record.get("emittance_uncertainty", 0.0), 0.0
    )
    if alpha_unc <= 0.0 or eps_unc <= 0.0:
        findings.append("design-data-issued-without-an-uncertainty-allowance")

    shortfalls = envelope_shortfalls(
        record.get("test_envelope", {}), record.get("mission_envelope", {})
    )
    if shortfalls:
        findings.append("test-envelope-does-not-cover-the-mission")

    cases = {}
    for case in DESIGN_CASES:
        alpha, epsilon = design_pair(record, case)
        cases[case] = {
            "absorptance": alpha,
            "emittance": epsilon,
            "alpha_over_epsilon": alpha_over_epsilon(alpha, epsilon),
            "equilibrium_temperature_k": equilibrium_temperature_k(
                alpha, epsilon, solar_flux
            ),
        }

    bol_ratio = alpha_over_epsilon(
        record.get("bol_absorptance"), record.get("bol_emittance")
    )
    eol_ratio = alpha_over_epsilon(
        record.get("eol_absorptance"), record.get("eol_emittance")
    )
    ratio_growth = eol_ratio / bol_ratio

    allocated_alpha = record.get("allocated_eol_absorptance")
    if allocated_alpha is not None:
        limit = _absorptance("allocated_eol_absorptance", allocated_alpha)
        if cases["hot"]["absorptance"] > limit + DESIGN_TOLERANCE:
            findings.append("hot-case-absorptance-above-its-allocation")

    allocated_emittance = record.get("allocated_eol_emittance_floor")
    if allocated_emittance is not None:
        floor = _emittance("allocated_eol_emittance_floor", allocated_emittance)
        if cases["hot"]["emittance"] + DESIGN_TOLERANCE < floor:
            findings.append("hot-case-emittance-below-its-allocation")

    allocated_ratio = record.get("allocated_eol_alpha_over_epsilon")
    if allocated_ratio is not None:
        ratio_limit = _numeric("allocated_eol_alpha_over_epsilon", allocated_ratio, 0.0)
        if cases["hot"]["alpha_over_epsilon"] > ratio_limit + DESIGN_TOLERANCE:
            findings.append("hot-case-ratio-above-the-thermal-allocation")

    return {
        "material": material,
        "solar_flux_w_m2": solar_flux,
        "bol_alpha_over_epsilon": bol_ratio,
        "eol_alpha_over_epsilon": eol_ratio,
        "ratio_growth": ratio_growth,
        "envelope_shortfalls": shortfalls,
        "cases": cases,
        "findings": findings,
        "issuable": not findings,
    }
