"""Radiation verification of a sensitive intermediate assurance commercial lot.

Anchor: ECSS-Q-ST-60-13C clause 5.3.8 (radiation verification testing of
sensitive parts at the intermediate assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

What the intermediate class changes
-----------------------------------
At this class the verification need not always be an irradiation of the
procured flight lot. Data from a similar lot may be credited instead, and the
whole question becomes what "similar" is allowed to mean and what that credit
costs. It costs margin: heritage evidence is compared against a requirement
raised by a penalty factor, because it describes a lot nobody is about to fly.

Procedure implemented here
--------------------------
1. Derive the required part-level capability: mission dose behind the actual
   shielding, multiplied by the class radiation design margin, multiplied
   again by the heritage penalty where the evidence is not lot-specific. The
   margins are ratios and they multiply; they are never subtracted.
2. Test the similarity claim before reading a single dose figure. Same
   manufacturer, same wafer process and a date-code gap inside the declared
   window; a different assembly site is reported, not refused.
3. Refuse the heritage credit outright for a dose-rate-sensitive family flown
   at a low dose rate with no low-dose-rate data behind it, whatever the
   similarity looks like. That failure mode does not show up in a high dose
   rate test, so the heritage figure is silent about it rather than wrong.
4. Reduce several heritage lots to their worst case, never their mean. The
   spread between lots is the uncertainty the credit is being asked to cover.
5. Compare capability with requirement, absorbing representation error at the
   boundary with a named tolerance rather than by relaxing the requirement.
6. Compare the single-event threshold in the same pass, because a lot can
   clear the dose requirement and still be destroyed by one heavy ion.
7. Separate inadmissible evidence from a genuine shortfall, and separate a
   shortfall the penalty caused from one a lot test could not fix. Where the
   evidence is inadmissible the capability figure is reported but not judged,
   because it says nothing about the lot in either direction.
"""

import math

__all__ = [
    "CLASS_TWO_DESIGN_MARGIN",
    "HERITAGE_PENALTY",
    "EVIDENCE_KINDS",
    "DOSE_SENSITIVE_FAMILIES",
    "LOW_DOSE_RATE_FAMILIES",
    "LOW_DOSE_RATE_LIMIT",
    "MAX_DATE_CODE_GAP_WEEKS",
    "MIN_LOT_SAMPLE",
    "required_capability",
    "evaluate_similarity",
    "low_dose_rate_concern",
    "worst_case_capability",
    "achieved_margin",
    "single_event_check",
    "assess_class_2_radiation_verification",
]

# The radiation design margin the intermediate assurance class applies to the
# part-level mission dose before anything is compared with it.
CLASS_TWO_DESIGN_MARGIN = 2.0

# What credited heritage data costs: the requirement it has to clear is raised
# by this factor, because the evidence describes a lot nobody will fly.
HERITAGE_PENALTY = 1.5

EVIDENCE_KINDS = ("lot-specific", "heritage-similarity")

# Families whose response to total ionising dose moves enough between lots that
# the capability has to be evidenced rather than assumed.
DOSE_SENSITIVE_FAMILIES = (
    "bipolar-linear",
    "cmos-digital",
    "mixed-signal-converter",
    "optocoupler",
    "power-mosfet",
    "non-volatile-memory",
    "voltage-regulator",
)

# Families that can degrade more at a low dose rate than at a high one, so a
# high dose rate heritage result says nothing about the mission case.
LOW_DOSE_RATE_FAMILIES = ("bipolar-linear", "optocoupler", "voltage-regulator")

# Mission dose rate at or below which the low dose rate question is live.
LOW_DOSE_RATE_LIMIT = 0.01

# How far apart two date codes may sit before the lots stop being comparable.
MAX_DATE_CODE_GAP_WEEKS = 104

# Units that have to be irradiated before a lot-specific result speaks for a lot.
MIN_LOT_SAMPLE = 3

# Relative tolerance used at every boundary comparison.
COMPARISON_TOLERANCE = 1e-9


def _at_least(value, bound):
    """Return True when value is at or above bound, absorbing float error."""
    return value > bound or math.isclose(
        value, bound, rel_tol=COMPARISON_TOLERANCE, abs_tol=1e-12
    )


def _at_most(value, bound):
    """Return True when value is at or below bound, absorbing float error."""
    return value < bound or math.isclose(
        value, bound, rel_tol=COMPARISON_TOLERANCE, abs_tol=1e-12
    )


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return value


