"""Equivalent Level of Safety (ELOS) finding logic for certification items.

Pure stdlib, deterministic. Implements the wave-26 leaf contract for
skills/systems-engineering-safety/certification/equivalent-level-of-safety:
regulation intent lookup, probability safety margin, compensation coverage
and the ELOS verdict for a design that cannot show literal compliance with
an airworthiness regulation paragraph.

Public functions:
- intent_for
- safety_margin
- margin_db
- compensation_coverage
- elos_verdict
- finding_summary

All rule tables live in module constants. Non-physical inputs raise
ValueError. No network, no external processes, no third party imports.
"""

import math

VALID_SEVERITIES = ("catastrophic", "hazardous", "major", "minor", "none")

# Probability targets (per flight hour) keyed by failure condition severity
# for quantitative regulation paragraphs. Summary-only, paraphrased from
# public certification guidance, not verbatim rule text.
PROBABILITY_TARGETS = {
    "catastrophic": 1e-9,
    "hazardous": 1e-7,
    "major": 1e-5,
}

# Regulation intent table. quantitative rows carry probability targets keyed
# by severity; qualitative rows carry an intent severity. intent_text is a
# paraphrase of the safety objective, never verbatim rule text.
INTENT_TABLE = {
    "25.1309": {
        "quantitative": True,
        "intent_severity": None,
        "intent_text": (
            "equipment, systems and installations must not create hazards and "
            "must be designed so failure conditions keep the airplane safe, "
            "with probability decreasing as severity increases"
        ),
    },
    "25.671": {
        "quantitative": False,
        "intent_severity": "hazardous",
        "intent_text": (
            "control system failures must not prevent continued safe flight "
            "and landing"
        ),
    },
    "23.1309": {
        "quantitative": True,
        "intent_severity": None,
        "intent_text": (
            "equipment, systems and installations must not create hazards and "
            "must be designed so failure conditions keep the airplane safe at "
            "normal category probability levels"
        ),
    },
    "25.683": {
        "quantitative": False,
        "intent_severity": "hazardous",
        "intent_text": (
            "operation of the controls must not be adversely affected by "
            "deformation of the structure"
        ),
    },
}

# Expected compensating measure count per (severity, quantitative flag).
# minor and none are always qualitative; major defaults qualitative but a
# quantitative major row keeps the same demand.
EXPECTED_MEASURES = {
    ("catastrophic", True): 3,
    ("catastrophic", False): 2,
    ("hazardous", True): 2,
    ("hazardous", False): 1,
    ("major", True): 2,
    ("major", False): 2,
    ("minor", True): 1,
    ("minor", False): 1,
    ("none", True): 1,
    ("none", False): 1,
}

# Canonical expected measure types per (severity, quantitative flag). Each
# canonical list has the same length as the corresponding EXPECTED_MEASURES
# count, so coverage 1.0 implies every canonical type is covered.
EXPECTED_MEASURE_TYPES = {
    ("catastrophic", True): ("redundancy", "monitoring", "flight-crew-procedure"),
    ("catastrophic", False): ("redundancy", "monitoring"),
    ("hazardous", True): ("redundancy", "monitoring"),
    ("hazardous", False): ("redundancy",),
    ("major", True): ("redundancy", "monitoring"),
    ("major", False): ("redundancy", "monitoring"),
    ("minor", True): ("redundancy",),
    ("minor", False): ("redundancy",),
    ("none", True): ("redundancy",),
    ("none", False): ("redundancy",),
}

# Measure types that protect a primary safety function (loss of the function
# itself). A qualitative finding cannot be recommended while one of these is
# missing from the accepted measures.
PRIMARY_SAFETY_FUNCTIONS = ("redundancy", "monitoring")

# Classification keywords in priority order. First match wins, so a measure
# named redundant-lane-monitoring is a redundancy measure (its safety
# contribution is the redundant lane architecture) while jam-detection-
# monitoring is a monitoring measure.
MEASURE_TYPE_KEYWORDS = (
    ("redundancy", ("redund", "duplicat", "backup", "standby")),
    ("operating-limitation", ("limitation", "limit")),
    ("flight-crew-procedure", ("crew", "procedure", "checklist")),
    ("monitoring", ("monitor", "detection", "detect")),
    ("maintenance-action", ("maintenance",)),
    ("inspection-interval", ("inspection", "interval")),
)

