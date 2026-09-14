#!/usr/bin/env python3
"""Which coverglass tests carry qualification, and which carry a lot.

Anchor: ECSS-E-ST-20-08C clause 8.3.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The coverglass test set is not one programme but two, and the clause's
job is to keep them apart:

    qualification   run once on a design and a process, often long and
                    often destructive, to show the article survives the
                    environment at all
    procurement     run again on every lot delivered, short and
                    non-destructive, to show this lot is the article
                    that was qualified

Some tests serve both, some serve only one. A test booked under a role
it cannot serve produces paperwork rather than evidence: an irradiation
endurance run cannot be a routine incoming check, and an incoming
identity check proves nothing about whether the design survives.

Each declared coating drags its own test in, and a destructive test
placed in the procurement programme has to be drawn from an over-build,
because the specimens it consumes never reach the customer.

A test matrix is therefore read as a mapping from each test to the
programme or programmes it is booked to, because a dual-role test that
serves both is the normal case rather than an exception.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROGRAMMES = ("qualification", "procurement")
ROLES = ("qualification-only", "procurement-only", "both")

COATINGS = (
    "antireflective-coating",
    "conductive-coating",
    "uv-reflective-coating",
)

TEST_CATALOGUE = {
    "coverglass-visual-inspection": {
        "role": "both",
        "destructive": False,
        "mandatory_for": ("qualification", "procurement"),
    },
    "coverglass-dimensional-inspection": {
        "role": "both",
        "destructive": False,
        "mandatory_for": ("qualification", "procurement"),
    },
    "coverglass-spectral-transmittance": {
        "role": "both",
        "destructive": False,
        "mandatory_for": ("qualification", "procurement"),
    },
    "coverglass-coating-adhesion-test": {
        "role": "both",
        "destructive": True,
        "mandatory_for": ("qualification",),
    },
    "coverglass-surface-conductivity-measurement": {
        "role": "both",
        "destructive": False,
        "mandatory_for": (),
    },
    "coverglass-thermal-cycling-endurance": {
        "role": "qualification-only",
        "destructive": True,
        "mandatory_for": ("qualification",),
    },
    "coverglass-ultraviolet-irradiation-stability": {
        "role": "qualification-only",
        "destructive": True,
        "mandatory_for": ("qualification",),
    },
    "coverglass-particle-irradiation-stability": {
        "role": "qualification-only",
        "destructive": True,
        "mandatory_for": ("qualification",),
    },
    "coverglass-humidity-resistance": {
        "role": "qualification-only",
        "destructive": True,
        "mandatory_for": (),
    },
    "coverglass-incoming-batch-identity-check": {
        "role": "procurement-only",
        "destructive": False,
        "mandatory_for": ("procurement",),
    },
    "coverglass-lot-sample-verification": {
        "role": "procurement-only",
        "destructive": False,
        "mandatory_for": ("procurement",),
    },
}

COATING_DRIVEN_TESTS = {
    "antireflective-coating": ("coverglass-spectral-transmittance",),
    "conductive-coating": ("coverglass-surface-conductivity-measurement",),
    "uv-reflective-coating": ("coverglass-ultraviolet-irradiation-stability",),
}

ROLES_MISASSIGNED = "test-roles-misassigned"
MANDATORY_TESTS_MISSING = "mandatory-tests-missing"
ROLES_PARTIALLY_SEPARATED = "test-roles-partially-separated"
ROLES_SEPARATED = "test-roles-separated"

DEFAULT_TEST_POLICY = {
    "programme_weights": {"qualification": 0.5, "procurement": 0.5},
    "lot_sample_fraction": 0.02,
    "min_lot_sample": 5,
    "max_lot_sample": 50,
    "partial_index_floor": 0.6,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_fraction(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_sequence(name, value):
    if isinstance(value, (str, bytes)) or not isinstance(
        value, (list, tuple, set, frozenset)
    ):
        raise ValueError("%s must be a sequence of names, got %r" % (name, value))
    return tuple(value)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    The overview index is a weighted mean of ratios, so a case sitting
    exactly on the floor can land a few units in the last place below
    it. The floor is never lowered; only the comparison tolerates the
    representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_test_policy(policy):
    """Check a testing-overview policy carries usable weights and limits."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    weights = policy.get("programme_weights")
    if not isinstance(weights, dict):
        raise ValueError("policy programme_weights must be a mapping")
    missing = set(PROGRAMMES) - set(weights)
    if missing:
        raise ValueError(
            "policy programme_weights is missing: %s" % ", ".join(sorted(missing))
        )
    for programme in PROGRAMMES:
        _require_positive("policy programme_weights[%s]" % programme, weights[programme])
    _require_fraction("lot_sample_fraction", policy.get("lot_sample_fraction"))
    low = _require_count("min_lot_sample", policy.get("min_lot_sample"))
    high = _require_count("max_lot_sample", policy.get("max_lot_sample"))
    if high < low:
        raise ValueError("policy max_lot_sample must not be below min_lot_sample")
    _require_fraction("partial_index_floor", policy.get("partial_index_floor"))
    return policy


