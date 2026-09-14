#!/usr/bin/env python3
"""Combined ultraviolet photon irradiation and thermal anneal run on bare cells.

Anchor: ECSS-E-ST-20-08C clause 7.5.15. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two stresses are applied to the same bare cell in a fixed order, and the
result only means something when both of them were really delivered:

    exposure    the cell is held under an ultraviolet source in vacuum
                until the declared equivalent sun hours have accumulated,
                at a cell temperature inside the declared window. Dose,
                temperature and pressure are all part of the stress; a
                run short on any of them exercised a milder cell than
                the one the mission flies
    anneal      the exposed cell is soaked at a declared temperature for
                a declared time, to give back whatever part of the loss
                was reversible
    accounting  the ultraviolet loss is split into the share the anneal
                returned and the residual the mission carries for the
                rest of the life. Only the residual is a degradation
                budget entry; the recovered share is a property of the
                test, not of the flight article

The order matters more than it looks. A soak recorded before the exposure
it is supposed to recover has annealed nothing, and the post-anneal
reading is then just a second baseline. A run in that order is stopped
rather than sentenced.

An apparent recovery past the pre-exposure baseline is treated as
instrument drift, not as a gain. Ultraviolet exposure does not make a
cell better than it started, so a post-anneal reading above the baseline
by more than the declared repeatability says the two measurements were
not taken under the same reference conditions.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

STEP_BASELINE = "baseline-measurement"
STEP_EXPOSURE = "ultraviolet-exposure"
STEP_INTERIM = "post-exposure-measurement"
STEP_ANNEAL = "thermal-anneal"
STEP_FINAL = "post-anneal-measurement"

REQUIRED_SEQUENCE = (
    STEP_BASELINE,
    STEP_EXPOSURE,
    STEP_INTERIM,
    STEP_ANNEAL,
    STEP_FINAL,
)

RECOVERY_COMPLETE = "recovery-complete"
RECOVERY_PARTIAL = "recovery-partial"
RECOVERY_NONE = "recovery-none"
RECOVERY_OVERSHOOT = "recovery-overshoot"
RECOVERY_NOT_APPLICABLE = "recovery-not-applicable"

RECOVERY_CATEGORIES = (
    RECOVERY_COMPLETE,
    RECOVERY_PARTIAL,
    RECOVERY_NONE,
    RECOVERY_OVERSHOOT,
    RECOVERY_NOT_APPLICABLE,
)

PROFILE_AS_DECLARED = "profile-as-declared"
PROFILE_SHORT = "profile-short"
PROFILE_OUT_OF_ORDER = "profile-out-of-order"

SPECIMEN_QUALIFIED = "specimen-qualified"
SPECIMEN_REJECTED = "specimen-rejected"
SPECIMEN_NOT_EVALUATED = "specimen-not-evaluated"

SPECIMEN_VERDICTS = (
    SPECIMEN_QUALIFIED,
    SPECIMEN_REJECTED,
    SPECIMEN_NOT_EVALUATED,
)

LOT_QUALIFIED = "lot-qualified"
LOT_OPEN = "lot-open"

# Declared qualification policy: project numbers, not physical constants.
DEFAULT_PHOTON_POLICY = {
    "required_equivalent_sun_hours": 1000.0,
    "min_exposure_temperature_c": 20.0,
    "max_exposure_temperature_c": 80.0,
    "max_exposure_pressure_pa": 1.0e-3,
    "min_anneal_soak_temperature_c": 60.0,
    "max_anneal_soak_temperature_c": 120.0,
    "min_anneal_soak_hours": 2.0,
    "max_residual_power_loss_fraction": 0.02,
    "min_full_recovery_share": 0.98,
    "max_recovery_overshoot_fraction": 0.005,
    "min_specimens": 3,
    "max_reject_fraction": 0.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(left, right):
    return math.isclose(left, right, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_fraction(name, value, minimum=0.0, maximum=1.0):
    value = _require_number(name, value)
    if value < minimum or value > maximum:
        raise ValueError(
            "%s must lie between %s and %s, got %r" % (name, minimum, maximum, value)
        )
    return value


def validate_photon_policy(policy):
    """Check a photon irradiation and anneal policy declares a usable profile."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_positive(
        "required_equivalent_sun_hours", policy.get("required_equivalent_sun_hours")
    )
    low = _require_number(
        "min_exposure_temperature_c", policy.get("min_exposure_temperature_c")
    )
    high = _require_number(
        "max_exposure_temperature_c", policy.get("max_exposure_temperature_c")
    )
    if not high > low:
        raise ValueError(
            "the exposure temperature window closes at or below where it opens "
            "(%r to %r)" % (low, high)
        )
    _require_positive(
        "max_exposure_pressure_pa", policy.get("max_exposure_pressure_pa")
    )
    soak_low = _require_number(
        "min_anneal_soak_temperature_c", policy.get("min_anneal_soak_temperature_c")
    )
    soak_high = _require_number(
        "max_anneal_soak_temperature_c", policy.get("max_anneal_soak_temperature_c")
    )
    if not soak_high > soak_low:
        raise ValueError(
            "the anneal soak window closes at or below where it opens (%r to %r)"
            % (soak_low, soak_high)
        )
    _require_positive("min_anneal_soak_hours", policy.get("min_anneal_soak_hours"))
    _require_fraction(
        "max_residual_power_loss_fraction",
        policy.get("max_residual_power_loss_fraction"),
    )
    _require_fraction(
        "min_full_recovery_share", policy.get("min_full_recovery_share"), 0.0, 1.0
    )
    _require_fraction(
        "max_recovery_overshoot_fraction",
        policy.get("max_recovery_overshoot_fraction"),
    )
    minimum = policy.get("min_specimens")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("min_specimens must be a positive integer, got %r" % (minimum,))
    _require_fraction("max_reject_fraction", policy.get("max_reject_fraction"))
    return policy


