"""Radiation verification testing of flight lots of sensitive commercial parts.

Anchor: ECSS-Q-ST-60-13C clause 4.3.8 (Class 1 use of commercial EEE
components -- radiation verification testing of the procured lot).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the required part-level capability from the part-level mission dose
   and the project radiation design margin.
2. Decide whether the purchased commercial lot needs a radiation verification
   test at all: a dose-sensitive technology family, a declared capability that
   does not cover the requirement, a missing capability figure, or capability
   evidence that is not traceable to the flight lot each force the test.
3. Size the verification sample and confirm every sample unit comes from the
   flight lot itself. Heritage units from another date code are evidence about
   another lot, not about this one.
4. Reduce the irradiation ladder into a lot capability: the highest dose step
   at which every irradiated unit stayed inside its end-of-life electrical
   limits, with no failed step below it.
5. Convert that capability into an achieved radiation design margin and
   compare it with the required margin.
6. Where a single-event requirement applies, compare the measured threshold
   linear energy transfer with the required threshold.
7. Report the lot disposition together with every finding raised on the way.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "MIN_RVT_SAMPLE",
    "DOSE_SENSITIVE_FAMILIES",
    "validate_dose_krad",
    "required_capability_krad",
    "is_dose_sensitive_family",
    "verification_test_required",
    "validate_sample",
    "lot_capability_krad",
    "achieved_margin",
    "margin_meets_requirement",
    "evaluate_single_event_threshold",
    "assess_radiation_verification",
]

# A margin comparison is a ratio of two measured doses. An intentional
# equality at the limit can land a few ULP on either side of it, so the
# representation error is absorbed here instead of by relaxing the margin.
MARGIN_TOLERANCE = 1e-12

# A verification test on fewer units than this cannot speak for a lot.
MIN_RVT_SAMPLE = 3

# Technology families whose parametric drift under total ionising dose is
# strongly process dependent, so a commercial lot cannot inherit a capability
# figure from a different lot of the same part number.
DOSE_SENSITIVE_FAMILIES = frozenset(
    {
        "bipolar-linear",
        "cmos-digital",
        "mixed-signal-converter",
        "optocoupler",
        "power-mosfet",
        "non-volatile-memory",
        "voltage-regulator",
    }
)


def validate_dose_krad(value, label):
    """Return a validated strictly positive dose in krad(Si)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    dose = float(value)
    if not math.isfinite(dose):
        raise ValueError("%s must be finite" % label)
    if dose <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return dose


