"""Radiation verification of a sensitive Class 3 EEE part against its mission.

Anchor: ECSS-Q-ST-60C clause 6.3.8 -- radiation testing that verifies sensitive
Class 3 parts against the declared mission environment. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether a radiation-sensitive Class 3 part is verified by the irradiation data
already in hand, still owes a flight-lot irradiation, or cannot be used at all.

1. Sensitivity. Only the technologies the project declared sensitive owe a
   verification. A film resistor does not, and demanding one for it buys
   nothing and hides the parts that do owe it.
2. Lot capability. A Class 3 verification rests on a sample of the flight lot,
   not on one piece. The capability carried forward is a one-sided lower
   tolerance bound -- the sample mean less a tolerance factor times the sample
   spread -- so a wide sample is not credited as though it were tight.
3. Tolerance factor. The factor comes from a project table keyed on the sample
   size. A size the table does not list is refused, never interpolated between
   two neighbours; an interpolated factor is an invented acceptance criterion.
4. Dose rate. Bipolar linear parts and optocouplers can fail at a lower total
   dose when the dose arrives slowly. Where only high-dose-rate data exists,
   the capability is derated before it is compared with anything.
5. Margin. The radiation design margin is the credited capability over the
   mission requirement, compared with the required margin through a named
   tolerance so a case sitting exactly on the bound is decided by the rule and
   not by which way the last bit rounded.
6. Single events. A destructive event whose onset sits at or below the mission
   threshold ends the part, unless the event is one the project permits to be
   mitigated at circuit level and a mitigation was actually declared.
"""

import statistics

__all__ = [
    "RADIATION_CATEGORIES",
    "ELDRS_SENSITIVE_CATEGORIES",
    "TOLERANCE_FACTORS",
    "DEFAULT_ELDRS_DERATING",
    "DEFAULT_REQUIRED_MARGIN",
    "MINIMUM_SAMPLE_SIZE",
    "BOUND_TOLERANCE",
    "DESTRUCTIVE_EVENT_TYPES",
    "MITIGABLE_EVENT_TYPES",
    "ROUTES",
    "normalize_category",
    "is_sensitive",
    "tolerance_factor",
    "sample_statistics",
    "lot_capability",
    "radiation_design_margin",
    "margin_meets",
    "single_event_verdict",
    "assess_radiation_verification",
]

# Part technologies and whether the project treats them as dose sensitive.
RADIATION_CATEGORIES = {
    "bipolar-linear": True,
    "cmos-digital": True,
    "power-mosfet": True,
    "optocoupler": True,
    "passive-film": False,
    "passive-ceramic": False,
}

# Technologies that can fail earlier when the dose arrives slowly.
ELDRS_SENSITIVE_CATEGORIES = ("bipolar-linear", "optocoupler")

# One-sided lower tolerance factors, keyed on the irradiated sample size.
TOLERANCE_FACTORS = {
    3: 3.15,
    5: 2.74,
    8: 2.44,
    10: 2.36,
    15: 2.07,
    20: 1.93,
    30: 1.78,
}

# Applied to the capability when only high-dose-rate data exists.
DEFAULT_ELDRS_DERATING = 2.0

# Class 3 radiation design margin the credited capability has to reach.
DEFAULT_REQUIRED_MARGIN = 1.2

# Fewer pieces than this cannot carry a lot capability.
MINIMUM_SAMPLE_SIZE = 3

# Absorbs floating-point representation error at a comparison bound. It is not
# an engineering allowance and is never widened to make a case pass.
BOUND_TOLERANCE = 1e-9

# Single event types that destroy the part rather than upset it.
DESTRUCTIVE_EVENT_TYPES = (
    "single-event-latch-up",
    "single-event-burnout",
    "single-event-gate-rupture",
)

# Destructive events the project may permit to be handled at circuit level.
MITIGABLE_EVENT_TYPES = ("single-event-latch-up",)

# The three ways a sensitive Class 3 part leaves this assessment.
ROUTES = ("accept-on-lot-data", "irradiate-flight-lot", "reject")


def _text(label, value):
    """Return value as a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def _positive(label, value):
    """Return value as a strictly positive float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not number > 0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    if number != number:
        raise ValueError("%s must be a real number, got %r" % (label, value))
    return number


def normalize_category(category):
    """Return a declared part technology in canonical form."""
    text = _text("category", category).lower()
    if text not in RADIATION_CATEGORIES:
        raise ValueError(
            "category %r is not one of %s"
            % (category, ", ".join(sorted(RADIATION_CATEGORIES)))
        )
    return text


