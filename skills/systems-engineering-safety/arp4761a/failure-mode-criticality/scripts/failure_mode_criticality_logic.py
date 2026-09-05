"""failure_mode_criticality_logic.py

MIL-STD-1629A style quantitative failure mode criticality analysis for a
single item, pure stdlib, deterministic.

The item failure rate lambda_p is split into per-mode rates with the mode
ratios alpha (each in (0, 1], summing to 1). Every mode carries a
conditional failure-effect probability beta in [0, 1] (0 means the mode
has no effect at the item consequence level, 1 means certain effect).
The quantitative criticality of a mode over the operating time t is

    C_m = beta * alpha * lambda_p * t

and the item criticality is the sum of the per-mode criticalities:

    C_r = sum(C_m over all modes)

rank_modes sorts the modes by C_m descending (ties broken by mode id
ascending) and attaches the share of item criticality cm / C_r plus a
dominant flag set when the share reaches DOMINANT_SHARE.

Non-physical inputs raise ValueError. See the SKILL.md contract test
scripts/test_failure_mode_criticality.py for the worked-example anchors.
"""

MODE_RATIO_TOLERANCE = 1e-9
DOMINANT_SHARE = 0.5


def _as_number(value, label):
    """Coerce value to float, raising ValueError for non-numeric input."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric" % label) from None


def _validated_mode_dicts(modes):
    """Return a normalized list of (mode_id, alpha, beta) tuples.

    Raises ValueError when the mode list is empty or any mode dict is
    missing an id, alpha or beta key, or carries alpha outside (0, 1] or
    beta outside [0, 1].
    """
    if not modes:
        raise ValueError("modes must not be empty")
    out = []
    for mode in modes:
        if not isinstance(mode, dict):
            raise ValueError("each mode must be a dict with id, alpha, beta")
        missing = [key for key in ("id", "alpha", "beta") if key not in mode]
        if missing:
            raise ValueError("mode missing keys: %s" % ", ".join(missing))
        alpha = _as_number(mode["alpha"], "alpha")
        beta = _as_number(mode["beta"], "beta")
        if alpha <= 0 or alpha > 1:
            raise ValueError("alpha must lie in (0, 1], got %r" % alpha)
        if beta < 0 or beta > 1:
            raise ValueError("beta must lie in [0, 1], got %r" % beta)
        out.append((mode["id"], alpha, beta))
    return out


def split_item_rate(item_failure_rate, mode_ratios):
    """Split the item failure rate into per-mode rates alpha * lambda_p.

    Workflow step 3 of the SKILL.md (the rate-split traverse over the
    mode ratios) is implemented here. mode_ratios maps every mode id to
    its alpha, the alphas must each lie in (0, 1] and sum to 1.0 within
    MODE_RATIO_TOLERANCE, and the item failure rate must be positive.

    Returns {mode_id: per-mode rate}. Raises ValueError for a
    non-positive failure rate, an empty ratio set, any alpha outside
    (0, 1], or a ratio sum more than MODE_RATIO_TOLERANCE away from 1.0.
    """
    lambda_p = _as_number(item_failure_rate, "item failure rate")
    if lambda_p <= 0:
        raise ValueError("item failure rate must be > 0, got %r" % lambda_p)
    if not mode_ratios:
        raise ValueError("mode_ratios must not be empty")
    total = 0.0
    for mode_id, alpha in mode_ratios.items():
        alpha = _as_number(alpha, "alpha for mode %r" % (mode_id,))
        if alpha <= 0 or alpha > 1:
            raise ValueError("alpha must lie in (0, 1], got %r" % alpha)
        total += alpha
    if abs(total - 1.0) > MODE_RATIO_TOLERANCE:
        raise ValueError(
            "mode ratios must sum to 1.0 within %g, got %r"
            % (MODE_RATIO_TOLERANCE, total)
        )
    return {
        mode_id: alpha * lambda_p
        for mode_id, alpha in mode_ratios.items()
    }


def mode_criticality(beta, alpha, item_failure_rate, operating_time):
    """Quantitative criticality C_m = beta * alpha * lambda_p * t.

    Workflow step 4 of the SKILL.md (the per-mode criticality pass) is
    implemented here for one mode with conditional failure-effect
    probability beta, mode ratio alpha, item failure rate lambda_p and
    operating time t. Raises ValueError when beta lies outside [0, 1],
    alpha outside (0, 1], the item failure rate is not positive, or the
    operating time is negative. A zero operating time yields 0.0.
    """
    beta = _as_number(beta, "beta")
    alpha = _as_number(alpha, "alpha")
    lambda_p = _as_number(item_failure_rate, "item failure rate")
    time = _as_number(operating_time, "operating time")
    if beta < 0 or beta > 1:
        raise ValueError("beta must lie in [0, 1], got %r" % beta)
    if alpha <= 0 or alpha > 1:
        raise ValueError("alpha must lie in (0, 1], got %r" % alpha)
    if lambda_p <= 0:
        raise ValueError("item failure rate must be > 0, got %r" % lambda_p)
    if time < 0:
        raise ValueError("operating time must be >= 0, got %r" % time)
    return beta * alpha * lambda_p * time


def item_criticality(modes, item_failure_rate, operating_time):
    """Item criticality C_r, the sum of C_m over all modes.

    Workflow step 5 of the SKILL.md (the item criticality summation) is
    implemented here. modes is a list of dicts each holding id, alpha
    and beta. Raises ValueError when the mode list is empty, any mode is
    invalid, the item failure rate is not positive, or the operating
    time is negative.
    """
    lambda_p = _as_number(item_failure_rate, "item failure rate")
    time = _as_number(operating_time, "operating time")
    if lambda_p <= 0:
        raise ValueError("item failure rate must be > 0, got %r" % lambda_p)
    if time < 0:
        raise ValueError("operating time must be >= 0, got %r" % time)
    validated = _validated_mode_dicts(modes)
    return sum(
        beta * alpha * lambda_p * time
        for _, alpha, beta in validated
    )


def rank_modes(modes, item_failure_rate, operating_time):
    """Rank the modes by C_m descending with share and dominant flag.

    Workflow step 6 of the SKILL.md (the criticality ranking pass) is
    implemented here. Returns a list of dicts, each with keys id, alpha,
    beta, cm, share and dominant, sorted by cm descending with ties
    broken by mode id ascending. share is cm / C_r; dominant is True
    when the share reaches DOMINANT_SHARE. When C_r is 0 (for example a
    zero operating time or all-zero beta), every share is 0.0 and no
    mode is dominant. Raises ValueError as item_criticality does.
    """
    lambda_p = _as_number(item_failure_rate, "item failure rate")
    time = _as_number(operating_time, "operating time")
    if lambda_p <= 0:
        raise ValueError("item failure rate must be > 0, got %r" % lambda_p)
    if time < 0:
        raise ValueError("operating time must be >= 0, got %r" % time)
    validated = _validated_mode_dicts(modes)
    rows = []
    cr = 0.0
    for mode_id, alpha, beta in validated:
        cm = beta * alpha * lambda_p * time
        cr += cm
        rows.append(
            {"id": mode_id, "alpha": alpha, "beta": beta, "cm": cm}
        )
    rows.sort(key=lambda row: (-row["cm"], row["id"]))
    if cr > 0.0:
        for row in rows:
            share = row["cm"] / cr
            row["share"] = share
            row["dominant"] = share >= DOMINANT_SHARE
    else:
        for row in rows:
            row["share"] = 0.0
            row["dominant"] = False
    return rows
