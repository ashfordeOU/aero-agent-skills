"""Software product quality objectives and the metrication programme.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), clause 7.1 (deriving quality
requirements, stating them quantitatively, the assurance activities that
check them, product metrics, basic metrics, reporting, numerical accuracy,
analysis of software maturity) and 6.3.5.2, under which test coverage goals
per test level are agreed between customer and supplier. The standard does
not fix threshold values: the numbers below are illustrative project
defaults, to be replaced by what the contract and the plan agree. No
requirement text is reproduced.

Procedure implemented here
--------------------------
1. Hold a metric catalogue: kind, unit, direction (a ceiling or a floor) and
   the clause group that asks for it.
2. Hold default thresholds per category, and let a project override any of
   them; the source of every threshold is reported.
3. Measure two code metrics straight from source text: comment density and
   a decision-count estimate of cyclomatic complexity.
4. Evaluate a measurement set against the thresholds: pass, fail, missing,
   with the margin.
5. Evaluate per-module metrics and list the offenders.
6. Analyse maturity from the problem-report history: the discovery trend
   across the last periods, which category D does not have to produce.
"""

import re

__all__ = [
    "CATEGORIES",
    "METRICS",
    "DEFAULT_THRESHOLDS",
    "TOLERANCE",
    "normalise_category",
    "thresholds_for",
    "comment_density",
    "cyclomatic_estimate",
    "evaluate_metrics",
    "evaluate_modules",
    "maturity_trend",
]

CATEGORIES = ("A", "B", "C", "D")

# Tolerance for comparing a measured ratio with a threshold.
TOLERANCE = 1e-9

# name -> (kind, unit, direction, clause group)
# direction 'max' means the value must not exceed the threshold,
# 'min' means it must reach it.
METRICS = {
    "cyclomatic_complexity": ("product", "per function", "max", "7.1.5"),
    "nesting_depth": ("product", "levels", "max", "7.1.4"),
    "function_size_loc": ("product", "lines", "max", "7.1.4"),
    "comment_density": ("product", "ratio", "min", "7.1.4"),
    "requirement_coverage": ("product", "ratio", "min", "7.2.1"),
    "requirement_test_coverage": ("product", "ratio", "min", "6.3.5.2"),
    "statement_coverage": ("product", "ratio", "min", "6.3.5.2"),
    "decision_coverage": ("product", "ratio", "min", "6.3.5.2"),
    "mcdc_coverage": ("product", "ratio", "min", "6.3.5.2"),
    "open_major_nonconformances": ("process", "count", "max", "5.2.6"),
    "open_problem_reports": ("process", "count", "max", "5.2.5"),
    "coding_standard_violations": ("product", "count", "max", "6.3.4"),
}

# Illustrative defaults per category. None means no default: the project
# sets it or the metric is not graded.
DEFAULT_THRESHOLDS = {
    "A": {"cyclomatic_complexity": 10, "nesting_depth": 4, "function_size_loc": 60,
          "comment_density": 0.25, "requirement_coverage": 1.0,
          "requirement_test_coverage": 1.0, "statement_coverage": 1.0,
          "decision_coverage": 1.0, "mcdc_coverage": 1.0,
          "open_major_nonconformances": 0, "open_problem_reports": None,
          "coding_standard_violations": 0},
    "B": {"cyclomatic_complexity": 10, "nesting_depth": 4, "function_size_loc": 80,
          "comment_density": 0.2, "requirement_coverage": 1.0,
          "requirement_test_coverage": 1.0, "statement_coverage": 1.0,
          "decision_coverage": 1.0, "mcdc_coverage": None,
          "open_major_nonconformances": 0, "open_problem_reports": None,
          "coding_standard_violations": 0},
    "C": {"cyclomatic_complexity": 15, "nesting_depth": 5, "function_size_loc": 100,
          "comment_density": 0.15, "requirement_coverage": 1.0,
          "requirement_test_coverage": 1.0, "statement_coverage": None,
          "decision_coverage": None, "mcdc_coverage": None,
          "open_major_nonconformances": 0, "open_problem_reports": None,
          "coding_standard_violations": None},
    "D": {"cyclomatic_complexity": 20, "nesting_depth": 6, "function_size_loc": 150,
          "comment_density": 0.1, "requirement_coverage": 1.0,
          "requirement_test_coverage": 0.9, "statement_coverage": None,
          "decision_coverage": None, "mcdc_coverage": None,
          "open_major_nonconformances": 0, "open_problem_reports": None,
          "coding_standard_violations": None},
}

_COMMENT_PREFIXES = ("//", "#", "--", "/*", "*", "*/", "!", ";")
_DECISION = re.compile(
    r"\b(if|elif|else\s+if|for|while|case|catch|except|when)\b|&&|\|\||\?(?!\?)"
)


def normalise_category(value):
    """Return the category letter A to D; raise ValueError otherwise."""
    if not isinstance(value, str) or value.strip().upper() not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return value.strip().upper()


def thresholds_for(category, overrides=None):
    """Return {metric: (threshold, source)} for a category.

    source is 'project' for an override and 'default' otherwise. An override
    of None removes the threshold. Unknown metric names are refused.
    """
    cat = normalise_category(category)
    out = {}
    for name, value in DEFAULT_THRESHOLDS[cat].items():
        if value is not None:
            out[name] = (value, "default")
    for name, value in dict(overrides or {}).items():
        if name not in METRICS:
            raise ValueError("unknown metric %r" % (name,))
        if value is None:
            out.pop(name, None)
        else:
            out[name] = (value, "project")
    return out


