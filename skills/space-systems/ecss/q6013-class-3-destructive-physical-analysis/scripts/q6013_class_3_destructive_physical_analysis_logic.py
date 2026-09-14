"""Destructive physical sampling of a lowest-assurance commercial EEE lot.

Anchor: ECSS-Q-ST-60-13C clause 6.3.9 (destructive physical sampling of
commercial part lots at the lowest assurance category, where the sampling is
owed on risk rather than on every lot). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Run the trigger register over the lot: source franchise, manufacturer
   history, technology watch list, application criticality and the age of the
   date code. Any one firing puts the lot into the teardown.
2. When nothing fires, the lot is still only released on a recorded
   justification. A waiver with no written reason leaves the question open
   rather than answering it.
3. Size the teardown sample from the lot with an exact integer percentage
   plan bounded by a declared floor and cap, and raise a finding when the
   sample would consume the lot.
4. Credit a prior destructive analysis only when it describes the same
   manufacturer, technology and date code, is young enough to describe the
   same build and found no major defect. A credited lot drops to a
   confirmation count; it never drops to nothing.
5. Categorize the construction findings against a named register, refusing a
   code the register does not hold, and dispose the lot on the major-defect
   rule.
"""

import math

__all__ = [
    "TRIGGER_REGISTER",
    "DEFECT_REGISTER",
    "DEFAULT_SAMPLE_PERCENT",
    "DEFAULT_SAMPLE_FLOOR",
    "DEFAULT_SAMPLE_CAP",
    "DEFAULT_CONFIRMATION_SAMPLE",
    "DEFAULT_CREDIT_AGE_LIMIT_MONTHS",
    "SAMPLING_TOLERANCE",
    "fired_triggers",
    "waiver_status",
    "teardown_sample_size",
    "prior_analysis_credit",
    "categorize_findings",
    "assess_class3_destructive_analysis",
]

# The conditions that put a commercial lot into a teardown at this category.
# None of them is about the part working; all of them are about how little is
# known regarding how it was built.
TRIGGER_REGISTER = (
    "unfranchised-source",
    "manufacturer-without-prior-lot-history",
    "technology-on-watch-register",
    "single-point-failure-application",
    "date-code-beyond-shelf-limit",
)

# Observations a teardown can return, grouped by how much each one says about
# the rest of the lot. A code outside this register is refused rather than
# being treated as cosmetic.
DEFECT_REGISTER = {
    "die-attach-voiding": "major",
    "wire-bond-lift": "major",
    "die-crack": "major",
    "conductive-foreign-material": "major",
    "package-seal-anomaly": "major",
    "marking-smear": "minor",
    "plating-discoloration": "minor",
    "lead-frame-burr": "minor",
    "residual-mould-flash": "minor",
}

DEFAULT_SAMPLE_PERCENT = 1
DEFAULT_SAMPLE_FLOOR = 2
DEFAULT_SAMPLE_CAP = 10
DEFAULT_CONFIRMATION_SAMPLE = 1
DEFAULT_CREDIT_AGE_LIMIT_MONTHS = 18.0

# Age comparisons land on the credit limit exactly in the normal case; absorb
# representation error here rather than by moving the limit.
SAMPLING_TOLERANCE = 1e-9


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _real(label, value):
    """Return value as a finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _text(label, value):
    """Return a stripped, lower-cased, non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def fired_triggers(conditions, register=TRIGGER_REGISTER):
    """Return the register entries that fired for this lot, in register order.

    conditions is a mapping of trigger name to True or False. A name outside
    the register is refused; an omitted name has not fired.
    """
    if not isinstance(conditions, dict):
        raise ValueError("conditions must be a mapping of trigger name to True or False")
    names = [_text("trigger", item) for item in register]
    seen = {}
    for key, value in conditions.items():
        name = _text("trigger name", key)
        seen[name] = _flag("conditions['%s']" % name, value)
    unknown = sorted(set(seen) - set(names))
    if unknown:
        raise ValueError("unknown teardown trigger: %s" % ", ".join(unknown))
    return [name for name in names if seen.get(name, False)]