def _family(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("family must be a non-empty string")
    return value.strip().lower()


def required_capability(mission_dose, design_margin=CLASS_TWO_DESIGN_MARGIN,
                        evidence_kind="lot-specific"):
    """Return the capability the lot has to demonstrate, and how it was built."""
    dose = _positive(mission_dose, "mission_dose")
    margin = _positive(design_margin, "design_margin")
    if margin < 1.0 and not math.isclose(margin, 1.0, rel_tol=COMPARISON_TOLERANCE):
        raise ValueError("design_margin below unity is an input error, got %r" % (design_margin,))
    if not isinstance(evidence_kind, str) or evidence_kind.strip().lower() not in EVIDENCE_KINDS:
        raise ValueError(
            "evidence_kind must be one of %s, got %r" % (EVIDENCE_KINDS, evidence_kind)
        )
    kind = evidence_kind.strip().lower()
    penalty = HERITAGE_PENALTY if kind == "heritage-similarity" else 1.0
    return {
        "mission_dose": dose,
        "design_margin": margin,
        "evidence_kind": kind,
        "heritage_penalty": penalty,
        "unpenalised": dose * margin,
        "required": dose * margin * penalty,
    }


def evaluate_similarity(claim):
    """Judge whether a heritage lot is close enough to speak for the flight lot.

    claim keys: same_manufacturer, same_wafer_process, same_assembly_site and
    date_code_gap_weeks.
    """
    if not isinstance(claim, dict):
        raise ValueError("similarity claim must be a mapping")
    for key in ("same_manufacturer", "same_wafer_process", "same_assembly_site",
                "date_code_gap_weeks"):
        if key not in claim:
            raise ValueError("similarity claim missing required key '%s'" % key)
    flags = {}
    for key in ("same_manufacturer", "same_wafer_process", "same_assembly_site"):
        value = claim[key]
        if not isinstance(value, bool):
            raise ValueError("similarity claim %s must be True or False" % key)
        flags[key] = value
    gap = claim["date_code_gap_weeks"]
    if not isinstance(gap, int) or isinstance(gap, bool):
        raise ValueError("date_code_gap_weeks must be an integer, got %r" % (gap,))
    if gap < 0:
        raise ValueError("date_code_gap_weeks must be non-negative, got %d" % gap)
    reasons = []
    advisories = []
    if not flags["same_manufacturer"]:
        reasons.append("heritage lot comes from a different manufacturer")
    if not flags["same_wafer_process"]:
        reasons.append("heritage lot was built on a different wafer process")
    if gap > MAX_DATE_CODE_GAP_WEEKS:
        reasons.append(
            "date codes %d weeks apart, beyond the %d week comparability window"
            % (gap, MAX_DATE_CODE_GAP_WEEKS)
        )
    if not flags["same_assembly_site"]:
        advisories.append("heritage lot was assembled at a different site")
    return {
        "date_code_gap_weeks": gap,
        "admissible": not reasons,
        "reasons": reasons,
        "advisories": advisories,
    }


def low_dose_rate_concern(family, mission_dose_rate):
    """Return True when the mission exposes a dose-rate-sensitive family slowly."""
    name = _family(family)
    rate = _positive(mission_dose_rate, "mission_dose_rate")
    return name in LOW_DOSE_RATE_FAMILIES and _at_most(rate, LOW_DOSE_RATE_LIMIT)


def worst_case_capability(lots):
    """Reduce the heritage lots to the lowest capability any of them showed."""
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("heritage lots must be a non-empty sequence of mappings")
    seen = set()
    worst = None
    governing = None
    for index, lot in enumerate(lots):
        if not isinstance(lot, dict):
            raise ValueError("heritage_lots[%d] must be a mapping" % index)
        for key in ("id", "capability"):
            if key not in lot:
                raise ValueError("heritage_lots[%d] missing required key '%s'" % (index, key))
        ident = lot["id"]
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError("heritage_lots[%d] id must be a non-empty string" % index)
        ident = ident.strip()
        if ident in seen:
            raise ValueError("heritage lot id '%s' appears more than once" % ident)
        seen.add(ident)
        capability = _positive(lot["capability"], "heritage_lots[%d] capability" % index)
        if worst is None or capability < worst:
            worst = capability
            governing = ident
    return {"capability": worst, "governing_lot": governing, "lot_count": len(lots)}


def achieved_margin(capability, mission_dose):
    """Return the ratio of demonstrated capability to part-level mission dose."""
    dose = _positive(mission_dose, "mission_dose")
    shown = _positive(capability, "capability")
    return shown / dose


def single_event_check(required_threshold, measured_threshold):
    """Compare the measured single-event threshold with the required one.

    A declared requirement with no measurement behind it is refused rather than
    defaulted; no requirement at all means there is nothing to compare.
    """
    if required_threshold is None:
        if measured_threshold is not None:
            _positive(measured_threshold, "measured_threshold")
        return {"declared": False, "required": None, "measured": None, "meets": True}
    required = _positive(required_threshold, "required_threshold")
    if measured_threshold is None:
        return {
            "declared": True,
            "required": required,
            "measured": None,
            "meets": False,
            "evidence_missing": True,
        }
    measured = _positive(measured_threshold, "measured_threshold")
    return {
        "declared": True,
        "required": required,
        "measured": measured,
        "meets": _at_least(measured, required),
        "evidence_missing": False,
    }


def assess_class_2_radiation_verification(spec):
    """Run the full clause 5.3.8 radiation verification assessment.

    spec keys: part_id, family, mission_dose, evidence_kind, and then either
    lot_capability with lot_sample_size and sample_from_flight_lot, or
    heritage_lots with similarity, mission_dose_rate and low_dose_rate_data.
    Optional: design_margin, required_let, measured_let.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("part_id", "family", "mission_dose", "evidence_kind"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    part_id = spec["part_id"]
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string")
    family = _family(spec["family"])
    requirement = required_capability(
        spec["mission_dose"],
        spec.get("design_margin", CLASS_TWO_DESIGN_MARGIN),
        spec["evidence_kind"],
    )
    kind = requirement["evidence_kind"]

    invalid_reasons = []
    test_reasons = []
    advisories = []
    similarity = None
    capability = None
    governing_lot = None

    if kind == "lot-specific":
        for key in ("lot_capability", "lot_sample_size", "sample_from_flight_lot"):
            if key not in spec:
                raise ValueError("lot-specific evidence missing required key '%s'" % key)
        sample = spec["lot_sample_size"]
        if not isinstance(sample, int) or isinstance(sample, bool):
            raise ValueError("lot_sample_size must be an integer, got %r" % (sample,))
        if sample < 0:
            raise ValueError("lot_sample_size must be non-negative, got %d" % sample)
        from_flight_lot = spec["sample_from_flight_lot"]
        if not isinstance(from_flight_lot, bool):
            raise ValueError("sample_from_flight_lot must be True or False")
        if sample < MIN_LOT_SAMPLE:
            invalid_reasons.append(
                "%d unit(s) irradiated, below the %d needed to speak for a lot"
                % (sample, MIN_LOT_SAMPLE)
            )
        if not from_flight_lot:
            invalid_reasons.append("irradiated units were not drawn from the procured flight lot")
        capability = _positive(spec["lot_capability"], "lot_capability")
        governing_lot = part_id.strip()
    else:
        for key in ("heritage_lots", "similarity", "mission_dose_rate", "low_dose_rate_data"):
            if key not in spec:
                raise ValueError("heritage evidence missing required key '%s'" % key)
        similarity = evaluate_similarity(spec["similarity"])
        advisories.extend(similarity["advisories"])
        if not similarity["admissible"]:
            invalid_reasons.extend(similarity["reasons"])
        low_dose_rate_data = spec["low_dose_rate_data"]
        if not isinstance(low_dose_rate_data, bool):
            raise ValueError("low_dose_rate_data must be True or False")
        if low_dose_rate_concern(family, spec["mission_dose_rate"]) and not low_dose_rate_data:
            test_reasons.append(
                "'%s' flown at a low dose rate with no low dose rate data behind the heritage"
                % family
            )
        reduced = worst_case_capability(spec["heritage_lots"])
        capability = reduced["capability"]
        governing_lot = reduced["governing_lot"]
        if reduced["lot_count"] > 1:
            advisories.append(
                "%d heritage lots reduced to the worst case held by '%s'"
                % (reduced["lot_count"], reduced["governing_lot"])
            )
        if family in DOSE_SENSITIVE_FAMILIES:
            advisories.append(
                "'%s' is a dose sensitive family; the heritage credit carries the penalty" % family
            )

    margin = achieved_margin(capability, requirement["mission_dose"])
    meets_dose = _at_least(capability, requirement["required"])
    single_event = single_event_check(spec.get("required_let"), spec.get("measured_let"))

    # Inadmissible evidence poisons the figures drawn from it. A capability
    # measured on the wrong units says nothing about the lot either way, so it
    # produces no verdict reason -- the evidence is refused, not the lot.
    evidence_admissible = not invalid_reasons
    if not evidence_admissible:
        advisories.append(
            "capability of %.6g not judged against the requirement: the evidence behind it is "
            "inadmissible" % capability
        )

    reject_reasons = []
    if not meets_dose and evidence_admissible:
        shortfall = "demonstrated %.6g against a required %.6g" % (
            capability,
            requirement["required"],
        )
        if kind == "heritage-similarity" and _at_least(capability, requirement["unpenalised"]):
            test_reasons.append(
                "heritage capability clears the design margin but not the heritage penalty: %s"
                % shortfall
            )
        else:
            reject_reasons.append("capability below requirement: %s" % shortfall)
    if single_event["declared"]:
        if single_event.get("evidence_missing"):
            invalid_reasons.append(
                "a single-event threshold is required with no measurement behind it"
            )
        elif not single_event["meets"] and evidence_admissible:
            reject_reasons.append(
                "single-event threshold %.6g below the required %.6g"
                % (single_event["measured"], single_event["required"])
            )

    if invalid_reasons:
        disposition = "evidence-invalid"
    elif test_reasons:
        disposition = "lot-test-required"
    elif reject_reasons:
        disposition = "rejected"
    else:
        disposition = "verified"
    return {
        "part_id": part_id.strip(),
        "family": family,
        "evidence_kind": kind,
        "requirement": requirement,
        "similarity": similarity,
        "capability": capability,
        "governing_lot": governing_lot,
        "achieved_margin": margin,
        "meets_dose_requirement": meets_dose,
        "single_event": single_event,
        "invalid_reasons": invalid_reasons,
        "test_reasons": test_reasons,
        "reject_reasons": reject_reasons,
        "advisories": advisories,
        "verified": disposition == "verified",
        "disposition": disposition,
    }
