#!/usr/bin/env python3
"""Short circuit current loss accepted after an ultraviolet exposure sequence.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.15.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Why short circuit current is the measurand
------------------------------------------
Ultraviolet damage in a photovoltaic assembly is an optical loss, not an
electrical one. The junction is unchanged; what changes is how much
light reaches it, because the coverglass adhesive darkened, the
front-surface silicone yellowed or a filter cutoff moved. Short circuit
current is very nearly proportional to the photon flux reaching the
junction and almost independent of the junction's own health, so it is
the most direct electrical read-out of a transmission loss the assembly
has. Open circuit voltage barely moves for the same damage.

What the criterion compares
---------------------------
A loss fraction, and it is a pre-versus-post comparison of the same
specimen. Both illuminated readings are reported back to reference
irradiance and reference cell temperature before the fraction is taken,
because short circuit current moves with irradiance almost linearly and
with temperature through its own small positive coefficient. A
pre-exposure reading at one set of conditions and a post-exposure
reading at another differ even on an undamaged specimen.

Two things sit around the comparison. The exposure sequence has to have
been completed -- a criterion applied after a partial dose passes a
specimen that never met the dose it was supposed to survive. And a
measured gain is reported as a negative loss rather than clamped to
zero, because a large apparent gain points at a measurement or
correction error worth chasing rather than at a specimen that improved
under ultraviolet light.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "DEFAULT_SHORT_CIRCUIT_TEMPERATURE_COEFFICIENT_PER_C",
    "LIMIT_TOLERANCE",
    "REFERENCE_IRRADIANCE_W_M2",
    "REFERENCE_TEMPERATURE_C",
    "assess_ultraviolet_acceptance",
    "correct_short_circuit_current_to_reference",
    "evaluate_specimen_set",
    "mean_loss_fraction",
    "measurement_current_at_reference",
    "sequence_findings",
    "short_circuit_current_loss_fraction",
    "short_circuit_current_retention_ratio",
    "within_limit",
    "worst_case_loss_fraction",
]

# The loss fraction is built from differences and ratios of measured values, so
# an exactly-compliant specimen can land a few units in the last place on the
# wrong side of the limit. Absorb that representation error here instead of
# widening any engineering limit.
LIMIT_TOLERANCE = 1e-9

# Illuminated readings are reported back to these reference conditions before
# any pre/post comparison is formed.
REFERENCE_IRRADIANCE_W_M2 = 1367.0
REFERENCE_TEMPERATURE_C = 25.0

# Relative short circuit current change per degree of cell temperature; small
# and positive. A specimen carrying its own measured value overrides this.
DEFAULT_SHORT_CIRCUIT_TEMPERATURE_COEFFICIENT_PER_C = 0.0005


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    """Return value as a strictly positive finite float."""
    out = _real(value, label)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _fraction(value, label):
    """Return a limit expressed as a fraction in the closed range 0 to 1."""
    out = _real(value, label)
    if out < 0.0 or out > 1.0:
        raise ValueError(
            "%s must be a fraction between 0 and 1, got %g" % (label, out)
        )
    return out


def within_limit(value, limit):
    """Return True when value respects limit, tolerating an exact equality."""
    measured = _real(value, "value")
    bound = _real(limit, "limit")
    if measured < bound:
        return True
    return math.isclose(measured, bound, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def correct_short_circuit_current_to_reference(
    current_a,
    irradiance_w_m2,
    cell_temperature_c,
    temperature_coefficient_per_c=DEFAULT_SHORT_CIRCUIT_TEMPERATURE_COEFFICIENT_PER_C,
    reference_irradiance_w_m2=REFERENCE_IRRADIANCE_W_M2,
    reference_temperature_c=REFERENCE_TEMPERATURE_C,
):
    """Return a measured short circuit current reported to reference conditions."""
    current = _positive(current_a, "current_a")
    irradiance = _positive(irradiance_w_m2, "irradiance_w_m2")
    reference_irradiance = _positive(
        reference_irradiance_w_m2, "reference_irradiance_w_m2"
    )
    temperature = _real(cell_temperature_c, "cell_temperature_c")
    reference_temperature = _real(reference_temperature_c, "reference_temperature_c")
    coefficient = _real(
        temperature_coefficient_per_c, "temperature_coefficient_per_c"
    )
    if coefficient <= -1.0 or coefficient >= 1.0:
        raise ValueError(
            "temperature_coefficient_per_c is a relative change per degree, "
            "got %g" % coefficient
        )
    factor = 1.0 + coefficient * (temperature - reference_temperature)
    if factor <= 0.0:
        raise ValueError(
            "temperature correction factor %g is not positive; the coefficient "
            "and the temperature span are inconsistent" % factor
        )
    return current * (reference_irradiance / irradiance) / factor


def measurement_current_at_reference(record, name="measurement"):
    """Return the reference-condition current of one illuminated reading."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % name)
    for key in ("current_a", "irradiance_w_m2", "cell_temperature_c"):
        if key not in record:
            raise ValueError("%s missing required key '%s'" % (name, key))
    return correct_short_circuit_current_to_reference(
        record["current_a"],
        record["irradiance_w_m2"],
        record["cell_temperature_c"],
        record.get(
            "temperature_coefficient_per_c",
            DEFAULT_SHORT_CIRCUIT_TEMPERATURE_COEFFICIENT_PER_C,
        ),
        record.get("reference_irradiance_w_m2", REFERENCE_IRRADIANCE_W_M2),
        record.get("reference_temperature_c", REFERENCE_TEMPERATURE_C),
    )