def comment_density(source, prefixes=_COMMENT_PREFIXES):
    """Return comment lines over non-blank lines for a piece of source text.

    A line counts as a comment when it starts with one of the prefixes or
    sits inside a block comment. Pass the prefixes of the language measured:
    the default set treats a C preprocessor line as a comment, which a C
    project should exclude by passing ('//', '/*', '*', '*/').
    Returns 0.0 for empty input.
    """
    lines = [l.strip() for l in str(source).splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        return 0.0
    comments = 0
    in_block = False
    for line in lines:
        if in_block:
            comments += 1
            if "*/" in line:
                in_block = False
            continue
        if line.startswith("/*") and "*/" not in line[2:]:
            in_block = True
            comments += 1
            continue
        if line.startswith(tuple(prefixes)):
            comments += 1
    return round(comments / len(lines), 4)


def cyclomatic_estimate(source, prefixes=_COMMENT_PREFIXES):
    """Estimate cyclomatic complexity of one function from its text.

    One plus the number of decision points (branches, loops, case labels,
    handlers, short-circuit operators and the ternary). Comment lines are
    ignored. An estimate, not a parser: use the project's analyser for the
    record and this to cross-check it.
    """
    count = 0
    for line in str(source).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(tuple(prefixes)):
            continue
        count += len(_DECISION.findall(stripped))
    return 1 + count


def _grade(name, value, threshold):
    direction = METRICS[name][2]
    if direction == "max":
        ok = value <= threshold + TOLERANCE
        margin = threshold - value
    else:
        ok = value + TOLERANCE >= threshold
        margin = value - threshold
    return ok, round(margin, 4)


def evaluate_metrics(measurements, category, overrides=None):
    """Evaluate a measurement set against the thresholds for a category.

    measurements: {metric: value}. Returns a dict with rows (metric, value,
    threshold, source, direction, status 'pass'/'fail'/'missing', margin),
    the failing and missing metric names, unknown metric names, and the
    verdict 'pass' only when nothing fails and nothing with a threshold is
    missing.
    """
    limits = thresholds_for(category, overrides)
    unknown = sorted(n for n in measurements if n not in METRICS)
    rows, failing, missing = [], [], []
    for name in sorted(limits):
        threshold, source = limits[name]
        direction = METRICS[name][2]
        if name not in measurements or measurements[name] is None:
            rows.append({"metric": name, "value": None, "threshold": threshold,
                         "source": source, "direction": direction,
                         "status": "missing", "margin": None})
            missing.append(name)
            continue
        value = measurements[name]
        ok, margin = _grade(name, value, threshold)
        rows.append({"metric": name, "value": value, "threshold": threshold,
                     "source": source, "direction": direction,
                     "status": "pass" if ok else "fail", "margin": margin})
        if not ok:
            failing.append(name)
    return {
        "category": normalise_category(category),
        "rows": rows,
        "failing": failing,
        "missing": missing,
        "unknown": unknown,
        "verdict": "pass" if not failing and not missing else "fail",
    }


def evaluate_modules(modules, category, overrides=None,
                     metrics=("cyclomatic_complexity", "nesting_depth",
                              "function_size_loc", "comment_density")):
    """Grade per-module metrics and list the offenders.

    modules: list of dicts with 'name' and metric values.
    Returns offenders (name -> list of failing metrics), the compliant
    fraction and the worst module per metric.
    """
    limits = thresholds_for(category, overrides)
    offenders = {}
    worst = {}
    names = set()
    for mod in modules:
        name = str(mod.get("name") or "").strip()
        if not name or name in names:
            raise ValueError("module name missing or duplicated: %r" % (name,))
        names.add(name)
        for metric in metrics:
            if metric not in limits or mod.get(metric) is None:
                continue
            ok, margin = _grade(metric, mod[metric], limits[metric][0])
            if not ok:
                offenders.setdefault(name, []).append(metric)
            if metric not in worst or margin < worst[metric][1]:
                worst[metric] = (name, margin)
    total = len(names)
    fraction = round((total - len(offenders)) / total, 4) if total else 1.0
    return {
        "offenders": offenders,
        "compliant_fraction": fraction,
        "worst": {m: w[0] for m, w in sorted(worst.items())},
    }


def maturity_trend(history, category, window=3):
    """Analyse software maturity from the problem-report history.

    history: ordered list of (period label, reports opened, reports closed).
    window: number of trailing periods the trend is read over.

    Returns the backlog after each period, the discovery trend over the
    window ('decreasing', 'flat', 'increasing'), and a verdict: 'maturing'
    when discovery decreases and the backlog does not grow, 'not-maturing'
    otherwise, 'not-required' for category D, 'insufficient-data' with
    fewer than window periods.
    """
    cat = normalise_category(category)
    if cat == "D":
        return {"verdict": "not-required", "backlog": [], "trend": None}
    backlog = []
    level = 0
    for label, opened, closed in history:
        if opened < 0 or closed < 0:
            raise ValueError("negative count in period %r" % (label,))
        level = level + opened - closed
        if level < 0:
            raise ValueError("more reports closed than ever opened by %r" % (label,))
        backlog.append((label, level))
    if window < 2 or len(history) < window:
        return {"verdict": "insufficient-data", "backlog": backlog, "trend": None}
    tail = [opened for _, opened, _ in history[-window:]]
    if all(b < a for a, b in zip(tail, tail[1:])):
        trend = "decreasing"
    elif all(b > a for a, b in zip(tail, tail[1:])):
        trend = "increasing"
    else:
        trend = "flat"
    growing = backlog[-1][1] > backlog[-window][1]
    verdict = "maturing" if trend == "decreasing" and not growing else "not-maturing"
    return {"verdict": verdict, "backlog": backlog, "trend": trend}
