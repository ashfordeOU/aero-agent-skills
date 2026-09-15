"""Radiation verification testing of sensitive Class 1 EEE parts.

Anchor: ECSS-Q-ST-60C clause 4.3.8 (Class 1 EEE components -- radiation
verification testing of sensitive parts against the declared mission
environment). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Resolve the radiation sensitivity grade of the part's technology family from
   a project register. A family the register never listed is refused, because a
   grade that was never declared cannot be assumed.
2. Decide whether the part needs its own irradiation at all: a low sensitivity
   grade does not, and a sensitive part does not when heritage evidence already
   demonstrates the required radiation design margin against the mission dose.
3. Reduce the irradiated sample to a lot capability: take the lowest
   failure-free dose reached across the irradiated parts and credit it by how
   many parts of the flight lot were actually irradiated, refusing a sample too
   small to earn any lot-level credit.
4. Compare the demonstrated radiation design margin with the required one and
   report the dose shortfall when it is short.
5. Judge the single event response separately: a threshold linear energy
   transfer above the mission requirement is not enough if a destructive event
   has an onset below that requirement.
6. Return the disposition: no test required, evidence incomplete, failed on
   single event response, failed on total dose, or verification passed.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "SENSITIVITY_GRADES",
    "DEFAULT_SAMPLE_CREDIT",
    "MINIMUM_IRRADIATED_SAMPLE",
    "DEFAULT_REQUIRED_MARGIN",
    "DESTRUCTIVE_EVENT_TYPES",
    "DEFAULT_LOW_DOSE_RATE_THRESHOLD",
    "radiation_sensitivity",
    "verification_test_required",
    "sample_credit_factor",
    "demonstrated_lot_capability",
    "radiation_design_margin",
    "assess_total_dose_adequacy",
    "low_dose_rate_test_required",
    "assess_single_event_response",
    "assess_radiation_verification",
]

# Margins are ratios of measured doses; an intentional equality with a required
# margin can land a few ULP either side of it after the division.
MARGIN_TOLERANCE = 1e-12

SENSITIVITY_GRADES = ("low", "moderate", "high")

DEFAULT_REQUIRED_MARGIN = 2.0

# Lot-level credit applied to the lowest failure-free dose of the sample, by how
# many parts of the flight lot were irradiated. A wider sample earns more of the
# dose it reached; a narrow one is derated because it evidences less of the lot.
DEFAULT_SAMPLE_CREDIT = ((11, 1.0), (5, 0.8), (3, 0.6))

MINIMUM_IRRADIATED_SAMPLE = 3

# Single event effects that destroy the part rather than upset it. An onset
# below the mission requirement vetoes the part whatever the dose margin is.
DESTRUCTIVE_EVENT_TYPES = frozenset(
    {
        "single-event-latch-up",
        "single-event-burnout",
        "single-event-gate-rupture",
    }
)

# Mission dose rate in rad(Si) per second under which a bipolar family has to be
# irradiated at low dose rate as well as at the accelerated rate.
DEFAULT_LOW_DOSE_RATE_THRESHOLD = 0.01


def _positive_real(value, label):
    """Return value as a finite positive float, refusing anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


def _meets(value, bound):
    """Return True when value is at or above bound, tolerant of float noise."""
    return value > bound or math.isclose(
        value, bound, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )


