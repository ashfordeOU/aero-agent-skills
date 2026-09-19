"""Link setup time budgeting for a space communication link.

Anchor: ECSS-E-ST-50C clause 5.6.8 -- link setup times.
Paraphrased into an implementable procedure; no standard text is reproduced.

The single normative item is that the time a link takes to come into service is
bounded and stated. Everything that has to complete before user data flows --
carrier acquisition, symbol and frame synchronisation, any negotiation
handshake and the round trips that handshake costs -- adds up to one setup
time, and that time has to fit two separate limits:

  budget  -- the setup time the design declares it will not exceed;
  pass    -- the contact window that has to absorb the setup and still carry
             useful data afterwards.

A design can satisfy the first and fail the second, which is why the verdict
here is three-valued rather than pass or fail.
"""

import math

__all__ = [
    "SPEED_OF_LIGHT_M_S",
    "WITHIN_BUDGET",
    "ERODES_PASS",
    "EXCEEDS_BUDGET",
    "REL_TOL",
    "validate_duration",
    "validate_positive_duration",
    "validate_count",
    "validate_fraction",
    "one_way_delay_s",
    "handshake_delay_s",
    "normalize_stages",
    "stage_total_s",
    "dominant_stage",
    "setup_time_s",
    "pass_share",
    "usable_pass_s",
    "required_reduction_s",
    "assess_link_setup",
]

SPEED_OF_LIGHT_M_S = 299792458.0

WITHIN_BUDGET = "within-budget"
ERODES_PASS = "erodes-pass"
EXCEEDS_BUDGET = "exceeds-budget"

# Relative tolerance for every bound comparison, so a setup time sized to land
# exactly on its budget is accepted on every platform rather than on some.
REL_TOL = 1e-9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_duration(value, name="seconds"):
    """Return a non-negative duration in seconds."""
    seconds = _validate_number(value, name)
    if seconds < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return seconds


def validate_positive_duration(value, name="seconds"):
    """Return a strictly positive duration in seconds."""
    seconds = _validate_number(value, name)
    if seconds <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return seconds