def validate_sequence(steps):
    """Refuse a run whose steps did not happen in the order the clause needs.

    The soak has to follow the exposure it is meant to recover, and each of
    the three measurements has to sit where it can mean something: one before
    the exposure, one between exposure and soak, one after the soak.
    """
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of step names")
    read = [_require_text("step", step) for step in steps]
    unknown = [step for step in read if step not in REQUIRED_SEQUENCE]
    if unknown:
        raise ValueError("run declares unknown steps: %s" % ", ".join(sorted(unknown)))
    missing = [step for step in REQUIRED_SEQUENCE if step not in read]
    if missing:
        return {
            "status": PROFILE_SHORT,
            "steps": tuple(read),
            "findings": [
                "run is missing the step %s, so the sequence carries no evidence for it"
                % step
                for step in missing
            ],
        }
    repeated = sorted({step for step in read if read.count(step) > 1})
    if repeated:
        raise ValueError("run declares the step %s twice" % ", ".join(repeated))
    if tuple(read) != REQUIRED_SEQUENCE:
        return {
            "status": PROFILE_OUT_OF_ORDER,
            "steps": tuple(read),
            "findings": [
                "run recorded its steps as %s, so a measurement or the soak sits "
                "where it cannot describe the stress before it" % " then ".join(read)
            ],
        }
    return {"status": PROFILE_AS_DECLARED, "steps": tuple(read), "findings": []}


def read_exposure(exposure, policy=DEFAULT_PHOTON_POLICY):
    """Read one ultraviolet exposure record and say whether it met the profile."""
    validate_photon_policy(policy)
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping, got %r" % (exposure,))
    hours = _require_non_negative(
        "equivalent_sun_hours", exposure.get("equivalent_sun_hours")
    )
    temperature = _require_number("temperature_c", exposure.get("temperature_c"))
    pressure = _require_positive("pressure_pa", exposure.get("pressure_pa"))
    findings = []
    required = float(policy["required_equivalent_sun_hours"])
    if not _at_least(hours, required):
        findings.append(
            "exposure accumulated %.1f equivalent sun hours against the %.1f the "
            "profile declares" % (hours, required)
        )
    if not _at_least(temperature, float(policy["min_exposure_temperature_c"])) or not (
        _at_most(temperature, float(policy["max_exposure_temperature_c"]))
    ):
        findings.append(
            "exposure ran at %.1f C, outside the declared window of %.1f C to %.1f C"
            % (
                temperature,
                float(policy["min_exposure_temperature_c"]),
                float(policy["max_exposure_temperature_c"]),
            )
        )
    if not _at_most(pressure, float(policy["max_exposure_pressure_pa"])):
        findings.append(
            "exposure ran at %.3e Pa, above the %.3e Pa the profile allows, so the "
            "cell saw a filtered ultraviolet spectrum"
            % (pressure, float(policy["max_exposure_pressure_pa"]))
        )
    return {
        "equivalent_sun_hours": hours,
        "temperature_c": temperature,
        "pressure_pa": pressure,
        "status": PROFILE_AS_DECLARED if not findings else PROFILE_SHORT,
        "findings": findings,
    }


