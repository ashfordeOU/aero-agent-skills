"""Component quality level and test coverage across the reliability classes.

Anchor: ECSS-Q-ST-60C clause 7, Tables 7-1 to 7-3 (the quality level each
component family has to reach, and the testing that level carries, for each
of the three reliability classes). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Map a component family and the project reliability class onto the quality
   level the family has to reach. The three tables are one lookup with the
   class as its second index, which is why a family that is demanding in
   class 1 can still be ordinary in class 3.
2. Build the test coverage that level demands: a cumulative baseline, where
   each level inherits everything the level below it requires and adds its
   own, plus the tests the family carries on its own account.
3. Decide whether a family test rides on the level or on the family. A few
   tests answer a failure mode the part has whatever it is bought to, and
   those are required at every level; the rest fall away at the lowest level.
4. Compare the stringency of a proposed part's level against the level
   required. Stringency is an ordinal, not the level number, because the
   level numbers run the other way.
5. Report the shortfall as the tests that are missing and as a coverage
   fraction, and return a verdict: the part meets the level, the part can be
   uprated by adding the missing tests, or the part cannot be used.
"""

import math

__all__ = [
    "RELIABILITY_CLASSES",
    "QUALITY_LEVELS",
    "LEVEL_STRINGENCY",
    "QUALITY_LEVEL_TABLE",
    "LEVEL_BASELINE_TESTS",
    "FAMILY_TESTS",
    "LEVEL_INDEPENDENT_FAMILY_TESTS",
    "MAX_UPRATING_STEPS",
    "SUBSTANTIAL_COVERAGE_FLOOR",
    "COVERAGE_TOLERANCE",
    "VERDICTS",
    "normalize_token",
    "validate_reliability_class",
    "validate_family",
    "validate_quality_level",
    "level_stringency",
    "required_quality_level",
    "baseline_tests_for_level",
    "family_tests_for_level",
    "required_test_coverage",
    "coverage_fraction",
    "missing_tests",
    "uprating_steps",
    "assess_proposed_part",
]

# The project reliability classes the three tables are indexed by.
RELIABILITY_CLASSES = (1, 2, 3)

# Quality levels, most demanding first.
QUALITY_LEVELS = ("level-1", "level-2", "level-3")

# Stringency runs the opposite way to the level number, so comparisons are
# made on this ordinal and never on the digit in the name.
LEVEL_STRINGENCY = {"level-1": 3, "level-2": 2, "level-3": 1}

# Tables 7-1 to 7-3 read as one lookup: family, then reliability class.
QUALITY_LEVEL_TABLE = {
    "microcircuit": {1: "level-1", 2: "level-2", 3: "level-3"},
    "discrete-semiconductor": {1: "level-1", 2: "level-2", 3: "level-3"},
    "ceramic-capacitor": {1: "level-1", 2: "level-2", 3: "level-3"},
    "tantalum-capacitor": {1: "level-1", 2: "level-2", 3: "level-3"},
    "film-capacitor": {1: "level-2", 2: "level-2", 3: "level-3"},
    "resistor": {1: "level-1", 2: "level-2", 3: "level-3"},
    "magnetic-component": {1: "level-2", 2: "level-2", 3: "level-3"},
    "relay": {1: "level-1", 2: "level-2", 3: "level-3"},
    "connector": {1: "level-2", 2: "level-2", 3: "level-3"},
    "crystal-oscillator": {1: "level-2", 2: "level-2", 3: "level-3"},
    "fuse": {1: "level-2", 2: "level-3", 3: "level-3"},
    "wire-and-cable": {1: "level-2", 2: "level-3", 3: "level-3"},
}

# What each level adds on its own account. The baseline is cumulative: a
# level inherits everything every less demanding level requires.
LEVEL_BASELINE_TESTS = {
    "level-3": frozenset({"lot-acceptance-electrical-test"}),
    "level-2": frozenset(
        {"lot-validation-testing", "component-destructive-physical-analysis"}
    ),
    "level-1": frozenset(
        {
            "full-lot-date-code-traceability-verification",
            "component-radiation-verification-testing",
        }
    ),
}