def is_sensitive(category):
    """Return whether the project treats this technology as dose sensitive."""
    return RADIATION_CATEGORIES[normalize_category(category)]


def tolerance_factor(sample_size, table=None):
    """Return the one-sided lower tolerance factor for an irradiated sample.

    A sample size the table does not list is refused. Between two entries the
    table states no factor at all, and inventing one invents the criterion.
    """
    if not isinstance(sample_size, int) or isinstance(sample_size, bool):
        raise ValueError("sample_size must be an integer, got %r" % (sample_size,))
    factors = TOLERANCE_FACTORS if table is None else table
    if not isinstance(factors, dict) or not factors:
        raise ValueError("table must be a non-empty mapping of size to factor")
    if sample_size not in factors:
        raise ValueError(
            "sample size %d is not tabulated; listed sizes are %s"
            % (sample_size, ", ".join(str(k) for k in sorted(factors)))
        )
    return _positive("tolerance factor for %d" % sample_size, factors[sample_size])


def sample_statistics(doses):
    """Return the size, mean and spread of an irradiated sample.

    doses: failure doses of the irradiated pieces, in the mission's dose unit.
    """
    if not isinstance(doses, (list, tuple)):
        raise ValueError("doses must be a sequence of measured failure doses")
    if len(doses) < MINIMUM_SAMPLE_SIZE:
        raise ValueError(
            "a lot capability needs at least %d irradiated pieces, got %d"
            % (MINIMUM_SAMPLE_SIZE, len(doses))
        )
    values = [_positive("doses[%d]" % i, d) for i, d in enumerate(doses)]
    return {
        "size": len(values),
        "mean": statistics.mean(values),
        "spread": statistics.stdev(values),
        "lowest": min(values),
    }


def lot_capability(
    doses,
    category,
    low_dose_rate_data=True,
    eldrs_derating=DEFAULT_ELDRS_DERATING,
    table=None,
):
    """Return the dose capability credited to an irradiated Class 3 lot.

    The lower tolerance bound is derated when the technology is dose-rate
    sensitive and only high-dose-rate data exists. A bound that falls to or
    below zero credits nothing rather than a negative capability.
    """
    kind = normalize_category(category)
    stats = sample_statistics(doses)
    factor = tolerance_factor(stats["size"], table)
    slow_data = _flag("low_dose_rate_data", low_dose_rate_data)
    bound = stats["mean"] - factor * stats["spread"]
    derating = 1.0
    eldrs_applies = kind in ELDRS_SENSITIVE_CATEGORIES and not slow_data
    if eldrs_applies:
        derating = _positive("eldrs_derating", eldrs_derating)
        if derating < 1.0:
            raise ValueError(
                "eldrs_derating must be at least 1.0, got %r" % (eldrs_derating,)
            )
    credited = bound / derating
    findings = []
    if credited <= 0.0:
        credited = 0.0
        findings.append(
            "the sample spread swallows its mean; the lot credits no capability"
        )
    if eldrs_applies:
        findings.append(
            "high-dose-rate data only on a dose-rate sensitive technology; "
            "capability derated by %g" % derating
        )
    return {
        "category": kind,
        "sample": stats,
        "tolerance_factor": factor,
        "lower_bound": bound,
        "eldrs_applied": eldrs_applies,
        "eldrs_derating": derating,
        "capability": credited,
        "findings": findings,
    }


def radiation_design_margin(capability, requirement):
    """Return the credited capability over the mission dose requirement."""
    if isinstance(capability, bool) or not isinstance(capability, (int, float)):
        raise ValueError("capability must be a number, got %r" % (capability,))
    if float(capability) < 0:
        raise ValueError("capability must be non-negative, got %r" % (capability,))
    needed = _positive("requirement", requirement)
    return float(capability) / needed


def margin_meets(margin, required=DEFAULT_REQUIRED_MARGIN, tolerance=BOUND_TOLERANCE):
    """Return whether a margin reaches the required one.

    A case sitting exactly on the bound is a pass. The tolerance absorbs how
    the division represented itself, not any part of the engineering limit.
    """
    if isinstance(margin, bool) or not isinstance(margin, (int, float)):
        raise ValueError("margin must be a number, got %r" % (margin,))
    needed = _positive("required", required)
    slack = _positive("tolerance", tolerance)
    return float(margin) >= needed - slack


