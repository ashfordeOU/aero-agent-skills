"""Legacy evaluation test list for active parts at the intermediate assurance
class.

Anchor: ECSS-Q-ST-60-13C Table 8-12 (legacy evaluation test list, active
parts, intermediate assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every subgroup of the declared evaluation: a subgroup names a
   grouping from the table, the devices it was run on, the sample the table
   asks for, an accept number, and whether the grouping consumes the devices
   it is run on. A consuming subgroup is judged accept-on-zero.
2. Require the full grouping set. An evaluation that skipped a grouping has
   not evaluated the part type, so the absent groupings are named rather than
   reported as a bare shortfall.
3. Draw the devices from more than one production lot. An evaluation taken
   from a single date code describes that build and not the part type, so the
   distinct source lots are counted and reported.
4. Age the evaluation. A record past its currency window, or one completed
   before a declared process or fab change, is not transferable to a new
   procurement however clean its subgroups were.
5. Hold the part type when any single subgroup rejects, rather than averaging
   the subgroups into one rate that a clean grouping can carry.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MARGINAL_FRACTION",
    "MIN_SOURCE_LOTS",
    "CURRENCY_WINDOW_MONTHS",
    "EVALUATION_SUBGROUPS",
    "CONSUMING_SUBGROUPS",
    "validate_subgroup",
    "subgroup_verdict",
    "source_lot_diversity",
    "evaluation_currency",
    "absent_subgroups",
    "assess_legacy_class_2_evaluation",
]

# Allowance ratios are quotients of small integers; an exact equality with a
# fraction can land a few ULPs on the wrong side. Absorb the representation
# error here, never by relaxing the engineering limit itself.
LIMIT_TOLERANCE = 1e-9

# An accepted subgroup that has used up this share of its accept number is
# reported as marginal: the part type passes, but the margin is gone.
MARGINAL_FRACTION = 0.8

# An evaluation drawn from fewer than this many production lots describes one
# build rather than the part type.
MIN_SOURCE_LOTS = 2

# Age past which a legacy evaluation record stops standing on its own.
CURRENCY_WINDOW_MONTHS = 60.0

# The grouping set the table asks for at the intermediate assurance class.
EVALUATION_SUBGROUPS = (
    "construction-analysis",
    "electrical-characterization",
    "environmental-mechanical",
    "endurance",
)

# Groupings that consume the devices they are run on.
CONSUMING_SUBGROUPS = (
    "construction-analysis",
    "environmental-mechanical",
    "endurance",
)


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _at_or_below(value, limit):
    """Return True when value is at or below limit within the tolerance."""
    return value < limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def _at_or_above(value, limit):
    """Return True when value is at or above limit within the tolerance."""
    return value > limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def validate_subgroup(entry):
    """Return the normalised record for one grouping of the evaluation.

    A grouping that consumes its devices is judged accept-on-zero, so an
    accept number above zero on such a grouping is refused rather than
    honoured: there is no rate to tolerate on four devices taken apart.
    """
    if not isinstance(entry, dict):
        raise ValueError("subgroup entry must be a mapping")
    for key in ("subgroup", "sample_size", "required_sample"):
        if key not in entry:
            raise ValueError("subgroup entry missing required key '%s'" % key)
    name = entry["subgroup"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("subgroup name must be a non-empty string")
    name = name.strip()
    if name not in EVALUATION_SUBGROUPS:
        raise ValueError(
            "'%s' is not a grouping of the class 2 evaluation list" % name
        )
    required = _count("required_sample", entry["required_sample"])
    if required < 1:
        raise ValueError("subgroup '%s' must require at least one device" % name)
    sample = _count("sample_size", entry["sample_size"])
    if sample < 1:
        raise ValueError("subgroup '%s' must sample at least one device" % name)
    accept_number = _count("accept_number", entry.get("accept_number", 0))
    if accept_number > sample:
        raise ValueError(
            "subgroup '%s' accept number %d exceeds its sample of %d"
            % (name, accept_number, sample)
        )
    consuming = bool(entry.get("consuming", name in CONSUMING_SUBGROUPS))
    if consuming and accept_number > 0:
        raise ValueError(
            "subgroup '%s' consumes its devices and is judged accept-on-zero, "
            "so accept number %d is a specification error"
            % (name, accept_number)
        )
    failures = _count("failures", entry.get("failures", 0))
    if failures > sample:
        raise ValueError(
            "subgroup '%s' records %d failures on a sample of %d"
            % (name, failures, sample)
        )
    return {
        "subgroup": name,
        "sample_size": sample,
        "required_sample": required,
        "accept_number": accept_number,
        "failures": failures,
        "consuming": consuming,
        "sample_shortfall": max(0, required - sample),
    }


def subgroup_verdict(entry):
    """Judge one grouping against its table sample and accept number."""
    record = validate_subgroup(entry)
    shortfall = record["sample_shortfall"]
    within_accept = record["failures"] <= record["accept_number"]
    accepted = shortfall == 0 and within_accept
    if record["accept_number"] > 0:
        allowance_used = record["failures"] / float(record["accept_number"])
    else:
        allowance_used = 0.0 if record["failures"] == 0 else 1.0
    marginal = (
        accepted
        and record["accept_number"] > 0
        and _at_or_above(allowance_used, MARGINAL_FRACTION)
    )
    record.update(
        {
            "sample_met": shortfall == 0,
            "within_accept_number": within_accept,
            "allowance_used": allowance_used,
            "marginal": marginal,
            "accepted": accepted,
        }
    )
    return record


def source_lot_diversity(date_codes):
    """Count the distinct production lots the evaluation devices came from."""
    if not isinstance(date_codes, (list, tuple)):
        raise ValueError("source lots must be given as a list of date codes")
    if not date_codes:
        raise ValueError("evaluation declares no source lots")
    seen = []
    for item in date_codes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("date code must be a non-empty string, got %r" % item)
        code = item.strip()
        if code not in seen:
            seen.append(code)
    accepted = len(seen) >= MIN_SOURCE_LOTS
    return {
        "date_codes": tuple(seen),
        "distinct_lots": len(seen),
        "required_lots": MIN_SOURCE_LOTS,
        "accepted": accepted,
    }


def evaluation_currency(age_months, process_change_since=False):
    """Decide whether a legacy evaluation record still stands on its own.

    A declared process or fab change voids the record whatever its age: the
    devices evaluated are no longer the devices being bought.
    """
    age = _real("age_months", age_months)
    if age < 0.0:
        raise ValueError("age_months must be non-negative, got %r" % age_months)
    if not isinstance(process_change_since, bool):
        raise ValueError("process_change_since must be a boolean")
    within_window = _at_or_below(age, CURRENCY_WINDOW_MONTHS)
    overrun = 0.0 if within_window else age - CURRENCY_WINDOW_MONTHS
    return {
        "age_months": age,
        "window_months": CURRENCY_WINDOW_MONTHS,
        "within_window": within_window,
        "overrun_months": overrun,
        "process_change_since": process_change_since,
        "accepted": within_window and not process_change_since,
    }


def absent_subgroups(names):
    """Return the table groupings the evaluation did not perform."""
    if not isinstance(names, (list, tuple)):
        raise ValueError("names must be a list of grouping names")
    present = {str(name).strip() for name in names}
    return tuple(item for item in EVALUATION_SUBGROUPS if item not in present)


def assess_legacy_class_2_evaluation(spec):
    """Turn an executed legacy evaluation into an evaluated-or-repeat verdict."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("subgroups", "source_lots", "evaluation_age_months"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    entries = spec["subgroups"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec['subgroups'] must be a non-empty list")
    judged = []
    seen = []
    for entry in entries:
        record = subgroup_verdict(entry)
        if record["subgroup"] in seen:
            raise ValueError(
                "grouping '%s' appears twice in the evaluation" % record["subgroup"]
            )
        seen.append(record["subgroup"])
        judged.append(record)
    missing = absent_subgroups(seen)
    diversity = source_lot_diversity(spec["source_lots"])
    currency = evaluation_currency(
        spec["evaluation_age_months"], bool(spec.get("process_change_since", False))
    )
    findings = []
    for record in judged:
        if not record["sample_met"]:
            findings.append(
                "grouping '%s' ran %d device(s) against a required sample of %d"
                % (
                    record["subgroup"],
                    record["sample_size"],
                    record["required_sample"],
                )
            )
        if not record["within_accept_number"]:
            findings.append(
                "grouping '%s': %d failure(s) exceed the accept number %d"
                % (record["subgroup"], record["failures"], record["accept_number"])
            )
        elif record["marginal"]:
            findings.append(
                "grouping '%s' accepted on its last allowance" % record["subgroup"]
            )
    if missing:
        findings.append("evaluation did not perform %s" % ", ".join(missing))
    if not diversity["accepted"]:
        findings.append(
            "devices came from %d production lot(s); %d are required for the "
            "result to describe the part type"
            % (diversity["distinct_lots"], diversity["required_lots"])
        )
    if not currency["within_window"]:
        findings.append(
            "evaluation is %.1f month(s) past its %.1f month currency window"
            % (currency["overrun_months"], currency["window_months"])
        )
    if currency["process_change_since"]:
        findings.append(
            "a process change was declared after the evaluation, so the record "
            "does not describe the devices being bought"
        )
    rejecting = [
        record["subgroup"] for record in judged if not record["accepted"]
    ]
    accepted = (
        not rejecting
        and not missing
        and diversity["accepted"]
        and currency["accepted"]
    )
    return {
        "subgroups": judged,
        "absent_subgroups": missing,
        "source_lots": diversity,
        "currency": currency,
        "rejecting_subgroups": rejecting,
        "marginal_subgroups": [
            record["subgroup"] for record in judged if record["marginal"]
        ],
        "accepted": accepted,
        "disposition": "part-type-evaluated" if accepted else "repeat-evaluation",
        "findings": findings,
    }