def _validate_margin(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    margin = float(value)
    if not math.isfinite(margin):
        raise ValueError("%s must be finite" % label)
    if margin < 1.0:
        raise ValueError("%s must be at least unity, got %r" % (label, value))
    return margin


def required_capability_krad(mission_dose_krad, required_margin):
    """Return the part-level capability the lot has to demonstrate."""
    dose = validate_dose_krad(mission_dose_krad, "mission_dose_krad")
    margin = _validate_margin(required_margin, "required_margin")
    return dose * margin


def is_dose_sensitive_family(family):
    """Return True when the technology family is treated as dose sensitive."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string")
    return family.strip().lower() in DOSE_SENSITIVE_FAMILIES


def verification_test_required(part):
    """Decide whether the purchased lot must undergo a verification test.

    part keys: family, required_capability_krad, declared_capability_krad
    (may be None), declared_from_flight_lot (bool).
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("family", "required_capability_krad", "declared_from_flight_lot"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    if not isinstance(part["declared_from_flight_lot"], bool):
        raise ValueError("declared_from_flight_lot must be a boolean")
    required = validate_dose_krad(
        part["required_capability_krad"], "required_capability_krad"
    )
    sensitive = is_dose_sensitive_family(part["family"])
    declared = part.get("declared_capability_krad")
    reasons = []
    if declared is None:
        reasons.append("no declared radiation capability for the part")
    else:
        declared = validate_dose_krad(declared, "declared_capability_krad")
        if declared < required and not math.isclose(
            declared, required, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
        ):
            reasons.append(
                "declared capability %g krad is below the required %g krad"
                % (declared, required)
            )
        elif sensitive and not part["declared_from_flight_lot"]:
            reasons.append(
                "technology family is dose sensitive, so the capability has to be "
                "evidenced on the flight lot rather than inherited"
            )
    return {
        "required": bool(reasons),
        "dose_sensitive_family": sensitive,
        "required_capability_krad": required,
        "reasons": reasons,
    }


def validate_sample(sample_size, lot_size, from_flight_lot, minimum=MIN_RVT_SAMPLE):
    """Return the validated sample record and any sampling findings."""
    for label, value in (("sample_size", sample_size), ("lot_size", lot_size)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
        if value <= 0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    if not isinstance(from_flight_lot, bool):
        raise ValueError("from_flight_lot must be a boolean")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum <= 0:
        raise ValueError("minimum must be a positive integer")
    if sample_size > lot_size:
        raise ValueError(
            "sample_size %d exceeds the lot size %d" % (sample_size, lot_size)
        )
    findings = []
    if not from_flight_lot:
        findings.append(
            "verification units were not drawn from the flight lot; the result "
            "speaks for another lot"
        )
    if sample_size < minimum:
        findings.append(
            "sample of %d unit(s) is below the %d-unit floor for a lot verification"
            % (sample_size, minimum)
        )
    return {
        "sample_size": sample_size,
        "lot_size": lot_size,
        "from_flight_lot": from_flight_lot,
        "minimum": minimum,
        "acceptable": not findings,
        "findings": findings,
    }


def _validate_step(step, index):
    if not isinstance(step, dict):
        raise ValueError("step %d must be a mapping" % index)
    for key in ("dose_krad", "units_tested", "units_within_limits"):
        if key not in step:
            raise ValueError("step %d missing key '%s'" % (index, key))
    dose = validate_dose_krad(step["dose_krad"], "step %d dose_krad" % index)
    tested = step["units_tested"]
    within = step["units_within_limits"]
    for label, value in (("units_tested", tested), ("units_within_limits", within)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("step %d %s must be an integer" % (index, label))
    if tested <= 0:
        raise ValueError("step %d units_tested must be positive" % index)
    if within < 0 or within > tested:
        raise ValueError(
            "step %d units_within_limits %d is outside 0..%d" % (index, within, tested)
        )
    return (dose, tested, within)


def lot_capability_krad(steps):
    """Return the demonstrated lot capability from an irradiation ladder.

    The capability is the highest dose step at which every irradiated unit was
    still inside its end-of-life limits, with no failed step below it. A ladder
    whose doses do not strictly increase is refused: without an ordered ladder
    the step below a failure is not defined.
    """
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence of dose steps")
    ladder = [_validate_step(step, i) for i, step in enumerate(steps)]
    for i in range(1, len(ladder)):
        if ladder[i][0] <= ladder[i - 1][0]:
            raise ValueError(
                "dose steps must strictly increase (step %d at %g krad)"
                % (i, ladder[i][0])
            )
    capability = 0.0
    for dose, tested, within in ladder:
        if within < tested:
            break
        capability = dose
    return capability


def achieved_margin(capability_krad, mission_dose_krad):
    """Return the achieved radiation design margin as a ratio."""
    mission = validate_dose_krad(mission_dose_krad, "mission_dose_krad")
    if not isinstance(capability_krad, (int, float)) or isinstance(
        capability_krad, bool
    ):
        raise ValueError("capability_krad must be a real number")
    capability = float(capability_krad)
    if not math.isfinite(capability) or capability < 0.0:
        raise ValueError(
            "capability_krad must be non-negative and finite, got %r" % (capability_krad,)
        )
    return capability / mission


def margin_meets_requirement(achieved, required):
    """Return True when the achieved margin reaches the required one."""
    if not isinstance(achieved, (int, float)) or isinstance(achieved, bool):
        raise ValueError("achieved must be a real number")
    achieved = float(achieved)
    if not math.isfinite(achieved) or achieved < 0.0:
        raise ValueError("achieved must be non-negative and finite")
    required = _validate_margin(required, "required")
    return achieved > required or math.isclose(
        achieved, required, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )


def evaluate_single_event_threshold(measured_let, required_let):
    """Compare a measured threshold LET with the required threshold.

    Both values are in MeV*cm2/mg. A measured threshold at or above the
    required one clears the requirement.
    """
    for label, value in (("measured_let", measured_let), ("required_let", required_let)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    measured = float(measured_let)
    required = float(required_let)
    compliant = measured > required or math.isclose(
        measured, required, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    return {
        "measured_let": measured,
        "required_let": required,
        "compliant": compliant,
        "findings": (
            []
            if compliant
            else [
                "measured threshold LET %g is below the required %g"
                % (measured, required)
            ]
        ),
    }


def assess_radiation_verification(spec):
    """Run the clause 4.3.8 verification assessment for one commercial lot.

    spec keys: family, mission_dose_krad, required_margin, lot_size,
    sample_size, sample_from_flight_lot, dose_steps; optional
    declared_capability_krad, declared_from_flight_lot, minimum_sample,
    measured_let, required_let.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in (
        "family",
        "mission_dose_krad",
        "required_margin",
        "lot_size",
        "sample_size",
        "sample_from_flight_lot",
        "dose_steps",
    ):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    mission = validate_dose_krad(spec["mission_dose_krad"], "mission_dose_krad")
    required_margin = _validate_margin(spec["required_margin"], "required_margin")
    required_capability = required_capability_krad(mission, required_margin)
    decision = verification_test_required(
        {
            "family": spec["family"],
            "required_capability_krad": required_capability,
            "declared_capability_krad": spec.get("declared_capability_krad"),
            "declared_from_flight_lot": bool(spec.get("declared_from_flight_lot", False)),
        }
    )
    sample = validate_sample(
        spec["sample_size"],
        spec["lot_size"],
        bool(spec["sample_from_flight_lot"]),
        spec.get("minimum_sample", MIN_RVT_SAMPLE),
    )
    capability = lot_capability_krad(spec["dose_steps"])
    margin = achieved_margin(capability, mission)
    margin_ok = margin_meets_requirement(margin, required_margin)
    findings = list(sample["findings"])
    if not margin_ok:
        findings.append(
            "lot capability %g krad gives a margin of %.4f against the required %.4f"
            % (capability, margin, required_margin)
        )
    single_event = None
    if "required_let" in spec:
        if "measured_let" not in spec:
            raise ValueError(
                "spec declares required_let but carries no measured_let to judge it"
            )
        single_event = evaluate_single_event_threshold(
            spec["measured_let"], spec["required_let"]
        )
        findings.extend(single_event["findings"])
    compliant = margin_ok and not findings
    if compliant:
        disposition = "lot-verified"
    elif sample["findings"]:
        disposition = "verification-evidence-invalid"
    else:
        disposition = "lot-rejected"
    return {
        "test_required": decision["required"],
        "test_required_reasons": decision["reasons"],
        "required_capability_krad": required_capability,
        "lot_capability_krad": capability,
        "achieved_margin": margin,
        "required_margin": required_margin,
        "margin_compliant": margin_ok,
        "sample": sample,
        "single_event": single_event,
        "compliant": compliant,
        "disposition": disposition,
        "findings": findings,
    }