def waiver_status(triggers, justification=None):
    """Return whether a lot with no trigger firing is properly waived.

    A lot that fired a trigger is not waivable here at all. A lot that fired
    nothing still needs a written reason on the record; an empty reason leaves
    the question open.
    """
    if not isinstance(triggers, (list, tuple)):
        raise ValueError("triggers must be a sequence of fired trigger names")
    fired = [_text("fired trigger", item) for item in triggers]
    if fired:
        return {
            "sampling_required": True,
            "fired": fired,
            "justification_recorded": False,
            "justification": None,
        }
    recorded = isinstance(justification, str) and bool(justification.strip())
    return {
        "sampling_required": False,
        "fired": [],
        "justification_recorded": recorded,
        "justification": justification.strip() if recorded else None,
    }


def teardown_sample_size(
    lot_size,
    percent=DEFAULT_SAMPLE_PERCENT,
    floor=DEFAULT_SAMPLE_FLOOR,
    cap=DEFAULT_SAMPLE_CAP,
):
    """Return the teardown sample size for a lot.

    Exact ceiling of percent/100 of the lot, computed in integer arithmetic,
    raised to the declared floor, limited by the declared cap and never larger
    than the lot itself. The same lot gives the same sample on every platform.
    """
    lot = _count("lot_size", lot_size)
    pct = _count("percent", percent)
    low = _count("floor", floor)
    high = _count("cap", cap)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if pct < 1 or pct > 100:
        raise ValueError("percent must lie in 1..100, got %d" % pct)
    if low < 1:
        raise ValueError("floor must be at least 1, got %d" % low)
    if high < low:
        raise ValueError("cap %d is below floor %d" % (high, low))
    proportional = -((-lot * pct) // 100)
    size = max(proportional, low)
    size = min(size, high)
    return min(size, lot)


def prior_analysis_credit(record, age_limit_months=DEFAULT_CREDIT_AGE_LIMIT_MONTHS):
    """Return whether a prior destructive analysis may be credited against this lot.

    record keys: manufacturer_matches, technology_matches, date_code_matches,
    months_since, major_defects_found. Every condition has to hold; a report
    sitting exactly on the age limit is still young enough.
    """
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    for key in (
        "manufacturer_matches",
        "technology_matches",
        "date_code_matches",
        "months_since",
        "major_defects_found",
    ):
        if key not in record:
            raise ValueError("record missing required key '%s'" % key)
    limit = _real("age_limit_months", age_limit_months)
    if limit <= 0.0:
        raise ValueError("age_limit_months must be positive, got %g" % limit)
    age = _real("months_since", record["months_since"])
    if age < 0.0:
        raise ValueError("months_since must be non-negative, got %g" % age)
    manufacturer = _flag("manufacturer_matches", record["manufacturer_matches"])
    technology = _flag("technology_matches", record["technology_matches"])
    date_code = _flag("date_code_matches", record["date_code_matches"])
    majors = _count("major_defects_found", record["major_defects_found"])
    young_enough = age < limit or math.isclose(
        age, limit, rel_tol=0.0, abs_tol=SAMPLING_TOLERANCE
    )
    reasons = []
    if not manufacturer:
        reasons.append("prior analysis is for a different manufacturer")
    if not technology:
        reasons.append("prior analysis is for a different technology")
    if not date_code:
        reasons.append("prior analysis is for a different date code")
    if not young_enough:
        reasons.append(
            "prior analysis is %.2f month(s) old against a limit of %.2f" % (age, limit)
        )
    if majors:
        reasons.append("prior analysis found %d major construction defect(s)" % majors)
    return {
        "months_since": age,
        "age_limit_months": limit,
        "months_remaining": limit - age,
        "credited": not reasons,
        "reasons": reasons,
    }


def categorize_findings(codes, register=DEFECT_REGISTER):
    """Return the observed teardown findings grouped as major and minor.

    A code the register does not hold is refused rather than defaulted to
    minor: an unregistered observation is unexamined, not cosmetic.
    """
    if not isinstance(register, dict) or not register:
        raise ValueError("register must be a non-empty mapping of code to severity")
    table = {}
    for key, value in register.items():
        name = _text("register code", key)
        severity = _text("register severity", value)
        if severity not in ("major", "minor"):
            raise ValueError("register severity for '%s' must be major or minor" % name)
        table[name] = severity
    if not isinstance(codes, (list, tuple)):
        raise ValueError("codes must be a sequence of observation codes")
    major = []
    minor = []
    for item in codes:
        name = _text("observation code", item)
        if name not in table:
            raise ValueError(
                "unregistered observation code %r; registered codes are %s"
                % (item, ", ".join(sorted(table)))
            )
        if table[name] == "major":
            major.append(name)
        else:
            minor.append(name)
    return {"major": major, "minor": minor, "total": len(major) + len(minor)}


def assess_class3_destructive_analysis(spec):
    """Run the full clause 6.3.9 destructive sampling assessment of one lot.

    spec keys: lot_size, trigger_conditions, observations, and optional
    waiver_justification, prior_analysis, sample_percent, sample_floor,
    sample_cap, confirmation_sample and credit_age_limit_months.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "trigger_conditions", "observations"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    lot = _count("lot_size", spec["lot_size"])
    if lot < 1:
        raise ValueError("lot_size must be at least 1 to assess a lot")
    triggers = fired_triggers(spec["trigger_conditions"])
    waiver = waiver_status(triggers, spec.get("waiver_justification"))
    findings = []
    if not waiver["sampling_required"]:
        if waiver["justification_recorded"]:
            return {
                "lot_size": lot,
                "fired_triggers": [],
                "waiver": waiver,
                "credit": None,
                "sample_size": 0,
                "categorized": None,
                "accepted": True,
                "verdict": "destructive-sampling-not-required",
                "findings": [],
            }
        findings.append("no teardown trigger fired but the waiver carries no recorded reason")
        return {
            "lot_size": lot,
            "fired_triggers": [],
            "waiver": waiver,
            "credit": None,
            "sample_size": 0,
            "categorized": None,
            "accepted": False,
            "verdict": "waiver-justification-missing",
            "findings": findings,
        }
    confirmation = _count(
        "confirmation_sample", spec.get("confirmation_sample", DEFAULT_CONFIRMATION_SAMPLE)
    )
    if confirmation < 1:
        raise ValueError("confirmation_sample must be at least 1; credit thins sampling, not removes it")
    full_sample = teardown_sample_size(
        lot,
        spec.get("sample_percent", DEFAULT_SAMPLE_PERCENT),
        spec.get("sample_floor", DEFAULT_SAMPLE_FLOOR),
        spec.get("sample_cap", DEFAULT_SAMPLE_CAP),
    )
    if confirmation > full_sample:
        raise ValueError(
            "confirmation_sample %d exceeds the full sample %d; a credited lot would be sampled harder"
            % (confirmation, full_sample)
        )
    credit = None
    sample = full_sample
    if spec.get("prior_analysis") is not None:
        credit = prior_analysis_credit(
            spec["prior_analysis"],
            spec.get("credit_age_limit_months", DEFAULT_CREDIT_AGE_LIMIT_MONTHS),
        )
        if credit["credited"]:
            sample = min(confirmation, lot)
    categorized = categorize_findings(spec["observations"])
    if categorized["total"] > sample:
        raise ValueError(
            "%d observation(s) reported from a sample of %d"
            % (categorized["total"], sample)
        )
    if sample >= lot:
        findings.append(
            "the teardown sample of %d consumes the lot of %d; buy a larger lot" % (sample, lot)
        )
        verdict = "sample-not-feasible"
        return {
            "lot_size": lot,
            "fired_triggers": triggers,
            "waiver": waiver,
            "credit": credit,
            "sample_size": sample,
            "categorized": categorized,
            "accepted": False,
            "verdict": verdict,
            "findings": findings,
        }
    for code in categorized["major"]:
        findings.append("major construction defect observed: %s" % code)
    if categorized["major"]:
        verdict = "construction-rejected"
    elif credit is not None and credit["credited"]:
        verdict = "prior-analysis-credited"
    else:
        verdict = "sampling-meets-class-three-scope"
    return {
        "lot_size": lot,
        "fired_triggers": triggers,
        "waiver": waiver,
        "credit": credit,
        "sample_size": sample,
        "categorized": categorized,
        "accepted": not categorized["major"],
        "verdict": verdict,
        "findings": findings,
    }