# Human phrasing of each measure type, used in reasons and summaries.
MEASURE_TYPE_DISPLAY = {
    "redundancy": "redundancy",
    "operating-limitation": "operating limitation",
    "flight-crew-procedure": "flight crew procedure",
    "monitoring": "monitoring",
    "maintenance-action": "maintenance action",
    "inspection-interval": "inspection interval",
}

# Rule predicates per measure type. Each predicate takes
# (measure, types_present, paragraph, severity, quantitative) and returns
# whether the measure is accepted as a compensating measure for this item.
# Rules are paraphrased acceptance criteria, summary-only.
def _rule_redundancy(measure, types_present, paragraph, severity, quantitative):
    # Redundancy anchors quantitative items at catastrophic, hazardous and
    # major severity and any qualitative item; a catastrophic quantitative
    # item additionally demands it through the expected measure table.
    if quantitative:
        return severity in ("catastrophic", "hazardous", "major")
    return True


def _rule_monitoring(measure, types_present, paragraph, severity, quantitative):
    # Monitoring is accepted only when a redundancy or an operating
    # limitation is present to act on the detected condition.
    return ("redundancy" in types_present) or ("operating-limitation" in types_present)


def _rule_operating_limitation(measure, types_present, paragraph, severity, quantitative):
    # Operating limitations apply to qualitative items and are accepted only
    # with a flight crew procedure that implements them.
    return (not quantitative) and ("flight-crew-procedure" in types_present)


def _rule_flight_crew_procedure(measure, types_present, paragraph, severity, quantitative):
    # A flight crew procedure is accepted when redundancy or an operating
    # limitation gives the crew something to act on.
    return ("redundancy" in types_present) or ("operating-limitation" in types_present)


def _rule_maintenance_action(measure, types_present, paragraph, severity, quantitative):
    # A maintenance action is accepted only when it restores a degraded
    # function before the next flight, signalled by restore in the name.
    return "restore" in measure


FATIGUE_AGING_PARAGRAPHS = ("25.571", "25.573", "23.571")


def fatigue_aging_item(paragraph):
    # Damage tolerance and fatigue paragraphs, where an inspection interval
    # is an effective compensating measure.
    return paragraph in FATIGUE_AGING_PARAGRAPHS


def _rule_inspection_interval(measure, types_present, paragraph, severity, quantitative):
    # An inspection interval is accepted for fatigue and aging items only.
    return fatigue_aging_item(paragraph)


MEASURE_RULES = {
    "redundancy": _rule_redundancy,
    "operating-limitation": _rule_operating_limitation,
    "flight-crew-procedure": _rule_flight_crew_procedure,
    "monitoring": _rule_monitoring,
    "maintenance-action": _rule_maintenance_action,
    "inspection-interval": _rule_inspection_interval,
}


def _fmt_prob(probability):
    """Format a probability for reasons text, 1e-09 becomes 1e-9."""
    text = "%.1e" % probability
    return text.replace("e-0", "e-")


def _validate_severity(severity):
    if severity not in VALID_SEVERITIES:
        raise ValueError(
            "unknown severity %r, expected one of %s"
            % (severity, ", ".join(VALID_SEVERITIES))
        )


def _expected_count(severity, quantitative):
    key = (severity, quantitative)
    if key not in EXPECTED_MEASURES:
        raise ValueError(
            "no expected measure count for severity %r quantitative %s"
            % (severity, quantitative)
        )
    return EXPECTED_MEASURES[key]


def _expected_types(severity, quantitative):
    key = (severity, quantitative)
    if key not in EXPECTED_MEASURE_TYPES:
        raise ValueError(
            "no expected measure types for severity %r quantitative %s"
            % (severity, quantitative)
        )
    return EXPECTED_MEASURE_TYPES[key]


def measure_type(measure):
    """Classify a measure name to a measure type, or None if unrecognized."""
    if not isinstance(measure, str):
        return None
    lowered = measure.lower()
    for measure_type_name, keywords in MEASURE_TYPE_KEYWORDS:
        for keyword in keywords:
            if keyword in lowered:
                return measure_type_name
    return None


