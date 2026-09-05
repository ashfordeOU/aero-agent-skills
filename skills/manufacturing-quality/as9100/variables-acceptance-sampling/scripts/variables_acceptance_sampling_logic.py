"""Variables acceptance-sampling plan logic (pure Python stdlib).

Design and run a variables acceptance sampling plan for a measured quality
characteristic with a single specification limit: map the lot size and the
inspection level to the sample size code letter, look up the sample size n
and the acceptability constant k (with the maximum allowable percent
nonconforming M) for the required AQL from an embedded reduced reference
table, form the Q statistic from the specification limit, the sample mean
and the sample standard deviation, and decide accept or reject by comparing
Q with k, with the estimated percent nonconforming p_hat available for the
M-method check.

Conventions and recorded assumptions:
- Single specification limit (USL or LSL), sigma unknown and estimated by
  the sample standard deviation s; the measured characteristic is assumed
  to follow a normal distribution (documented in the SKILL body).
- The embedded tables are a documented reduced training table of paraphrase
  values in the style of the public ANSI Z1.9 / MIL-STD-414 k-method,
  summary data only, never a reproduction of the standard.
- Only general inspection level II code-letter rows are embedded: 91-150 E,
  151-280 F, 281-500 G, 501-1200 H, 1201-3200 J, 3201-10000 K. Lot sizes
  outside 91-10000 and levels I or III raise ValueError because the reduced
  table has no row for them (same convention as the attribute
  acceptance-sampling sibling leaf).
- The k values repeat across codes and are keyed by AQL only (spec table:
  AQL 0.65/1.0/1.5/2.5/4.0 -> k 1.75/1.62/1.47/1.28/1.09); M pairs with the
  same AQL order and differs per code. The spec body fixes these exact
  values; they are module constants, not derived quantities.
- variables_sampling_decision reads the limit direction from the geometry:
  a limit value above the sample mean is treated as an upper specification
  limit, a limit at or below the mean as a lower specification limit. The
  spec single-sided convention keeps the sample mean inside the limit;
  two-sided or crossed-limit checks call form_q_upper / form_q_lower and
  accept_verdict directly.

Every function is deterministic and offline: no RNG, no network, no
external processes. Non-physical inputs raise ValueError.
"""

import math

INSPECTION_LEVELS = ("I", "II", "III")

# Reduced code-letter bands, general inspection level II (inclusive edges).
CODE_LETTER_BANDS = (
    (91, 150, "E"),
    (151, 280, "F"),
    (281, 500, "G"),
    (501, 1200, "H"),
    (1201, 3200, "J"),
    (3201, 10000, "K"),
)

# AQL values covered by the reduced plan table, ascending strictness order
# as paired in the spec body.
AQLS = (0.65, 1.0, 1.5, 2.5, 4.0)

# Acceptability constant k by AQL (identical across every embedded code).
K_BY_AQL = {0.65: 1.75, 1.0: 1.62, 1.5: 1.47, 2.5: 1.28, 4.0: 1.09}

# Maximum allowable percent nonconforming M by code and AQL (spec-fixed).
M_BY_CODE_AQL = {
    "E": {0.65: 4.17, 1.0: 3.61, 1.5: 2.98, 2.5: 2.28, 4.0: 1.66},
    "F": {0.65: 4.05, 1.0: 3.50, 1.5: 2.89, 2.5: 2.21, 4.0: 1.61},
    "G": {0.65: 3.97, 1.0: 3.43, 1.5: 2.83, 2.5: 2.16, 4.0: 1.58},
    "H": {0.65: 3.90, 1.0: 3.37, 1.5: 2.78, 2.5: 2.13, 4.0: 1.55},
    "J": {0.65: 3.85, 1.0: 3.33, 1.5: 2.75, 2.5: 2.10, 4.0: 1.53},
    "K": {0.65: 3.80, 1.0: 3.29, 1.5: 2.72, 2.5: 2.08, 4.0: 1.52},
}

# Sample size n by code letter.
N_BY_CODE = {"E": 15, "F": 20, "G": 25, "H": 30, "J": 35, "K": 40}