def validate_count(value, name="exchanges"):
    """Return a non-negative whole number of protocol exchanges."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % name)
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def validate_fraction(value, name="max_pass_share"):
    """Return a share of the pass in the closed interval zero to one."""
    share = _validate_number(value, name)
    if share <= 0.0 or share > 1.0:
        raise ValueError("%s must lie above zero and at most one, got %r" % (name, value))
    return share


def one_way_delay_s(range_km):
    """Return the one-way propagation delay over a slant range in kilometres."""
    distance = validate_duration(range_km, "range_km")
    return (distance * 1000.0) / SPEED_OF_LIGHT_M_S


def handshake_delay_s(exchanges, one_way_s):
    """Return the propagation cost of a handshake of this many round trips.

    Each exchange is a message out and an answer back, so it costs two one-way
    delays. A protocol that needs no answer costs nothing here, which is the
    whole argument for a one-shot setup on a long link.
    """
    count = validate_count(exchanges)
    delay = validate_duration(one_way_s, "one_way_s")
    return 2.0 * count * delay


def normalize_stages(stages):
    """Return validated (name, seconds) pairs for the setup sequence."""
    if isinstance(stages, (str, bytes)) or not isinstance(stages, (list, tuple)):
        raise ValueError("stages must be a sequence of stage entries")
    if not stages:
        raise ValueError("stages must not be empty: a setup with no stage is not a budget")
    seen = set()
    pairs = []
    for entry in stages:
        if isinstance(entry, dict):
            if "name" not in entry or "seconds" not in entry:
                raise ValueError("a stage mapping needs both 'name' and 'seconds'")
            name = entry["name"]
            seconds = entry["seconds"]
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            name, seconds = entry
        else:
            raise ValueError("a stage entry must be a (name, seconds) pair or a mapping")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("stage name must be a non-empty string")
        key = name.strip()
        if key in seen:
            raise ValueError("duplicate stage name %r: two entries size the same stage" % key)
        seen.add(key)
        pairs.append((key, validate_duration(seconds, "stage %r seconds" % key)))
    return pairs


def stage_total_s(stages):
    """Return the summed duration of the declared setup stages."""
    return sum(seconds for _name, seconds in normalize_stages(stages))


def dominant_stage(stages):
    """Return the (name, seconds) of the stage that costs the most.

    Ties go to the first stage declared, so the answer is stable rather than
    dependent on dictionary ordering.
    """
    pairs = normalize_stages(stages)
    best = pairs[0]
    for pair in pairs[1:]:
        if pair[1] > best[1]:
            best = pair
    return best


def setup_time_s(stages, exchanges=0, one_way_s=0.0):
    """Return the total setup time: stage work plus handshake propagation."""
    return stage_total_s(stages) + handshake_delay_s(exchanges, one_way_s)


def pass_share(setup_s, pass_duration_s):
    """Return the fraction of the contact window the setup consumes."""
    setup = validate_duration(setup_s, "setup_s")
    window = validate_positive_duration(pass_duration_s, "pass_duration_s")
    return setup / window


def usable_pass_s(setup_s, pass_duration_s):
    """Return the seconds of the pass left for user data after setup.

    Never negative: a setup longer than the pass leaves nothing, and a negative
    number there would read as a credit.
    """
    setup = validate_duration(setup_s, "setup_s")
    window = validate_positive_duration(pass_duration_s, "pass_duration_s")
    left = window - setup
    if left < 0.0:
        return 0.0
    return left


def required_reduction_s(setup_s, budget_s):
    """Return the seconds that must come out of the setup to meet the budget."""
    setup = validate_duration(setup_s, "setup_s")
    budget = validate_duration(budget_s, "budget_s")
    over = setup - budget
    if over < 0.0:
        return 0.0
    return over


def assess_link_setup(
    stages,
    budget_s,
    pass_duration_s,
    exchanges=0,
    one_way_s=0.0,
    max_pass_share=0.1,
):
    """Assess one link setup sequence against its budget and its contact window."""
    pairs = normalize_stages(stages)
    budget = validate_positive_duration(budget_s, "budget_s")
    window = validate_positive_duration(pass_duration_s, "pass_duration_s")
    share_limit = validate_fraction(max_pass_share)
    propagation = handshake_delay_s(exchanges, one_way_s)
    setup = sum(seconds for _name, seconds in pairs) + propagation
    budget_tolerance = REL_TOL * max(budget, 1.0)
    within_budget = setup <= budget + budget_tolerance
    share = setup / window
    share_tolerance = REL_TOL * max(share_limit, 1.0)
    within_share = share <= share_limit + share_tolerance
    if not within_budget:
        verdict = EXCEEDS_BUDGET
    elif not within_share:
        verdict = ERODES_PASS
    else:
        verdict = WITHIN_BUDGET
    worst = dominant_stage(pairs)
    findings = []
    if not within_budget:
        findings.append(
            "setup of %.6g s exceeds the %.6g s budget by %.6g s" % (setup, budget, setup - budget)
        )
    if not within_share:
        findings.append(
            "setup consumes %.4g of the %.6g s pass against a %.4g limit" % (share, window, share_limit)
        )
    if propagation > 0.0 and propagation > 0.5 * setup:
        findings.append(
            "handshake propagation is %.6g s, more than half the setup; fewer exchanges "
            "buys more than a faster receiver" % propagation
        )
    return {
        "stages": [{"name": name, "seconds": seconds} for name, seconds in pairs],
        "stage_total_s": setup - propagation,
        "handshake_delay_s": propagation,
        "setup_time_s": setup,
        "budget_s": budget,
        "budget_margin_s": budget - setup,
        "required_reduction_s": required_reduction_s(setup, budget),
        "pass_duration_s": window,
        "pass_share": share,
        "max_pass_share": share_limit,
        "usable_pass_s": usable_pass_s(setup, window),
        "dominant_stage": worst[0],
        "dominant_stage_s": worst[1],
        "within_budget": within_budget,
        "within_pass_share": within_share,
        "verdict": verdict,
        "findings": findings,
    }
