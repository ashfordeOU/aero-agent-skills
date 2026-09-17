"""Radiation effect mechanisms credible for a space component technology.

Anchor: ECSS-Q-ST-60-15C clause 4.2 (the cumulative dose, displacement damage
and single event mechanisms that act on electronic components in a space
radiation environment). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the component: its technology, its declared single-event onset
   threshold in linear energy transfer, and the verification methods the plan
   already carries.
2. Validate the environment: the cumulative dose and displacement damage the
   part will accumulate, and the highest linear energy transfer the mission
   makes available.
3. Take the mechanism set the technology is open to, then screen it against
   the environment: a cumulative mechanism needs a positive level of its own
   driving quantity, and a single event mechanism needs the environment to
   reach the part's onset threshold.
4. Group the surviving mechanisms into cumulative and single event families
   and separate the destructive ones, because a destructive mechanism changes
   what the verification has to prove and what a failure costs.
5. Derive the verification methods the credible set demands, compare them with
   the declared plan, and name every method the plan is short of.
6. Return the grouped mechanism sets, the demanded methods and a verdict that
   treats an unaddressed destructive mechanism as its own finding.
"""

import math

__all__ = [
    "MECHANISMS",
    "MECHANISM_FAMILIES",
    "TECHNOLOGIES",
    "TECHNOLOGY_SUSCEPTIBILITY",
    "LOW_DOSE_RATE_SENSITIVE",
    "DEFAULT_LET_SCREENING_FACTOR",
    "LET_TOLERANCE",
    "normalize_token",
    "validate_mechanism",
    "validate_technology",
    "mechanism_family",
    "is_destructive",
    "driving_quantity",
    "required_method",
    "group_by_family",
    "destructive_subset",
    "validate_environment",
    "single_event_reachable",
    "credible_mechanisms",
    "demanded_methods",
    "validate_component",
    "assess_component",
]

# Each mechanism carries the family it belongs to, whether one occurrence can
# destroy the part, the environment quantity that drives it and the
# verification method that demonstrates the part against it.
MECHANISMS = {
    "total-ionising-dose": {
        "family": "cumulative",
        "destructive": False,
        "driver": "total-ionising-dose",
        "method": "cumulative-dose-step-test",
    },
    "displacement-damage": {
        "family": "cumulative",
        "destructive": False,
        "driver": "displacement-damage-dose",
        "method": "proton-displacement-test",
    },
    "single-event-upset": {
        "family": "single-event",
        "destructive": False,
        "driver": "linear-energy-transfer",
        "method": "heavy-ion-single-event-test",
    },
    "single-event-transient": {
        "family": "single-event",
        "destructive": False,
        "driver": "linear-energy-transfer",
        "method": "heavy-ion-single-event-test",
    },
    "single-event-functional-interrupt": {
        "family": "single-event",
        "destructive": False,
        "driver": "linear-energy-transfer",
        "method": "heavy-ion-single-event-test",
    },
    "single-event-latchup": {
        "family": "single-event",
        "destructive": True,
        "driver": "linear-energy-transfer",
        "method": "heavy-ion-destructive-event-test",
    },
    "single-event-gate-rupture": {
        "family": "single-event",
        "destructive": True,
        "driver": "linear-energy-transfer",
        "method": "heavy-ion-destructive-event-test",
    },
    "single-event-burnout": {
        "family": "single-event",
        "destructive": True,
        "driver": "linear-energy-transfer",
        "method": "heavy-ion-destructive-event-test",
    },
}

MECHANISM_FAMILIES = ("cumulative", "single-event")

# Which mechanisms each technology is open to before the environment is
# considered. The order is the order they are reported in.
TECHNOLOGY_SUSCEPTIBILITY = {
    "bulk-cmos-digital": (
        "total-ionising-dose",
        "single-event-upset",
        "single-event-transient",
        "single-event-functional-interrupt",
        "single-event-latchup",
    ),
    "soi-cmos-digital": (
        "total-ionising-dose",
        "single-event-upset",
        "single-event-transient",
        "single-event-functional-interrupt",
    ),
    "sram-based-fpga": (
        "total-ionising-dose",
        "single-event-upset",
        "single-event-transient",
        "single-event-functional-interrupt",
        "single-event-latchup",
    ),
    "bipolar-linear": (
        "total-ionising-dose",
        "displacement-damage",
        "single-event-transient",
    ),
    "power-mosfet": (
        "total-ionising-dose",
        "single-event-gate-rupture",
        "single-event-burnout",
    ),
    "optocoupler": (
        "total-ionising-dose",
        "displacement-damage",
        "single-event-transient",
    ),
    "imaging-detector": (
        "total-ionising-dose",
        "displacement-damage",
        "single-event-upset",
    ),
    "solar-cell-assembly": (
        "total-ionising-dose",
        "displacement-damage",
    ),
}

