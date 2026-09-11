"""
Element acceptance test baseline logic.
Anchor: ECSS-E-ST-10C §6.3, Tables 6-3/6-4 (paraphrased; no verbatim text).
stdlib only — no external dependencies.
"""
from __future__ import annotations

import math
from typing import NamedTuple

# ---------- Test type identifiers ----------
VIB_SINE = "vibration_sine"
VIB_RANDOM = "vibration_random"
THERMAL_CYCLING = "thermal_cycling"
THERMAL_VACUUM = "thermal_vacuum"
EMC = "emc"
FUNCTIONAL = "functional"
VISUAL = "visual_inspection"

VALID_TEST_TYPES: frozenset = frozenset({
    VIB_SINE, VIB_RANDOM, THERMAL_CYCLING, THERMAL_VACUUM, EMC, FUNCTIONAL, VISUAL,
})

# ---------- Acceptance level parameters ----------
# Random vibration: acceptance PSD = qual PSD × 10^(−3/10).
# In grms: acceptance_grms = qual_grms × sqrt(10^(−3/10)) ≈ 0.7079.
VIB_RANDOM_ACCEPTANCE_GRMS_FACTOR: float = math.sqrt(10.0 ** (-3.0 / 10.0))

# Sine vibration: acceptance amplitude = qual amplitude × 10^(−3/20) ≈ 0.7079.
VIB_SINE_ACCEPTANCE_G_FACTOR: float = 10.0 ** (-3.0 / 20.0)

# Thermal: acceptance range narrows by this value at each extreme (°C).
THERMAL_ACCEPTANCE_MARGIN_C: float = 5.0

# ---------- Minimum acceptance test durations (minutes) — Table 6-3 paraphrased ----------
MIN_DURATION_MIN: dict = {
    VIB_SINE:        4.0,    # 2 min/axis × 2 axes minimum
    VIB_RANDOM:      2.0,    # 1 min/axis × 2 axes minimum
    THERMAL_CYCLING: 480.0,  # 4 cycles at ~2 h each
    THERMAL_VACUUM:  1440.0, # 24 h soak minimum
    EMC:             60.0,
    FUNCTIONAL:      30.0,
    VISUAL:          15.0,
}

# ---------- Mandatory tests by element category — Table 6-4 paraphrased ----------
MANDATORY_TESTS: dict = {
    "simple": frozenset({VISUAL, FUNCTIONAL}),
    "standard": frozenset({VISUAL, FUNCTIONAL, VIB_RANDOM, THERMAL_CYCLING}),
    "critical": frozenset({
        VISUAL, FUNCTIONAL, VIB_SINE, VIB_RANDOM,
        THERMAL_CYCLING, THERMAL_VACUUM, EMC,
    }),
}

VALID_CATEGORIES: frozenset = frozenset(MANDATORY_TESTS.keys())


# ---------- Level derivation ----------

def derive_vibration_random_acceptance_grms(qual_grms: float) -> float:
    """Return the acceptance overall grms level (−3 dB PSD from qualification)."""
    if qual_grms <= 0.0:
        raise ValueError(f"qual_grms must be positive; got {qual_grms!r}")
    return qual_grms * VIB_RANDOM_ACCEPTANCE_GRMS_FACTOR


def derive_vibration_sine_acceptance_g(qual_g: float) -> float:
    """Return the acceptance sine amplitude (−3 dB amplitude from qualification)."""
    if qual_g <= 0.0:
        raise ValueError(f"qual_g must be positive; got {qual_g!r}")
    return qual_g * VIB_SINE_ACCEPTANCE_G_FACTOR


def derive_thermal_acceptance_range(
    qual_high_c: float,
    qual_low_c: float,
) -> tuple:
    """
    Return (acceptance_high_c, acceptance_low_c) by applying THERMAL_ACCEPTANCE_MARGIN_C
    at each extreme of the qualification temperature range.
    Raises ValueError if the qualification range is inverted or too narrow.
    """
    if qual_high_c <= qual_low_c:
        raise ValueError(
            f"qual_high_c ({qual_high_c}) must exceed qual_low_c ({qual_low_c})"
        )
    acc_high = qual_high_c - THERMAL_ACCEPTANCE_MARGIN_C
    acc_low = qual_low_c + THERMAL_ACCEPTANCE_MARGIN_C
    if acc_high <= acc_low:
        raise ValueError(
            f"Degenerate acceptance range after applying {THERMAL_ACCEPTANCE_MARGIN_C} °C margin "
            f"to qualification range [{qual_low_c}, {qual_high_c}]; "
            f"widen the qualification range before planning acceptance thermal tests."
        )
    return acc_high, acc_low