def test_role(test_id):
    """Role the catalogue gives a test, rejecting one nobody recognises."""
    if test_id not in TEST_CATALOGUE:
        raise ValueError(
            "test must be one of %s, got %r"
            % (", ".join(sorted(TEST_CATALOGUE)), test_id)
        )
    return TEST_CATALOGUE[test_id]["role"]


def is_destructive(test_id):
    """Whether running the test consumes the specimen."""
    if test_id not in TEST_CATALOGUE:
        raise ValueError("unrecognised test %r" % (test_id,))
    return bool(TEST_CATALOGUE[test_id]["destructive"])


def tests_permitted_in(programme):
    """Tests the catalogue allows a given programme to claim."""
    _require_choice("programme", programme, PROGRAMMES)
    only = "%s-only" % programme
    return tuple(
        sorted(
            test
            for test, entry in TEST_CATALOGUE.items()
            if entry["role"] in ("both", only)
        )
    )


def normalise_coatings(coatings):
    """Order and de-duplicate a declared coating stack, rejecting unknowns."""
    declared = _require_sequence("coatings", coatings)
    seen = []
    for coating in declared:
        if coating not in COATINGS:
            raise ValueError(
                "coating must be one of %s, got %r" % (", ".join(COATINGS), coating)
            )
        if coating not in seen:
            seen.append(coating)
    return tuple(sorted(seen, key=COATINGS.index))


def mandatory_tests(programme, coatings=()):
    """Tests a programme must carry, base set plus what the coatings drag in."""
    _require_choice("programme", programme, PROGRAMMES)
    stack = normalise_coatings(coatings)
    permitted = set(tests_permitted_in(programme))
    required = {
        test
        for test, entry in TEST_CATALOGUE.items()
        if programme in entry["mandatory_for"]
    }
    for coating in stack:
        for test in COATING_DRIVEN_TESTS[coating]:
            if test in permitted:
                required.add(test)
    return tuple(sorted(required & permitted))


def partition_tests(declared_tests):
    """Group a declared test set by the role the catalogue gives each test."""
    declared = _require_sequence("declared_tests", declared_tests)
    groups = {"qualification-only": [], "procurement-only": [], "both": []}
    for test in declared:
        groups[test_role(test)].append(test)
    return {role: tuple(sorted(set(tests))) for role, tests in groups.items()}


def declared_programmes(test, value):
    """Programmes one test is booked to, given as a name or a sequence."""
    role = test_role(test)
    if isinstance(value, str):
        candidates = (value,)
    else:
        candidates = _require_sequence("programmes for %s" % test, value)
    if not candidates:
        raise ValueError("%s is booked to no programme at all" % test)
    ordered = []
    for programme in candidates:
        _require_choice("programme for %s" % test, programme, PROGRAMMES)
        if programme not in ordered:
            ordered.append(programme)
    if role is None:
        raise ValueError("unrecognised test %r" % (test,))
    return tuple(sorted(ordered, key=PROGRAMMES.index))


def _require_assignments(assignments):
    if not isinstance(assignments, dict):
        raise ValueError("assignments must be a mapping of test to programme")
    return {test: declared_programmes(test, assignments[test]) for test in assignments}


def misassigned_tests(assignments):
    """Tests booked under a programme the catalogue does not let them serve."""
    booked = _require_assignments(assignments)
    findings = []
    for test in sorted(booked):
        role = test_role(test)
        for programme in booked[test]:
            if role != "both" and role != "%s-only" % programme:
                findings.append(
                    {
                        "test": test,
                        "declared_programme": programme,
                        "catalogue_role": role,
                        "reason": "%s is a %s test and cannot carry the %s programme"
                        % (test, role, programme),
                    }
                )
    return tuple(findings)


