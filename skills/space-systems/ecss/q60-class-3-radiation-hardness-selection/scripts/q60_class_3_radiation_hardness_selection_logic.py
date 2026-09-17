#!/usr/bin/env python3
"""Matching a Class 3 part's radiation tolerance to its mission.

Anchor: ECSS-Q-ST-60C clause 6.2.2.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A Class 3 part is not selected against a radiation number in the
abstract. It is selected against the dose it will actually accumulate
behind its own local shielding over the whole declared lifetime, and
against the heavy ions it will meet while it is switched on.

Dose is a lifetime quantity, so it is accumulated phase by phase.
A transfer orbit contributes more per year than the operational orbit
and a short commissioning phase can dominate a long quiet one. Local
shielding scales what arrives; a part inside a filled box sees less
than the box wall implies, and a part on an external panel sees more.

The margin applied on top is not a constant. It is set by how the
capability figure was obtained. A lot-specific test on the parts being
bought carries the least uncertainty; heritage on the same date code
carries more; a manufacturer's datasheet figure is a population claim,
not a lot claim; and a similarity argument to another part is the
weakest of all. The margin rises as the evidence weakens, which is what
makes a cheap datasheet number expensive in dose terms. Past a mission
dose threshold a datasheet or similarity claim stops being admissible
at all and a lot-specific test is owed instead.

A rate-sensitive technology adds a trap. Bipolar and BiCMOS parts
degrade more at the slow dose rates of a real orbit than in a fast
ground test, so a capability characterised at high dose rate is cut
before it is compared with anything.

Single event effects are graded separately and not all alike. A
destructive mechanism -- latch-up, burnout, gate rupture -- ends the
part, so the ion threshold has to clear the environment with margin,
and only latch-up can be argued away at application level by limiting
and cycling the supply. A recoverable mechanism costs availability, not
hardware, so a credited application-level mitigation closes it.

The useful output is the binding mechanism, the margin on each one, the
evidence still owed, and one disposition.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

TECHNOLOGIES = (
    "cmos-bulk",
    "cmos-soi",
    "bipolar-linear",
    "bicmos",
    "gan-power",
    "compound-semiconductor",
)

RATE_SENSITIVE_TECHNOLOGIES = frozenset(("bipolar-linear", "bicmos"))

DOSE_RATE_BASES = ("high-dose-rate", "low-dose-rate")

LOW_DOSE_RATE_DERATE = 0.5

CAPABILITY_DATA_SOURCES = (
    "lot-specific-test",
    "same-date-code-heritage",
    "manufacturer-datasheet",
    "similarity-to-another-part",
)

RADIATION_DESIGN_MARGIN = {
    "lot-specific-test": 1.5,
    "same-date-code-heritage": 2.0,
    "manufacturer-datasheet": 3.0,
    "similarity-to-another-part": 5.0,
}

LOT_TEST_TRIGGER_DOSE_KRAD = 10.0

LOT_EVIDENCE_SOURCES = frozenset(("lot-specific-test", "same-date-code-heritage"))

SINGLE_EVENT_MECHANISMS = (
    "single-event-latch-up",
    "single-event-burnout",
    "single-event-gate-rupture",
    "single-event-upset",
    "single-event-transient",
    "single-event-functional-interrupt",
)

DESTRUCTIVE_MECHANISMS = frozenset(
    (
        "single-event-latch-up",
        "single-event-burnout",
        "single-event-gate-rupture",
    )
)

DESTRUCTIVE_LET_MARGIN = 1.2
RECOVERABLE_LET_MARGIN = 1.0

APPLICATION_MITIGATIONS = (
    "none",
    "supply-current-limiting-and-cycle",
    "error-detection-and-correction",
    "triple-modular-redundancy",
    "watchdog-reset",
)

RECOVERABLE_MITIGATIONS = frozenset(
    (
        "error-detection-and-correction",
        "triple-modular-redundancy",
        "watchdog-reset",
    )
)

LATCH_UP_MITIGATIONS = frozenset(("supply-current-limiting-and-cycle",))

MARGIN_ADEQUATE = "margin-adequate"
MARGIN_ON_LIMIT = "margin-on-limit"
MARGIN_SHORT = "margin-short"
EVIDENCE_ABSENT = "evidence-absent"

RADIATION_ADEQUATE = "class-3-radiation-selection-adequate"
RADIATION_MITIGATION_REQUIRED = "class-3-radiation-selection-needs-mitigation"
RADIATION_EVIDENCE_INCOMPLETE = "class-3-radiation-selection-evidence-incomplete"
RADIATION_INADEQUATE = "class-3-radiation-selection-inadequate"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_shielding_factor(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0 or value > 1.0:
        raise ValueError("%s must sit above 0 and at most 1, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _equal(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    Every margin here is a quotient of two accumulated quantities while
    the bound it is graded against is unity, so a part sized exactly to
    its requirement can land a few units in the last place under it. The
    bound is never moved; only the comparison tolerates the error.
    """
    return value >= limit or _equal(value, limit)


