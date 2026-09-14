#!/usr/bin/env python3
"""Microwave monolithic integrated circuits applied at the intermediate class.

Anchor: ECSS-Q-ST-60-13C clause 5.6.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause governs the use of a microwave monolithic integrated circuit
in commercial form at the intermediate assurance class. An MMIC is not a
catalogue part that can be judged on its datasheet line: the compound
semiconductor channel runs hot under RF drive, the die is usually
delivered bare into a module rather than in its own qualified package,
and the wafer lot behind the die is the real unit of quality.

Four things are computed rather than asserted. The channel temperature
follows from the baseplate temperature, the dissipated power and the
thermal resistance of the path out of the die, and it is the channel and
not the case that ages the part. The margin is taken against the lower of
the class ceiling and the part's own rated channel temperature, so a part
rated below the class ceiling is held to its own rating. The RF drive is
compared with the rated drive as a fraction, because a microwave part run
near its rated drive has no headroom for the gain drop that arrives with
temperature and with life. The median life follows an Arrhenius model
referred to a declared reference life at a reference channel temperature,
which is how a channel temperature becomes a number a mission duration
can be compared against.

Package form decides one further condition. A die delivered bare into a
sealed module, or a part in a hermetic package, carries its own moisture
protection. A part in a non-hermetic plastic package does not, and at
this class it is admissible only where a moisture barrier is declared for
the assembly it sits in.

The evidence list is scored rather than ticked. A subject may be carried
by similarity to an evaluated sibling part at this class, which the class
above does not allow, and similarity is credited below a direct record so
that a part evaluated entirely by analogy cannot read as an evaluated
part.

The policy numbers below are declared project values, not physical
constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

GAAS_MESFET = "gaas-mesfet"
GAAS_PHEMT = "gaas-phemt"
GAN_HEMT = "gan-hemt"
SIGE_BICMOS = "sige-bicmos"
INP_HBT = "inp-hbt"

RECOGNISED_TECHNOLOGIES = (
    GAAS_MESFET,
    GAAS_PHEMT,
    GAN_HEMT,
    SIGE_BICMOS,
    INP_HBT,
)

HERMETIC_PACKAGE = "hermetic-package"
BARE_DIE_IN_SEALED_MODULE = "bare-die-in-sealed-module"
NON_HERMETIC_PACKAGE = "non-hermetic-package"

RECOGNISED_PACKAGE_FORMS = (
    HERMETIC_PACKAGE,
    BARE_DIE_IN_SEALED_MODULE,
    NON_HERMETIC_PACKAGE,
)

SELF_PROTECTING_PACKAGE_FORMS = (HERMETIC_PACKAGE, BARE_DIE_IN_SEALED_MODULE)

WAFER_LOT_PROCESS_MONITOR_DATA = "wafer-lot-process-monitor-data"
RF_PERFORMANCE_SCREENING = "rf-performance-screening"
DIE_VISUAL_INSPECTION = "die-visual-inspection"
BOND_INTEGRITY_EVALUATION = "bond-integrity-evaluation"
MOISTURE_PROTECTION_EVIDENCE = "moisture-protection-evidence"
SINGLE_EVENT_EFFECT_EVALUATION = "single-event-effect-evaluation"

REQUIRED_EVIDENCE = (
    WAFER_LOT_PROCESS_MONITOR_DATA,
    RF_PERFORMANCE_SCREENING,
    DIE_VISUAL_INSPECTION,
    BOND_INTEGRITY_EVALUATION,
    MOISTURE_PROTECTION_EVIDENCE,
    SINGLE_EVENT_EFFECT_EVALUATION,
)

HELD_DIRECTLY = "held-as-a-direct-record"
HELD_BY_SIMILARITY = "held-by-similarity-to-an-evaluated-part"
DECLARED_WITHOUT_RECORD = "declared-without-a-record"
ABSENT = "absent"

HELD_STATES = (HELD_DIRECTLY, HELD_BY_SIMILARITY)

MMIC_NOT_IDENTIFIED = "mmic-part-not-identified"
MMIC_CHANNEL_MARGIN_SHORT = "mmic-channel-temperature-margin-short"
MMIC_RF_DRIVE_EXCEEDED = "mmic-rf-drive-derating-exceeded"
MMIC_MEDIAN_LIFE_SHORT = "mmic-median-life-below-mission-need"
MMIC_MOISTURE_BARRIER_MISSING = "non-hermetic-mmic-without-moisture-barrier"
MMIC_EVIDENCE_SHORT = "mmic-evaluation-evidence-short"
MMIC_MEETS_CLASS_TWO_SCOPE = "mmic-application-meets-class-two-scope"

DEFAULT_MMIC_POLICY = {
    "max_channel_temperature_c": 125.0,
    "min_channel_margin_c": 10.0,
    "max_rf_drive_fraction": 0.7,
    "min_median_life_years": 15.0,
    "min_evidence_share": 1.0,
    "min_weighted_evidence": 0.6,
    "similarity_credit": 0.7,
    "marginal_margin_band_c": 5.0,
    "require_moisture_barrier_for_non_hermetic": True,
}

DEFAULT_LIFE_MODEL = {
    "reference_channel_temperature_c": 125.0,
    "reference_median_life_years": 20.0,
    "activation_energy_ev": 1.5,
}

BOLTZMANN_EV_PER_K = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must sit between zero and one, got %r" % (name, value))
    return number


def _require_temperature(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must sit above absolute zero, got %r" % (name, value)
        )
    return number


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_mmic_policy(policy):
    """Check the application policy is complete and usable."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    ceiling = _require_temperature(
        "max_channel_temperature_c", policy.get("max_channel_temperature_c")
    )
    margin = _require_non_negative(
        "min_channel_margin_c", policy.get("min_channel_margin_c")
    )
    if margin >= ceiling:
        raise ValueError(
            "min_channel_margin_c %g is not below the %g channel ceiling; no "
            "baseplate temperature could ever clear it" % (margin, ceiling)
        )
    drive = _require_fraction(
        "max_rf_drive_fraction", policy.get("max_rf_drive_fraction")
    )
    if drive <= 0.0:
        raise ValueError(
            "max_rf_drive_fraction must be greater than zero, got %r" % (drive,)
        )
    _require_positive("min_median_life_years", policy.get("min_median_life_years"))
    share = _require_fraction("min_evidence_share", policy.get("min_evidence_share"))
    weighted = _require_fraction(
        "min_weighted_evidence", policy.get("min_weighted_evidence")
    )
    if weighted > share:
        raise ValueError(
            "min_weighted_evidence %g is above min_evidence_share %g; a credited "
            "figure can never exceed the plain one" % (weighted, share)
        )
    credit = _require_fraction("similarity_credit", policy.get("similarity_credit"))
    if credit <= 0.0:
        raise ValueError(
            "similarity_credit must be greater than zero, got %r" % (credit,)
        )
    _require_non_negative(
        "marginal_margin_band_c", policy.get("marginal_margin_band_c")
    )
    _require_flag(
        "require_moisture_barrier_for_non_hermetic",
        policy.get("require_moisture_barrier_for_non_hermetic"),
    )
    return policy