TECHNOLOGIES = tuple(sorted(TECHNOLOGY_SUSCEPTIBILITY))

# Technologies whose cumulative dose response worsens at the low dose rates a
# mission actually delivers, so a high-rate test alone does not demonstrate
# them.
LOW_DOSE_RATE_SENSITIVE = ("bipolar-linear", "optocoupler")

# Onset screening is done against the environment as it stands unless the
# project declares a factor.
DEFAULT_LET_SCREENING_FACTOR = 1.0

# The onset comparison is between two measured energies; a part whose onset
# sits exactly at the environment maximum must not be screened out on
# representation alone.
LET_TOLERANCE = 1e-9


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %s" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _non_negative_number(value, label):
    """Return a finite real number that is not below zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _positive_number(value, label):
    """Return a strictly positive finite real number."""
    number = _non_negative_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %g" % (label, number))
    return number


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_mechanism(value):
    """Return the validated mechanism token."""
    token = normalize_token(value, "mechanism")
    if token not in MECHANISMS:
        raise ValueError(
            "mechanism '%s' is not recognized; expected one of %s"
            % (token, ", ".join(sorted(MECHANISMS)))
        )
    return token


def validate_technology(value):
    """Return the validated component technology token."""
    token = normalize_token(value, "technology")
    if token not in TECHNOLOGY_SUSCEPTIBILITY:
        raise ValueError(
            "technology '%s' is not recognized; expected one of %s"
            % (token, ", ".join(TECHNOLOGIES))
        )
    return token


def mechanism_family(value):
    """Return the family a mechanism belongs to."""
    return MECHANISMS[validate_mechanism(value)]["family"]


def is_destructive(value):
    """Return whether one occurrence of a mechanism can destroy the part."""
    return MECHANISMS[validate_mechanism(value)]["destructive"]


def driving_quantity(value):
    """Return the environment quantity that drives a mechanism."""
    return MECHANISMS[validate_mechanism(value)]["driver"]


def required_method(value):
    """Return the verification method a mechanism demands."""
    return MECHANISMS[validate_mechanism(value)]["method"]


def group_by_family(mechanisms):
    """Return the mechanisms grouped into their families, order preserved."""
    if not isinstance(mechanisms, (list, tuple)):
        raise ValueError("mechanisms must be a sequence")
    grouped = {family: [] for family in MECHANISM_FAMILIES}
    for value in mechanisms:
        token = validate_mechanism(value)
        family = MECHANISMS[token]["family"]
        if token not in grouped[family]:
            grouped[family].append(token)
    return grouped


def destructive_subset(mechanisms):
    """Return only the mechanisms that can destroy the part in one event."""
    if not isinstance(mechanisms, (list, tuple)):
        raise ValueError("mechanisms must be a sequence")
    out = []
    for value in mechanisms:
        token = validate_mechanism(value)
        if MECHANISMS[token]["destructive"] and token not in out:
            out.append(token)
    return out


def validate_environment(environment):
    """Return the validated environment the component will be exposed to."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping")
    for key in (
        "total_ionising_dose",
        "displacement_damage_dose",
        "max_linear_energy_transfer",
    ):
        if key not in environment:
            raise ValueError("environment missing required key '%s'" % key)
    return {
        "total-ionising-dose": _non_negative_number(
            environment["total_ionising_dose"], "total_ionising_dose"
        ),
        "displacement-damage-dose": _non_negative_number(
            environment["displacement_damage_dose"], "displacement_damage_dose"
        ),
        "linear-energy-transfer": _non_negative_number(
            environment["max_linear_energy_transfer"], "max_linear_energy_transfer"
        ),
    }


