#!/usr/bin/env python3
"""ECSS-E-ST-10-11 §4.5.4 cognitive performance and fatigue reference data
assessment (paraphrase, not copy).

Common-knowledge engineering summary (standards-map.yaml, ecss: gated false):
the human factors standard's cognitive performance clause supplies reference
thresholds for three domains -- sustained attention, working memory, and
decision-making -- as functions of crew fatigue level; fatigue is sourced from
task-induced load (acute), sleep deprivation, or circadian disruption; each
domain limit degrades with fatigue from a rested baseline to a minimum floor;
each domain is rated acceptable, marginal, or unacceptable against its adjusted
limit; the aggregate crew cognitive risk is the worst domain rating. This module
implements fatigue source categorization, per-domain limit calculation,
per-domain risk rating, and crew cognitive assessment; it does not define
mission scheduling policies, set rest requirements, or establish countermeasure
procedures.
"""

FATIGUE_SOURCE_TYPES = frozenset({"acute_task", "sleep_deprivation", "circadian"})

COGNITIVE_DOMAINS = frozenset({"attention", "working_memory", "decision_making"})

RISK_LEVELS = ("acceptable", "marginal", "unacceptable")
_RISK_RANK = {level: i for i, level in enumerate(RISK_LEVELS)}

# Sustained attention: baseline maximum duration and minimum floor (minutes).
ATTENTION_BASELINE_DURATION_MIN = 25.0
ATTENTION_MINIMUM_DURATION_MIN = 5.0
# Minutes of available attention lost per 0.1 unit of fatigue.
_ATTENTION_PENALTY_PER_STEP = 2.0
_ATTENTION_STEP_SIZE = 0.1

# Working memory: baseline capacity and critical floor (item count).
MEMORY_BASELINE_CAPACITY = 7
MEMORY_MINIMUM_CAPACITY = 3
# Items of capacity lost per 0.2 unit of fatigue.
_MEMORY_PENALTY_PER_STEP = 1
_MEMORY_STEP_SIZE = 0.2

# Decision-making: minimum time per option at zero fatigue (seconds).
DECISION_MIN_TIME_PER_OPTION_S = 30.0
# Factor by which per-option time is multiplied at full fatigue (linear interpolation).
_DECISION_FATIGUE_SCALE_AT_MAX = 2.0

# Marginal band upper limit: demand <= this factor times the adjusted limit => marginal.
_ATTENTION_MARGINAL_FACTOR = 2.0
_MEMORY_MARGINAL_EXTRA_ITEMS = 2
_DECISION_MARGINAL_FACTOR = 1.33


def categorize_fatigue_source(source_type):
    """Fatigue category string for source_type: "acute_task",
    "sleep_deprivation", or "circadian".  Raises ValueError for an
    unrecognized source type."""
    if source_type in FATIGUE_SOURCE_TYPES:
        return source_type
    raise ValueError(
        "unrecognized fatigue source type %r under "
        "E-ST-10-11 §4.5.4" % (source_type,)
    )


def _validate_fatigue_level(fatigue_level):
    if not isinstance(fatigue_level, (int, float)):
        raise TypeError("fatigue_level must be a number")
    if fatigue_level < 0.0 or fatigue_level > 1.0:
        raise ValueError(
            "fatigue_level must be in [0.0, 1.0]; got %r" % (fatigue_level,)
        )


def available_attention_duration_min(fatigue_level):
    """Fatigue-adjusted sustained attention duration (minutes) for
    fatigue_level in [0.0, 1.0].  Decreases by _ATTENTION_PENALTY_PER_STEP
    minutes for each _ATTENTION_STEP_SIZE unit of fatigue, floored at
    ATTENTION_MINIMUM_DURATION_MIN.  Raises ValueError for out-of-range
    fatigue_level."""
    _validate_fatigue_level(fatigue_level)
    steps = fatigue_level / _ATTENTION_STEP_SIZE
    adjusted = ATTENTION_BASELINE_DURATION_MIN - steps * _ATTENTION_PENALTY_PER_STEP
    return max(adjusted, ATTENTION_MINIMUM_DURATION_MIN)


def available_memory_capacity(fatigue_level):
    """Fatigue-adjusted working memory capacity (item count) for
    fatigue_level in [0.0, 1.0].  Decreases by _MEMORY_PENALTY_PER_STEP
    items for each _MEMORY_STEP_SIZE unit of fatigue, floored at
    MEMORY_MINIMUM_CAPACITY.  Raises ValueError for out-of-range
    fatigue_level."""
    _validate_fatigue_level(fatigue_level)
    steps = int(fatigue_level / _MEMORY_STEP_SIZE)
    adjusted = MEMORY_BASELINE_CAPACITY - steps * _MEMORY_PENALTY_PER_STEP
    return max(adjusted, MEMORY_MINIMUM_CAPACITY)


def required_decision_time_s(option_count, fatigue_level):
    """Total time (seconds) required to safely evaluate option_count
    options at fatigue_level.  Per-option time scales linearly from
    DECISION_MIN_TIME_PER_OPTION_S at zero fatigue to
    _DECISION_FATIGUE_SCALE_AT_MAX times that at fatigue 1.0.
    Raises ValueError for option_count < 1 or out-of-range
    fatigue_level."""
    if option_count < 1:
        raise ValueError(
            "option_count must be >= 1; got %r" % (option_count,)
        )
    _validate_fatigue_level(fatigue_level)
    scale = 1.0 + (_DECISION_FATIGUE_SCALE_AT_MAX - 1.0) * fatigue_level
    per_option = DECISION_MIN_TIME_PER_OPTION_S * scale
    return option_count * per_option