def _clean_name(value, label):
    """Return a lower-cased non-empty token, refusing anything else."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def radiation_sensitivity(register, technology):
    """Return the declared radiation sensitivity grade of a technology family.

    register maps a technology family to one of SENSITIVITY_GRADES. A family the
    project never declared is refused rather than defaulted to the nearest one.
    """
    if not isinstance(register, dict) or not register:
        raise ValueError(
            "register must be a non-empty mapping of technology family to grade"
        )
    family = _clean_name(technology, "technology")
    if family not in register:
        raise ValueError(
            "technology family '%s' is not in the radiation sensitivity register"
            % family
        )
    grade = register[family]
    if not isinstance(grade, str) or grade.strip().lower() not in SENSITIVITY_GRADES:
        raise ValueError(
            "sensitivity grade for '%s' must be one of %s"
            % (family, ", ".join(SENSITIVITY_GRADES))
        )
    return grade.strip().lower()


def verification_test_required(
    sensitivity,
    mission_dose,
    heritage_capability=None,
    required_margin=DEFAULT_REQUIRED_MARGIN,
):
    """Decide whether this part needs its own radiation verification test.

    A low sensitivity grade needs none. A sensitive part needs none only when
    heritage evidence already carries the required margin over the mission dose;
    absent heritage evidence the test is required, never waived by silence.
    """
    grade = _clean_name(sensitivity, "sensitivity")
    if grade not in SENSITIVITY_GRADES:
        raise ValueError(
            "sensitivity must be one of %s, got %r"
            % (", ".join(SENSITIVITY_GRADES), sensitivity)
        )
    mission = _positive_real(mission_dose, "mission_dose")
    required = _positive_real(required_margin, "required_margin")
    if grade == "low":
        return False
    if heritage_capability is None:
        return True
    heritage = _positive_real(heritage_capability, "heritage_capability")
    return not _meets(heritage / mission, required)


def sample_credit_factor(sample_size, credit_table=DEFAULT_SAMPLE_CREDIT):
    """Return the lot-level credit earned by an irradiated sample of this size."""
    if not isinstance(sample_size, int) or isinstance(sample_size, bool):
        raise ValueError("sample_size must be an integer, got %r" % (sample_size,))
    if sample_size <= 0:
        raise ValueError("sample_size must be positive, got %d" % sample_size)
    if not isinstance(credit_table, (list, tuple)) or not credit_table:
        raise ValueError(
            "credit_table must be a non-empty sequence of (size, factor) pairs"
        )
    smallest = None
    best = None
    for entry in credit_table:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("credit_table entries must be (size, factor) pairs")
        size, factor = entry
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError("credit_table sizes must be positive integers")
        factor = _positive_real(factor, "credit factor")
        if factor > 1.0:
            raise ValueError("credit factor must not exceed 1.0, got %r" % (factor,))
        if smallest is None or size < smallest:
            smallest = size
        if sample_size >= size and (best is None or factor > best):
            best = factor
    if best is None:
        raise ValueError(
            "a sample of %d part(s) earns no lot-level credit; the smallest "
            "credited sample is %d" % (sample_size, smallest)
        )
    return best


def demonstrated_lot_capability(
    failure_free_doses,
    credit_table=DEFAULT_SAMPLE_CREDIT,
    minimum_sample=MINIMUM_IRRADIATED_SAMPLE,
):
    """Reduce the irradiated sample to the dose the flight lot may be credited.

    failure_free_doses is one dose per irradiated part: the highest dose that
    part reached with no failure. The lot is credited with the lowest of them,
    derated by the credit the sample size earns.
    """
    if not isinstance(failure_free_doses, (list, tuple)) or not failure_free_doses:
        raise ValueError("failure_free_doses must be a non-empty sequence of doses")
    if not isinstance(minimum_sample, int) or isinstance(minimum_sample, bool):
        raise ValueError("minimum_sample must be an integer")
    if minimum_sample <= 0:
        raise ValueError("minimum_sample must be positive, got %d" % minimum_sample)
    doses = [
        _positive_real(dose, "failure-free dose %d" % index)
        for index, dose in enumerate(failure_free_doses)
    ]
    if len(doses) < minimum_sample:
        raise ValueError(
            "%d irradiated part(s) is below the minimum sample of %d"
            % (len(doses), minimum_sample)
        )
    lowest = min(doses)
    factor = sample_credit_factor(len(doses), credit_table)
    return {
        "sample_size": len(doses),
        "lowest_failure_free_dose": lowest,
        "credit_factor": factor,
        "lot_capability": lowest * factor,
    }


def radiation_design_margin(capability_dose, mission_dose):
    """Return the ratio of demonstrated capability to the declared mission dose."""
    capability = _positive_real(capability_dose, "capability_dose")
    mission = _positive_real(mission_dose, "mission_dose")
    return capability / mission


def assess_total_dose_adequacy(
    capability_dose, mission_dose, required_margin=DEFAULT_REQUIRED_MARGIN
):
    """Compare the demonstrated total dose margin with the required margin."""
    capability = _positive_real(capability_dose, "capability_dose")
    mission = _positive_real(mission_dose, "mission_dose")
    required = _positive_real(required_margin, "required_margin")
    margin = capability / mission
    needed = required * mission
    compliant = _meets(margin, required)
    return {
        "capability_dose": capability,
        "mission_dose": mission,
        "radiation_design_margin": margin,
        "required_margin": required,
        "required_capability_dose": needed,
        "dose_shortfall": 0.0 if compliant else needed - capability,
        "compliant": compliant,
    }


def low_dose_rate_test_required(
    technology,
    mission_dose_rate,
    low_dose_rate_families,
    threshold=DEFAULT_LOW_DOSE_RATE_THRESHOLD,
):
    """Decide whether a low dose rate irradiation is owed as well.

    Bipolar families listed as low-dose-rate sensitive degrade further at the
    slow rates a real orbit delivers than an accelerated test shows, so a
    mission rate under the threshold owes a second irradiation.
    """
    family = _clean_name(technology, "technology")
    rate = _positive_real(mission_dose_rate, "mission_dose_rate")
    limit = _positive_real(threshold, "threshold")
    if not isinstance(low_dose_rate_families, (list, tuple, set, frozenset)):
        raise ValueError("low_dose_rate_families must be a sequence or set of names")
    listed = {_clean_name(name, "low dose rate family") for name in low_dose_rate_families}
    if family not in listed:
        return False
    return not _meets(rate, limit)


def assess_single_event_response(
    threshold_let, required_let, observed_events=()
):
    """Judge the single event response against the mission requirement.

    threshold_let is the linear energy transfer at which upsets begin. An upset
    threshold above the requirement is not sufficient on its own: a destructive
    event whose onset sits below the requirement vetoes the part.
    """
    threshold = _positive_real(threshold_let, "threshold_let")
    required = _positive_real(required_let, "required_let")
    if not isinstance(observed_events, (list, tuple)):
        raise ValueError("observed_events must be a sequence of event records")
    below = []
    for index, event in enumerate(observed_events):
        if not isinstance(event, dict):
            raise ValueError("observed event %d must be a mapping" % index)
        for key in ("type", "onset_let"):
            if key not in event:
                raise ValueError("observed event %d missing key '%s'" % (index, key))
        kind = _clean_name(event["type"], "observed event %d type" % index)
        if kind not in DESTRUCTIVE_EVENT_TYPES:
            raise ValueError(
                "observed event type '%s' is not a recognised destructive event"
                % kind
            )
        onset = _positive_real(event["onset_let"], "observed event %d onset_let" % index)
        if not _meets(onset, required):
            below.append({"type": kind, "onset_let": onset})
    immune = _meets(threshold, required)
    return {
        "threshold_let": threshold,
        "required_let": required,
        "upset_threshold_adequate": immune,
        "destructive_events_below_requirement": below,
        "compliant": immune and not below,
    }


def assess_radiation_verification(spec):
    """Run the clause 4.3.8 radiation verification assessment for one part.

    spec keys: technology, sensitivity_register, mission_dose; optional
    heritage_capability_dose, required_margin, failure_free_doses, credit_table,
    minimum_sample, threshold_let, required_let, observed_events,
    mission_dose_rate, low_dose_rate_families, low_dose_rate_threshold,
    low_dose_rate_test_performed.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("technology", "sensitivity_register", "mission_dose"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    sensitivity = radiation_sensitivity(spec["sensitivity_register"], spec["technology"])
    mission = _positive_real(spec["mission_dose"], "mission_dose")
    required_margin = _positive_real(
        spec.get("required_margin", DEFAULT_REQUIRED_MARGIN), "required_margin"
    )
    heritage = spec.get("heritage_capability_dose")
    test_required = verification_test_required(
        sensitivity, mission, heritage, required_margin
    )
    findings = []
    result = {
        "sensitivity": sensitivity,
        "mission_dose": mission,
        "required_margin": required_margin,
        "test_required": test_required,
        "lot_capability": None,
        "total_dose": None,
        "single_event": None,
        "low_dose_rate_test_required": False,
    }
    if not test_required:
        if sensitivity == "low":
            findings.append(
                "technology family is graded low sensitivity; no part-level "
                "irradiation is owed"
            )
        else:
            findings.append(
                "heritage evidence already carries the required margin of %g over "
                "the mission dose" % required_margin
            )
        result["disposition"] = "no-test-required"
        result["findings"] = findings
        return result

    eldrs_required = False
    if "mission_dose_rate" in spec and spec.get("low_dose_rate_families"):
        eldrs_required = low_dose_rate_test_required(
            spec["technology"],
            spec["mission_dose_rate"],
            spec["low_dose_rate_families"],
            spec.get("low_dose_rate_threshold", DEFAULT_LOW_DOSE_RATE_THRESHOLD),
        )
    result["low_dose_rate_test_required"] = eldrs_required
    if eldrs_required and not spec.get("low_dose_rate_test_performed", False):
        findings.append(
            "mission dose rate obliges a low dose rate irradiation that has not "
            "been performed; the accelerated result alone is not evidence"
        )
        result["disposition"] = "evidence-incomplete"
        result["findings"] = findings
        return result

    if "failure_free_doses" not in spec:
        raise ValueError(
            "a verification test is required but no irradiated sample results "
            "were supplied; a missing result is not a pass"
        )
    capability = demonstrated_lot_capability(
        spec["failure_free_doses"],
        spec.get("credit_table", DEFAULT_SAMPLE_CREDIT),
        spec.get("minimum_sample", MINIMUM_IRRADIATED_SAMPLE),
    )
    result["lot_capability"] = capability

    single_event = None
    if "threshold_let" in spec and "required_let" in spec:
        single_event = assess_single_event_response(
            spec["threshold_let"],
            spec["required_let"],
            spec.get("observed_events", ()),
        )
        result["single_event"] = single_event

    total_dose = assess_total_dose_adequacy(
        capability["lot_capability"], mission, required_margin
    )
    result["total_dose"] = total_dose

    if single_event is not None and not single_event["compliant"]:
        if single_event["destructive_events_below_requirement"]:
            for event in single_event["destructive_events_below_requirement"]:
                findings.append(
                    "%s onset at %g is below the required level of %g"
                    % (event["type"], event["onset_let"], single_event["required_let"])
                )
        if not single_event["upset_threshold_adequate"]:
            findings.append(
                "upset threshold of %g is below the required level of %g"
                % (single_event["threshold_let"], single_event["required_let"])
            )
        result["disposition"] = "failed-single-event"
        result["findings"] = findings
        return result

    if not total_dose["compliant"]:
        findings.append(
            "demonstrated margin of %g is short of the required %g by %g rad of "
            "capability"
            % (
                total_dose["radiation_design_margin"],
                required_margin,
                total_dose["dose_shortfall"],
            )
        )
        result["disposition"] = "failed-total-dose"
        result["findings"] = findings
        return result

    findings.append(
        "sample of %d part(s) credited at %g demonstrates a margin of %g"
        % (
            capability["sample_size"],
            capability["credit_factor"],
            total_dose["radiation_design_margin"],
        )
    )
    result["disposition"] = "verification-passed"
    result["findings"] = findings
    return result