def read_anneal(anneal, policy=DEFAULT_PHOTON_POLICY):
    """Read one thermal anneal record and say whether it met the profile."""
    validate_photon_policy(policy)
    if not isinstance(anneal, dict):
        raise ValueError("anneal must be a mapping, got %r" % (anneal,))
    temperature = _require_number(
        "soak_temperature_c", anneal.get("soak_temperature_c")
    )
    hours = _require_non_negative("soak_hours", anneal.get("soak_hours"))
    findings = []
    if not _at_least(
        temperature, float(policy["min_anneal_soak_temperature_c"])
    ) or not _at_most(temperature, float(policy["max_anneal_soak_temperature_c"])):
        findings.append(
            "soak held %.1f C, outside the declared window of %.1f C to %.1f C"
            % (
                temperature,
                float(policy["min_anneal_soak_temperature_c"]),
                float(policy["max_anneal_soak_temperature_c"]),
            )
        )
    if not _at_least(hours, float(policy["min_anneal_soak_hours"])):
        findings.append(
            "soak lasted %.2f h against the %.2f h the profile declares"
            % (hours, float(policy["min_anneal_soak_hours"]))
        )
    return {
        "soak_temperature_c": temperature,
        "soak_hours": hours,
        "status": PROFILE_AS_DECLARED if not findings else PROFILE_SHORT,
        "findings": findings,
    }


def relative_loss(reference_w, measured_w):
    """The share of the reference power a later measurement has given up."""
    reference = _require_positive("reference_w", reference_w)
    measured = _require_non_negative("measured_w", measured_w)
    return (reference - measured) / reference


def recovered_share(pre_exposure_w, post_exposure_w, post_anneal_w):
    """The share of the ultraviolet loss the soak gave back.

    Returns None where the exposure took nothing away, because there is then
    no loss for a recovery share to be a share of.
    """
    pre = _require_positive("pre_exposure_w", pre_exposure_w)
    exposed = _require_non_negative("post_exposure_w", post_exposure_w)
    annealed = _require_non_negative("post_anneal_w", post_anneal_w)
    lost = pre - exposed
    if lost <= 0.0 or _close(lost, 0.0):
        return None
    return (annealed - exposed) / lost


def categorize_recovery(
    pre_exposure_w, post_exposure_w, post_anneal_w, policy=DEFAULT_PHOTON_POLICY
):
    """Group the anneal outcome into complete, partial, none or an overshoot."""
    validate_photon_policy(policy)
    pre = _require_positive("pre_exposure_w", pre_exposure_w)
    annealed = _require_non_negative("post_anneal_w", post_anneal_w)
    overshoot = (annealed - pre) / pre
    if overshoot > float(policy["max_recovery_overshoot_fraction"]) and not _close(
        overshoot, float(policy["max_recovery_overshoot_fraction"])
    ):
        return RECOVERY_OVERSHOOT
    share = recovered_share(pre, post_exposure_w, annealed)
    if share is None:
        return RECOVERY_NOT_APPLICABLE
    if _at_least(share, float(policy["min_full_recovery_share"])):
        return RECOVERY_COMPLETE
    if share > 0.0 and not _close(share, 0.0):
        return RECOVERY_PARTIAL
    return RECOVERY_NONE


