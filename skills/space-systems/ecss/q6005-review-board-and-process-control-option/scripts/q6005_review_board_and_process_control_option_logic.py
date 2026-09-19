"""Line monitoring and technical review board in place of batch sampling.

Anchor: ECSS-Q-ST-60-05C clause 12.2.2 (the alternative acceptance scheme
relying on statistical monitoring of the production line and a technical
review board rather than drawing a sample from every batch). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the monitoring window: a run of per-lot yields, oldest first,
   each a fraction between nothing and everything.
2. Compute the window statistics and the control limits from them. The limits
   come out of the line's own history, not out of a specification: the
   question is whether the line is behaving as it has been behaving, not
   whether it is good.
3. Find the lots outside those limits, and separately find the runs that sit
   on one side of the mean for long enough to be a drift rather than noise.
   A line can be inside its limits on every point and still be walking.
4. Check the board that carries the substitution: the roles it holds, whether
   it is quorate, and whether it has reviewed recently enough in lots.
5. Return one of three standings. The scheme continues; or it reverts to
   per-lot testing because the evidence for the substitution has weakened;
   or it is suspended because the line's central performance has fallen
   below the floor or no board exists at all.
"""

import statistics

__all__ = [
    "MIN_WINDOW_LOTS",
    "RUN_RULE_LENGTH",
    "SIGMA_MULTIPLIER",
    "MIN_MEAN_YIELD",
    "MAX_LOTS_BETWEEN_REVIEWS",
    "REQUIRED_BOARD_ROLES",
    "BOARD_QUORUM",
    "CONTROL_TOLERANCE",
    "validate_yields",
    "monitoring_statistics",
    "control_limits",
    "out_of_control_lots",
    "run_rule_violations",
    "board_status",
    "assess_line_monitoring",
]

# Lots of history below which the chart has too little to say.
MIN_WINDOW_LOTS = 10

# Consecutive lots on one side of the mean that count as a drift.
RUN_RULE_LENGTH = 7

# Spread each control limit sits from the window mean.
SIGMA_MULTIPLIER = 3.0

# Central yield below which the line is not performing, however stable.
MIN_MEAN_YIELD = 0.80

# Lots the board may let pass between reviews.
MAX_LOTS_BETWEEN_REVIEWS = 6

# Roles the technical review board draws its members from.
REQUIRED_BOARD_ROLES = (
    "manufacturer-quality-assurance",
    "manufacturing-engineering",
    "component-engineering",
    "customer-product-assurance",
)

# Members needed for the board to decide anything.
BOARD_QUORUM = 3

# Yields and limits are quotients that land on a bound exactly in worked
# cases; comparisons absorb representation error rather than moving the bound.
CONTROL_TOLERANCE = 1e-9


def _require_non_negative_int(value, label):
    """Return value as a non-negative int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_yields(yields):
    """Return the monitoring window as a list of floats, oldest lot first."""
    if isinstance(yields, str) or not isinstance(yields, (list, tuple)):
        raise ValueError("yields must be a sequence of per-lot yield fractions")
    if len(yields) < 2:
        raise ValueError("a monitoring window needs at least two lots to have a spread")
    cleaned = []
    for index, value in enumerate(yields):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("yields[%d] must be a number, got %r" % (index, value))
        value = float(value)
        if value < 0.0 or value > 1.0:
            raise ValueError("yields[%d] must be a fraction in [0, 1], got %r" % (index, value))
        cleaned.append(value)
    return cleaned


def monitoring_statistics(yields):
    """Return the window size, mean, spread and extremes of the yields."""
    window = validate_yields(yields)
    return {
        "lots": len(window),
        "mean_yield": statistics.fmean(window),
        "stdev": statistics.stdev(window),
        "minimum": min(window),
        "maximum": max(window),
    }


def control_limits(yields, sigma_multiplier=SIGMA_MULTIPLIER):
    """Return the lower and upper control limits from the line's own history.

    Limits are clamped into the range a yield can actually take, so a quiet
    line does not acquire an upper limit above one that nothing can cross.
    """
    if isinstance(sigma_multiplier, bool) or not isinstance(sigma_multiplier, (int, float)):
        raise ValueError("sigma_multiplier must be a number")
    if sigma_multiplier <= 0:
        raise ValueError("sigma_multiplier must be positive")
    stats = monitoring_statistics(yields)
    spread = float(sigma_multiplier) * stats["stdev"]
    lower = max(0.0, stats["mean_yield"] - spread)
    upper = min(1.0, stats["mean_yield"] + spread)
    return {
        "mean_yield": stats["mean_yield"],
        "stdev": stats["stdev"],
        "lower_control_limit": lower,
        "upper_control_limit": upper,
    }


def out_of_control_lots(yields, sigma_multiplier=SIGMA_MULTIPLIER):
    """Return the indices of lots sitting outside the line's control limits."""
    window = validate_yields(yields)
    limits = control_limits(yields, sigma_multiplier)
    lower = limits["lower_control_limit"] - CONTROL_TOLERANCE
    upper = limits["upper_control_limit"] + CONTROL_TOLERANCE
    return [i for i, value in enumerate(window) if value < lower or value > upper]


