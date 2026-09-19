"""IR verification of the result of an ultracleaning process.

Anchor: ECSS-Q-ST-70-05C used as the verification measurement for the
ultracleaning processes of ECSS-Q-ST-70-54C (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Cleaning is verified by measurement, not by procedure compliance. The
   process having been executed as written is a precondition; the areal
   organic level left on the surface is the evidence.
2. A cleaning campaign is a sequence of cycles, and each cycle has its
   own removal efficiency measured against the level the previous cycle
   left. A campaign average hides the only pattern that matters.
3. That pattern is the plateau. A process that has stopped removing will
   not start again, and repeating it is a way of spending schedule
   while the surface stays where it is. Successive low-efficiency
   cycles above the target mean a different process is needed, not
   another cycle.
4. A level that rises across a cycle is recontamination, and it is
   reported as such: the cleaning step is not the suspect, the handling
   between measurement and measurement is.
5. A residual reading that sits close to the blank of the solvent and
   consumables used to take it is a bound, not a value. It demonstrates
   cleanliness when the bound itself sits at or under the target, and
   demonstrates nothing when it does not.
6. Whether another cycle can reach the target is answerable. Projecting
   the current efficiency forward gives a cycle count, and a target that
   cannot be reached inside the permitted number of cycles is a finding
   about the process, not about the part.

Stdlib only, offline, deterministic.
"""

ACCEPTED = "ultracleaning-accepted"
FURTHER_CYCLE_REQUIRED = "further-cleaning-cycle-required"
PROCESS_CHANGE_REQUIRED = "cleaning-process-change-required"
NOT_DEMONSTRATED = "cleanliness-not-demonstrated"

DEFAULT_POLICY = {
    "minimum_cycle_efficiency": 0.10,
    "plateau_cycle_count": 2,
    "minimum_blank_margin_factor": 3.0,
    "maximum_projected_cycles": 20,
}

# Levels and efficiencies are quotients, so a value that should sit
# exactly on a bound can land a few units in the last place past it.
LEVEL_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _whole(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %r" % (label, minimum, value))
    return value


def resolved_policy(policy=None):
    """Merge a caller policy over the defaults and validate it."""
    merged = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict):
            raise ValueError("policy must be a mapping")
        unknown = sorted(set(policy) - set(DEFAULT_POLICY))
        if unknown:
            raise ValueError("unknown policy keys: %s" % ", ".join(unknown))
        merged.update(policy)
    _numeric("minimum_cycle_efficiency", merged["minimum_cycle_efficiency"],
             0.0, 1.0)
    _whole("plateau_cycle_count", merged["plateau_cycle_count"], 1)
    _numeric("minimum_blank_margin_factor",
             merged["minimum_blank_margin_factor"], 1.0)
    _whole("maximum_projected_cycles", merged["maximum_projected_cycles"], 1)
    return merged


def removal_efficiency(before_level, after_level):
    """Fraction of the level a single cleaning cycle removed."""
    before = _numeric("before_level", before_level, 0.0)
    after = _numeric("after_level", after_level, 0.0)
    if before <= 0.0:
        raise ValueError("before_level must be greater than zero")
    return (before - after) / before


def cumulative_removal(initial_level, final_level):
    """Fraction of the starting level a whole campaign removed."""
    return removal_efficiency(initial_level, final_level)


def blank_bounded_level(measured_level, blank_level, margin_factor):
    """Return (reported level, whether it is only a blank-limited bound)."""
    measured = _numeric("measured_level", measured_level, 0.0)
    blank = _numeric("blank_level", blank_level, 0.0)
    factor = _numeric("margin_factor", margin_factor, 1.0)
    floor = blank * factor
    if measured + LEVEL_TOLERANCE < floor:
        return floor, True
    return measured, False


def projected_cycles_to_target(current_level, target_level, efficiency,
                               maximum_cycles=None):
    """How many further cycles at this efficiency would reach the target."""
    current = _numeric("current_level", current_level, 0.0)
    target = _numeric("target_level", target_level, 0.0)
    rate = _numeric("efficiency", efficiency)
    if target <= 0.0:
        raise ValueError("target_level must be greater than zero")
    cap = DEFAULT_POLICY["maximum_projected_cycles"]
    if maximum_cycles is not None:
        cap = _whole("maximum_cycles", maximum_cycles, 1)
    if current <= target + LEVEL_TOLERANCE:
        return 0
    if rate <= 0.0:
        return None
    remaining = current
    for cycle in range(1, cap + 1):
        remaining = remaining * (1.0 - rate)
        if remaining <= target + LEVEL_TOLERANCE:
            return cycle
    return None


def plateau_detected(efficiencies, minimum_efficiency, plateau_cycle_count):
    """True when the trailing cycles have all stopped removing."""
    if not isinstance(efficiencies, list):
        raise ValueError("efficiencies must be a list")
    floor = _numeric("minimum_efficiency", minimum_efficiency, 0.0, 1.0)
    span = _whole("plateau_cycle_count", plateau_cycle_count, 1)
    if len(efficiencies) < span:
        return False
    trailing = efficiencies[-span:]
    for value in trailing:
        rate = _numeric("efficiency", value)
        if rate + LEVEL_TOLERANCE >= floor:
            return False
    return True