def validate_life_model(model):
    """Check the Arrhenius reference the median life is referred to."""
    if not isinstance(model, dict):
        raise ValueError("life model must be a mapping, got %r" % (model,))
    _require_temperature(
        "reference_channel_temperature_c",
        model.get("reference_channel_temperature_c"),
    )
    _require_positive(
        "reference_median_life_years", model.get("reference_median_life_years")
    )
    _require_positive("activation_energy_ev", model.get("activation_energy_ev"))
    return model


def validate_mmic_part(case):
    """Read the part identity, its thermal path and its RF drive."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    reference = _require_label("part_reference", case.get("part_reference", ""))
    technology = _require_label("technology", case.get("technology", ""))
    if technology and technology not in RECOGNISED_TECHNOLOGIES:
        raise ValueError(
            "unrecognised MMIC technology %r; the technology names are fixed"
            % (technology,)
        )
    package = _require_label("package_form", case.get("package_form", ""))
    if package and package not in RECOGNISED_PACKAGE_FORMS:
        raise ValueError(
            "unrecognised package form %r; the package names are fixed" % (package,)
        )
    baseplate = _require_temperature(
        "baseplate_temperature_c", case.get("baseplate_temperature_c")
    )
    dissipated = _require_non_negative(
        "dissipated_power_w", case.get("dissipated_power_w")
    )
    resistance = _require_non_negative(
        "thermal_resistance_c_per_w", case.get("thermal_resistance_c_per_w")
    )
    rated_channel = _require_temperature(
        "rated_channel_temperature_c", case.get("rated_channel_temperature_c")
    )
    applied_rf = _require_non_negative(
        "applied_rf_power_w", case.get("applied_rf_power_w")
    )
    rated_rf = _require_positive("rated_rf_power_w", case.get("rated_rf_power_w"))
    barrier = _require_flag(
        "moisture_barrier_declared", case.get("moisture_barrier_declared", False)
    )
    mission = _require_positive(
        "mission_duration_years", case.get("mission_duration_years")
    )
    return {
        "part_reference": reference,
        "technology": technology,
        "package_form": package,
        "baseplate_temperature_c": baseplate,
        "dissipated_power_w": dissipated,
        "thermal_resistance_c_per_w": resistance,
        "rated_channel_temperature_c": rated_channel,
        "applied_rf_power_w": applied_rf,
        "rated_rf_power_w": rated_rf,
        "moisture_barrier_declared": barrier,
        "mission_duration_years": mission,
    }


def channel_temperature_c(case):
    """Channel temperature from the baseplate up the thermal path."""
    part = validate_mmic_part(case)
    return (
        part["baseplate_temperature_c"]
        + part["dissipated_power_w"] * part["thermal_resistance_c_per_w"]
    )


def governing_channel_ceiling_c(case, policy=DEFAULT_MMIC_POLICY):
    """The lower of the class ceiling and the part's own rated channel."""
    validate_mmic_policy(policy)
    part = validate_mmic_part(case)
    return min(
        float(policy["max_channel_temperature_c"]),
        part["rated_channel_temperature_c"],
    )