def intent_for(paragraph, severity, intent_severity_override=None,
               intent_description_override=None, quantitative=None):
    """Resolve the regulation intent for a certification item.

    Returns a dict with quantitative, target_prob, intent_severity and
    intent_text. Quantitative paragraphs carry the probability target keyed
    by the supplied severity; qualitative paragraphs carry the intent
    severity. Paragraphs outside INTENT_TABLE are accepted only when an
    intent description override is supplied (qualitative, intent severity
    defaults to major). ValueError on unknown severity, on a quantitative
    paragraph with a severity that has no target, and on an unknown
    paragraph with no overrides.
    """
    _validate_severity(severity)
    if intent_severity_override is not None:
        _validate_severity(intent_severity_override)

    row = INTENT_TABLE.get(paragraph)
    if row is None:
        if intent_description_override is None:
            raise ValueError(
                "no intent data for paragraph %r; supply "
                "intent_description_override" % paragraph
            )
        is_quantitative = False if quantitative is None else quantitative
        if is_quantitative:
            raise ValueError(
                "no probability target for paragraph %r outside the intent "
                "table" % paragraph
            )
        return {
            "quantitative": False,
            "target_prob": None,
            "intent_severity": intent_severity_override or "major",
            "intent_text": intent_description_override,
        }

    is_quantitative = row["quantitative"] if quantitative is None else quantitative
    if is_quantitative:
        if severity not in PROBABILITY_TARGETS:
            raise ValueError(
                "no probability target for severity %r on quantitative "
                "paragraph %r" % (severity, paragraph)
            )
        target = PROBABILITY_TARGETS[severity]
    else:
        target = None
    intent_severity = intent_severity_override
    if intent_severity is None and not is_quantitative:
        intent_severity = row["intent_severity"]
    if intent_severity is None:
        intent_severity = severity
    intent_text = intent_description_override or row["intent_text"]
    return {
        "quantitative": is_quantitative,
        "target_prob": target,
        "intent_severity": intent_severity,
        "intent_text": intent_text,
    }


def safety_margin(target, achieved):
    """Safety margin as the ratio target / achieved probability.

    A margin of 1.0 means the achieved probability equals the target; above
    1.0 the design is better than the target. ValueError when either input
    is non-positive or non-finite.
    """
    if not math.isfinite(target) or not math.isfinite(achieved):
        raise ValueError("target and achieved must be finite numbers")
    if target <= 0.0:
        raise ValueError("target must be positive, got %r" % target)
    if achieved <= 0.0:
        raise ValueError("achieved probability must be positive, got %r" % achieved)
    return target / achieved


def margin_db(target, achieved):
    """Safety margin in decibels, 10 * log10(target / achieved)."""
    margin = safety_margin(target, achieved)
    value = 10.0 * math.log10(margin)
    if not math.isfinite(value):
        raise ValueError("margin in dB is not finite for target %r achieved %r"
                         % (target, achieved))
    return value


def _accepted_measure_types(measures, paragraph, severity, quantitative):
    """Return (accepted types, present types) for the measure list."""
    present = set()
    for measure in measures:
        found = measure_type(measure)
        if found is not None:
            present.add(found)
    accepted = set()
    for measure in measures:
        measure_type_name = measure_type(measure)
        if measure_type_name is None:
            continue
        predicate = MEASURE_RULES[measure_type_name]
        if predicate(measure, present, paragraph, severity, quantitative):
            accepted.add(measure_type_name)
    return accepted, present


def compensation_coverage(measures, paragraph, severity,
                          intent_severity_override=None,
                          intent_description_override=None, quantitative=None):
    """Assess compensating measure coverage for an item.

    Returns (coverage, accepted, gaps) where coverage is 0..1 capped at 1.0,
    accepted lists the measure types accepted by MEASURE_RULES, and gaps
    list the canonical expected measure types that are missing or not
    accepted. Coverage is the accepted type count over the expected count
    for the item severity class.
    """
    _validate_severity(severity)
    resolved = intent_for(paragraph, severity,
                          intent_severity_override=intent_severity_override,
                          intent_description_override=intent_description_override,
                          quantitative=quantitative)
    is_quantitative = resolved["quantitative"]
    accepted, _present = _accepted_measure_types(
        measures, paragraph, severity, is_quantitative
    )
    expected = _expected_count(severity, is_quantitative)
    coverage = round(min(1.0, len(accepted) / float(expected)), 6)
    gaps = [t for t in _expected_types(severity, is_quantitative)
            if t not in accepted]
    accepted_list = [t for t in _expected_types(severity, is_quantitative)
                     if t in accepted]
    extras = sorted(accepted - set(accepted_list))
    accepted_list.extend(extras)
    return coverage, accepted_list, gaps


