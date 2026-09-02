#!/usr/bin/env python3
"""ARP4761A functional hazard assessment (FHA) logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4761a: gated): the FHA
opens the safety assessment process. It identifies failure conditions
(the effects on the aircraft and occupants caused by one or more
failures or errors) for each function at aircraft level (A-FHA) and
system level (S-FHA), rates each failure condition by severity, and
derives the quantitative probability target that the downstream PSSA
and SSA must show is met. The severity categories are catastrophic,
hazardous, major, minor, and no safety effect; the commonly applied
probability targets (per flight hour) are below 1e-9, 1e-7, 1e-5, and
1e-3 respectively, with no quantitative target for no safety effect.
Bands follow AC 25.1309-1A terminology: extremely improbable below 1e-9,
extremely remote 1e-9 to 1e-7, remote 1e-7 to 1e-5, probable at or above
1e-5. All logic is deterministic, stdlib only, offline.

Worked anchors (verified by scripts/test_functional_hazard_assessment.py):
    severity_order("Catastrophic") == 5, severity_order("Minor") == 2
    probability_target("Hazardous") ==
        ("extremely remote", 1e-7, "< 1e-7 per flight hour")
    target_met("Catastrophic", 5e-10) is True   (5e-10 < 1e-9)
    target_met("Major", 2e-5) is False          (2e-5 is not < 1e-5)
    highest_severity_met(1e-6) == "Major"       (1e-6 < 1e-5, not < 1e-7)
    worksheet_row("Autopilot", "Loss of all pitch control", "Climb",
        "Loss of the aircraft", "Catastrophic", 5e-10)["meets_target"] is True
"""

SEVERITY_TO_TARGET = {
    "Catastrophic": ("extremely improbable", 1e-9, "< 1e-9 per flight hour"),
    "Hazardous": ("extremely remote", 1e-7, "< 1e-7 per flight hour"),
    "Major": ("remote", 1e-5, "< 1e-5 per flight hour"),
    "Minor": ("probable", 1e-3, "< 1e-3 per flight hour"),
    "No safety effect": ("no quantitative target", None, "no quantitative target"),
}

SEVERITY_ORDER = {
    "Catastrophic": 5,
    "Hazardous": 4,
    "Major": 3,
    "Minor": 2,
    "No safety effect": 1,
}

# AC 25.1309-1A band terminology, used for reverse lookups.
BAND_THRESHOLDS = (
    (1e-9, "extremely improbable"),
    (1e-7, "extremely remote"),
    (1e-5, "remote"),
)

# Keyword heuristic for rating severity from a written effect statement.
# Checked in severity order; first keyword hit wins. The result is a
# starting point for the FHA worksheet row, always confirmed by the team.
EFFECT_KEYWORDS = (
    ("Catastrophic", ("loss of all", "uncontrolled", "crash", "fatal", "catastrophic")),
    ("Hazardous", ("serious injury", "large reduction in safety margins", "hazardous", "uncontained")),
    ("Major", ("significant reduction in safety margins", "physical discomfort", "major")),
    ("Minor", ("slight reduction", "inconvenience", "minor")),
)


def _check_severity(severity):
    if severity not in SEVERITY_ORDER:
        raise ValueError(
            "unknown failure-condition severity: %r (expected one of %s)"
            % (severity, ", ".join(sorted(SEVERITY_ORDER)))
        )


def _check_probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("probability per flight hour must be a number, got %r" % (value,))
    if value < 0:
        raise ValueError("probability per flight hour cannot be negative: %r" % (value,))


def severity_order(severity):
    """Rank of a severity category, 5 = catastrophic down to 1 = no safety
    effect. Anchor: severity_order("Catastrophic") == 5;
    severity_order("Minor") == 2."""
    _check_severity(severity)
    return SEVERITY_ORDER[severity]


def probability_target(severity):
    """(band, upper_bound_per_fh, target_text) for a severity category.
    Anchor: probability_target("Hazardous") == ("extremely remote", 1e-7,
    "< 1e-7 per flight hour"); "No safety effect" has upper_bound None."""
    _check_severity(severity)
    return SEVERITY_TO_TARGET[severity]