def run_rule_violations(yields, run_length=RUN_RULE_LENGTH):
    """Return the start indices of runs sitting on one side of the mean.

    A line inside its control limits on every point can still be walking off
    its centre, and the run is what makes that visible.
    """
    window = validate_yields(yields)
    length = _require_non_negative_int(run_length, "run_length")
    if length < 2:
        raise ValueError("run_length must be at least two lots")
    mean_yield = statistics.fmean(window)
    starts = []
    run_start = 0
    run_side = None
    for index, value in enumerate(window):
        if abs(value - mean_yield) <= CONTROL_TOLERANCE:
            side = None
        else:
            side = "above" if value > mean_yield else "below"
        if side is None or side != run_side:
            run_side = side
            run_start = index
        if run_side is not None and index - run_start + 1 == length:
            starts.append(run_start)
    return starts


def board_status(board):
    """Return the technical review board's composition and currency.

    An absent board normalises to an empty one rather than raising: a scheme
    running without a board is a real and serious case to be graded.
    """
    if board is None:
        board = {}
    if not isinstance(board, dict):
        raise ValueError("board must be a mapping")
    roles = board.get("roles", ())
    if isinstance(roles, str) or not isinstance(roles, (list, tuple, set, frozenset)):
        raise ValueError("board roles must be a sequence of role names")
    held = set()
    for role in roles:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role names must be non-empty strings, got %r" % (role,))
        held.add(role.strip().lower().replace("_", "-").replace(" ", "-"))
    present = [role for role in REQUIRED_BOARD_ROLES if role in held]
    missing = [role for role in REQUIRED_BOARD_ROLES if role not in held]
    lots_since_review = _require_non_negative_int(
        board.get("lots_since_last_review", 0), "lots_since_last_review"
    )
    interval = _require_non_negative_int(
        board.get("max_lots_between_reviews", MAX_LOTS_BETWEEN_REVIEWS),
        "max_lots_between_reviews",
    )
    return {
        "roles_present": present,
        "roles_missing": missing,
        "quorate": len(present) >= BOARD_QUORUM,
        "has_customer_member": "customer-product-assurance" in held,
        "convened": bool(held),
        "lots_since_last_review": lots_since_review,
        "max_lots_between_reviews": interval,
        "review_overdue": lots_since_review > interval,
    }


def assess_line_monitoring(spec):
    """Run the full clause 12.2.2 standing assessment for a monitored line.

    spec keys: yields (per-lot, oldest first), optional board, optional
    sigma_multiplier, optional run_length, optional minimum_mean_yield,
    optional minimum_window_lots.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "yields" not in spec:
        raise ValueError("spec missing required key 'yields'")
    sigma = spec.get("sigma_multiplier", SIGMA_MULTIPLIER)
    limits = control_limits(spec["yields"], sigma)
    stats = monitoring_statistics(spec["yields"])
    outliers = out_of_control_lots(spec["yields"], sigma)
    drifts = run_rule_violations(spec["yields"], spec.get("run_length", RUN_RULE_LENGTH))
    board = board_status(spec.get("board"))

    minimum_mean = spec.get("minimum_mean_yield", MIN_MEAN_YIELD)
    if isinstance(minimum_mean, bool) or not isinstance(minimum_mean, (int, float)):
        raise ValueError("minimum_mean_yield must be a number")
    if not 0.0 < minimum_mean <= 1.0:
        raise ValueError("minimum_mean_yield must lie in (0, 1]")
    minimum_window = _require_non_negative_int(
        spec.get("minimum_window_lots", MIN_WINDOW_LOTS), "minimum_window_lots"
    )

    suspensions = []
    reversions = []
    if stats["mean_yield"] < float(minimum_mean) - CONTROL_TOLERANCE:
        suspensions.append(
            "mean yield %.4f is below the floor of %.4f" % (stats["mean_yield"], minimum_mean)
        )
    if not board["convened"]:
        suspensions.append("no technical review board has been convened for this line")
    if stats["lots"] < minimum_window:
        reversions.append(
            "monitoring window holds %d lots against the %d the chart needs"
            % (stats["lots"], minimum_window)
        )
    if outliers:
        reversions.append(
            "lots outside the control limits at position(s) %s"
            % ", ".join(str(i) for i in outliers)
        )
    if drifts:
        reversions.append(
            "yield sits on one side of the mean from lot position(s) %s"
            % ", ".join(str(i) for i in drifts)
        )
    if board["convened"] and not board["quorate"]:
        reversions.append(
            "review board is not quorate; missing %s" % ", ".join(board["roles_missing"])
        )
    if board["convened"] and not board["has_customer_member"]:
        reversions.append("review board carries no customer product assurance member")
    if board["review_overdue"]:
        reversions.append(
            "%d lots since the last board review against an interval of %d"
            % (board["lots_since_last_review"], board["max_lots_between_reviews"])
        )

    if suspensions:
        standing = "suspend"
    elif reversions:
        standing = "revert-to-lot-control"
    else:
        standing = "continue"
    return {
        "lots": stats["lots"],
        "mean_yield": stats["mean_yield"],
        "stdev": stats["stdev"],
        "lower_control_limit": limits["lower_control_limit"],
        "upper_control_limit": limits["upper_control_limit"],
        "out_of_control_lots": outliers,
        "drift_runs": drifts,
        "board": board,
        "standing": standing,
        "sampling_may_be_substituted": standing == "continue",
        "suspensions": suspensions,
        "reversions": reversions,
    }