def short_circuit_current_loss_fraction(current_before_a, current_after_a):
    """Return the relative short circuit current loss; a gain comes back negative."""
    before = _positive(current_before_a, "current_before_a")
    after = _positive(current_after_a, "current_after_a")
    return (before - after) / before


def short_circuit_current_retention_ratio(current_before_a, current_after_a):
    """Return the fraction of the pre-exposure current still delivered."""
    before = _positive(current_before_a, "current_before_a")
    after = _positive(current_after_a, "current_after_a")
    return after / before


def _evaluate_one_specimen(specimen, index, limit):
    """Return the corrected pre/post comparison for one exposed specimen."""
    if not isinstance(specimen, dict):
        raise ValueError("specimens[%d] must be a mapping" % index)
    for key in ("specimen_id", "pre_exposure", "post_exposure"):
        if key not in specimen:
            raise ValueError("specimens[%d] missing required key '%s'" % (index, key))
    specimen_id = specimen["specimen_id"]
    if not isinstance(specimen_id, str) or not specimen_id.strip():
        raise ValueError(
            "specimens[%d] specimen_id must be a non-empty string" % index
        )
    specimen_id = specimen_id.strip()
    before = measurement_current_at_reference(
        specimen["pre_exposure"], "specimens[%d] pre_exposure" % index
    )
    after = measurement_current_at_reference(
        specimen["post_exposure"], "specimens[%d] post_exposure" % index
    )
    loss = short_circuit_current_loss_fraction(before, after)
    return {
        "specimen_id": specimen_id,
        "current_before_a": before,
        "current_after_a": after,
        "loss_fraction": loss,
        "retention_ratio": short_circuit_current_retention_ratio(before, after),
        "max_loss_fraction": limit,
        "within_limit": within_limit(loss, limit),
    }


def evaluate_specimen_set(specimens, max_loss_fraction):
    """Return one corrected comparison record per exposed specimen."""
    limit = _fraction(max_loss_fraction, "max_loss_fraction")
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("specimens must be a non-empty sequence of records")
    seen = set()
    records = []
    for index, specimen in enumerate(specimens):
        record = _evaluate_one_specimen(specimen, index, limit)
        if record["specimen_id"] in seen:
            raise ValueError(
                "duplicate specimen_id %r in specimens" % record["specimen_id"]
            )
        seen.add(record["specimen_id"])
        records.append(record)
    return records


def worst_case_loss_fraction(records):
    """Return the largest loss fraction in a set of specimen records."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    return max(_real(record["loss_fraction"], "loss_fraction") for record in records)


def mean_loss_fraction(records):
    """Return the mean loss fraction across a set of specimen records."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    total = sum(
        _real(record["loss_fraction"], "loss_fraction") for record in records
    )
    return total / len(records)


def sequence_findings(spec):
    """Return the findings raised by an incomplete ultraviolet exposure sequence."""
    required = _non_negative(
        spec.get("required_equivalent_sun_hours", 0.0),
        "required_equivalent_sun_hours",
    )
    if required == 0.0:
        return []
    if (
        "accumulated_equivalent_sun_hours" not in spec
        or spec["accumulated_equivalent_sun_hours"] is None
    ):
        return [
            "the dose accumulated over the exposure sequence was not recorded; "
            "the required sequence is %g ESH" % required
        ]
    accumulated = _non_negative(
        spec["accumulated_equivalent_sun_hours"], "accumulated_equivalent_sun_hours"
    )
    if accumulated > required or math.isclose(
        accumulated, required, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    ):
        return []
    return [
        "the exposure sequence stopped at %g ESH, short of the required %g ESH, "
        "so the loss criterion is being applied to a partial dose"
        % (accumulated, required)
    ]


def assess_ultraviolet_acceptance(spec):
    """Run the full clause 6.4.3.15.3 post-exposure acceptance assessment.

    spec keys: specimens, max_loss_fraction, optional
    required_equivalent_sun_hours and accumulated_equivalent_sun_hours.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("specimens", "max_loss_fraction"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    findings = list(sequence_findings(spec))
    records = evaluate_specimen_set(spec["specimens"], spec["max_loss_fraction"])
    limit = _fraction(spec["max_loss_fraction"], "max_loss_fraction")
    for record in records:
        if not record["within_limit"]:
            findings.append(
                "specimen %s lost %.4f of its pre-exposure short circuit "
                "current, past the accepted %.4f"
                % (record["specimen_id"], record["loss_fraction"], limit)
            )
    failing = [record["specimen_id"] for record in records if not record["within_limit"]]
    return {
        "specimens": records,
        "max_loss_fraction": limit,
        "worst_case_loss_fraction": worst_case_loss_fraction(records),
        "mean_loss_fraction": mean_loss_fraction(records),
        "failing_specimen_ids": failing,
        "findings": findings,
        "accepted": not findings,
    }
