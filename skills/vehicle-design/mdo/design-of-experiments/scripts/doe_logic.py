#!/usr/bin/env python3
"""Design of experiments (DOE) planning and analysis logic (stdlib only).

Common-knowledge methodology summary (standards-map.yaml, far-25/cs-25:
gated false, reference-only): DOE plans a small, structured set of
experiments or simulations that map a design space and screen the
factors before optimization. Coded design matrices keep the algebra
clean: a two-level factor takes the coded levels -1 (low) and +1
(high), so contrasts are direct sums over the runs.

Supported designs:
- full_factorial: every combination of the per-factor level counts.
  Two-level factors code as (-1, +1); factors with three or more
  levels enumerate 0 .. m-1.
- fractional_factorial_2k: the full 2^k (k <= 7, at most 128 runs) or
  the 2^(k-1) half-fraction (k = 4..7) built from one defining
  relation word, default I = ABC...K, which is the maximal-resolution
  half-fraction with resolution k. Every run of the principal fraction
  satisfies product over the defining word letters = +1, so main
  effects stay clear of the two-factor interactions (I = ABCD aliases
  A with BCD and AB with CD at k = 4).
- latin_hypercube: n_samples x k_factors midpoint samples in [0, 1]^k,
  one sample per stratified row and column, random permutation per
  column from a fixed seed, so the strata of every factor are covered
  exactly once.
- central_composite: the 2^k factorial portion plus 2k axial points at
  +-alpha on each axis plus center runs at the origin. The default
  rotatable alpha = (2^k)^(1/4); alpha = 'faced' places the axial
  points on the factorial cube faces at +-1. Run count is
  2^k + 2k + center.

Analysis is for two-level designs: analyze_main_effects reports the
high-minus-low mean response per factor (twice the linear regression
coefficient) and ranks the factors; analyze_interactions reports the
same contrast for every factor pair. On y = 2*A + 1.5*B + A*B with
A, B coded -1/+1 the main effect of A is 4.0, of B is 3.0, and the
A-by-B interaction effect is 2.0. Invalid inputs raise ValueError.
"""

import itertools
import math
import random

FACTOR_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FULL_FACTORIAL_MAX_K = 7      # full 2^k cap: 2^7 = 128 runs
HALF_FRACTION_MIN_K = 4       # half-fraction support window
HALF_FRACTION_MAX_K = 7
CCD_MIN_K = 2
CCD_MAX_K = FULL_FACTORIAL_MAX_K
CCD_MIN_CENTER = 1
LHS_MIN_SAMPLES = 2
LHS_MIN_FACTORS = 1


def factor_label(index):
    """Return the spreadsheet-style label for factor index (0 -> A)."""
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ValueError("factor index must be a non-negative int, got %r" % (index,))
    if index < len(FACTOR_LETTERS):
        return FACTOR_LETTERS[index]
    return "F%d" % (index + 1)


def _validate_levels(levels_per_factor):
    if not isinstance(levels_per_factor, list) or not levels_per_factor:
        raise ValueError(
            "levels_per_factor must be a non-empty list of ints >= 2, got %r"
            % (levels_per_factor,)
        )
    for level in levels_per_factor:
        if not isinstance(level, int) or isinstance(level, bool) or level < 2:
            raise ValueError(
                "each level count must be an int >= 2, got %r" % (level,)
            )


def full_factorial(levels_per_factor):
    """Enumerate every combination of the per-factor level counts.

    A two-level factor (count 2) takes the coded levels (-1, +1); a
    factor with m >= 3 levels enumerates the coded levels 0 .. m-1.
    Returns a list of tuples, one per run, leftmost factor varying
    slowest. Raises ValueError when any level count is below 2 or the
    list is empty.
    """
    _validate_levels(levels_per_factor)
    coded = []
    for level in levels_per_factor:
        if level == 2:
            coded.append((-1, 1))
        else:
            coded.append(tuple(range(level)))
    return list(itertools.product(*coded))