def _severity_class_phrase(severity, quantitative):
    if quantitative and severity in ("catastrophic", "hazardous", "major"):
        return "%s quantitative item" % severity
    return "%s severity item" % severity


def _margin_reason(margin, target):
    return (
        "safety margin %s against the %s per flight hour target"
        % (repr(round(margin, 6)), _fmt_prob(target))
    )


def _coverage_reason(coverage, severity, quantitative, gaps):
    expected = _expected_count(severity, quantitative)
    reason = (
        "compensating measure coverage %s below the 1.0 acceptance line, "
        "expected %d measures for a %s"
        % (repr(round(coverage, 3)), expected,
           _severity_class_phrase(severity, quantitative))
    )
    if gaps:
        reason += "; missing compensating measure: %s" % ", ".join(
            MEASURE_TYPE_DISPLAY[g] for g in gaps
        )
    return reason


def _primary_safety_gap(gaps):
    return [g for g in gaps if g in PRIMARY_SAFETY_FUNCTIONS]


def elos_verdict(paragraph, severity, achieved_probability, measures,
                 intent_severity_override=None, intent_description_override=None,
                 quantitative=None):
    """Return the ELOS verdict dict for one certification item.

    Verdict is PASS (finding recommended), CONDITIONAL or FAIL (finding not
    supportable). Quantitative items need a margin of at least 1.0 (achieved
    probability at or better than the target) and coverage of at least 1.0;
    a margin below 1.0 always fails. Qualitative items need coverage of at
    least 1.0 with no primary safety function gap. Coverage between 0.5 and
    1.0 is CONDITIONAL, below 0.5 is FAIL.
    """
    resolved = intent_for(paragraph, severity,
                          intent_severity_override=intent_severity_override,
                          intent_description_override=intent_description_override,
                          quantitative=quantitative)
    is_quantitative = resolved["quantitative"]
    target = resolved["target_prob"]

    margin = None
    margin_value = None
    if is_quantitative:
        if achieved_probability is None:
            raise ValueError(
                "achieved_probability is required for quantitative paragraph %r"
                % paragraph
            )
        if not math.isfinite(achieved_probability):
            raise ValueError("achieved_probability must be finite")
        if achieved_probability <= 0.0:
            raise ValueError(
                "achieved_probability must be positive for a quantitative "
                "item, got %r" % achieved_probability
            )
        margin_value = safety_margin(target, achieved_probability)
        margin = margin_value
        margin_value_db = margin_db(target, achieved_probability)
    else:
        margin_value_db = None

    coverage, accepted_list, gaps = compensation_coverage(
        measures, paragraph, severity,
        intent_severity_override=intent_severity_override,
        intent_description_override=intent_description_override,
        quantitative=quantitative
    )

    reasons = []
    if is_quantitative:
        if margin_value < 1.0:
            reasons.append(
                _margin_reason(margin_value, target) + ", below the 1.0 "
                "acceptance line"
            )
            return {
                "margin": margin, "margin_db": margin_value_db,
                "coverage": coverage, "verdict": "FAIL",
                "reasons": reasons, "accepted": accepted_list, "gaps": gaps,
            }
        if coverage >= 1.0:
            reasons.append(
                "safety margin %s meets the %s per flight hour target"
                % (repr(round(margin_value, 6)), _fmt_prob(target))
            )
            reasons.append(
                "compensating measure coverage 1.0 covers the expected %d "
                "measures for a %s"
                % (_expected_count(severity, True),
                   _severity_class_phrase(severity, True))
            )
            return {
                "margin": margin, "margin_db": margin_value_db,
                "coverage": coverage, "verdict": "PASS",
                "reasons": reasons, "accepted": accepted_list, "gaps": gaps,
            }
        if coverage >= 0.5:
            reasons.append(_coverage_reason(coverage, severity, True, gaps))
            return {
                "margin": margin, "margin_db": margin_value_db,
                "coverage": coverage, "verdict": "CONDITIONAL",
                "reasons": reasons, "accepted": accepted_list, "gaps": gaps,
            }
        reasons.append(_coverage_reason(coverage, severity, True, gaps))
        return {
            "margin": margin, "margin_db": margin_value_db,
            "coverage": coverage, "verdict": "FAIL",
            "reasons": reasons, "accepted": accepted_list, "gaps": gaps,
        }

    # Qualitative branch.
    if coverage >= 1.0 and not _primary_safety_gap(gaps):
        reasons.append(
            "compensating measure coverage 1.0 covers the expected %d "
            "measures for a %s"
            % (_expected_count(severity, False),
               _severity_class_phrase(severity, False))
        )
        reasons.append("no primary safety function gap in the accepted measures")
        return {
            "margin": None, "margin_db": None, "coverage": coverage,
            "verdict": "PASS", "reasons": reasons,
            "accepted": accepted_list, "gaps": gaps,
        }
    primary_gap = _primary_safety_gap(gaps)
    if primary_gap and coverage >= 1.0:
        reasons.append(
            "primary safety function gap in the accepted measures: %s"
            % ", ".join(MEASURE_TYPE_DISPLAY[g] for g in primary_gap)
        )
        return {
            "margin": None, "margin_db": None, "coverage": coverage,
            "verdict": "CONDITIONAL", "reasons": reasons,
            "accepted": accepted_list, "gaps": gaps,
        }
    if coverage >= 0.5:
        reasons.append(_coverage_reason(coverage, severity, False, gaps))
        return {
            "margin": None, "margin_db": None, "coverage": coverage,
            "verdict": "CONDITIONAL", "reasons": reasons,
            "accepted": accepted_list, "gaps": gaps,
        }
    reasons.append(_coverage_reason(coverage, severity, False, gaps))
    return {
        "margin": None, "margin_db": None, "coverage": coverage,
        "verdict": "FAIL", "reasons": reasons,
        "accepted": accepted_list, "gaps": gaps,
    }