# ---------- Duration check ----------

class DurationResult(NamedTuple):
    test_type: str
    duration_min: float
    minimum_required_min: float
    passes: bool
    shortfall_min: float


def check_test_duration(test_type: str, duration_min: float) -> DurationResult:
    """
    Check that a test's declared duration meets the Table 6-3 minimum.
    Returns a DurationResult; shortfall_min is 0.0 when passes is True.
    """
    if test_type not in VALID_TEST_TYPES:
        raise ValueError(
            f"Unknown test type: {test_type!r}. "
            f"Valid types: {sorted(VALID_TEST_TYPES)}"
        )
    if duration_min < 0.0:
        raise ValueError(f"duration_min must be non-negative; got {duration_min!r}")
    minimum = MIN_DURATION_MIN[test_type]
    passes = duration_min >= minimum
    shortfall = max(0.0, minimum - duration_min)
    return DurationResult(
        test_type=test_type,
        duration_min=duration_min,
        minimum_required_min=minimum,
        passes=passes,
        shortfall_min=shortfall,
    )


# ---------- Baseline completeness ----------

class BaselineResult(NamedTuple):
    element_category: str
    proposed_tests: frozenset
    mandatory_tests: frozenset
    missing_tests: frozenset
    extra_tests: frozenset
    baseline_complete: bool


def check_test_baseline(
    element_category: str,
    proposed_tests: set,
) -> BaselineResult:
    """
    Verify that proposed_tests covers all mandatory tests for the element category.
    Tests beyond the mandatory set are permitted (extra_tests) but do not compensate
    for missing mandatory ones.
    Raises ValueError for an unknown category or unknown test type in proposed_tests.
    """
    if element_category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown element category: {element_category!r}. "
            f"Valid categories: {sorted(VALID_CATEGORIES)}"
        )
    proposed = frozenset(proposed_tests)
    unknown = proposed - VALID_TEST_TYPES
    if unknown:
        raise ValueError(
            f"Unrecognised test types in proposed set: {sorted(unknown)}"
        )
    mandatory = MANDATORY_TESTS[element_category]
    missing = mandatory - proposed
    extra = proposed - mandatory
    return BaselineResult(
        element_category=element_category,
        proposed_tests=proposed,
        mandatory_tests=mandatory,
        missing_tests=missing,
        extra_tests=extra,
        baseline_complete=len(missing) == 0,
    )


# ---------- Full plan entry ----------

class TestPlanEntry:
    """A single entry in an element acceptance test plan."""

    __slots__ = ("test_type", "duration_min")

    def __init__(self, test_type: str, duration_min: float) -> None:
        if test_type not in VALID_TEST_TYPES:
            raise ValueError(f"Unknown test type: {test_type!r}")
        if duration_min < 0.0:
            raise ValueError(f"duration_min must be non-negative; got {duration_min!r}")
        self.test_type = test_type
        self.duration_min = duration_min

    def __repr__(self) -> str:
        return f"TestPlanEntry({self.test_type!r}, {self.duration_min} min)"


# ---------- Full plan validation ----------

class PlanValidationResult(NamedTuple):
    element_category: str
    baseline_complete: bool
    missing_tests: frozenset
    duration_failures: list   # list[DurationResult] where not passes
    all_durations_pass: bool
    plan_accepted: bool       # True only when baseline complete AND all durations pass


def validate_acceptance_plan(
    element_category: str,
    plan_entries: list,
) -> PlanValidationResult:
    """
    Full acceptance plan validation combining baseline completeness (§6.3 Table 6-4)
    and minimum duration compliance (Table 6-3).

    plan_entries: sequence of TestPlanEntry objects.
    Returns PlanValidationResult; plan_accepted is True only when both checks pass.
    """
    proposed_types = {e.test_type for e in plan_entries}
    baseline = check_test_baseline(element_category, proposed_types)

    duration_results = [
        check_test_duration(entry.test_type, entry.duration_min)
        for entry in plan_entries
    ]
    duration_failures = [r for r in duration_results if not r.passes]
    all_durations_pass = len(duration_failures) == 0

    return PlanValidationResult(
        element_category=element_category,
        baseline_complete=baseline.baseline_complete,
        missing_tests=baseline.missing_tests,
        duration_failures=duration_failures,
        all_durations_pass=all_durations_pass,
        plan_accepted=baseline.baseline_complete and all_durations_pass,
    )
