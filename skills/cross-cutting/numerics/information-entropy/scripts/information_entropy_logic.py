"""Information entropy for aerospace data-channel analysis (pure stdlib).

Functions:
- shannon_entropy: Shannon entropy in bits per symbol of a probability
  mass function or a measured count distribution.
- binary_entropy: entropy of a two-symbol source as a function of the
  probability of one symbol.
- uniform_entropy: log2 of the symbol count, the max-entropy bound.
- min_bit_rate: entropy times the symbol rate, the minimum source
  coding bit rate of a symbol stream.
- entropy_summary: combined report with the uniform-distribution bound
  and the redundancy verdict against it.

Conventions: raw counts are accepted and normalized by their sum; a
zero-probability symbol contributes 0 * log2(0) = 0. All functions are
deterministic and offline.
"""

import math

# No module constants beyond stdlib imports; every scale is an
# explicit argument so callers keep physical units (symbols, bits,
# symbols per second) visible.


def shannon_entropy(symbol_probs_or_counts):
    """Shannon entropy in bits per symbol of a symbol distribution.

    Accepts a probability mass function or raw counts; counts are
    normalized by their total. A symbol with zero probability
    contributes nothing. Returns dict {entropy_bits, normalized}
    where normalized is the normalized probability list.
    ValueError on empty input, any negative value, or a non-positive
    total.
    """
    if len(symbol_probs_or_counts) == 0:
        raise ValueError("empty input: at least one symbol is required")
    if any(v < 0 for v in symbol_probs_or_counts):
        raise ValueError("probabilities and counts must be non-negative")
    total = float(sum(symbol_probs_or_counts))
    if total <= 0.0:
        raise ValueError("symbol total must be positive")
    normalized = [v / total for v in symbol_probs_or_counts]
    entropy = 0.0
    for p in normalized:
        if p > 0.0:
            entropy -= p * math.log2(p)
    return {"entropy_bits": entropy, "normalized": normalized}


def binary_entropy(p):
    """Binary entropy function of a two-symbol source, in bits.

    b(p) = -p log2 p - (1-p) log2(1-p) with 0 * log2(0) = 0 at the
    endpoints, so b(0) = b(1) = 0 and b(0.5) = 1. ValueError when p
    lies outside [0, 1].
    """
    if p < 0.0 or p > 1.0:
        raise ValueError("binary probability p must lie in [0, 1]")
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def uniform_entropy(n_symbols):
    """Entropy of the uniform distribution over n_symbols symbols.

    H = log2(n_symbols) bits, the maximum entropy reachable by any
    distribution over that many symbols. ValueError when n_symbols is
    below 1.
    """
    if n_symbols < 1:
        raise ValueError("n_symbols must be at least 1")
    return math.log2(n_symbols)


def min_bit_rate(entropy_bits, symbol_rate_per_s):
    """Minimum source coding bit rate of a symbol stream, in bps.

    R_min = H * r with H the per-symbol entropy in bits and r the
    symbol rate in symbols per second (Shannon source coding bound).
    ValueError when entropy or symbol rate is negative.
    """
    if entropy_bits < 0.0:
        raise ValueError("entropy_bits must be non-negative")
    if symbol_rate_per_s < 0.0:
        raise ValueError("symbol rate must be non-negative")
    return entropy_bits * symbol_rate_per_s


def entropy_summary(symbol_probs_or_counts, symbol_rate_per_s):
    """Information report: entropy, bound, redundancy, minimum bit rate.

    Returns dict {entropy_bits, n_symbols, uniform_bound_bits,
    redundancy, min_bit_rate_bps} with redundancy = 1 - H / log2(n):
    0 for a uniform source, 1 for a fully deterministic one.
    ValueError when fewer than 2 symbols are given, because the
    uniform bound needs at least 2 symbols.
    """
    result = shannon_entropy(symbol_probs_or_counts)
    n_symbols = len(symbol_probs_or_counts)
    if n_symbols < 2:
        raise ValueError("entropy_summary needs at least 2 symbols")
    bound = math.log2(n_symbols)
    entropy = result["entropy_bits"]
    return {
        "entropy_bits": entropy,
        "n_symbols": n_symbols,
        "uniform_bound_bits": bound,
        "redundancy": 1.0 - entropy / bound,
        "min_bit_rate_bps": min_bit_rate(entropy, symbol_rate_per_s),
    }