def validate_campaign(campaign):
    """Validate an ultracleaning campaign record and normalize it."""
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    item = campaign.get("item")
    if not isinstance(item, str) or not item.strip():
        raise ValueError("campaign needs a non-empty string item")
    item = item.strip()
    process = campaign.get("process_reference")
    if not isinstance(process, str) or not process.strip():
        raise ValueError(
            "%s needs the ultracleaning process reference it is verifying" % item
        )
    initial = _numeric(
        "%s initial_level_mg_m2" % item, campaign.get("initial_level_mg_m2"), 0.0
    )
    if initial <= 0.0:
        raise ValueError("%s initial_level_mg_m2 must be greater than zero" % item)
    target = _numeric(
        "%s target_level_mg_m2" % item, campaign.get("target_level_mg_m2"), 0.0
    )
    if target <= 0.0:
        raise ValueError("%s target_level_mg_m2 must be greater than zero" % item)
    cycles = campaign.get("cycles")
    if not isinstance(cycles, list) or not cycles:
        raise ValueError("%s needs a non-empty cycles list" % item)
    normalized = []
    for index, cycle in enumerate(cycles, start=1):
        if not isinstance(cycle, dict):
            raise ValueError("%s cycle %d must be a mapping" % (item, index))
        level = _numeric(
            "%s cycle %d post_level_mg_m2" % (item, index),
            cycle.get("post_level_mg_m2"),
            0.0,
        )
        normalized.append({"cycle": index, "post_level_mg_m2": level})
    blank = _numeric(
        "%s verification_blank_level_mg_m2" % item,
        campaign.get("verification_blank_level_mg_m2", 0.0),
        0.0,
    )
    return {
        "item": item,
        "process_reference": process.strip(),
        "initial_level_mg_m2": initial,
        "target_level_mg_m2": target,
        "cycles": normalized,
        "verification_blank_level_mg_m2": blank,
    }


def cycle_efficiencies(campaign):
    """Per-cycle removal efficiencies, each against the previous level."""
    norm = validate_campaign(campaign)
    previous = norm["initial_level_mg_m2"]
    rows = []
    for cycle in norm["cycles"]:
        rate = removal_efficiency(previous, cycle["post_level_mg_m2"])
        rows.append(
            {
                "cycle": cycle["cycle"],
                "before_level_mg_m2": previous,
                "after_level_mg_m2": cycle["post_level_mg_m2"],
                "efficiency": rate,
            }
        )
        previous = cycle["post_level_mg_m2"]
    return rows


def verify_ultracleaning(campaign, policy=None):
    """Decide what an IR verification says about an ultracleaning campaign."""
    norm = validate_campaign(campaign)
    rules = resolved_policy(policy)
    rows = cycle_efficiencies(norm)
    findings = []

    for row in rows:
        if row["efficiency"] < -LEVEL_TOLERANCE:
            findings.append(
                "level-rose-across-cycle-%d-recontamination-suspected"
                % row["cycle"]
            )

    final_measured = rows[-1]["after_level_mg_m2"]
    reported, blank_limited = blank_bounded_level(
        final_measured,
        norm["verification_blank_level_mg_m2"],
        rules["minimum_blank_margin_factor"],
    )
    if blank_limited:
        findings.append("residual-indistinguishable-from-the-verification-blank")

    target = norm["target_level_mg_m2"]
    meets_target = reported <= target + LEVEL_TOLERANCE

    efficiencies = [row["efficiency"] for row in rows]
    plateau = plateau_detected(
        efficiencies, rules["minimum_cycle_efficiency"],
        rules["plateau_cycle_count"]
    )
    projected = projected_cycles_to_target(
        reported, target, efficiencies[-1], rules["maximum_projected_cycles"]
    )

    if meets_target:
        outcome = ACCEPTED
    elif blank_limited:
        outcome = NOT_DEMONSTRATED
    elif plateau:
        outcome = PROCESS_CHANGE_REQUIRED
        findings.append("successive-cycles-below-the-efficiency-floor")
    elif projected is None:
        outcome = PROCESS_CHANGE_REQUIRED
        findings.append("target-unreachable-within-the-permitted-cycle-count")
    else:
        outcome = FURTHER_CYCLE_REQUIRED

    return {
        "item": norm["item"],
        "process_reference": norm["process_reference"],
        "target_level_mg_m2": target,
        "initial_level_mg_m2": norm["initial_level_mg_m2"],
        "final_measured_level_mg_m2": final_measured,
        "reported_level_mg_m2": reported,
        "blank_limited": blank_limited,
        "cycles": rows,
        "campaign_removal": cumulative_removal(
            norm["initial_level_mg_m2"], final_measured
        ),
        "plateau": plateau,
        "projected_further_cycles": projected,
        "findings": findings,
        "outcome": outcome,
    }


def verify_campaign_set(campaigns, policy=None):
    """Verify several campaigns and group them by outcome."""
    if not isinstance(campaigns, list) or not campaigns:
        raise ValueError("campaigns must be a non-empty list")
    rules = resolved_policy(policy)
    verified = []
    seen = set()
    for campaign in campaigns:
        row = verify_ultracleaning(campaign, rules)
        if row["item"] in seen:
            raise ValueError("duplicate campaign item %r" % (row["item"],))
        seen.add(row["item"])
        verified.append(row)
    return {
        "campaigns": verified,
        "accepted": [r["item"] for r in verified if r["outcome"] == ACCEPTED],
        "further_cycle": [
            r["item"] for r in verified if r["outcome"] == FURTHER_CYCLE_REQUIRED
        ],
        "process_change": [
            r["item"] for r in verified if r["outcome"] == PROCESS_CHANGE_REQUIRED
        ],
        "not_demonstrated": [
            r["item"] for r in verified if r["outcome"] == NOT_DEMONSTRATED
        ],
        "all_accepted": all(r["outcome"] == ACCEPTED for r in verified),
    }
