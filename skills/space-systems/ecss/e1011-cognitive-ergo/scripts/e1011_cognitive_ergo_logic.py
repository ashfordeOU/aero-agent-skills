#!/usr/bin/env python3
"""ECSS-E-ST-10-11C §4.6.6 cognitive ergonomics for human-operated space system
interfaces (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): cognitive
ergonomics in space system interface design covers three interconnected areas.
Information presentation is governed by two density limits rooted in
working-memory research: a display view should carry no more than nine distinct
elements (Miller's Law upper bound, 7 ± 2 chunks), and each individual element
should use no more than three simultaneous coding dimensions drawn from the
recognised set (color, shape, size, position, brightness, motion, text label,
auditory code), because adding a fourth or more dimension degrades rather than
improves discrimination. Workload is assessed on a composite 0-to-10 scale
(NASA-TLX-inspired, common knowledge): below 3.0 is under-load (vigilance risk),
3.0 to 7.0 is the optimal range for sustained performance, and above 7.0 is
over-load (commission error risk). The peak simultaneous-task count is checked
independently against a four-task threshold (multiple-resource theory, common
knowledge). Situation awareness is decomposed into three levels (Endsley model,
common knowledge): Level 1 perception of current states, Level 2 comprehension
of their meaning, Level 3 projection of future states; an interface that does
not supply indicators at every level is SA-incomplete. This module implements
workload categorization, simultaneous-task checking, coding-dimension checking,
information-density checking, SA-coverage assessment, and aggregate review; it
does not set mission-specific thresholds — those are set by system requirements
and override the HFE-literature-derived defaults supplied here.
"""

VALID_CODING_DIMENSIONS = frozenset({
    "color",
    "shape",
    "size",
    "position",
    "brightness",
    "motion",
    "text_label",
    "auditory_code",
})

MAX_CODING_DIMENSIONS_PER_ELEMENT = 3   # HFE design guideline (common knowledge)
MAX_ELEMENTS_PER_VIEW = 9               # Miller's Law upper bound (7 + 2 chunks)
MAX_SIMULTANEOUS_TASKS = 4              # multiple-resource theory threshold

SA_LEVELS = frozenset({
    "level_1_perception",
    "level_2_comprehension",
    "level_3_projection",
})

WORKLOAD_MIN = 0.0
WORKLOAD_MAX = 10.0
WORKLOAD_LOWER_OPTIMAL = 3.0
WORKLOAD_UPPER_OPTIMAL = 7.0


def categorize_workload(workload_index):
    """Return the workload band for a composite workload index on [0, 10].

    Returns "under_loaded" (index < 3.0), "optimal" (3.0 <= index <= 7.0),
    or "over_loaded" (index > 7.0).
    Raises ValueError for a value outside [0.0, 10.0]."""
    if not (WORKLOAD_MIN <= workload_index <= WORKLOAD_MAX):
        raise ValueError(
            "workload_index %r is outside the valid range [%.1f, %.1f]"
            % (workload_index, WORKLOAD_MIN, WORKLOAD_MAX)
        )
    if workload_index < WORKLOAD_LOWER_OPTIMAL:
        return "under_loaded"
    if workload_index <= WORKLOAD_UPPER_OPTIMAL:
        return "optimal"
    return "over_loaded"


def check_simultaneous_tasks(task_count, threshold=None):
    """Return a result dict for a count of simultaneous cognitive tasks.

    Returns {"task_count": int, "threshold": int, "within_limit": bool}.
    threshold defaults to MAX_SIMULTANEOUS_TASKS.
    Raises ValueError for negative task_count or threshold < 1."""
    if threshold is None:
        threshold = MAX_SIMULTANEOUS_TASKS
    if task_count < 0:
        raise ValueError(
            "task_count must be non-negative; got %r" % (task_count,)
        )
    if threshold < 1:
        raise ValueError(
            "threshold must be >= 1; got %r" % (threshold,)
        )
    return {
        "task_count": task_count,
        "threshold": threshold,
        "within_limit": task_count <= threshold,
    }


