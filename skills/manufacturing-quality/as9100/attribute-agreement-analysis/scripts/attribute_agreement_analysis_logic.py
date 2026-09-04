"""Attribute agreement analysis logic: inter-rater agreement on attribute judgments.

Pure stdlib. Analyzes inspector agreement on attribute (go/no-go or
accept/rework/reject) judgments: percent agreement, Cohen kappa for two
inspectors, Fleiss kappa for three or more inspectors with the
chance-agreement correction, and the kappa verdict against the
attribute MSA acceptance bands.

Conventions: two-inspector tables are square agreement tables of counts
(rows inspector A category, columns inspector B category).
Multi-inspector data are per-part rating vectors: each part has n raters
and one count per category (counts sum to n).
"""

KAPPA_GOOD = 0.75  # band threshold: kappa at or above is good
KAPPA_MARGINAL = 0.40  # band threshold: kappa at or above is marginal


def _validate_square_table(table):
    """Return the total count of a valid square agreement table.

    Raises ValueError on an empty, non-square, or negative-count table
    and on a zero total.
    """
    if not isinstance(table, (list, tuple)) or len(table) == 0:
        raise ValueError("table must be a non-empty list of rows")
    n = len(table)
    total = 0
    for row in table:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError("table must be square")
        for count in row:
            if count < 0:
                raise ValueError("counts must be non-negative")
            total += count
    if total <= 0:
        raise ValueError("total count must be positive")
    return total


def percent_agreement(table):
    """Return the observed percent agreement: diagonal / total count."""
    _validate_square_table(table)
    diagonal = sum(table[i][i] for i in range(len(table)))
    total = sum(sum(row) for row in table)
    return diagonal / total


def cohen_kappa(table):
    """Cohen kappa for two inspectors on a square agreement table.

    Returns dict with keys kappa, observed_agreement, chance_agreement.
    kappa = (po - pe) / (1 - pe) with pe = sum(row_i * col_i) / N^2.
    """
    _validate_square_table(table)
    n = len(table)
    total = sum(sum(row) for row in table)
    row_totals = [sum(row) for row in table]
    col_totals = [sum(table[i][j] for i in range(n)) for j in range(n)]
    observed = sum(table[i][i] for i in range(n)) / total
    chance = sum(row_totals[i] * col_totals[i] for i in range(n)) / (total * total)
    if chance == 1.0:
        raise ValueError("chance agreement is 1.0; kappa is undefined")
    kappa = (observed - chance) / (1.0 - chance)
    return {
        "kappa": kappa,
        "observed_agreement": observed,
        "chance_agreement": chance,
    }


def _validate_ratings_matrix(ratings_matrix):
    """Return the total rating count of a valid per-part ratings matrix.

    Raises ValueError on an empty matrix, ragged rows, row sums below 2
    ratings, negative counts, and rows shorter than two categories.
    """
    if not isinstance(ratings_matrix, (list, tuple)) or len(ratings_matrix) == 0:
        raise ValueError("ratings matrix must be a non-empty list of rows")
    width = None
    total = 0
    for row in ratings_matrix:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            raise ValueError("each part row must hold at least two category counts")
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValueError("ratings matrix rows must have equal length")
        if sum(row) < 2:
            raise ValueError("each part needs at least two ratings")
        for count in row:
            if count < 0:
                raise ValueError("counts must be non-negative")
            total += count
    if total <= 0:
        raise ValueError("total rating count must be positive")
    return total


def fleiss_kappa(ratings_matrix):
    """Fleiss kappa for three or more inspectors on per-part ratings.

    Returns dict with keys kappa, pbar, pe. Each row holds the category
    counts for one part and sums to the rater count n:
    Pi = (sum_j x_ij^2 - n) / (n (n - 1)), Pbar = mean(Pi),
    p_j = column total / total ratings, pe = sum p_j^2,
    kappa = (Pbar - pe) / (1 - pe).
    """
    total = _validate_ratings_matrix(ratings_matrix)
    parts = len(ratings_matrix)
    width = len(ratings_matrix[0])
    pi_values = []
    col_totals = [0] * width
    for row in ratings_matrix:
        n = sum(row)
        sum_sq = sum(count * count for count in row)
        pi_values.append((sum_sq - n) / (n * (n - 1)))
        for j, count in enumerate(row):
            col_totals[j] += count
    pbar = sum(pi_values) / parts
    pe = sum((col_totals[j] / total) ** 2 for j in range(width))
    if pe == 1.0:
        raise ValueError("chance agreement is 1.0; kappa is undefined")
    kappa = (pbar - pe) / (1.0 - pe)
    return {"kappa": kappa, "pbar": pbar, "pe": pe}


def kappa_verdict(kappa):
    """Classify kappa: good >= 0.75, marginal 0.40 to 0.75, poor < 0.40."""
    if kappa < -1.0 or kappa > 1.0:
        raise ValueError("kappa must lie in [-1, 1]")
    if kappa >= KAPPA_GOOD:
        return "good"
    if kappa >= KAPPA_MARGINAL:
        return "marginal"
    return "poor"


def agreement_summary(table=None, ratings_matrix=None):
    """Return the applicable agreement statistic plus the band verdict.

    Pass exactly one of table (two-inspector counts) or ratings_matrix
    (per-part counts for three or more inspectors). Keys: method, kappa,
    verdict, and the pair-specific observed/percent agreement terms.
    """
    if (table is None) == (ratings_matrix is None):
        raise ValueError("provide exactly one of table or ratings_matrix")
    if table is not None:
        result = cohen_kappa(table)
        return {
            "method": "cohen",
            "kappa": result["kappa"],
            "observed_agreement": result["observed_agreement"],
            "chance_agreement": result["chance_agreement"],
            "verdict": kappa_verdict(result["kappa"]),
        }
    result = fleiss_kappa(ratings_matrix)
    return {
        "method": "fleiss",
        "kappa": result["kappa"],
        "pbar": result["pbar"],
        "pe": result["pe"],
        "verdict": kappa_verdict(result["kappa"]),
    }
