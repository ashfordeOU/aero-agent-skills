"""Legacy lot acceptance test list for active commercial parts at the lowest
assurance class.

Anchor: ECSS-Q-ST-60-13C Table 8-15 (legacy lot acceptance test list, active
commercial parts, lowest assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Split the group set the way the table does at this assurance class: a
   small core that has to be run on the delivered lot, and the remainder that
   heritage or supplier evidence may stand in for.
2. Judge a group satisfied by test against its sample and accept number. A
   group that consumes its devices stays accept-on-zero even here; only the
   non-consuming groups carry an accept number above zero.
3. Judge a group satisfied by evidence against the conditions that make the
   evidence transferable: the same part type, the same manufacturing site,
   and an age inside the validity window. Evidence offered for a core group
   is refused outright rather than weighed.
4. Cap how much of the set may be satisfied by evidence. Past the cap the
   acceptance has become a documentation exercise, and the reduced assurance
   class is not a licence to stop testing altogether.
5. Hold the lot when any single group rejects, rather than trading a tested
   group off against a credited one.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "CREDIT_VALIDITY_MONTHS",
    "MAX_CREDITED_FRACTION",
    "GROUP_RULES",
    "CLASS_3_GROUPS",
    "CORE_GROUPS",
    "SATISFACTION_ROUTES",
    "validate_group",
    "credit_admissibility",
    "group_verdict",
    "credit_budget",
    "assess_legacy_class_3_acceptance",
]

# Fractions here are quotients of small integers; an exact equality with a cap
# can land a few ULPs on the wrong side. Absorb the representation error here,
# never by relaxing the cap itself.
LIMIT_TOLERANCE = 1e-9

# Heritage or supplier evidence older than this no longer describes the
# devices being bought.
CREDIT_VALIDITY_MONTHS = 36.0

# The largest share of the group set that evidence may stand in for.
MAX_CREDITED_FRACTION = 0.5

# Each group: whether it belongs to the core that has to be run on the lot,
# and whether it consumes the devices it is run on.
GROUP_RULES = {
    "electrical-end-points": {"core": True, "consuming": False},
    "external-visual": {"core": True, "consuming": False},
    "thermal-shock-and-seal": {"core": False, "consuming": True},
    "mechanical-shock-and-vibration": {"core": False, "consuming": True},
    "solderability": {"core": False, "consuming": True},
    "endurance-life-test": {"core": False, "consuming": True},
}

CLASS_3_GROUPS = (
    "electrical-end-points",
    "external-visual",
    "thermal-shock-and-seal",
    "mechanical-shock-and-vibration",
    "solderability",
    "endurance-life-test",
)

CORE_GROUPS = tuple(
    name for name in CLASS_3_GROUPS if GROUP_RULES[name]["core"]
)

SATISFACTION_ROUTES = ("test", "credit")


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


def validate_group(entry):
    """Return the normalised record for one group of the class 3 list."""
    if not isinstance(entry, dict):
        raise ValueError("group entry must be a mapping")
    if "group" not in entry:
        raise ValueError("group entry missing required key 'group'")
    name = entry["group"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("group name must be a non-empty string")
    name = name.strip()
    if name not in GROUP_RULES:
        raise ValueError(
            "'%s' is not a group of the class 3 lot acceptance list" % name
        )
    route = entry.get("satisfied_by", "test")
    if route not in SATISFACTION_ROUTES:
        raise ValueError(
            "group '%s' declares an unknown satisfaction route %r" % (name, route)
        )
    rules = GROUP_RULES[name]
    record = {
        "group": name,
        "core": rules["core"],
        "consuming": rules["consuming"],
        "satisfied_by": route,
    }
    if route == "test":
        required = _count("required_sample", entry.get("required_sample", 1))
        if required < 1:
            raise ValueError("group '%s' must require at least one device" % name)
        sample = _count("sample_size", entry.get("sample_size", required))
        if sample < 1:
            raise ValueError("group '%s' must sample at least one device" % name)
        accept_number = _count("accept_number", entry.get("accept_number", 0))
        if rules["consuming"] and accept_number > 0:
            raise ValueError(
                "group '%s' consumes its devices and stays accept-on-zero, so "
                "accept number %d is a specification error" % (name, accept_number)
            )
        if accept_number > sample:
            raise ValueError(
                "group '%s' accept number %d exceeds its sample of %d"
                % (name, accept_number, sample)
            )
        failures = _count("failures", entry.get("failures", 0))
        if failures > sample:
            raise ValueError(
                "group '%s' records %d failures on a sample of %d"
                % (name, failures, sample)
            )
        record.update(
            {
                "required_sample": required,
                "sample_size": sample,
                "sample_shortfall": max(0, required - sample),
                "accept_number": accept_number,
                "failures": failures,
            }
        )
    else:
        evidence = entry.get("evidence")
        if not isinstance(evidence, dict):
            raise ValueError(
                "group '%s' is credited but declares no evidence mapping" % name
            )
        record["evidence"] = evidence
    return record


def credit_admissibility(group, evidence):
    """Decide whether heritage evidence may stand in for one group."""
    if not isinstance(group, str) or group.strip() not in GROUP_RULES:
        raise ValueError("'%r' is not a group of the class 3 list" % (group,))
    name = group.strip()
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping")
    for key in ("same_part_type", "same_site", "age_months"):
        if key not in evidence:
            raise ValueError("evidence missing required key '%s'" % key)
    same_part_type = evidence["same_part_type"]
    same_site = evidence["same_site"]
    if not isinstance(same_part_type, bool) or not isinstance(same_site, bool):
        raise ValueError("evidence match flags must be booleans")
    age = _real("age_months", evidence["age_months"])
    if age < 0.0:
        raise ValueError("age_months must be non-negative, got %r" % age)
    within_window = _at_or_below(age, CREDIT_VALIDITY_MONTHS)
    reasons = []
    if GROUP_RULES[name]["core"]:
        reasons.append(
            "group '%s' is run on the delivered lot and cannot be credited" % name
        )
    if not same_part_type:
        reasons.append("evidence is not for the same part type")
    if not same_site:
        reasons.append("evidence is not from the same manufacturing site")
    if not within_window:
        reasons.append(
            "evidence is %.1f month(s) past its %.1f month validity window"
            % (age - CREDIT_VALIDITY_MONTHS, CREDIT_VALIDITY_MONTHS)
        )
    return {
        "group": name,
        "age_months": age,
        "window_months": CREDIT_VALIDITY_MONTHS,
        "within_window": within_window,
        "same_part_type": same_part_type,
        "same_site": same_site,
        "admissible": not reasons,
        "reasons": reasons,
    }


def group_verdict(entry):
    """Judge one group by whichever route it was satisfied through."""
    record = validate_group(entry)
    if record["satisfied_by"] == "test":
        sample_met = record["sample_shortfall"] == 0
        within_accept = record["failures"] <= record["accept_number"]
        record.update(
            {
                "sample_met": sample_met,
                "within_accept_number": within_accept,
                "credit": None,
                "accepted": sample_met and within_accept,
            }
        )
    else:
        credit = credit_admissibility(record["group"], record["evidence"])
        record.update(
            {
                "sample_met": None,
                "within_accept_number": None,
                "credit": credit,
                "accepted": credit["admissible"],
            }
        )
    return record


def credit_budget(records):
    """Compare the share of the set satisfied by evidence with the cap."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty list")
    total = len(records)
    credited = sum(1 for item in records if item["satisfied_by"] == "credit")
    fraction = credited / float(total)
    return {
        "groups": total,
        "credited": credited,
        "tested": total - credited,
        "credited_fraction": fraction,
        "cap_fraction": MAX_CREDITED_FRACTION,
        "accepted": _at_or_below(fraction, MAX_CREDITED_FRACTION),
    }