def single_event_verdict(
    events, mission_let, mitigations=None, allow_mitigation_credit=False
):
    """Return the single event outcome for one part against its mission.

    events: sequence of mappings with event_type and onset_let. A destructive
    event whose onset sits at or below the mission threshold vetoes the part,
    unless the project permits mitigation for that event type and a mitigation
    was declared for it.
    """
    if events is None:
        events = ()
    if not isinstance(events, (list, tuple)):
        raise ValueError("events must be a sequence of single event records")
    threshold = _positive("mission_let", mission_let)
    if mitigations is None:
        mitigations = ()
    if not isinstance(mitigations, (list, tuple)):
        raise ValueError("mitigations must be a sequence of event type names")
    permitted = _flag("allow_mitigation_credit", allow_mitigation_credit)
    declared = {_text("mitigation", m).lower() for m in mitigations}
    vetoes = []
    mitigated = []
    survivors = []
    for index, item in enumerate(events):
        if not isinstance(item, dict):
            raise ValueError("events[%d] must be a mapping" % index)
        for key in ("event_type", "onset_let"):
            if key not in item:
                raise ValueError("events[%d] missing required key '%s'" % (index, key))
        kind = _text("events[%d].event_type" % index, item["event_type"]).lower()
        onset = _positive("events[%d].onset_let" % index, item["onset_let"])
        record = {"event_type": kind, "onset_let": onset}
        if kind not in DESTRUCTIVE_EVENT_TYPES:
            survivors.append(record)
            continue
        if onset > threshold + BOUND_TOLERANCE:
            survivors.append(record)
            continue
        if permitted and kind in MITIGABLE_EVENT_TYPES and kind in declared:
            mitigated.append(record)
        else:
            vetoes.append(record)
    findings = [
        "%s onsets at %g, at or below the mission threshold %g"
        % (v["event_type"], v["onset_let"], threshold)
        for v in vetoes
    ]
    findings.extend(
        "%s onsets inside the mission environment but a declared mitigation covers it"
        % m["event_type"]
        for m in mitigated
    )
    return {
        "mission_let": threshold,
        "vetoes": vetoes,
        "mitigated": mitigated,
        "survivors": survivors,
        "vetoed": bool(vetoes),
        "findings": findings,
    }


def assess_radiation_verification(spec):
    """Return the clause 6.3.8 verification decision for one Class 3 part.

    spec keys: category and mission_dose; optional doses, low_dose_rate_data,
    eldrs_derating, required_margin, mission_let, events, mitigations,
    allow_mitigation_credit and tolerance_table.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("category", "mission_dose"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    kind = normalize_category(spec["category"])
    requirement = _positive("mission_dose", spec["mission_dose"])
    if not RADIATION_CATEGORIES[kind]:
        return {
            "category": kind,
            "sensitive": False,
            "route": "accept-on-lot-data",
            "capability": None,
            "margin": None,
            "required_margin": None,
            "single_events": None,
            "findings": [
                "technology '%s' is not dose sensitive; no verification is owed" % kind
            ],
        }
    required = _positive(
        "required_margin", spec.get("required_margin", DEFAULT_REQUIRED_MARGIN)
    )
    findings = []
    events = single_event_verdict(
        spec.get("events"),
        spec.get("mission_let", 60.0),
        spec.get("mitigations"),
        spec.get("allow_mitigation_credit", False),
    )
    findings.extend(events["findings"])
    doses = spec.get("doses")
    if not doses:
        findings.append(
            "no flight-lot irradiation data; the part owes its own irradiation"
        )
        route = "reject" if events["vetoed"] else "irradiate-flight-lot"
        return {
            "category": kind,
            "sensitive": True,
            "capability": None,
            "margin": None,
            "required_margin": required,
            "meets_margin": False,
            "single_events": events,
            "route": route,
            "findings": findings,
        }
    capability = lot_capability(
        doses,
        kind,
        spec.get("low_dose_rate_data", True),
        spec.get("eldrs_derating", DEFAULT_ELDRS_DERATING),
        spec.get("tolerance_table"),
    )
    findings.extend(capability["findings"])
    margin = radiation_design_margin(capability["capability"], requirement)
    meets = margin_meets(margin, required)
    if not meets:
        findings.append(
            "radiation design margin %.4f falls short of the required %.4f"
            % (margin, required)
        )
    if events["vetoed"]:
        route = "reject"
    elif meets:
        route = "accept-on-lot-data"
    else:
        route = "irradiate-flight-lot"
    return {
        "category": kind,
        "sensitive": True,
        "capability": capability,
        "margin": margin,
        "required_margin": required,
        "meets_margin": meets,
        "single_events": events,
        "route": route,
        "findings": findings,
    }