def attention_risk(task_duration_min, fatigue_level):
    """Risk rating for a sustained attention task of task_duration_min
    minutes at fatigue_level.  Returns "acceptable", "marginal", or
    "unacceptable".  Raises ValueError for negative task_duration_min or
    out-of-range fatigue_level."""
    if task_duration_min < 0.0:
        raise ValueError(
            "task_duration_min must be >= 0; got %r" % (task_duration_min,)
        )
    limit = available_attention_duration_min(fatigue_level)
    if task_duration_min <= limit:
        return "acceptable"
    if task_duration_min <= limit * _ATTENTION_MARGINAL_FACTOR:
        return "marginal"
    return "unacceptable"


def memory_risk(item_count, fatigue_level):
    """Risk rating for a working memory load of item_count items at
    fatigue_level.  Returns "acceptable", "marginal", or "unacceptable".
    Raises ValueError for negative item_count or out-of-range
    fatigue_level."""
    if item_count < 0:
        raise ValueError(
            "item_count must be >= 0; got %r" % (item_count,)
        )
    capacity = available_memory_capacity(fatigue_level)
    if item_count <= capacity:
        return "acceptable"
    if item_count <= capacity + _MEMORY_MARGINAL_EXTRA_ITEMS:
        return "marginal"
    return "unacceptable"


def decision_risk(option_count, time_available_s, fatigue_level):
    """Risk rating for a decision with option_count choices and
    time_available_s seconds at fatigue_level.  Returns "acceptable",
    "marginal", or "unacceptable".  Raises ValueError for option_count < 1,
    negative time_available_s, or out-of-range fatigue_level."""
    if time_available_s < 0.0:
        raise ValueError(
            "time_available_s must be >= 0; got %r" % (time_available_s,)
        )
    required = required_decision_time_s(option_count, fatigue_level)
    if time_available_s >= required:
        return "acceptable"
    if time_available_s >= required / _DECISION_MARGINAL_FACTOR:
        return "marginal"
    return "unacceptable"


def aggregate_cognitive_risk(domain_risks):
    """Worst risk level across a dict mapping domain name to risk string.
    Raises ValueError for an empty dict or an unknown domain or risk value.
    Does not mutate domain_risks."""
    if not domain_risks:
        raise ValueError("domain_risks must contain at least one domain")
    worst_rank = -1
    worst_level = "acceptable"
    for domain, risk in domain_risks.items():
        if domain not in COGNITIVE_DOMAINS:
            raise ValueError("unrecognized cognitive domain %r" % (domain,))
        if risk not in _RISK_RANK:
            raise ValueError("unrecognized risk level %r" % (risk,))
        rank = _RISK_RANK[risk]
        if rank > worst_rank:
            worst_rank = rank
            worst_level = risk
    return worst_level


def crew_cognitive_assessment(crew_member):
    """Full §4.5.4 cognitive performance assessment for one crew member.

    crew_member: {
        "crew_id": str,
        "fatigue_level": float (0.0–1.0),
        "tasks": [
            {
                "domain": "attention" | "working_memory" | "decision_making",
                # attention requires: {"task_duration_min": float}
                # working_memory requires: {"item_count": int}
                # decision_making requires: {"option_count": int,
                #                            "time_available_s": float}
            },
            ...
        ]
    }
    Returns {
        "crew_id": str,
        "domain_risks": {domain: risk_string, ...},
        "aggregate_risk": str,
        "findings": [{"domain": str, "issue": str, "risk": str}, ...]
    }.
    Raises ValueError for an unrecognized domain, missing required fields,
    out-of-range fatigue_level, or an empty tasks list.
    Does not mutate crew_member or any nested structure.
    """
    crew_id = crew_member["crew_id"]
    fatigue_level = crew_member["fatigue_level"]
    tasks = crew_member.get("tasks", [])

    _validate_fatigue_level(fatigue_level)

    if not tasks:
        raise ValueError(
            "crew_member %r has no tasks; at least one task is required" % (crew_id,)
        )

    domain_risks = {}
    findings = []

    for task in tasks:
        domain = task["domain"]
        if domain == "attention":
            duration = task["task_duration_min"]
            risk = attention_risk(duration, fatigue_level)
            domain_risks["attention"] = risk
            if risk != "acceptable":
                findings.append({
                    "domain": "attention",
                    "issue": "attention_limit_exceeded",
                    "adjusted_limit_min": available_attention_duration_min(fatigue_level),
                    "task_duration_min": duration,
                    "risk": risk,
                })
        elif domain == "working_memory":
            items = task["item_count"]
            risk = memory_risk(items, fatigue_level)
            domain_risks["working_memory"] = risk
            if risk != "acceptable":
                findings.append({
                    "domain": "working_memory",
                    "issue": "memory_capacity_exceeded",
                    "adjusted_capacity": available_memory_capacity(fatigue_level),
                    "item_count": items,
                    "risk": risk,
                })
        elif domain == "decision_making":
            options = task["option_count"]
            time_avail = task["time_available_s"]
            risk = decision_risk(options, time_avail, fatigue_level)
            domain_risks["decision_making"] = risk
            if risk != "acceptable":
                findings.append({
                    "domain": "decision_making",
                    "issue": "decision_time_insufficient",
                    "required_time_s": required_decision_time_s(options, fatigue_level),
                    "time_available_s": time_avail,
                    "risk": risk,
                })
        else:
            raise ValueError(
                "unrecognized cognitive domain %r in crew %r task list"
                % (domain, crew_id)
            )

    agg = aggregate_cognitive_risk(domain_risks)
    return {
        "crew_id": crew_id,
        "domain_risks": domain_risks,
        "aggregate_risk": agg,
        "findings": findings,
    }