def channel_margin_c(case, policy=DEFAULT_MMIC_POLICY):
    """Headroom between the governing ceiling and the channel temperature."""
    return governing_channel_ceiling_c(case, policy) - channel_temperature_c(case)


def rf_drive_fraction(case):
    """Applied RF drive as a fraction of the rated drive."""
    part = validate_mmic_part(case)
    return part["applied_rf_power_w"] / part["rated_rf_power_w"]


def median_life_years(case, model=DEFAULT_LIFE_MODEL):
    """Arrhenius median life referred to the declared reference life.

    A channel running at the reference temperature returns the reference
    life exactly; hotter shortens it and cooler extends it.
    """
    validate_life_model(model)
    channel_k = channel_temperature_c(case) - ABSOLUTE_ZERO_C
    reference_k = float(model["reference_channel_temperature_c"]) - ABSOLUTE_ZERO_C
    scale = float(model["activation_energy_ev"]) / BOLTZMANN_EV_PER_K
    exponent = scale * (1.0 / channel_k - 1.0 / reference_k)
    return float(model["reference_median_life_years"]) * math.exp(exponent)


def validate_evidence_record(entry):
    """Read one declared evaluation evidence item."""
    if not isinstance(entry, dict):
        raise ValueError("evidence entry must be a mapping, got %r" % (entry,))
    subject = _require_label("subject", entry.get("subject"))
    if subject not in REQUIRED_EVIDENCE:
        raise ValueError(
            "unrecognised evidence subject %r; the subject names are fixed"
            % (subject,)
        )
    by_similarity = _require_flag(
        "held_by_similarity on %s" % subject, entry.get("held_by_similarity", False)
    )
    record = _require_label(
        "record_reference on %s" % subject, entry.get("record_reference", "")
    )
    sibling = _require_label(
        "similar_part_reference on %s" % subject,
        entry.get("similar_part_reference", ""),
    )
    if by_similarity and record:
        raise ValueError(
            "%s is declared both as a direct record and as a similarity claim; "
            "it is one or the other" % subject
        )
    return {
        "subject": subject,
        "held_by_similarity": by_similarity,
        "record_reference": record,
        "similar_part_reference": sibling,
    }