def validate_mission_phases(phases):
    """Check a declared mission profile before anything is accumulated."""
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("mission_phases must be a non-empty sequence of mappings")
    names = set()
    validated = []
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError("each mission phase must be a mapping, got %r" % (phase,))
        name = _require_text("phase name", phase.get("name"))
        if name in names:
            raise ValueError("mission phase %s declared twice" % name)
        names.add(name)
        years = _require_positive("years of %s" % name, phase.get("years"))
        annual = _require_non_negative(
            "annual_dose_krad of %s" % name, phase.get("annual_dose_krad")
        )
        validated.append({"name": name, "years": years, "annual_dose_krad": annual})
    return validated


def mission_duration_years(mission_phases):
    """Declared lifetime, which is the span the dose is accumulated over."""
    return sum(phase["years"] for phase in validate_mission_phases(mission_phases))


def mission_accumulated_dose(mission_phases, shielding_factor=1.0):
    """Dose the part actually sees behind its own local shielding."""
    factor = _require_shielding_factor("shielding_factor", shielding_factor)
    phases = validate_mission_phases(mission_phases)
    return sum(phase["years"] * phase["annual_dose_krad"] for phase in phases) * factor


def radiation_design_margin(data_source):
    """Margin factor set by how the capability figure was obtained."""
    _require_choice("capability_data_source", data_source, CAPABILITY_DATA_SOURCES)
    return RADIATION_DESIGN_MARGIN[data_source]


def required_capability(environment_value, margin_factor):
    """What the part has to withstand once the margin is applied."""
    value = _require_non_negative("environment_value", environment_value)
    margin = _require_positive("margin_factor", margin_factor)
    return value * margin


def effective_dose_capability(rated_dose_krad, technology, characterisation_dose_rate):
    """Rated dose after the rate-sensitivity cut, where one applies."""
    rated = _require_non_negative("rated_dose_krad", rated_dose_krad)
    _require_choice("technology", technology, TECHNOLOGIES)
    _require_choice(
        "characterisation_dose_rate", characterisation_dose_rate, DOSE_RATE_BASES
    )
    if (
        technology in RATE_SENSITIVE_TECHNOLOGIES
        and characterisation_dose_rate == "high-dose-rate"
    ):
        return rated * LOW_DOSE_RATE_DERATE
    return rated


def _grade_ratio(capability, requirement):
    if _equal(requirement, 0.0):
        return MARGIN_ADEQUATE, None
    ratio = capability / requirement
    if _equal(ratio, 1.0):
        return MARGIN_ON_LIMIT, ratio
    if ratio > 1.0:
        return MARGIN_ADEQUATE, ratio
    return MARGIN_SHORT, ratio