def assess_legacy_class_3_acceptance(spec):
    """Turn a class 3 acceptance campaign into an accept-or-hold verdict."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "groups" not in spec:
        raise ValueError("spec missing required key 'groups'")
    entries = spec["groups"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec['groups'] must be a non-empty list")
    judged = []
    seen = []
    for entry in entries:
        record = group_verdict(entry)
        if record["group"] in seen:
            raise ValueError(
                "group '%s' appears twice in the campaign" % record["group"]
            )
        seen.append(record["group"])
        judged.append(record)
    missing = tuple(item for item in CLASS_3_GROUPS if item not in seen)
    absent_core = tuple(item for item in CORE_GROUPS if item not in seen)
    budget = credit_budget(judged)
    findings = []
    for record in judged:
        if record["satisfied_by"] == "test":
            if not record["sample_met"]:
                findings.append(
                    "group '%s' ran %d device(s) against a required sample of %d"
                    % (
                        record["group"],
                        record["sample_size"],
                        record["required_sample"],
                    )
                )
            if not record["within_accept_number"]:
                findings.append(
                    "group '%s': %d failure(s) exceed the accept number %d"
                    % (
                        record["group"],
                        record["failures"],
                        record["accept_number"],
                    )
                )
        elif not record["credit"]["admissible"]:
            findings.append(
                "credit refused for group '%s': %s"
                % (record["group"], "; ".join(record["credit"]["reasons"]))
            )
    if absent_core:
        findings.append(
            "campaign did not run the core group(s) %s" % ", ".join(absent_core)
        )
    elif missing:
        findings.append("campaign did not cover %s" % ", ".join(missing))
    if not budget["accepted"]:
        findings.append(
            "evidence stands in for %d of %d groups, past the %.2f cap"
            % (budget["credited"], budget["groups"], budget["cap_fraction"])
        )
    rejecting = [record["group"] for record in judged if not record["accepted"]]
    accepted = (
        not rejecting and not missing and not absent_core and budget["accepted"]
    )
    return {
        "groups": judged,
        "absent_groups": missing,
        "absent_core_groups": absent_core,
        "budget": budget,
        "rejecting_groups": rejecting,
        "credited_groups": [
            record["group"] for record in judged
            if record["satisfied_by"] == "credit"
        ],
        "accepted": accepted,
        "disposition": "accept-class-3-lot" if accepted else "hold-class-3-lot",
        "findings": findings,
    }