def _letters_for(k):
    if len(FACTOR_LETTERS) < k:
        raise ValueError(
            "factor count %d exceeds the %d supported letters" % (k, len(FACTOR_LETTERS))
        )
    return FACTOR_LETTERS[:k]


def _validate_generator_words(words, letters):
    if not isinstance(words, list) or len(words) != 1:
        raise ValueError(
            "a 2^(k-1) half-fraction takes exactly one defining word "
            "in generator_words, got %r" % (words,)
        )
    word = words[0]
    if not isinstance(word, str) or len(word) < 2:
        raise ValueError(
            "defining word must be a string of at least two distinct "
            "letters, got %r" % (word,)
        )
    seen = set()
    for ch in word:
        if ch not in letters or ch in seen:
            raise ValueError(
                "defining word letters must be distinct and drawn from "
                "%s, got %r" % (letters, word)
            )
        seen.add(ch)
    return word


def fractional_factorial_2k(k, fraction=1, generator_words=None):
    """Two-level factorial design, full 2^k or 2^(k-1) half-fraction.

    fraction=1 returns the full 2^k design for 1 <= k <= 7 (at most
    128 runs). fraction=2 returns the principal 2^(k-1) half-fraction
    for 4 <= k <= 7: the base full factorial on k-1 factors with the
    remaining factor set by the defining relation word, default
    I = ABC...K, the maximal-resolution half-fraction (resolution k).
    Every returned run satisfies product over the word letters = +1.
    generator_words, when given, must hold exactly one word made of
    distinct letters from A..(k-th letter), at least two letters long;
    the largest letter in the word is the factor determined by the
    product of the other letters in the word. Raises ValueError for
    k, fraction, or generator words outside these rules.
    """
    if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= FULL_FACTORIAL_MAX_K:
        raise ValueError(
            "k must be an int from 1 to %d, got %r" % (FULL_FACTORIAL_MAX_K, k)
        )
    if not isinstance(fraction, int) or isinstance(fraction, bool) or fraction not in (1, 2):
        raise ValueError("fraction must be 1 (full 2^k) or 2 (half 2^(k-1)), got %r" % (fraction,))
    if fraction == 1:
        if generator_words is not None:
            raise ValueError(
                "generator_words only applies to a half-fraction, got %r" % (generator_words,)
            )
        return full_factorial([2] * k)
    if not HALF_FRACTION_MIN_K <= k <= HALF_FRACTION_MAX_K:
        raise ValueError(
            "half-fraction 2^(k-1) is supported for k = %d..%d, got k = %d"
            % (HALF_FRACTION_MIN_K, HALF_FRACTION_MAX_K, k)
        )
    letters = _letters_for(k)
    word = _validate_generator_words(
        generator_words if generator_words is not None else [letters], letters
    )
    word_index = [letters.index(ch) for ch in word]
    chosen = max(word_index)
    base_factors = [j for j in range(k) if j != chosen]
    rows = []
    for base_combo in itertools.product((-1, 1), repeat=k - 1):
        row_map = {}
        for pos, j in enumerate(base_factors):
            row_map[j] = base_combo[pos]
        product = 1
        for j in word_index:
            if j != chosen:
                product *= row_map[j]
        row_map[chosen] = product
        rows.append(tuple(row_map[j] for j in range(k)))
    return rows


def check_principal_fraction(design, word):
    """Verify every run satisfies product over the word letters = +1.

    The defining relation of the principal fraction. Returns True when
    every two-level run multiplies the letters of word to +1, False
    otherwise. Raises ValueError for a non-two-level design or a word
    with letters outside the design's factor count.
    """
    _validate_two_level_design(design, [0.0] * len(design))
    k = len(design[0])
    letters = _letters_for(k)
    idx = [letters.index(ch) for ch in word]
    for row in design:
        product = 1
        for j in idx:
            product *= row[j]
        if product != 1:
            return False
    return True