def single_event_reachable(onset_threshold, max_let, screening_factor=None):
    """Return whether the environment reaches a part's single-event onset.

    A part whose onset sits exactly at the screened environment maximum is
    reachable; the equality is met, and only its floating-point representation
    is in question.
    """
    onset = _positive_number(onset_threshold, "onset threshold")
    available = _non_negative_number(max_let, "max_linear_energy_transfer")
    factor = (
        DEFAULT_LET_SCREENING_FACTOR
        if screening_factor is None
        else _positive_number(screening_factor, "screening factor")
    )
    screened = available * factor
    if math.isclose(onset, screened, rel_tol=LET_TOLERANCE, abs_tol=0.0):
        return True
    return onset < screened


def credible_mechanisms(technology, environment, onset_threshold=None,
                        screening_factor=None):
    """Return the mechanisms that survive screening against the environment."""
    token = validate_technology(technology)
    levels = validate_environment(environment)
    credible = []
    screened_out = []
    for mechanism in TECHNOLOGY_SUSCEPTIBILITY[token]:
        driver = MECHANISMS[mechanism]["driver"]
        if driver == "linear-energy-transfer":
            if levels["linear-energy-transfer"] <= 0.0:
                screened_out.append(mechanism)
                continue
            if onset_threshold is None:
                credible.append(mechanism)
                continue
            if single_event_reachable(
                onset_threshold, levels["linear-energy-transfer"], screening_factor
            ):
                credible.append(mechanism)
            else:
                screened_out.append(mechanism)
        else:
            if levels[driver] > 0.0:
                credible.append(mechanism)
            else:
                screened_out.append(mechanism)
    return {"credible": credible, "screened_out": screened_out}


def demanded_methods(mechanisms, technology=None):
    """Return the verification methods a mechanism set demands, deduplicated."""
    if not isinstance(mechanisms, (list, tuple)):
        raise ValueError("mechanisms must be a sequence")
    methods = []
    for value in mechanisms:
        method = required_method(value)
        if method not in methods:
            methods.append(method)
    if technology is not None:
        token = validate_technology(technology)
        if token in LOW_DOSE_RATE_SENSITIVE and "cumulative-dose-step-test" in methods:
            extra = "low-dose-rate-cumulative-test"
            if extra not in methods:
                methods.append(extra)
    return methods


def validate_component(component):
    """Return one validated component declaration."""
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping")
    for key in ("part_number", "technology"):
        if key not in component:
            raise ValueError("component missing required key '%s'" % key)

    onset = component.get("onset_threshold")
    if onset is not None:
        onset = _positive_number(onset, "onset_threshold")

    declared = component.get("declared_methods", [])
    if declared is None:
        declared = []
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared_methods must be a sequence")
    methods = []
    for index, value in enumerate(declared):
        method = normalize_token(value, "declared_methods[%d]" % index)
        if method in methods:
            raise ValueError("verification method '%s' is declared twice" % method)
        methods.append(method)

    return {
        "part_number": _require_text(component["part_number"], "part_number"),
        "technology": validate_technology(component["technology"]),
        "onset_threshold": onset,
        "declared_methods": methods,
    }


def assess_component(component, environment, screening_factor=None):
    """Run the full clause 4.2 mechanism assessment of one component."""
    entry = validate_component(component)
    levels = validate_environment(environment)

    screening = credible_mechanisms(
        entry["technology"], environment, entry["onset_threshold"], screening_factor
    )
    credible = screening["credible"]
    grouped = group_by_family(credible)
    destructive = destructive_subset(credible)
    demanded = demanded_methods(credible, entry["technology"])
    absent_methods = [m for m in demanded if m not in entry["declared_methods"]]

    findings = []
    for method in absent_methods:
        covered = [
            m for m in credible if required_method(m) == method
        ]
        if any(MECHANISMS[m]["destructive"] for m in covered):
            findings.append(
                "component '%s' leaves a destructive mechanism unverified: "
                "no '%s' in the plan" % (entry["part_number"], method)
            )
        else:
            findings.append(
                "component '%s' has no '%s' in the plan"
                % (entry["part_number"], method)
            )
    if not credible:
        findings.append(
            "component '%s' screens out every mechanism its technology is open to"
            % entry["part_number"]
        )

    return {
        "part_number": entry["part_number"],
        "technology": entry["technology"],
        "environment": levels,
        "credible_mechanisms": credible,
        "screened_out_mechanisms": screening["screened_out"],
        "grouped_mechanisms": grouped,
        "destructive_mechanisms": destructive,
        "demanded_methods": demanded,
        "absent_methods": absent_methods,
        "coverage_complete": not absent_methods,
        "findings": findings,
        "acceptable": not findings,
    }
