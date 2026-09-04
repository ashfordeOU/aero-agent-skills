"""Two-way ANOVA estimator for replicated Gage R and R studies.

Pure Python stdlib, deterministic, no RNG. Implements the balanced
two-way random-effects analysis of variance for a gage repeatability
and reproducibility study: part, operator, part-by-operator interaction
and equipment (repeatability) sources, expected-mean-square variance
components with the non-negative floor, the GRR/part/total variation
chain, the percent GRR verdict against the 10/30 bands, the F
statistics and the number of distinct categories.

Readings are passed as a dict {operator: {part: [trials]}} with every
operator measuring every part the same number of times (balanced).

The range-method Gage R and R estimator (average-range path) is NOT
implemented here; it lives in the measurement-systems-analysis leaf.
"""

from math import floor, sqrt

DISTINCT_CATEGORIES_CONST = 1.41


def _is_number(value):
    """True for int or float readings; bools and strings are rejected."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_study(data):
    """Check study layout; return (operators, parts, trials_per_cell).

    Raises ValueError when fewer than 2 operators, fewer than 2 parts,
    fewer than 2 trials per cell, cells are ragged (an operator misses
    a part or trial counts differ), or a reading is non-numeric.
    """
    if not isinstance(data, dict) or len(data) < 2:
        raise ValueError("study needs at least 2 operators")
    parts_sets = []
    trials_per_cell = None
    for operator, parts in data.items():
        if not isinstance(parts, dict) or len(parts) < 2:
            raise ValueError("study needs at least 2 parts per operator")
        parts_sets.append(set(parts.keys()))
        for part, trials in parts.items():
            if not isinstance(trials, (list, tuple)) or len(trials) < 2:
                raise ValueError("each cell needs at least 2 trials")
            if trials_per_cell is None:
                trials_per_cell = len(trials)
            if len(trials) != trials_per_cell:
                raise ValueError("ragged cells: trial counts differ")
            for reading in trials:
                if not _is_number(reading):
                    raise ValueError("non-numeric reading in cell")
    first_parts = parts_sets[0]
    if any(parts != first_parts for parts in parts_sets[1:]):
        raise ValueError("ragged cells: operators measure different parts")
    if trials_per_cell is None:
        raise ValueError("study has no cells")
    operators = sorted(data.keys())
    parts = sorted(first_parts)
    return operators, parts, trials_per_cell


def _mean(values):
    """Arithmetic mean of a non-empty numeric sequence."""
    return sum(values) / len(values)


def _f_ratio(numerator_ms, denominator_ms):
    """F statistic; None when both mean squares are zero, else inf on
    a zero denominator with a positive numerator."""
    if denominator_ms == 0:
        if numerator_ms == 0:
            return None
        return float("inf")
    return numerator_ms / denominator_ms


def verdict_for_percent_grr(percent_grr):
    """Map a percent GRR onto the 10/30 acceptance bands.

    Under 10 percent is acceptable, 10 through 30 percent is
    conditional (usable only for specific applications), over 30
    percent is unacceptable.
    """
    if percent_grr < 10.0:
        return "acceptable"
    if percent_grr <= 30.0:
        return "conditional"
    return "unacceptable"


def anova_grr_study(data):
    """Run the two-way ANOVA Gage R and R decomposition.

    Returns a dict with the sums of squares, degrees of freedom, mean
    squares, variance components, the ev/av/iv/grr/pv/tv variation
    chain, percent_grr, ndc and distinct_categories, the part and
    interaction F statistics, and the verdict string.
    """
    operators, parts, trials = validate_study(data)
    op_count = len(operators)
    part_count = len(parts)

    readings = []
    part_readings = {part: [] for part in parts}
    op_readings = {operator: [] for operator in operators}
    cell_readings = {}
    for operator in operators:
        for part in parts:
            cell = list(data[operator][part])
            cell_readings[(operator, part)] = cell
            readings.extend(cell)
            part_readings[part].extend(cell)
            op_readings[operator].extend(cell)

    grand_mean = _mean(readings)
    part_means = {part: _mean(cell) for part, cell in part_readings.items()}
    op_means = {operator: _mean(cell) for operator, cell in op_readings.items()}
    cell_means = {
        (operator, part): _mean(cell)
        for (operator, part), cell in cell_readings.items()
    }

    ss_part = trials * op_count * sum(
        (part_means[part] - grand_mean) ** 2 for part in parts
    )
    ss_operator = trials * part_count * sum(
        (op_means[operator] - grand_mean) ** 2 for operator in operators
    )
    ss_interaction = trials * sum(
        (
            cell_means[(operator, part)]
            - part_means[part]
            - op_means[operator]
            + grand_mean
        )
        ** 2
        for operator in operators
        for part in parts
    )
    ss_equipment = sum(
        (reading - cell_means[(operator, part)]) ** 2
        for operator in operators
        for part in parts
        for reading in data[operator][part]
    )

    df_part = part_count - 1
    df_operator = op_count - 1
    df_interaction = (part_count - 1) * (op_count - 1)
    df_equipment = op_count * part_count * (trials - 1)

    ms_part = ss_part / df_part
    ms_operator = ss_operator / df_operator
    ms_interaction = ss_interaction / df_interaction
    ms_equipment = ss_equipment / df_equipment

    var_equipment = ms_equipment
    var_interaction = max(0.0, (ms_interaction - ms_equipment) / trials)
    var_operator = max(0.0, (ms_operator - ms_interaction) / (part_count * trials))
    var_part = max(0.0, (ms_part - ms_interaction) / (op_count * trials))

    ev = sqrt(var_equipment)
    av = sqrt(var_operator)
    iv = sqrt(var_interaction)
    grr = sqrt(ev * ev + av * av + iv * iv)
    pv = sqrt(var_part)
    tv = sqrt(grr * grr + pv * pv)

    percent_grr = 0.0 if tv == 0 else 100.0 * grr / tv
    if grr == 0:
        ndc = None
    else:
        ndc = floor(DISTINCT_CATEGORIES_CONST * pv / grr)

    verdict = verdict_for_percent_grr(percent_grr)

    return {
        "grand_mean": grand_mean,
        "ss_part": ss_part,
        "ss_operator": ss_operator,
        "ss_interaction": ss_interaction,
        "ss_equipment": ss_equipment,
        "df_part": df_part,
        "df_operator": df_operator,
        "df_interaction": df_interaction,
        "df_equipment": df_equipment,
        "ms_part": ms_part,
        "ms_operator": ms_operator,
        "ms_interaction": ms_interaction,
        "ms_equipment": ms_equipment,
        "var_equipment": var_equipment,
        "var_interaction": var_interaction,
        "var_operator": var_operator,
        "var_part": var_part,
        "ev": ev,
        "av": av,
        "iv": iv,
        "grr": grr,
        "pv": pv,
        "tv": tv,
        "percent_grr": percent_grr,
        "ndc": ndc,
        "f_part": _f_ratio(ms_part, ms_interaction),
        "f_interaction": _f_ratio(ms_interaction, ms_equipment),
        "verdict": verdict,
        "distinct_categories": ndc,
    }


def anova_table(data):
    """Return the ANOVA table as row dicts for the five sources.

    Each row has keys source, ss, df, ms, F; the total row carries the
    grand totals and F None. The sum of the four effect rows equals the
    total row (balanced-design identity).
    """
    result = anova_grr_study(data)
    rows = [
        {
            "source": "part",
            "ss": result["ss_part"],
            "df": result["df_part"],
            "ms": result["ms_part"],
            "F": result["f_part"],
        },
        {
            "source": "operator",
            "ss": result["ss_operator"],
            "df": result["df_operator"],
            "ms": result["ms_operator"],
            "F": None,
        },
        {
            "source": "interaction",
            "ss": result["ss_interaction"],
            "df": result["df_interaction"],
            "ms": result["ms_interaction"],
            "F": result["f_interaction"],
        },
        {
            "source": "equipment",
            "ss": result["ss_equipment"],
            "df": result["df_equipment"],
            "ms": result["ms_equipment"],
            "F": None,
        },
        {
            "source": "total",
            "ss": sum(
                [
                    result["ss_part"],
                    result["ss_operator"],
                    result["ss_interaction"],
                    result["ss_equipment"],
                ]
            ),
            "df": result["df_part"]
            + result["df_operator"]
            + result["df_interaction"]
            + result["df_equipment"],
            "ms": None,
            "F": None,
        },
    ]
    return rows