def latin_hypercube(n_samples, k_factors, seed):
    """Stratified sample of n_samples points in [0, 1]^k_factors.

    Midpoint latin hypercube: each factor column is a random
    permutation of the n_samples strata (fixed seed), and row i takes
    the midpoint (perm[i] + 0.5) / n_samples of its stratum, so every
    factor covers its strata exactly once and all rows are distinct.
    Returns a list of n_samples tuples. Raises ValueError when
    n_samples < 2, k_factors < 1, or seed is not an int.
    """
    if not isinstance(n_samples, int) or isinstance(n_samples, bool) or n_samples < LHS_MIN_SAMPLES:
        raise ValueError(
            "n_samples must be an int >= %d, got %r" % (LHS_MIN_SAMPLES, n_samples)
        )
    if not isinstance(k_factors, int) or isinstance(k_factors, bool) or k_factors < LHS_MIN_FACTORS:
        raise ValueError(
            "k_factors must be an int >= %d, got %r" % (LHS_MIN_FACTORS, k_factors)
        )
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be a fixed int, got %r" % (seed,))
    rng = random.Random(seed)
    perms = []
    for _ in range(k_factors):
        perm = list(range(n_samples))
        rng.shuffle(perm)
        perms.append(perm)
    return [
        tuple((perms[j][i] + 0.5) / n_samples for j in range(k_factors))
        for i in range(n_samples)
    ]


def central_composite(k, center=1, alpha="axial"):
    """Central composite design matrix around the coded baseline.

    Returns the 2^k factorial portion (coded -1/+1), then the 2k axial
    runs at +-alpha on each axis with the other factors at 0.0, then
    center runs at the origin repeated center times. Run count is
    2^k + 2k + center. alpha='axial' (default) uses the rotatable
    value (2^k)^(1/4); alpha='faced' uses 1.0; a numeric alpha must be
    positive. Raises ValueError for k outside 2..7, center < 1, or a
    non-positive or unknown alpha.
    """
    if not isinstance(k, int) or isinstance(k, bool) or not CCD_MIN_K <= k <= CCD_MAX_K:
        raise ValueError(
            "central composite k must be an int from %d to %d, got %r"
            % (CCD_MIN_K, CCD_MAX_K, k)
        )
    if not isinstance(center, int) or isinstance(center, bool) or center < CCD_MIN_CENTER:
        raise ValueError(
            "center must be an int >= %d, got %r" % (CCD_MIN_CENTER, center)
        )
    if isinstance(alpha, str):
        if alpha == "axial":
            a = 2.0 ** (k / 4.0)
        elif alpha == "faced":
            a = 1.0
        else:
            raise ValueError("alpha must be 'axial', 'faced', or a positive number, got %r" % (alpha,))
    elif isinstance(alpha, (int, float)) and not isinstance(alpha, bool):
        if alpha <= 0:
            raise ValueError("alpha must be positive, got %r" % (alpha,))
        a = float(alpha)
    else:
        raise ValueError("alpha must be 'axial', 'faced', or a positive number, got %r" % (alpha,))
    rows = list(full_factorial([2] * k))
    for j in range(k):
        plus = [0.0] * k
        minus = [0.0] * k
        plus[j] = a
        minus[j] = -a
        rows.append(tuple(plus))
        rows.append(tuple(minus))
    center_row = (0.0,) * k
    rows.extend([center_row] * center)
    return rows


def _validate_two_level_design(design, responses):
    if not isinstance(design, list) or not design:
        raise ValueError("design must be a non-empty list of runs, got %r" % (design,))
    k = len(design[0])
    if k < 1:
        raise ValueError("design runs must have at least one factor")
    for row in design:
        if not isinstance(row, (list, tuple)) or len(row) != k:
            raise ValueError(
                "every design run must be a row of %d coded levels" % k
            )
        for value in row:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value not in (-1, 1):
                raise ValueError(
                    "factor analysis needs a two-level design with every "
                    "entry coded -1 or +1, found %r" % (value,)
                )
    if not isinstance(responses, list) or len(responses) != len(design):
        raise ValueError(
            "responses must match the design run count: got %d responses "
            "for %d runs" % (len(responses), len(design))
        )
    for y in responses:
        if not isinstance(y, (int, float)) or isinstance(y, bool):
            raise ValueError(
                "responses must be numeric, found %r" % (y,)
            )


