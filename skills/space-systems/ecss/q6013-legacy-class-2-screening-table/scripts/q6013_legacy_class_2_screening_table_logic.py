"""Legacy screening test list for active parts at the intermediate assurance
class.

Anchor: ECSS-Q-ST-60-13C Table 8-13 (legacy screening test list, active
parts, intermediate assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Walk the screening sequence in order. Screening is a chain: the devices
   entering a step are the devices that survived the step before it, so a
   declared population that does not follow from the previous step's rejects
   is an arithmetic error in the record rather than a judgement call.
2. Require full coverage at every step. Screening is applied to the whole
   remaining population; a step that tested a sample of it has not been
   performed, however large the sample was.
3. Hold the declared order. A step run out of sequence does not screen what
   the sequence was built to expose, so the first out-of-order step is named.
4. Take the burn-in percent defective on the devices that entered burn-in,
   not on the devices that came out of it.
5. Compare the cumulative attrition across the whole sequence with its cap,
   and compare the surviving population with the quantity the lot has to
   deliver, so a lot that screens clean but can no longer fill the order is
   reported rather than passed.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MAX_CUMULATIVE_ATTRITION_PERCENT",
    "SCREENING_SEQUENCE",
    "BURN_IN_STEP",
    "validate_step",
    "screening_chain",
    "sequence_order",
    "burn_in_pda",
    "cumulative_attrition",
    "deliverable_check",
    "assess_legacy_class_2_screening",
]

# Percentages are quotients of integers scaled by 100; an exact equality with
# a limit can land a few ULPs on the wrong side. Absorb the representation
# error here, never by relaxing the limit itself.
LIMIT_TOLERANCE = 1e-9

# Attrition across the whole sequence past this share of the starting lot
# says the build, not the screen, is the finding.
MAX_CUMULATIVE_ATTRITION_PERCENT = 10.0

# The screening sequence at the intermediate assurance class, in order.
SCREENING_SEQUENCE = (
    "precap-internal-visual",
    "stabilization-bake",
    "temperature-cycling",
    "constant-acceleration",
    "burn-in",
    "final-electrical",
    "seal-fine-and-gross",
    "external-visual",
)

BURN_IN_STEP = "burn-in"


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


def validate_step(step, entering):
    """Return the normalised record for one step of the screening sequence.

    Screening is a hundred-percent operation, so the devices tested are
    compared with the whole population entering the step; a smaller number is
    recorded as incomplete coverage rather than accepted as a sample.
    """
    if not isinstance(step, dict):
        raise ValueError("step must be a mapping")
    if "step" not in step:
        raise ValueError("step missing required key 'step'")
    name = step["step"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("step name must be a non-empty string")
    name = name.strip()
    if name not in SCREENING_SEQUENCE:
        raise ValueError(
            "'%s' is not a step of the class 2 screening sequence" % name
        )
    population = _count("entering", entering)
    if population < 1:
        raise ValueError(
            "step '%s' was reached with no devices left to screen" % name
        )
    tested = _count("devices_tested", step.get("devices_tested", population))
    if tested > population:
        raise ValueError(
            "step '%s' tested %d devices from a population of %d"
            % (name, tested, population)
        )
    rejects = _count("rejects", step.get("rejects", 0))
    if rejects > tested:
        raise ValueError(
            "step '%s' rejected %d of the %d devices it tested"
            % (name, rejects, tested)
        )
    untested = population - tested
    return {
        "step": name,
        "entering": population,
        "devices_tested": tested,
        "untested": untested,
        "rejects": rejects,
        "surviving": population - rejects,
        "full_coverage": untested == 0,
    }


def sequence_order(names):
    """Return the first step that breaks the declared screening order."""
    if not isinstance(names, (list, tuple)):
        raise ValueError("names must be a list of step names")
    position = -1
    for name in names:
        if not isinstance(name, str) or name.strip() not in SCREENING_SEQUENCE:
            raise ValueError("'%r' is not a screening step" % (name,))
        index = SCREENING_SEQUENCE.index(name.strip())
        if index <= position:
            return {"in_order": False, "first_out_of_order": name.strip()}
        position = index
    return {"in_order": True, "first_out_of_order": None}


def screening_chain(steps, lot_size):
    """Walk the sequence, carrying the surviving population step to step."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty list")
    population = _count("lot_size", lot_size)
    if population < 1:
        raise ValueError("lot_size must be at least 1, got %d" % population)
    records = []
    seen = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("step must be a mapping")
        declared = step.get("entering")
        if declared is not None:
            declared = _count("entering", declared)
            if declared != population:
                raise ValueError(
                    "step '%s' declares %d devices entering but %d survived "
                    "the previous step"
                    % (step.get("step"), declared, population)
                )
        record = validate_step(step, population)
        if record["step"] in seen:
            raise ValueError(
                "step '%s' appears twice in the sequence" % record["step"]
            )
        seen.append(record["step"])
        records.append(record)
        population = record["surviving"]
    return {
        "steps": records,
        "lot_size": records[0]["entering"],
        "surviving": population,
        "order": sequence_order(seen),
        "absent_steps": tuple(
            item for item in SCREENING_SEQUENCE if item not in seen
        ),
    }