def programme_coverage(programme, assignments, coatings=()):
    """Grade one programme on the mandatory tests correctly booked to it."""
    _require_choice("programme", programme, PROGRAMMES)
    declared = _require_assignments(assignments)
    permitted = set(tests_permitted_in(programme))
    booked = {
        test
        for test, programmes in declared.items()
        if programme in programmes and test in permitted
    }
    required = mandatory_tests(programme, coatings)
    present = tuple(test for test in required if test in booked)
    missing = tuple(test for test in required if test not in booked)
    fraction = 1.0 if not required else float(len(present)) / float(len(required))
    return {
        "programme": programme,
        "required": required,
        "present": present,
        "missing": missing,
        "fraction": fraction,
    }


def sample_size(lot_size, policy=DEFAULT_TEST_POLICY):
    """Specimens one lot has to give up for a routine procurement draw."""
    validate_test_policy(policy)
    size = _require_count("lot_size", lot_size)
    drawn = math.ceil(float(policy["lot_sample_fraction"]) * size)
    drawn = max(drawn, int(policy["min_lot_sample"]))
    drawn = min(drawn, int(policy["max_lot_sample"]))
    return min(drawn, size)


def destructive_specimen_demand(assignments, lot_size, policy=DEFAULT_TEST_POLICY):
    """Over-build a lot needs because procurement tests consume specimens."""
    validate_test_policy(policy)
    declared = _require_assignments(assignments)
    per_test = sample_size(lot_size, policy)
    consuming = tuple(
        sorted(
            test
            for test, programmes in declared.items()
            if "procurement" in programmes and is_destructive(test)
        )
    )
    specimens = per_test * len(consuming)
    return {
        "sample_size": per_test,
        "destructive_tests": consuming,
        "specimens_consumed": specimens,
        "over_build_required": specimens > 0,
    }


def testing_overview_index(coverage_by_programme, policy=DEFAULT_TEST_POLICY):
    """Weighted mean of the two programmes' mandatory-test coverage."""
    validate_test_policy(policy)
    if not isinstance(coverage_by_programme, dict):
        raise ValueError("coverage_by_programme must be a mapping")
    weights = policy["programme_weights"]
    total = 0.0
    total_weight = 0.0
    for programme, coverage in coverage_by_programme.items():
        _require_choice("programme", programme, PROGRAMMES)
        fraction = _require_fraction("coverage fraction", coverage.get("fraction"))
        total += weights[programme] * fraction
        total_weight += weights[programme]
    if total_weight <= 0.0:
        raise ValueError("no programme carries weight; the index is undefined")
    return total / total_weight


def assess_testing_overview(case, policy=DEFAULT_TEST_POLICY):
    """Full clause 8.3.1 role separation with a programme verdict."""
    validate_test_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    assignments = case.get("assignments")
    _require_assignments(assignments)
    coatings = normalise_coatings(case.get("coatings", ()))
    lot_size = _require_count("lot_size", case.get("lot_size", 1))
    misassigned = misassigned_tests(assignments)
    grouped = partition_tests(tuple(assignments))
    coverage = {
        programme: programme_coverage(programme, assignments, coatings)
        for programme in PROGRAMMES
    }
    index = testing_overview_index(coverage, policy)
    demand = destructive_specimen_demand(assignments, lot_size, policy)
    findings = []
    for entry in misassigned:
        findings.append(entry["reason"])
    for programme in PROGRAMMES:
        if coverage[programme]["missing"]:
            findings.append(
                "the %s programme is missing %s"
                % (programme, ", ".join(coverage[programme]["missing"]))
            )
    if demand["over_build_required"]:
        findings.append(
            "%d specimen(s) are consumed by %s in the procurement programme, so the "
            "lot has to be over-built by that many"
            % (demand["specimens_consumed"], ", ".join(demand["destructive_tests"]))
        )
    any_missing = any(coverage[p]["missing"] for p in PROGRAMMES)
    if misassigned:
        verdict = ROLES_MISASSIGNED
    elif not any_missing:
        verdict = ROLES_SEPARATED
    elif _at_least(index, policy["partial_index_floor"]):
        verdict = ROLES_PARTIALLY_SEPARATED
    else:
        verdict = MANDATORY_TESTS_MISSING
    return {
        "verdict": verdict,
        "grouped_tests": grouped,
        "coverage": coverage,
        "overview_index": index,
        "misassigned": misassigned,
        "specimen_demand": demand,
        "coatings": coatings,
        "findings": findings,
    }