def assess_specimen(specimen, policy=DEFAULT_PHOTON_POLICY):
    """Sentence one bare cell taken through the exposure and anneal sequence."""
    validate_photon_policy(policy)
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping, got %r" % (specimen,))
    specimen_id = _require_text("specimen_id", specimen.get("specimen_id"))
    pre = _require_positive("pre_exposure_pmax_w", specimen.get("pre_exposure_pmax_w"))
    exposed = _require_non_negative(
        "post_exposure_pmax_w", specimen.get("post_exposure_pmax_w")
    )
    annealed = _require_non_negative(
        "post_anneal_pmax_w", specimen.get("post_anneal_pmax_w")
    )
    sequence = validate_sequence(specimen.get("steps", list(REQUIRED_SEQUENCE)))
    exposure = read_exposure(specimen.get("exposure"), policy)
    anneal = read_anneal(specimen.get("anneal"), policy)

    findings = []
    for part in (sequence, exposure, anneal):
        findings.extend("%s: %s" % (specimen_id, text) for text in part["findings"])

    exposure_loss = relative_loss(pre, exposed)
    residual_loss = relative_loss(pre, annealed)
    share = recovered_share(pre, exposed, annealed)
    recovery = categorize_recovery(pre, exposed, annealed, policy)

    if recovery == RECOVERY_OVERSHOOT:
        findings.append(
            "%s: the post-anneal reading sits above the pre-exposure baseline by "
            "more than the declared repeatability, so the two measurements were not "
            "taken at the same reference conditions" % specimen_id
        )

    profile_met = (
        sequence["status"] == PROFILE_AS_DECLARED
        and exposure["status"] == PROFILE_AS_DECLARED
        and anneal["status"] == PROFILE_AS_DECLARED
    )
    residual_ok = _at_most(
        residual_loss, float(policy["max_residual_power_loss_fraction"])
    )
    if not residual_ok:
        findings.append(
            "%s: %.4f of the baseline power is still missing after the soak, against "
            "an allowance of %.4f"
            % (
                specimen_id,
                residual_loss,
                float(policy["max_residual_power_loss_fraction"]),
            )
        )

    if not profile_met or recovery == RECOVERY_OVERSHOOT:
        verdict = SPECIMEN_NOT_EVALUATED
    elif residual_ok:
        verdict = SPECIMEN_QUALIFIED
    else:
        verdict = SPECIMEN_REJECTED

    return {
        "specimen_id": specimen_id,
        "verdict": verdict,
        "sequence_status": sequence["status"],
        "exposure": exposure,
        "anneal": anneal,
        "exposure_loss_fraction": exposure_loss,
        "residual_loss_fraction": residual_loss,
        "recovered_share": share,
        "recovery_category": recovery,
        "profile_met": profile_met,
        "residual_within_allowance": residual_ok,
        "findings": findings,
    }


def assess_photon_irradiation_and_annealing(case, policy=DEFAULT_PHOTON_POLICY):
    """Full clause 7.5.15 sweep over one photon irradiation and anneal run."""
    validate_photon_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    specimens = case.get("specimens")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("case specimens must be a non-empty sequence of mappings")
    seen = set()
    records = []
    for specimen in specimens:
        record = assess_specimen(specimen, policy)
        if record["specimen_id"] in seen:
            raise ValueError("case declares specimen %s twice" % record["specimen_id"])
        seen.add(record["specimen_id"])
        records.append(record)
    records.sort(key=lambda entry: entry["specimen_id"])

    findings = []
    for record in records:
        findings.extend(record["findings"])

    grouped = {verdict: [] for verdict in SPECIMEN_VERDICTS}
    for record in records:
        grouped[record["verdict"]].append(record["specimen_id"])
    for verdict in grouped:
        grouped[verdict].sort()

    total = len(records)
    minimum = int(policy["min_specimens"])
    population_ok = total >= minimum
    if not population_ok:
        findings.append(
            "the run carried %d specimens against the %d the profile declares"
            % (total, minimum)
        )
    rejected = len(grouped[SPECIMEN_REJECTED])
    reject_fraction = rejected / float(total)
    reject_ok = _at_most(reject_fraction, float(policy["max_reject_fraction"]))
    if not reject_ok:
        findings.append(
            "the run rejected %.4f of its specimens against an allowance of %.4f"
            % (reject_fraction, float(policy["max_reject_fraction"]))
        )
    not_evaluated = grouped[SPECIMEN_NOT_EVALUATED]
    if not_evaluated:
        findings.append(
            "the run left %s unsentenced, so the lot cannot be closed on this evidence"
            % ", ".join(not_evaluated)
        )

    residuals = [record["residual_loss_fraction"] for record in records]
    return {
        "verdict": LOT_QUALIFIED
        if population_ok and reject_ok and not not_evaluated
        else LOT_OPEN,
        "specimen_records": records,
        "specimens_by_verdict": grouped,
        "specimen_count": total,
        "required_specimen_count": minimum,
        "population_met": population_ok,
        "reject_fraction": reject_fraction,
        "reject_fraction_met": reject_ok,
        "worst_residual_loss_fraction": max(residuals),
        "mean_residual_loss_fraction": sum(residuals) / float(total),
        "findings": findings,
    }