def check_coding_dimensions(coding_set, max_dims=None):
    """Return a result dict for the coding dimensions used on one display element.

    coding_set: iterable of coding dimension name strings.
    max_dims: maximum allowed count; defaults to MAX_CODING_DIMENSIONS_PER_ELEMENT.
    Returns {"dimensions": sorted list, "count": int, "max_dims": int,
             "within_limit": bool, "excess": sorted list of excess names}.
    Raises ValueError for any unrecognized coding dimension name."""
    if max_dims is None:
        max_dims = MAX_CODING_DIMENSIONS_PER_ELEMENT
    dims = sorted(set(coding_set))
    unknown = [d for d in dims if d not in VALID_CODING_DIMENSIONS]
    if unknown:
        raise ValueError(
            "unrecognized coding dimension(s) %r; valid dimensions: %s"
            % (unknown, sorted(VALID_CODING_DIMENSIONS))
        )
    count = len(dims)
    within_limit = count <= max_dims
    excess = dims[max_dims:] if count > max_dims else []
    return {
        "dimensions": dims,
        "count": count,
        "max_dims": max_dims,
        "within_limit": within_limit,
        "excess": excess,
    }


def check_information_density(element_count, max_elements=None):
    """Return a result dict for the number of distinct elements in one view.

    element_count: non-negative integer count of distinct information elements.
    max_elements: upper limit; defaults to MAX_ELEMENTS_PER_VIEW.
    Returns {"element_count": int, "max_elements": int, "in_bounds": bool}.
    Raises ValueError for negative element_count or max_elements < 1."""
    if max_elements is None:
        max_elements = MAX_ELEMENTS_PER_VIEW
    if element_count < 0:
        raise ValueError(
            "element_count must be non-negative; got %r" % (element_count,)
        )
    if max_elements < 1:
        raise ValueError(
            "max_elements must be >= 1; got %r" % (max_elements,)
        )
    return {
        "element_count": element_count,
        "max_elements": max_elements,
        "in_bounds": element_count <= max_elements,
    }


def assess_sa_coverage(provided_sa_levels):
    """Return a sorted list of SA level names absent from provided_sa_levels.

    provided_sa_levels: any iterable of SA level name strings.
    Does not mutate its input."""
    provided = frozenset(provided_sa_levels)
    return sorted(SA_LEVELS - provided)


def cognitive_ergo_review(
    workload_index,
    task_count,
    coding_sets=None,
    element_counts=None,
    sa_levels=None,
):
    """Full §4.6.6 cognitive ergonomics review.

    workload_index: float on [0, 10].
    task_count: int, number of simultaneous cognitive tasks.
    coding_sets: optional list of iterables; each is the coding dimensions for
                 one display element. If None, coding-dimension check is skipped.
    element_counts: optional list of ints; each is the element count for one
                    display view. If None, density check is skipped.
    sa_levels: iterable of SA level names the interface provides; defaults to
               empty (all SA levels will be flagged as missing).

    Returns:
        {
          "workload_band": str,
          "workload_ok": bool,               # True when band is "optimal"
          "simultaneous_tasks_ok": bool,
          "coding_violations": list,         # coding results where within_limit is False
          "density_violations": list,        # density results where in_bounds is False
          "sa_missing": list,                # sorted SA level names not covered
          "compliant": bool,                 # True when all checks pass
        }
    Raises ValueError for invalid inputs (propagated from sub-checks)."""
    workload_band = categorize_workload(workload_index)
    workload_ok = workload_band == "optimal"

    tasks_result = check_simultaneous_tasks(task_count)
    simultaneous_tasks_ok = tasks_result["within_limit"]

    coding_violations = []
    if coding_sets is not None:
        for cs in coding_sets:
            result = check_coding_dimensions(cs)
            if not result["within_limit"]:
                coding_violations.append(result)

    density_violations = []
    if element_counts is not None:
        for ec in element_counts:
            result = check_information_density(ec)
            if not result["in_bounds"]:
                density_violations.append(result)

    sa_missing = assess_sa_coverage(sa_levels if sa_levels is not None else [])

    compliant = (
        workload_ok
        and simultaneous_tasks_ok
        and len(coding_violations) == 0
        and len(density_violations) == 0
        and len(sa_missing) == 0
    )

    return {
        "workload_band": workload_band,
        "workload_ok": workload_ok,
        "simultaneous_tasks_ok": simultaneous_tasks_ok,
        "coding_violations": coding_violations,
        "density_violations": density_violations,
        "sa_missing": sa_missing,
        "compliant": compliant,
    }


def is_cognitively_ergonomic(review):
    """True when cognitive_ergo_review shows no violations and all SA levels covered."""
    return review["compliant"]