def target_met(severity, probability_per_fh):
    """True when the assessed probability is strictly below the severity's
    quantitative target; None for 'No safety effect' (no quantitative
    target applies). Anchor: target_met("Catastrophic", 5e-10) is True;
    target_met("Major", 2e-5) is False; target_met("Minor", 1e-3) is
    False because the target is strict (< 1e-3)."""
    _check_severity(severity)
    _check_probability(probability_per_fh)
    if severity == "No safety effect":
        return None
    return probability_per_fh < SEVERITY_TO_TARGET[severity][1]


def probability_band(probability_per_fh):
    """AC 25.1309-1A band name for a probability per flight hour.
    Anchor: probability_band(1e-10) == "extremely improbable";
    probability_band(5e-8) == "extremely remote";
    probability_band(1e-6) == "remote"; probability_band(1e-4) == "probable"."""
    _check_probability(probability_per_fh)
    for threshold, band in BAND_THRESHOLDS:
        if probability_per_fh < threshold:
            return band
    return "probable"


def highest_severity_met(probability_per_fh):
    """Most severe category whose quantitative target the assessed
    probability satisfies, or 'None'. Anchor:
    highest_severity_met(5e-10) == "Catastrophic";
    highest_severity_met(5e-8) == "Hazardous";
    highest_severity_met(1e-6) == "Major";
    highest_severity_met(1e-4) == "Minor";
    highest_severity_met(1e-2) == "None"."""
    _check_probability(probability_per_fh)
    for severity, (_, upper, _) in SEVERITY_TO_TARGET.items():
        if upper is None:
            continue
        if probability_per_fh < upper:
            return severity
    return "None"


def rate_severity_from_effects(effect_on_aircraft):
    """Heuristic severity rating from a written effect statement, using the
    first keyword match in severity order. Returns (severity, matched
    keyword) or ("No safety effect", None). Anchor:
    rate_severity_from_effects("Loss of all thrust on takeoff") ==
        ("Catastrophic", "loss of all");
    rate_severity_from_effects("Crew physical discomfort") ==
        ("Major", "physical discomfort")."""
    if not isinstance(effect_on_aircraft, str) or not effect_on_aircraft.strip():
        raise ValueError("effect_on_aircraft must be a non-empty string")
    lowered = effect_on_aircraft.lower()
    for severity, keywords in EFFECT_KEYWORDS:
        for keyword in keywords:
            if keyword in lowered:
                return (severity, keyword)
    return ("No safety effect", None)


def fha_scope(level):
    """FHA level name: aircraft-level assessment is the A-FHA, system-level
    is the S-FHA. Anchor: fha_scope("aircraft-level") == "A-FHA";
    fha_scope("system-level") == "S-FHA"."""
    scopes = {"aircraft-level": "A-FHA", "system-level": "S-FHA"}
    if level not in scopes:
        raise ValueError("unknown FHA scope: %r (expected 'aircraft-level' or 'system-level')" % (level,))
    return scopes[level]


def worksheet_row(function, failure_condition, flight_phase, effect_on_aircraft,
                  severity, assessed_probability_per_fh):
    """One populated FHA worksheet row as an ordered dict. Validates every
    input, looks up the probability target from the severity, and computes
    the meets_target verdict. Anchor: the autopilot row in the module
    docstring; worksheet_row("APU", "Loss of both generators", "Cruise",
    "Loss of electrical power", "Hazardous", 2e-8)["probability_target"] ==
    "< 1e-7 per flight hour"."""
    for name, value in (("function", function), ("failure_condition", failure_condition),
                        ("flight_phase", flight_phase), ("effect_on_aircraft", effect_on_aircraft)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be a non-empty string" % name)
    _check_severity(severity)
    _check_probability(assessed_probability_per_fh)
    band, upper, target_text = SEVERITY_TO_TARGET[severity]
    return {
        "function": function.strip(),
        "failure_condition": failure_condition.strip(),
        "flight_phase": flight_phase.strip(),
        "effect_on_aircraft": effect_on_aircraft.strip(),
        "severity": severity,
        "probability_target_band": band,
        "probability_target_upper_bound": upper,
        "probability_target": target_text,
        "assessed_probability_per_fh": assessed_probability_per_fh,
        "meets_target": target_met(severity, assessed_probability_per_fh),
        "safety_objective": (
            "P(failure condition) %s" % target_text
            if upper is not None
            else "no quantitative objective; confirm no safety effect"
        ),
    }