def grade_total_dose(case):
    """Grade accumulated mission dose against the part's rated capability."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    technology = _require_choice("technology", case.get("technology"), TECHNOLOGIES)
    data_source = _require_choice(
        "capability_data_source", case.get("capability_data_source"),
        CAPABILITY_DATA_SOURCES,
    )
    dose_rate = _require_choice(
        "characterisation_dose_rate",
        case.get("characterisation_dose_rate"),
        DOSE_RATE_BASES,
    )
    shielding = case.get("shielding_factor", 1.0)
    accumulated = mission_accumulated_dose(case.get("mission_phases"), shielding)
    margin = radiation_design_margin(data_source)
    requirement = required_capability(accumulated, margin)
    capability = effective_dose_capability(
        case.get("rated_dose_krad"), technology, dose_rate
    )
    grade, ratio = _grade_ratio(capability, requirement)
    derated = (
        technology in RATE_SENSITIVE_TECHNOLOGIES and dose_rate == "high-dose-rate"
    )
    lot_evidence_owed = (
        accumulated > LOT_TEST_TRIGGER_DOSE_KRAD
        and not _equal(accumulated, LOT_TEST_TRIGGER_DOSE_KRAD)
        and data_source not in LOT_EVIDENCE_SOURCES
    )
    if lot_evidence_owed:
        grade = EVIDENCE_ABSENT
    return {
        "mechanism": "total-ionising-dose",
        "accumulated_dose_krad": accumulated,
        "shielding_factor": _require_shielding_factor("shielding_factor", shielding),
        "mission_years": mission_duration_years(case.get("mission_phases")),
        "capability_data_source": data_source,
        "radiation_design_margin": margin,
        "required_dose_krad": requirement,
        "rated_dose_krad": _require_non_negative(
            "rated_dose_krad", case.get("rated_dose_krad")
        ),
        "effective_dose_krad": capability,
        "rate_sensitivity_applied": derated,
        "lot_evidence_owed": lot_evidence_owed,
        "margin_ratio": ratio,
        "grade": grade,
    }


def grade_single_event(entry, environment_let):
    """Grade one single event mechanism against the ion environment."""
    if not isinstance(entry, dict):
        raise ValueError("single event entry must be a mapping, got %r" % (entry,))
    mechanism = _require_choice(
        "mechanism", entry.get("mechanism"), SINGLE_EVENT_MECHANISMS
    )
    environment = _require_positive("environment_let", environment_let)
    mitigation = _require_choice(
        "mitigation of %s" % mechanism,
        entry.get("mitigation", "none"),
        APPLICATION_MITIGATIONS,
    )
    destructive = mechanism in DESTRUCTIVE_MECHANISMS
    factor = DESTRUCTIVE_LET_MARGIN if destructive else RECOVERABLE_LET_MARGIN
    requirement = environment * factor
    threshold = entry.get("let_threshold")
    if threshold is None:
        return {
            "mechanism": mechanism,
            "destructive": destructive,
            "environment_let": environment,
            "required_let": requirement,
            "let_threshold": None,
            "mitigation": mitigation,
            "margin_ratio": None,
            "grade": EVIDENCE_ABSENT,
            "mitigated": False,
        }
    capability = _require_non_negative("let_threshold of %s" % mechanism, threshold)
    grade, ratio = _grade_ratio(capability, requirement)
    mitigated = False
    if grade == MARGIN_SHORT:
        if destructive:
            mitigated = (
                mechanism == "single-event-latch-up"
                and mitigation in LATCH_UP_MITIGATIONS
            )
        else:
            mitigated = mitigation in RECOVERABLE_MITIGATIONS
    return {
        "mechanism": mechanism,
        "destructive": destructive,
        "environment_let": environment,
        "required_let": requirement,
        "let_threshold": capability,
        "mitigation": mitigation,
        "margin_ratio": ratio,
        "grade": grade,
        "mitigated": mitigated,
    }


def _binding(graded):
    ranked = [entry for entry in graded if entry.get("margin_ratio") is not None]
    if not ranked:
        return graded[0]["mechanism"] if graded else None
    return min(ranked, key=lambda entry: entry["margin_ratio"])["mechanism"]


def evaluate_radiation_selection(case):
    """Full clause 6.2.2.4 read on one Class 3 part choice."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    part_reference = _require_text("part_reference", case.get("part_reference"))
    environment_let = _require_positive(
        "environment_let", case.get("environment_let")
    )
    dose = grade_total_dose(case)
    entries = case.get("single_event_data", [])
    if not isinstance(entries, (list, tuple)):
        raise ValueError("single_event_data must be a sequence of mappings")
    graded_events = [grade_single_event(entry, environment_let) for entry in entries]
    seen = set()
    for graded in graded_events:
        if graded["mechanism"] in seen:
            raise ValueError("mechanism %s declared twice" % graded["mechanism"])
        seen.add(graded["mechanism"])
    covered = {graded["mechanism"] for graded in graded_events}
    uncovered_destructive = sorted(DESTRUCTIVE_MECHANISMS - covered)

    findings = []
    evidence_owed = []
    mitigations = []
    if dose["grade"] == EVIDENCE_ABSENT:
        evidence_owed.append(
            "a lot-specific dose test on %s: the mission accumulates %.2f krad, "
            "past the point where a %s figure can stand in"
            % (part_reference, dose["accumulated_dose_krad"], dose["capability_data_source"])
        )
    elif dose["grade"] == MARGIN_SHORT:
        findings.append(
            "the part withstands %.2f krad against %.2f krad required once the "
            "%.1f margin is applied"
            % (dose["effective_dose_krad"], dose["required_dose_krad"], dose["radiation_design_margin"])
        )
    for mechanism in uncovered_destructive:
        evidence_owed.append(
            "a %s threshold for %s: an undeclared destructive mechanism is "
            "untested, not immune" % (mechanism, part_reference)
        )
    for graded in graded_events:
        if graded["grade"] == EVIDENCE_ABSENT:
            evidence_owed.append(
                "a %s threshold for %s" % (graded["mechanism"], part_reference)
            )
        elif graded["grade"] == MARGIN_SHORT and not graded["mitigated"]:
            findings.append(
                "%s clears only %.2f against %.2f required in this environment"
                % (graded["mechanism"], graded["let_threshold"], graded["required_let"])
            )
        elif graded["grade"] == MARGIN_SHORT and graded["mitigated"]:
            mitigations.append(
                "hold the %s mitigation on %s as a design constraint"
                % (graded["mitigation"], graded["mechanism"])
            )
    if dose["rate_sensitivity_applied"]:
        mitigations.append(
            "the dose capability was cut for rate sensitivity; a low dose rate "
            "characterisation would recover it"
        )

    if findings:
        disposition = RADIATION_INADEQUATE
    elif evidence_owed:
        disposition = RADIATION_EVIDENCE_INCOMPLETE
    elif mitigations:
        disposition = RADIATION_MITIGATION_REQUIRED
    else:
        disposition = RADIATION_ADEQUATE
    return {
        "part_reference": part_reference,
        "disposition": disposition,
        "acceptable": disposition
        in (RADIATION_ADEQUATE, RADIATION_MITIGATION_REQUIRED),
        "mission_years": dose["mission_years"],
        "total_dose": dose,
        "single_events": graded_events,
        "uncovered_destructive_mechanisms": uncovered_destructive,
        "binding_mechanism": _binding([dose] + graded_events),
        "evidence_owed": evidence_owed,
        "required_mitigations": mitigations,
        "findings": findings,
    }