def code_letter(lot_size, level="II"):
    """Return the sample size code letter for a lot size at a level.

    Reduced table, level II rows only: 91-150 E, 151-280 F, 281-500 G,
    501-1200 H, 1201-3200 J, 3201-10000 K. Raises ValueError for a
    non-positive lot size, an unknown level, a level whose rows are not
    embedded (I, III), or a lot size outside the documented bands.
    """
    if lot_size <= 0:
        raise ValueError("lot_size must be positive, got %r" % (lot_size,))
    if level not in INSPECTION_LEVELS:
        raise ValueError(
            "level must be one of %r, got %r" % (INSPECTION_LEVELS, level)
        )
    if level != "II":
        raise ValueError(
            "reduced table embeds only general level II rows; "
            "level %r has no code-letter row" % (level,)
        )
    for low, high, code in CODE_LETTER_BANDS:
        if low <= lot_size <= high:
            return code
    raise ValueError(
        "lot_size %r outside the documented reduced bands 91-10000" % (lot_size,)
    )


def plan_lookup(code, aql):
    """Return {"n", "k", "M"} for a code letter and AQL from the table.

    Raises ValueError for an unknown code letter or an AQL that has no row
    in the reduced table (AQLs covered: 0.65, 1.0, 1.5, 2.5, 4.0).
    """
    if code not in N_BY_CODE:
        raise ValueError(
            "unknown code letter %r (embedded codes: E, F, G, H, J, K)" % (code,)
        )
    if aql not in K_BY_AQL:
        raise ValueError(
            "AQL %r has no row in the reduced table (AQLs: %s)"
            % (aql, ", ".join(str(v) for v in AQLS))
        )
    return {
        "n": N_BY_CODE[code],
        "k": K_BY_AQL[aql],
        "M": M_BY_CODE_AQL[code][aql],
    }


def normal_survival(z):
    """Return the standard normal upper-tail probability P(Z > z)."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def normal_cdf(z):
    """Return the standard normal cumulative probability P(Z <= z)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def form_q_upper(usl, xbar, s):
    """Return the upper-limit Q statistic (USL - xbar) / s.

    Raises ValueError when the sample standard deviation s is not positive.
    """
    if s <= 0:
        raise ValueError("s must be positive, got %r" % (s,))
    return (usl - xbar) / s


def form_q_lower(lsl, xbar, s):
    """Return the lower-limit Q statistic (xbar - LSL) / s.

    Raises ValueError when the sample standard deviation s is not positive.
    """
    if s <= 0:
        raise ValueError("s must be positive, got %r" % (s,))
    return (xbar - lsl) / s


def estimated_pct_nonconforming(Q, tail="upper"):
    """Return the estimated percent nonconforming for a Q statistic.

    Upper tail: 100 * normal_survival(Q), the estimated share above the USL.
    Lower tail: 100 * normal_cdf(-Q), the estimated share below the LSL when
    Q = (xbar - LSL) / s. Both forms agree for any Q because the standard
    normal is symmetric: cdf(-Q) equals survival(Q).
    """
    if tail not in ("upper", "lower"):
        raise ValueError("tail must be 'upper' or 'lower', got %r" % (tail,))
    if tail == "upper":
        return 100.0 * normal_survival(Q)
    return 100.0 * normal_cdf(-Q)


def accept_verdict(Q, k):
    """Return True when Q >= k (k-method acceptance decision)."""
    return Q >= k


def variables_sampling_decision(lot_size, aql, usl_or_lsl, xbar, s, level="II"):
    """Run the full single-sided variables sampling decision.

    Returns {"code", "n", "k", "M", "Q", "p_hat", "accept"}. The limit is
    read as an upper specification limit when it exceeds the sample mean
    and as a lower specification limit otherwise; accept is the k-method
    verdict Q >= k, and p_hat is the M-method check companion.
    """
    code = code_letter(lot_size, level)
    plan = plan_lookup(code, aql)
    if usl_or_lsl > xbar:
        Q = form_q_upper(usl_or_lsl, xbar, s)
        p_hat = estimated_pct_nonconforming(Q, tail="upper")
    else:
        Q = form_q_lower(usl_or_lsl, xbar, s)
        p_hat = estimated_pct_nonconforming(Q, tail="lower")
    return {
        "code": code,
        "n": plan["n"],
        "k": plan["k"],
        "M": plan["M"],
        "Q": Q,
        "p_hat": p_hat,
        "accept": accept_verdict(Q, plan["k"]),
    }