def analyze_main_effects(design, responses):
    """Per-factor high-minus-low mean response and factor ranking.

    For each two-level factor, splits the runs on the coded level,
    computes the mean response at the high (+1) and low (-1) level,
    and the effect = high_mean - low_mean, which equals twice the
    linear regression coefficient of that factor. Returns
    {"n_runs": n, "effects": [per-factor dicts in factor order],
    "ranking": [factor labels sorted by |effect| descending, ties in
    factor order]}. Raises ValueError for a non-two-level design or a
    response count that does not match the run count.
    """
    _validate_two_level_design(design, responses)
    k = len(design[0])
    effects = []
    for j in range(k):
        high = [y for row, y in zip(design, responses) if row[j] == 1]
        low = [y for row, y in zip(design, responses) if row[j] == -1]
        high_mean = sum(high) / len(high)
        low_mean = sum(low) / len(low)
        effects.append(
            {
                "factor": factor_label(j),
                "effect": high_mean - low_mean,
                "low_mean": low_mean,
                "high_mean": high_mean,
            }
        )
    ranked = sorted(range(k), key=lambda j: (-abs(effects[j]["effect"]), j))
    return {
        "n_runs": len(design),
        "effects": effects,
        "ranking": [effects[j]["factor"] for j in ranked],
    }


def analyze_interactions(design, responses):
    """Two-factor interaction effects for a two-level design.

    For every factor pair (i, j), the interaction effect is the mean
    response where the product x_i * x_j equals +1 minus the mean
    response where it equals -1, again twice the pair's regression
    coefficient. Returns {"n_runs": n, "interactions": [per-pair
    dicts sorted by |effect| descending, ties in pair order]} with
    each dict carrying the factor label tuple and a joined label.
    Raises ValueError for a non-two-level design, fewer than two
    factors, or a mismatched response count.
    """
    _validate_two_level_design(design, responses)
    k = len(design[0])
    if k < 2:
        raise ValueError(
            "interaction analysis needs at least two factors, got %d" % k
        )
    results = []
    for i in range(k):
        for j in range(i + 1, k):
            high = [y for row, y in zip(design, responses) if row[i] * row[j] == 1]
            low = [y for row, y in zip(design, responses) if row[i] * row[j] == -1]
            pair = (factor_label(i), factor_label(j))
            results.append(
                {
                    "factors": pair,
                    "label": "%s%s" % pair,
                    "effect": sum(high) / len(high) - sum(low) / len(low),
                }
            )
    results.sort(key=lambda entry: (-abs(entry["effect"]), entry["factors"]))
    return {"n_runs": len(design), "interactions": results}


_KINDS = {
    "full-factorial": full_factorial,
    "fractional-factorial": fractional_factorial_2k,
    "fractional-factorial-2k": fractional_factorial_2k,
    "latin-hypercube": latin_hypercube,
    "central-composite": central_composite,
}


def build_design_matrix(kind, **params):
    """Dispatch a DOE kind and return the coded matrix with its run count.

    kind is one of 'full-factorial', 'fractional-factorial-2k' (alias
    'fractional-factorial'), 'latin-hypercube', 'central-composite'.
    Keyword params are passed to the underlying builder, for example
    levels_per_factor=[2, 2, 2], k=4, fraction=2, n_samples=10,
    k_factors=3, seed=5, center=1, alpha='axial'. Returns
    {"kind": kind, "matrix": [rows], "run_count": n}. Raises
    ValueError for an unknown kind or for invalid builder parameters.
    """
    if not isinstance(kind, str) or kind not in _KINDS:
        raise ValueError(
            "unknown design kind %r; choose from %s"
            % (kind, ", ".join(sorted(_KINDS)))
        )
    rows = _KINDS[kind](**params)
    return {"kind": kind, "matrix": rows, "run_count": len(rows)}
