#!/usr/bin/env python3
"""Qualification envelopes and fluid choice for two-phase equipment.

Anchor: ECSS-E-ST-31-02 clause 4.4.2 and its working-fluid merit chart
(figure 4-2). The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Three things are fixed here before a qualification programme can be
written. The temperature envelope the equipment is qualified over, the
mechanical levels it is qualified to, and which working fluid can
actually carry heat across that temperature envelope.

Temperatures build outward from the prediction in two steps. The
acceptance envelope is the predicted range widened by the acceptance
margin; the qualification envelope is the acceptance envelope widened
again by the qualification margin. The declared survival range has to
contain the qualification envelope, because a unit that cannot survive
the temperature it is qualified at cannot be qualified at it.

Mechanical levels build the same way: an acceptance spectral density
lifted by a decibel uplift, and a test duration lifted by its own
factor.

Fluid choice runs off the merit number of the liquid transport
capability,

    merit = surface_tension * liquid_density * latent_heat / viscosity

evaluated at each end of the qualification envelope. A fluid is admitted
only when it is liquid across the whole envelope: its freezing point
must sit at or below the cold end and its critical point at or above the
hot end, each with the declared clearance. Among the admitted fluids the
choice is the one whose WORST end of the envelope is strongest, not the
one with the best headline number, because the weak end is what sizes
the transport limit.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

_REL_TOL = 1e-9
_ABS_TOL = 1e-12

FLUID_PROPERTY_KEYS = (
    "surface_tension_n_per_m",
    "liquid_density_kg_per_m3",
    "latent_heat_j_per_kg",
    "liquid_viscosity_pa_s",
)

ENVELOPE_ADMITTED = "envelope-admitted"
ENVELOPE_REJECTED = "envelope-rejected"


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


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def acceptance_temperature_envelope(
    predicted_min_k, predicted_max_k, acceptance_margin_k
):
    """Predicted range widened by the acceptance margin at both ends."""
    low = _require_positive("predicted_min_k", predicted_min_k)
    high = _require_positive("predicted_max_k", predicted_max_k)
    margin = _require_non_negative("acceptance_margin_k", acceptance_margin_k)
    if high <= low:
        raise ValueError(
            "predicted_max_k %g K must be above predicted_min_k %g K" % (high, low)
        )
    cold = low - margin
    if cold <= 0.0:
        raise ValueError(
            "an acceptance margin of %g K takes the cold end to %g K, which is "
            "not a physical temperature" % (margin, cold)
        )
    return {"min_k": cold, "max_k": high + margin}


def qualification_temperature_envelope(
    predicted_min_k, predicted_max_k, acceptance_margin_k, qualification_margin_k
):
    """Acceptance envelope widened again by the qualification margin."""
    acceptance = acceptance_temperature_envelope(
        predicted_min_k, predicted_max_k, acceptance_margin_k
    )
    margin = _require_non_negative("qualification_margin_k", qualification_margin_k)
    cold = acceptance["min_k"] - margin
    if cold <= 0.0:
        raise ValueError(
            "a qualification margin of %g K takes the cold end to %g K, which "
            "is not a physical temperature" % (margin, cold)
        )
    return {
        "acceptance_min_k": acceptance["min_k"],
        "acceptance_max_k": acceptance["max_k"],
        "min_k": cold,
        "max_k": acceptance["max_k"] + margin,
    }


def audit_survival_envelope(qualification_envelope, survival_min_k, survival_max_k):
    """Check the declared survival range contains the qualification one."""
    if not isinstance(qualification_envelope, dict):
        raise ValueError(
            "qualification_envelope must be a mapping, got %r"
            % (qualification_envelope,)
        )
    qual_min = _require_positive("envelope min_k", qualification_envelope.get("min_k"))
    qual_max = _require_positive("envelope max_k", qualification_envelope.get("max_k"))
    low = _require_positive("survival_min_k", survival_min_k)
    high = _require_positive("survival_max_k", survival_max_k)
    if high <= low:
        raise ValueError(
            "survival_max_k %g K must be above survival_min_k %g K" % (high, low)
        )
    findings = []
    if not _at_most(low, qual_min):
        findings.append(
            "the survival cold limit %g K sits above the qualification cold "
            "end %g K" % (low, qual_min)
        )
    if not _at_least(high, qual_max):
        findings.append(
            "the survival hot limit %g K sits below the qualification hot "
            "end %g K" % (high, qual_max)
        )
    return {"contains_envelope": not findings, "findings": findings}


def qualification_vibration_level(acceptance_asd_g2_per_hz, uplift_db):
    """Acceptance spectral density lifted by the qualification decibel."""
    acceptance = _require_positive(
        "acceptance_asd_g2_per_hz", acceptance_asd_g2_per_hz
    )
    uplift = _require_non_negative("uplift_db", uplift_db)
    return acceptance * (10.0 ** (uplift / 10.0))


def qualification_vibration_duration(acceptance_duration_s, duration_factor):
    """Acceptance duration lifted by the qualification duration factor."""
    duration = _require_positive("acceptance_duration_s", acceptance_duration_s)
    factor = _require_number("duration_factor", duration_factor)
    if factor < 1.0:
        raise ValueError(
            "duration_factor must be at least 1.0, got %r" % (duration_factor,)
        )
    return duration * factor


def validate_fluid(fluid):
    """Check one candidate working fluid carries every property needed."""
    if not isinstance(fluid, dict):
        raise ValueError("fluid must be a mapping, got %r" % (fluid,))
    _require_text("fluid name", fluid.get("name"))
    for key in FLUID_PROPERTY_KEYS:
        _require_positive("%s %s" % (fluid["name"], key), fluid.get(key))
    freeze = _require_positive(
        "%s freezing_point_k" % fluid["name"], fluid.get("freezing_point_k")
    )
    critical = _require_positive(
        "%s critical_point_k" % fluid["name"], fluid.get("critical_point_k")
    )
    if critical <= freeze:
        raise ValueError(
            "%s declares a critical point %g K at or below its freezing point "
            "%g K" % (fluid["name"], critical, freeze)
        )
    return fluid


def merit_number(fluid, temperature_scaling=1.0):
    """Liquid transport merit of a working fluid, in watt per square metre.

    merit = surface_tension * liquid_density * latent_heat / viscosity.
    The scaling factor carries how the grouped properties move across the
    envelope; it is supplied per temperature rather than modelled here.
    """
    validate_fluid(fluid)
    scaling = _require_positive("temperature_scaling", temperature_scaling)
    return (
        fluid["surface_tension_n_per_m"]
        * fluid["liquid_density_kg_per_m3"]
        * fluid["latent_heat_j_per_kg"]
        / fluid["liquid_viscosity_pa_s"]
    ) * scaling


def assess_fluid_against_envelope(fluid, envelope, clearance_k=0.0):
    """Admit or reject a fluid on whether it stays liquid over the envelope."""
    validate_fluid(fluid)
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping, got %r" % (envelope,))
    cold = _require_positive("envelope min_k", envelope.get("min_k"))
    hot = _require_positive("envelope max_k", envelope.get("max_k"))
    clearance = _require_non_negative("clearance_k", clearance_k)
    reasons = []
    if not _at_most(fluid["freezing_point_k"], cold - clearance):
        reasons.append(
            "freezes at %g K, above the cold end %g K with %g K clearance"
            % (fluid["freezing_point_k"], cold, clearance)
        )
    if not _at_least(fluid["critical_point_k"], hot + clearance):
        reasons.append(
            "reaches its critical point at %g K, below the hot end %g K with "
            "%g K clearance" % (fluid["critical_point_k"], hot, clearance)
        )
    return {
        "name": fluid["name"],
        "status": ENVELOPE_ADMITTED if not reasons else ENVELOPE_REJECTED,
        "reasons": reasons,
    }


def worst_end_merit(fluid, cold_scaling, hot_scaling):
    """Weakest of the two envelope ends, which is what sizes the transport."""
    cold = merit_number(fluid, cold_scaling)
    hot = merit_number(fluid, hot_scaling)
    return min(cold, hot)


def select_working_fluid(candidates, envelope, clearance_k=0.0):
    """Pick the admitted fluid whose weakest envelope end is strongest.

    Ties are broken by name so the choice is reproducible rather than
    dependent on the order the candidates were listed in.
    """
    if isinstance(candidates, (str, bytes)) or not isinstance(
        candidates, (list, tuple)
    ):
        raise ValueError("candidates must be a list or tuple, got %r" % (candidates,))
    if not candidates:
        raise ValueError("no candidate working fluids were supplied")
    admitted = []
    rejected = []
    seen = set()
    for fluid in candidates:
        validate_fluid(fluid)
        if fluid["name"] in seen:
            raise ValueError("duplicate candidate fluid %r" % fluid["name"])
        seen.add(fluid["name"])
        verdict = assess_fluid_against_envelope(fluid, envelope, clearance_k)
        if verdict["status"] == ENVELOPE_REJECTED:
            rejected.append(verdict)
            continue
        admitted.append(
            {
                "name": fluid["name"],
                "worst_end_merit_w_per_m2": worst_end_merit(
                    fluid,
                    _require_positive(
                        "%s cold_scaling" % fluid["name"], fluid.get("cold_scaling", 1.0)
                    ),
                    _require_positive(
                        "%s hot_scaling" % fluid["name"], fluid.get("hot_scaling", 1.0)
                    ),
                ),
            }
        )
    if not admitted:
        return {
            "selected": None,
            "admitted": [],
            "rejected": rejected,
            "findings": [
                "no candidate fluid stays liquid across the qualification "
                "envelope; the envelope or the candidate set has to change"
            ],
        }
    admitted.sort(key=lambda item: (-item["worst_end_merit_w_per_m2"], item["name"]))
    return {
        "selected": admitted[0],
        "admitted": admitted,
        "rejected": rejected,
        "findings": [],
    }


def define_qualification_envelopes(case):
    """Full clause 4.4.2 envelope definition with a fluid selection."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    envelope = qualification_temperature_envelope(
        case.get("predicted_min_k"),
        case.get("predicted_max_k"),
        case.get("acceptance_margin_k"),
        case.get("qualification_margin_k"),
    )
    findings = []
    survival_min = case.get("survival_min_k")
    survival_max = case.get("survival_max_k")
    if survival_min is not None and survival_max is not None:
        survival = audit_survival_envelope(envelope, survival_min, survival_max)
        findings.extend(survival["findings"])
    mechanical = {
        "qualification_asd_g2_per_hz": qualification_vibration_level(
            case.get("acceptance_asd_g2_per_hz"), case.get("vibration_uplift_db", 3.0)
        ),
        "qualification_duration_s": qualification_vibration_duration(
            case.get("acceptance_duration_s"), case.get("duration_factor", 2.0)
        ),
    }
    selection = select_working_fluid(
        case.get("candidate_fluids", ()),
        {"min_k": envelope["min_k"], "max_k": envelope["max_k"]},
        case.get("fluid_clearance_k", 0.0),
    )
    findings.extend(selection["findings"])
    return {
        "temperature": envelope,
        "mechanical": mechanical,
        "fluid": selection["selected"],
        "fluids_rejected": selection["rejected"],
        "findings": findings,
        "verdict": "envelopes-defined" if not findings else "envelopes-open",
    }