VERDICT_TEXT = {
    "PASS": "finding recommended",
    "CONDITIONAL": "finding conditional",
    "FAIL": "finding not supportable",
}


def finding_summary(item, verdict):
    """One paragraph ELOS summary for the item and verdict dict."""
    paragraph = item["paragraph"]
    severity = item["severity"]
    coverage = verdict["coverage"]
    parts = [
        "ELOS finding for paragraph %s at %s severity:"
        % (paragraph, severity)
    ]
    if verdict["margin"] is not None:
        parts.append(
            "safety margin %s (%s dB) against the probability target"
            % (repr(round(verdict["margin"], 6)),
               repr(round(verdict["margin_db"], 2)))
        )
    else:
        parts.append("qualitative rule, no numeric margin")
    parts.append("compensating measure coverage %s" % repr(round(coverage, 3)))
    parts.append(
        "verdict %s (%s)" % (verdict["verdict"], VERDICT_TEXT[verdict["verdict"]])
    )
    return ". ".join(parts) + "."


if __name__ == "__main__":
    # Smoke check mirrors the worked example anchors from the leaf spec.
    check = elos_verdict("25.1309", "catastrophic", 2e-10,
                         ["redundant-lane-monitoring", "flight-crew-procedure"])
    print(check["margin"], check["coverage"], check["verdict"], check["gaps"])
    check_pass = elos_verdict("25.1309", "catastrophic", 2e-10,
                              ["redundant-lane-monitoring",
                               "flight-crew-procedure", "failure-monitoring"])
    print(check_pass["margin"], check_pass["coverage"], check_pass["verdict"])
    check_fail = elos_verdict("25.1309", "catastrophic", 3e-9,
                              ["redundant-lane-monitoring",
                               "flight-crew-procedure", "failure-monitoring"])
    print(check_fail["margin"], check_fail["verdict"])