# Tests a family carries for its own failure modes, on top of the baseline.
FAMILY_TESTS = {
    "microcircuit": frozenset(
        {"microcircuit-burn-in", "microcircuit-particle-impact-noise-detection"}
    ),
    "discrete-semiconductor": frozenset({"discrete-semiconductor-burn-in"}),
    "ceramic-capacitor": frozenset({"ceramic-capacitor-voltage-conditioning"}),
    "tantalum-capacitor": frozenset({"tantalum-capacitor-surge-current-test"}),
    "film-capacitor": frozenset(),
    "resistor": frozenset({"resistor-power-conditioning"}),
    "magnetic-component": frozenset({"magnetic-component-insulation-test"}),
    "relay": frozenset({"relay-contact-endurance-test"}),
    "connector": frozenset({"connector-mating-endurance-test"}),
    "crystal-oscillator": frozenset({"crystal-oscillator-frequency-ageing-test"}),
    "fuse": frozenset({"fuse-current-interruption-test"}),
    "wire-and-cable": frozenset({"wire-and-cable-insulation-flaw-test"}),
}

# A few family tests answer a failure mode the part has however it is bought,
# so they survive even at the least demanding level.
LEVEL_INDEPENDENT_FAMILY_TESTS = frozenset(
    {"tantalum-capacitor-surge-current-test", "fuse-current-interruption-test"}
)

# A part may be uprated across one stringency step, never two.
MAX_UPRATING_STEPS = 1

# Below this share of the required tests an uprating is not a top-up.
SUBSTANTIAL_COVERAGE_FLOOR = 0.5

# The coverage fraction is a quotient of counts; a part sitting exactly on
# the floor must not be failed on representation alone.
COVERAGE_TOLERANCE = 1e-9

VERDICTS = ("meets-required-level", "uprating-required", "not-acceptable")


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _flag(value, label):
    """Return a strict boolean flag."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_reliability_class(value):
    """Return the project reliability class as one of the three table indices."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("reliability_class must be a whole number, got %r" % (value,))
    if value not in RELIABILITY_CLASSES:
        raise ValueError(
            "reliability_class must be one of %s, got %r"
            % (", ".join(str(c) for c in RELIABILITY_CLASSES), value)
        )
    return value


def validate_family(value):
    """Return a recognized component family token."""
    token = normalize_token(value, "family")
    if token not in QUALITY_LEVEL_TABLE:
        raise ValueError(
            "family '%s' is not in the quality level tables; expected one of %s"
            % (token, ", ".join(sorted(QUALITY_LEVEL_TABLE)))
        )
    return token


def validate_quality_level(value):
    """Return a recognized quality level token."""
    token = normalize_token(value, "quality_level")
    if token not in LEVEL_STRINGENCY:
        raise ValueError(
            "quality_level '%s' is not recognized; expected one of %s"
            % (token, ", ".join(QUALITY_LEVELS))
        )
    return token


def level_stringency(level):
    """Return how demanding a level is, as an ordinal that rises with rigour."""
    return LEVEL_STRINGENCY[validate_quality_level(level)]


def required_quality_level(family, reliability_class):
    """Return the quality level a family has to reach in a reliability class."""
    token = validate_family(family)
    rel_class = validate_reliability_class(reliability_class)
    return QUALITY_LEVEL_TABLE[token][rel_class]


def baseline_tests_for_level(level):
    """Return the cumulative baseline coverage a level carries."""
    token = validate_quality_level(level)
    target = LEVEL_STRINGENCY[token]
    covered = set()
    for name, stringency in LEVEL_STRINGENCY.items():
        if stringency <= target:
            covered |= set(LEVEL_BASELINE_TESTS[name])
    return covered


def family_tests_for_level(family, level):
    """Return the family's own tests that survive at a given level.

    At the least demanding level only the tests answering a failure mode the
    part has whatever it is bought to remain.
    """
    token = validate_family(family)
    level_token = validate_quality_level(level)
    tests = set(FAMILY_TESTS[token])
    if LEVEL_STRINGENCY[level_token] <= LEVEL_STRINGENCY["level-3"]:
        tests &= set(LEVEL_INDEPENDENT_FAMILY_TESTS)
    return tests


