"""Legacy lot acceptance test list for active commercial parts at the
intermediate assurance class.

Anchor: ECSS-Q-ST-60-13C Table 8-14 (legacy lot acceptance test list, active
commercial parts, intermediate assurance class). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Size each acceptance group from the lot itself. The sample is read from a
   banded plan keyed on the lot size, so a small lot is not quietly accepted
   on a sample sized for a large one, and a lot too small to yield the plan
   is reported rather than rounded down.
2. Judge every group accept-on-zero. Lot acceptance consumes the devices it
   is run on, so there is no rate to tolerate and an accept number above zero
   is a specification error.
3. Draw the sample from the lot being accepted. Devices from another build or
   date code test that build, so the sample provenance is checked against the
   lot before the result is allowed to stand for it.
4. Account for the devices the campaign consumes. Acceptance removes its
   samples permanently, so the population left after the campaign is compared
   with the quantity the lot has to deliver.
5. Apply the resubmission rule. At this assurance class a failed lot may come
   back once, and only once, and only when the failure mechanism has been
   identified and removed by a re-screen first.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MAX_RESUBMISSIONS",
    "LOT_SIZE_BANDS",
    "LARGE_LOT_SAMPLE",
    "ACCEPTANCE_GROUPS",
    "sample_size_for_lot",
    "validate_group",
    "group_verdict",
    "sample_provenance",
    "consumption_balance",
    "resubmission_decision",
    "assess_legacy_class_2_acceptance",
]

# Ratios here are quotients of small integers; an exact equality with a limit
# can land a few ULPs on the wrong side. Absorb the representation error here,
# never by relaxing the engineering limit itself.
LIMIT_TOLERANCE = 1e-9

# A failed lot may be resubmitted this many times at the intermediate
# assurance class, and only after the mechanism is found and screened out.
MAX_RESUBMISSIONS = 1

# Banded sampling plan: (largest lot size in the band, devices per group).
LOT_SIZE_BANDS = (
    (25, 3),
    (50, 5),
    (100, 8),
    (300, 13),
    (500, 20),
    (1200, 32),
)

# Devices per group for a lot larger than the last band.
LARGE_LOT_SAMPLE = 50

# The acceptance groups the table asks for at this assurance class.
ACCEPTANCE_GROUPS = (
    "physical-dimensions",
    "thermal-shock-and-seal",
    "mechanical-shock-and-vibration",
    "endurance-life-test",
    "solderability",
)


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _at_or_below(value, limit):
    """Return True when value is at or below limit within the tolerance."""
    return value < limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def sample_size_for_lot(lot_size):
    """Read the per-group sample for a lot size out of the banded plan."""
    size = _count("lot_size", lot_size)
    if size < 1:
        raise ValueError("lot_size must be at least 1, got %d" % size)
    sample = LARGE_LOT_SAMPLE
    band_upper = None
    for upper, devices in LOT_SIZE_BANDS:
        if size <= upper:
            sample = devices
            band_upper = upper
            break
    return {
        "lot_size": size,
        "sample_size": sample,
        "band_upper": band_upper,
        "drawable": size >= sample,
    }


def validate_group(group, lot_size):
    """Return the normalised record for one acceptance group.

    Every group consumes the devices it is run on, so an accept number above
    zero is refused rather than honoured, and a sample below the banded plan
    is carried as a shortfall rather than silently accepted.
    """
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping")
    if "group" not in group:
        raise ValueError("group missing required key 'group'")
    name = group["group"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("group name must be a non-empty string")
    name = name.strip()
    if name not in ACCEPTANCE_GROUPS:
        raise ValueError(
            "'%s' is not a group of the class 2 lot acceptance list" % name
        )
    plan = sample_size_for_lot(lot_size)
    sample = _count("sample_size", group.get("sample_size", plan["sample_size"]))
    if sample < 1:
        raise ValueError("group '%s' must sample at least one device" % name)
    if sample > plan["lot_size"]:
        raise ValueError(
            "group '%s' samples %d devices from a lot of %d"
            % (name, sample, plan["lot_size"])
        )
    accept_number = _count("accept_number", group.get("accept_number", 0))
    if accept_number > 0:
        raise ValueError(
            "group '%s' consumes its devices and is judged accept-on-zero, so "
            "accept number %d is a specification error" % (name, accept_number)
        )
    failures = _count("failures", group.get("failures", 0))
    if failures > sample:
        raise ValueError(
            "group '%s' records %d failures on a sample of %d"
            % (name, failures, sample)
        )
    return {
        "group": name,
        "lot_size": plan["lot_size"],
        "sample_size": sample,
        "planned_sample": plan["sample_size"],
        "sample_shortfall": max(0, plan["sample_size"] - sample),
        "accept_number": 0,
        "failures": failures,
        "consumed": sample,
    }


def group_verdict(group, lot_size):
    """Judge one acceptance group against its plan and accept-on-zero rule."""
    record = validate_group(group, lot_size)
    sample_met = record["sample_shortfall"] == 0
    within_accept = record["failures"] == 0
    record.update(
        {
            "sample_met": sample_met,
            "within_accept_number": within_accept,
            "accepted": sample_met and within_accept,
        }
    )
    return record


def sample_provenance(sample_date_codes, lot_date_code):
    """Confirm every device sampled came from the lot being accepted."""
    if not isinstance(lot_date_code, str) or not lot_date_code.strip():
        raise ValueError("lot_date_code must be a non-empty string")
    lot_code = lot_date_code.strip()
    if not isinstance(sample_date_codes, (list, tuple)):
        raise ValueError("sample date codes must be given as a list")
    if not sample_date_codes:
        raise ValueError("no sample date codes were declared")
    foreign = []
    for item in sample_date_codes:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("date code must be a non-empty string, got %r" % item)
        code = item.strip()
        if code != lot_code and code not in foreign:
            foreign.append(code)
    return {
        "lot_date_code": lot_code,
        "foreign_date_codes": tuple(foreign),
        "accepted": not foreign,
    }


def consumption_balance(screened_population, consumed, required_quantity):
    """Compare what the campaign leaves with what the lot has to deliver."""
    population = _count("screened_population", screened_population)
    if population < 1:
        raise ValueError("screened_population must be at least 1")
    used = _count("consumed", consumed)
    if used > population:
        raise ValueError(
            "acceptance consumed %d devices from a screened population of %d"
            % (used, population)
        )
    needed = _count("required_quantity", required_quantity)
    if needed < 1:
        raise ValueError("required_quantity must be at least 1")
    remaining = population - used
    return {
        "screened_population": population,
        "consumed": used,
        "remaining": remaining,
        "required_quantity": needed,
        "shortfall": max(0, needed - remaining),
        "accepted": remaining >= needed,
    }


def resubmission_decision(attempt, mechanism_identified=False, rescreened=False):
    """Decide whether a further acceptance attempt is admissible."""
    number = _count("attempt", attempt)
    if number < 1:
        raise ValueError("attempt must be at least 1, got %d" % number)
    if not isinstance(mechanism_identified, bool):
        raise ValueError("mechanism_identified must be a boolean")
    if not isinstance(rescreened, bool):
        raise ValueError("rescreened must be a boolean")
    resubmissions = number - 1
    reasons = []
    if resubmissions > MAX_RESUBMISSIONS:
        reasons.append(
            "attempt %d is resubmission %d; %d is the limit at this assurance "
            "class" % (number, resubmissions, MAX_RESUBMISSIONS)
        )
    if resubmissions > 0:
        if not mechanism_identified:
            reasons.append(
                "a resubmission needs the failure mechanism identified first"
            )
        if not rescreened:
            reasons.append(
                "a resubmission needs the mechanism screened out of the lot first"
            )
    return {
        "attempt": number,
        "resubmissions": resubmissions,
        "mechanism_identified": mechanism_identified,
        "rescreened": rescreened,
        "admissible": not reasons,
        "reasons": reasons,
    }


def assess_legacy_class_2_acceptance(spec):
    """Turn an executed legacy acceptance campaign into an accept-or-hold verdict."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "groups"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    entries = spec["groups"]
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("spec['groups'] must be a non-empty list")
    plan = sample_size_for_lot(spec["lot_size"])
    judged = []
    seen = []
    for entry in entries:
        record = group_verdict(entry, spec["lot_size"])
        if record["group"] in seen:
            raise ValueError(
                "group '%s' appears twice in the campaign" % record["group"]
            )
        seen.append(record["group"])
        judged.append(record)
    missing = tuple(item for item in ACCEPTANCE_GROUPS if item not in seen)
    findings = []
    if not plan["drawable"]:
        findings.append(
            "a lot of %d cannot yield the %d device sample the plan asks for"
            % (plan["lot_size"], plan["sample_size"])
        )
    for record in judged:
        if not record["sample_met"]:
            findings.append(
                "group '%s' ran %d device(s) against a planned sample of %d"
                % (record["group"], record["sample_size"], record["planned_sample"])
            )
        if not record["within_accept_number"]:
            findings.append(
                "group '%s' failed %d device(s) on an accept-on-zero group"
                % (record["group"], record["failures"])
            )
    if missing:
        findings.append("campaign did not run %s" % ", ".join(missing))
    provenance = None
    if "sample_date_codes" in spec:
        provenance = sample_provenance(
            spec["sample_date_codes"], spec.get("lot_date_code", "")
        )
        if not provenance["accepted"]:
            findings.append(
                "sample carries device(s) from %s, which is not the lot being "
                "accepted" % ", ".join(provenance["foreign_date_codes"])
            )
    consumed = sum(record["consumed"] for record in judged)
    balance = None
    if "screened_population" in spec and "required_quantity" in spec:
        balance = consumption_balance(
            spec["screened_population"], consumed, spec["required_quantity"]
        )
        if not balance["accepted"]:
            findings.append(
                "acceptance leaves %d device(s), %d short of the %d to be "
                "delivered"
                % (
                    balance["remaining"],
                    balance["shortfall"],
                    balance["required_quantity"],
                )
            )
    resubmission = resubmission_decision(
        spec.get("attempt", 1),
        bool(spec.get("mechanism_identified", False)),
        bool(spec.get("rescreened", False)),
    )
    if not resubmission["admissible"]:
        findings.extend(resubmission["reasons"])
    rejecting = [record["group"] for record in judged if not record["accepted"]]
    accepted = (
        not rejecting
        and not missing
        and plan["drawable"]
        and (provenance is None or provenance["accepted"])
        and (balance is None or balance["accepted"])
        and resubmission["admissible"]
    )
    return {
        "plan": plan,
        "groups": judged,
        "absent_groups": missing,
        "provenance": provenance,
        "consumed": consumed,
        "balance": balance,
        "resubmission": resubmission,
        "rejecting_groups": rejecting,
        "accepted": accepted,
        "disposition": "accept-lot" if accepted else "hold-lot",
        "findings": findings,
    }