def burn_in_pda(entered, failures, allowable_percent):
    """Percent defective across burn-in, taken on the devices that entered."""
    population = _count("entered", entered)
    if population < 1:
        raise ValueError("burn-in must be entered by at least one device")
    rejects = _count("failures", failures)
    if rejects > population:
        raise ValueError(
            "burn-in records %d failures on %d devices" % (rejects, population)
        )
    allowable = _real("allowable_percent", allowable_percent)
    if allowable < 0.0 or allowable > 100.0:
        raise ValueError(
            "allowable_percent must be a percentage, got %r" % allowable_percent
        )
    percent = 100.0 * rejects / population
    return {
        "entered": population,
        "failures": rejects,
        "percent_defective": percent,
        "allowable_percent": allowable,
        "accepted": _at_or_below(percent, allowable),
    }


def cumulative_attrition(lot_size, surviving):
    """Share of the starting lot lost across the whole screening sequence."""
    start = _count("lot_size", lot_size)
    if start < 1:
        raise ValueError("lot_size must be at least 1, got %d" % start)
    left = _count("surviving", surviving)
    if left > start:
        raise ValueError(
            "%d devices survived a lot of %d" % (left, start)
        )
    percent = 100.0 * (start - left) / start
    return {
        "lot_size": start,
        "surviving": left,
        "removed": start - left,
        "attrition_percent": percent,
        "cap_percent": MAX_CUMULATIVE_ATTRITION_PERCENT,
        "accepted": _at_or_below(percent, MAX_CUMULATIVE_ATTRITION_PERCENT),
    }


def deliverable_check(surviving, required_quantity):
    """Compare the screened population with the quantity to be delivered."""
    left = _count("surviving", surviving)
    needed = _count("required_quantity", required_quantity)
    if needed < 1:
        raise ValueError("required_quantity must be at least 1")
    return {
        "surviving": left,
        "required_quantity": needed,
        "shortfall": max(0, needed - left),
        "accepted": left >= needed,
    }


def assess_legacy_class_2_screening(spec):
    """Turn an executed legacy screening run into a screened-or-reject verdict."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "steps"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    chain = screening_chain(spec["steps"], spec["lot_size"])
    findings = []
    incomplete = [
        record["step"] for record in chain["steps"] if not record["full_coverage"]
    ]
    for record in chain["steps"]:
        if not record["full_coverage"]:
            findings.append(
                "step '%s' left %d of %d devices untested; screening is a "
                "hundred-percent operation"
                % (record["step"], record["untested"], record["entering"])
            )
    if chain["absent_steps"]:
        findings.append(
            "sequence did not run %s" % ", ".join(chain["absent_steps"])
        )
    if not chain["order"]["in_order"]:
        findings.append(
            "step '%s' was run out of sequence" % chain["order"]["first_out_of_order"]
        )
    burn_in = None
    entered_burn_in = None
    for record in chain["steps"]:
        if record["step"] == BURN_IN_STEP:
            entered_burn_in = record
            break
    if entered_burn_in is not None:
        burn_in = burn_in_pda(
            entered_burn_in["entering"],
            entered_burn_in["rejects"],
            spec.get("burn_in_allowable_percent", 5.0),
        )
        if not burn_in["accepted"]:
            findings.append(
                "burn-in percent defective %.3f%% exceeds the %.3f%% allowance"
                % (burn_in["percent_defective"], burn_in["allowable_percent"])
            )
    attrition = cumulative_attrition(chain["lot_size"], chain["surviving"])
    if not attrition["accepted"]:
        findings.append(
            "cumulative attrition %.3f%% exceeds the %.3f%% cap"
            % (attrition["attrition_percent"], attrition["cap_percent"])
        )
    deliverable = None
    if "required_quantity" in spec:
        deliverable = deliverable_check(chain["surviving"], spec["required_quantity"])
        if not deliverable["accepted"]:
            findings.append(
                "screened population is %d device(s) short of the %d to be "
                "delivered"
                % (deliverable["shortfall"], deliverable["required_quantity"])
            )
    accepted = (
        not incomplete
        and not chain["absent_steps"]
        and chain["order"]["in_order"]
        and (burn_in is None or burn_in["accepted"])
        and attrition["accepted"]
        and (deliverable is None or deliverable["accepted"])
    )
    return {
        "chain": chain,
        "incomplete_steps": incomplete,
        "burn_in": burn_in,
        "attrition": attrition,
        "deliverable": deliverable,
        "accepted": accepted,
        "disposition": "lot-screened" if accepted else "reject-screening-run",
        "findings": findings,
    }