def validate_evidence(records):
    """Read every declared evidence item, refusing an empty or repeated set."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("evidence must be a sequence of evidence records")
    if not records:
        raise ValueError("no evaluation evidence is declared for the part")
    checked = []
    seen = set()
    for entry in records:
        item = validate_evidence_record(entry)
        if item["subject"] in seen:
            raise ValueError(
                "evidence subject %r is declared twice" % item["subject"]
            )
        seen.add(item["subject"])
        checked.append(item)
    return tuple(checked)


def evidence_disposition(records, policy=DEFAULT_MMIC_POLICY):
    """How each required evidence subject is held, with its credit."""
    validate_mmic_policy(policy)
    checked = validate_evidence(records)
    credit = float(policy["similarity_credit"])
    declared = {item["subject"]: item for item in checked}
    disposition = {}
    for subject in REQUIRED_EVIDENCE:
        item = declared.get(subject)
        if item is None:
            disposition[subject] = {"state": ABSENT, "credit": 0.0}
            continue
        if item["held_by_similarity"]:
            if item["similar_part_reference"]:
                disposition[subject] = {
                    "state": HELD_BY_SIMILARITY,
                    "credit": credit,
                }
            else:
                disposition[subject] = {
                    "state": DECLARED_WITHOUT_RECORD,
                    "credit": 0.0,
                }
            continue
        if item["record_reference"]:
            disposition[subject] = {"state": HELD_DIRECTLY, "credit": 1.0}
        else:
            disposition[subject] = {"state": DECLARED_WITHOUT_RECORD, "credit": 0.0}
    return disposition


def _evidence_in_state(records, states, policy):
    disposition = evidence_disposition(records, policy)
    return tuple(
        subject
        for subject in REQUIRED_EVIDENCE
        if disposition[subject]["state"] in states
    )


def held_evidence(records, policy=DEFAULT_MMIC_POLICY):
    """Required subjects the evaluation actually holds."""
    return _evidence_in_state(records, HELD_STATES, policy)


def absent_evidence(records, policy=DEFAULT_MMIC_POLICY):
    """Required subjects the evaluation does not declare at all."""
    return _evidence_in_state(records, (ABSENT,), policy)


def unrecorded_evidence(records, policy=DEFAULT_MMIC_POLICY):
    """Subjects declared with neither a record nor a named sibling part."""
    return _evidence_in_state(records, (DECLARED_WITHOUT_RECORD,), policy)


def similarity_evidence(records, policy=DEFAULT_MMIC_POLICY):
    """Subjects carried by similarity rather than by a direct record."""
    return _evidence_in_state(records, (HELD_BY_SIMILARITY,), policy)


def evidence_share(records, policy=DEFAULT_MMIC_POLICY):
    """Share of the required subjects the evaluation holds."""
    return len(held_evidence(records, policy)) / len(REQUIRED_EVIDENCE)


def weighted_evidence(records, policy=DEFAULT_MMIC_POLICY):
    """Credited evidence over the full required subject list."""
    disposition = evidence_disposition(records, policy)
    total = 0.0
    for subject in REQUIRED_EVIDENCE:
        total += disposition[subject]["credit"]
    return total / len(REQUIRED_EVIDENCE)


def thermal_advisories(case, policy=DEFAULT_MMIC_POLICY):
    """Name a channel margin clearing its floor by less than the band.

    These do not move the verdict -- a margin above the floor is a margin --
    but a part clearing the floor by a degree and one clearing it by thirty
    carry the same word, and nobody recovers the difference later from the
    word alone.
    """
    validate_mmic_policy(policy)
    margin = channel_margin_c(case, policy)
    floor = float(policy["min_channel_margin_c"])
    band = float(policy["marginal_margin_band_c"])
    advisories = []
    if _at_least(margin, floor) and _at_most(margin - floor, band):
        advisories.append(
            "the channel clears the %.3g K margin floor by %.3g K, inside the "
            "%.3g K marginal band; the application holds today and is the one "
            "a baseplate rise would take out first" % (floor, margin - floor, band)
        )
    return tuple(advisories)


def assess_mmic_application(case, policy=DEFAULT_MMIC_POLICY, model=DEFAULT_LIFE_MODEL):
    """Full clause 5.6.5 application decision for one MMIC."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_mmic_policy(policy)
    validate_life_model(model)

    findings = []
    advisories = []
    result = {
        "part_reference": None,
        "technology": None,
        "package_form": None,
        "channel_temperature_c": None,
        "channel_margin_c": None,
        "rf_drive_fraction": None,
        "median_life_years": None,
        "evidence_share": None,
        "weighted_evidence": None,
        "absent_evidence": (),
        "unrecorded_evidence": (),
        "similarity_evidence": (),
        "findings": findings,
        "advisories": advisories,
    }

    part = validate_mmic_part(case)
    result["part_reference"] = part["part_reference"]
    result["technology"] = part["technology"]
    result["package_form"] = part["package_form"]
    if (
        not part["part_reference"]
        or not part["technology"]
        or not part["package_form"]
    ):
        findings.append(
            "the part carries no reference, no technology or no package form, "
            "so nothing about its channel or its sealing can be argued"
        )
        result["verdict"] = MMIC_NOT_IDENTIFIED
        return result

    channel = channel_temperature_c(case)
    margin = channel_margin_c(case, policy)
    drive = rf_drive_fraction(case)
    life = median_life_years(case, model)
    result["channel_temperature_c"] = channel
    result["channel_margin_c"] = margin
    result["rf_drive_fraction"] = drive
    result["median_life_years"] = life
    advisories.extend(thermal_advisories(case, policy))

    if not _at_least(margin, float(policy["min_channel_margin_c"])):
        findings.append(
            "the channel reaches %.4g C against a governing ceiling of %.4g C, "
            "leaving %.4g K against the %.4g K the class asks for"
            % (
                channel,
                governing_channel_ceiling_c(case, policy),
                margin,
                float(policy["min_channel_margin_c"]),
            )
        )
        result["verdict"] = MMIC_CHANNEL_MARGIN_SHORT
        return result

    if not _at_most(drive, float(policy["max_rf_drive_fraction"])):
        findings.append(
            "the applied RF drive is %.4g of the rated drive against the %.4g "
            "the class allows, so the gain drop that arrives with temperature "
            "and with life has nowhere to go"
            % (drive, float(policy["max_rf_drive_fraction"]))
        )
        result["verdict"] = MMIC_RF_DRIVE_EXCEEDED
        return result

    needed_life = max(
        float(policy["min_median_life_years"]), part["mission_duration_years"]
    )
    if not _at_least(life, needed_life):
        findings.append(
            "the Arrhenius median life at this channel temperature is %.4g "
            "years against the %.4g years the mission needs"
            % (life, needed_life)
        )
        result["verdict"] = MMIC_MEDIAN_LIFE_SHORT
        return result

    if (
        policy["require_moisture_barrier_for_non_hermetic"]
        and part["package_form"] not in SELF_PROTECTING_PACKAGE_FORMS
        and not part["moisture_barrier_declared"]
    ):
        findings.append(
            "the part sits in a non-hermetic package with no moisture barrier "
            "declared for the assembly around it, so the die is exposed to "
            "whatever the assembly lets through"
        )
        result["verdict"] = MMIC_MOISTURE_BARRIER_MISSING
        return result

    records = case.get("evidence")
    if records is None:
        findings.append(
            "no evaluation evidence is declared, so the wafer lot behind this "
            "die has never been looked at"
        )
        result["verdict"] = MMIC_EVIDENCE_SHORT
        return result

    checked = validate_evidence(records)
    share = evidence_share(checked, policy)
    weighted = weighted_evidence(checked, policy)
    absent = absent_evidence(checked, policy)
    unrecorded = unrecorded_evidence(checked, policy)
    similar = similarity_evidence(checked, policy)
    result["evidence_share"] = share
    result["weighted_evidence"] = weighted
    result["absent_evidence"] = absent
    result["unrecorded_evidence"] = unrecorded
    result["similarity_evidence"] = similar

    for subject in absent:
        findings.append("the evaluation does not declare %s at all" % subject)
    for subject in unrecorded:
        findings.append(
            "%s is declared with neither a record reference nor a named "
            "evaluated sibling part behind it" % subject
        )

    share_short = not _at_least(share, float(policy["min_evidence_share"]))
    weighted_short = not _at_least(weighted, float(policy["min_weighted_evidence"]))
    if share_short or weighted_short:
        findings.append(
            "the evaluation holds %.4g of the required subjects against %.4g, "
            "at a credited %.4g against %.4g"
            % (
                share,
                float(policy["min_evidence_share"]),
                weighted,
                float(policy["min_weighted_evidence"]),
            )
        )
        result["verdict"] = MMIC_EVIDENCE_SHORT
        return result

    result["verdict"] = MMIC_MEETS_CLASS_TWO_SCOPE
    return result