def required_test_coverage(family, reliability_class):
    """Return the tests a family has to carry in a reliability class, sorted."""
    level = required_quality_level(family, reliability_class)
    covered = baseline_tests_for_level(level) | family_tests_for_level(family, level)
    return sorted(covered)


def _validate_test_list(value, label):
    """Return a normalized, duplicate-free set of test tokens."""
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError("%s must be a list of test tokens" % label)
    tokens = set()
    for entry in value:
        token = normalize_token(entry, label)
        tokens.add(token)
    return tokens


def coverage_fraction(proposed_tests, required_tests):
    """Return the share of the required tests a proposal already carries."""
    proposed = _validate_test_list(proposed_tests, "proposed_tests")
    required = _validate_test_list(required_tests, "required_tests")
    if not required:
        raise ValueError("required_tests must not be empty")
    return len(proposed & required) / len(required)


def missing_tests(proposed_tests, required_tests):
    """Return the required tests a proposal does not yet carry, sorted."""
    proposed = _validate_test_list(proposed_tests, "proposed_tests")
    required = _validate_test_list(required_tests, "required_tests")
    return sorted(required - proposed)


def uprating_steps(proposed_level, required_level):
    """Return how many stringency steps a proposal sits below what is required.

    Zero means the proposal already meets or exceeds the level; a negative
    result is never returned.
    """
    proposed = level_stringency(proposed_level)
    required = level_stringency(required_level)
    return max(0, required - proposed)


def _at_or_above(value, floor):
    """Return whether a value meets a floor, tolerant at the boundary."""
    return value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )


def assess_proposed_part(part):
    """Judge one proposed part against its family's clause 7 quality level.

    part keys: part_number, family, reliability_class, proposed_quality_level,
    tests_performed, and optionally uprating_permitted.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in (
        "part_number",
        "family",
        "reliability_class",
        "proposed_quality_level",
        "tests_performed",
    ):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)

    part_number = _require_text(part["part_number"], "part_number")
    family = validate_family(part["family"])
    rel_class = validate_reliability_class(part["reliability_class"])
    proposed_level = validate_quality_level(part["proposed_quality_level"])
    permitted = _flag(part.get("uprating_permitted", True), "uprating_permitted")

    required_level = required_quality_level(family, rel_class)
    required = required_test_coverage(family, rel_class)
    performed = _validate_test_list(part["tests_performed"], "tests_performed")
    gap = missing_tests(performed, required)
    fraction = coverage_fraction(performed, required)
    steps = uprating_steps(proposed_level, required_level)

    if steps == 0 and not gap:
        verdict = "meets-required-level"
    elif (
        permitted
        and steps <= MAX_UPRATING_STEPS
        and _at_or_above(fraction, SUBSTANTIAL_COVERAGE_FLOOR)
    ):
        verdict = "uprating-required"
    else:
        verdict = "not-acceptable"

    findings = []
    if steps > 0:
        findings.append(
            "part '%s' is offered at %s where class %d needs %s for a %s"
            % (part_number, proposed_level, rel_class, required_level, family)
        )
    if gap:
        findings.append(
            "part '%s' is short of %d of the %d tests its level requires"
            % (part_number, len(gap), len(required))
        )
    if steps > MAX_UPRATING_STEPS:
        findings.append(
            "part '%s' sits %d stringency steps below the level required, "
            "beyond what an uprating can close" % (part_number, steps)
        )
    if not permitted and steps > 0:
        findings.append(
            "uprating is not permitted for part '%s' on this project"
            % part_number
        )
    if not _at_or_above(fraction, SUBSTANTIAL_COVERAGE_FLOOR):
        findings.append(
            "part '%s' carries %.3f of the required coverage, below the %.2f "
            "an uprating can build on" % (part_number, fraction, SUBSTANTIAL_COVERAGE_FLOOR)
        )

    return {
        "part_number": part_number,
        "family": family,
        "reliability_class": rel_class,
        "proposed_quality_level": proposed_level,
        "required_quality_level": required_level,
        "uprating_steps": steps,
        "uprating_permitted": permitted,
        "required_tests": required,
        "tests_performed": sorted(performed),
        "missing_tests": gap,
        "coverage_fraction": fraction,
        "verdict": verdict,
        "usable_as_proposed": verdict == "meets-required-level",
        "findings": findings,
    }
