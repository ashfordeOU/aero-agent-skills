#!/usr/bin/env python3
"""Acceptance thermal-cycle exposure of photovoltaic-assembly coupons.

Anchor: ECSS-E-ST-20-08C Rev.2 clause 5.5.3.7.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The acceptance cycling of a coupon set differs from the qualification
campaign in where its cycle count comes from. A qualification count is
derived from the mission: eclipse rate, duration, a qualification factor.
An acceptance count is not derived at all. It is *looked up* in the
testing standard the assembly documentation references, against the
category of coupon being exposed, and the only legitimate job of the
project is to name that reference and read the number out of it.

That makes three things go wrong in practice, and all three are decided
here:

    substitution   a count invented locally, or copied from a previous
                   programme, that sits below the referenced one; the
                   lot is then accepted on an exposure it never had
    silent overtest a count above the referenced one, which is not a
                   failure but is a schedule and a life cost that has to
                   surface rather than hide in a chamber log
    lost cycles    an interruption -- a chamber excursion out of profile,
                   a power loss, a coupon removed and re-installed --
                   invalidates the cycles run since the last valid
                   checkpoint, so cycles *run* and cycles *credited* are
                   different numbers and only the second one counts

The catalogue of referenced standards and the counts they define is a
declared project policy below, not a physical constant: a programme
substitutes the references its own assembly documentation names.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COUPON_CATEGORIES = (
    "cell-stack",
    "interconnect",
    "substrate-bond",
    "harness-termination",
)

DEFAULT_ACCEPTANCE_POLICY = {
    # Referenced testing standard key -> acceptance cycles it defines for
    # each coupon category. Declared policy; a project substitutes its own.
    "referenced_standard_cycles": {
        "coupon-cycling-baseline": {
            "cell-stack": 200,
            "interconnect": 200,
            "substrate-bond": 100,
            "harness-termination": 50,
        },
        "coupon-cycling-extended": {
            "cell-stack": 500,
            "interconnect": 500,
            "substrate-bond": 300,
            "harness-termination": 150,
        },
        "coupon-cycling-reduced": {
            "cell-stack": 100,
            "interconnect": 100,
            "substrate-bond": 50,
            "harness-termination": 25,
        },
    },
    "minimum_coupons_per_category": 2,
    "maximum_interruptions": 2,
    "overtest_finding_fraction": 0.10,
}

EXPOSURE_COMPLETE = "acceptance-cycling-complete"
EXPOSURE_SHORT = "acceptance-cycling-short"
EXPOSURE_NOT_RUN = "acceptance-cycling-not-run"

COUPON_EXPOSED = "coupon-exposed"
COUPON_SHORT = "coupon-short"
COUPON_INVALID = "coupon-invalid"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_int(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_acceptance_policy(policy):
    """Check the referenced-standard catalogue is complete and sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    catalogue = policy.get("referenced_standard_cycles")
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("policy referenced_standard_cycles must be a non-empty mapping")
    for standard_key, counts in catalogue.items():
        _require_text("referenced standard key", standard_key)
        if not isinstance(counts, dict):
            raise ValueError(
                "referenced_standard_cycles[%s] must be a mapping" % (standard_key,)
            )
        missing = set(COUPON_CATEGORIES) - set(counts)
        if missing:
            raise ValueError(
                "referenced_standard_cycles[%s] is missing coupon categories: %s"
                % (standard_key, ", ".join(sorted(missing)))
            )
        for category in COUPON_CATEGORIES:
            _require_int(
                "referenced_standard_cycles[%s][%s]" % (standard_key, category),
                counts[category],
                minimum=1,
            )
    _require_int(
        "minimum_coupons_per_category",
        policy.get("minimum_coupons_per_category"),
        minimum=1,
    )
    _require_int("maximum_interruptions", policy.get("maximum_interruptions"), minimum=0)
    _require_non_negative(
        "overtest_finding_fraction", policy.get("overtest_finding_fraction")
    )
    return policy


def referenced_cycle_count(standard_key, coupon_category, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Acceptance cycles the referenced testing standard defines."""
    validate_acceptance_policy(policy)
    key = _require_text("standard_key", standard_key)
    category = _require_choice("coupon_category", coupon_category, COUPON_CATEGORIES)
    catalogue = policy["referenced_standard_cycles"]
    if key not in catalogue:
        raise ValueError(
            "standard_key %r is not in the referenced-standard catalogue; name a "
            "reference the assembly documentation actually cites" % (key,)
        )
    return int(catalogue[key][category])


def reconcile_declared_count(
    standard_key,
    coupon_category,
    declared_count,
    policy=DEFAULT_ACCEPTANCE_POLICY,
):
    """Compare a locally declared cycle count with the referenced one."""
    required = referenced_cycle_count(standard_key, coupon_category, policy)
    declared = _require_int("declared_count", declared_count, minimum=1)
    if declared < required:
        raise ValueError(
            "declared_count %d is below the %d cycles the referenced standard %r "
            "defines for a %s coupon; the reference sets the count, not the "
            "programme" % (declared, required, standard_key, coupon_category)
        )
    findings = []
    overtest = declared - required
    fraction = float(policy["overtest_finding_fraction"])
    if overtest > 0 and not _at_most(float(overtest), fraction * required):
        findings.append(
            "declared count %d exceeds the referenced %d by %d cycles, beyond the "
            "recorded overtest allowance" % (declared, required, overtest)
        )
    elif overtest > 0:
        findings.append(
            "declared count %d runs %d cycles of overtest against the referenced %d"
            % (declared, overtest, required)
        )
    return {
        "standard_key": standard_key,
        "coupon_category": coupon_category,
        "required_cycles": required,
        "declared_cycles": declared,
        "overtest_cycles": overtest,
        "findings": findings,
    }


def credited_cycles(record, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Cycles a coupon may count, after interruptions take theirs back."""
    validate_acceptance_policy(policy)
    if not isinstance(record, dict):
        raise ValueError("coupon record must be a mapping, got %r" % (record,))
    coupon_id = _require_text("coupon_id", record.get("coupon_id"))
    run = _require_int("cycles_run", record.get("cycles_run"), minimum=0)
    interruptions = record.get("interruptions", ())
    if not isinstance(interruptions, (list, tuple)):
        raise ValueError(
            "coupon %s interruptions must be a list of records" % (coupon_id,)
        )
    invalidated = 0
    for index, event in enumerate(interruptions, 1):
        if not isinstance(event, dict):
            raise ValueError(
                "coupon %s interruption %d must be a mapping" % (coupon_id, index)
            )
        at_cycle = _require_int(
            "coupon %s interruption %d at_cycle" % (coupon_id, index),
            event.get("at_cycle"),
            minimum=1,
        )
        if at_cycle > run:
            raise ValueError(
                "coupon %s interruption %d is logged at cycle %d but only %d "
                "cycles were run" % (coupon_id, index, at_cycle, run)
            )
        lost = _require_int(
            "coupon %s interruption %d cycles_invalidated" % (coupon_id, index),
            event.get("cycles_invalidated"),
            minimum=0,
        )
        if lost > at_cycle:
            raise ValueError(
                "coupon %s interruption %d invalidates %d cycles at cycle %d; an "
                "interruption cannot take back cycles that were never run"
                % (coupon_id, index, lost, at_cycle)
            )
        invalidated += lost
    if invalidated > run:
        raise ValueError(
            "coupon %s has %d invalidated cycles against %d run" % (coupon_id, invalidated, run)
        )
    return {
        "coupon_id": coupon_id,
        "cycles_run": run,
        "cycles_invalidated": invalidated,
        "cycles_credited": run - invalidated,
        "interruption_count": len(interruptions),
    }


def grade_coupon_exposure(record, required_cycles, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Decide whether one coupon has actually taken its acceptance cycles."""
    required = _require_int("required_cycles", required_cycles, minimum=1)
    tally = credited_cycles(record, policy)
    findings = []
    verdict = COUPON_EXPOSED
    if tally["interruption_count"] > int(policy["maximum_interruptions"]):
        verdict = COUPON_INVALID
        findings.append(
            "coupon %s took %d interruptions against an allowance of %d; the "
            "exposure is not representative and the coupon is re-run"
            % (
                tally["coupon_id"],
                tally["interruption_count"],
                policy["maximum_interruptions"],
            )
        )
    elif tally["cycles_credited"] < required:
        verdict = COUPON_SHORT
        findings.append(
            "coupon %s credited %d of %d cycles"
            % (tally["coupon_id"], tally["cycles_credited"], required)
        )
    if tally["cycles_invalidated"] > 0 and verdict == COUPON_EXPOSED:
        findings.append(
            "coupon %s lost %d cycles to interruptions and still met the count"
            % (tally["coupon_id"], tally["cycles_invalidated"])
        )
    result = dict(tally)
    result.update(
        {
            "required_cycles": required,
            "completion_fraction": tally["cycles_credited"] / float(required),
            "verdict": verdict,
            "findings": findings,
        }
    )
    return result


def assess_acceptance_cycling(case, policy=DEFAULT_ACCEPTANCE_POLICY):
    """Full clause 5.5.3.7.3 exposure assessment for a coupon set."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_acceptance_policy(policy)
    standard_key = _require_text("standard_key", case.get("standard_key"))
    category = _require_choice(
        "coupon_category", case.get("coupon_category"), COUPON_CATEGORIES
    )
    declared = case.get("declared_cycles")
    if declared is None:
        required = referenced_cycle_count(standard_key, category, policy)
        reconciliation = {
            "standard_key": standard_key,
            "coupon_category": category,
            "required_cycles": required,
            "declared_cycles": required,
            "overtest_cycles": 0,
            "findings": [],
        }
    else:
        reconciliation = reconcile_declared_count(
            standard_key, category, declared, policy
        )
        required = reconciliation["declared_cycles"]
    findings = list(reconciliation["findings"])
    coupons = case.get("coupons")
    if coupons is None:
        findings.append(
            "no coupon exposure records supplied; the required count is resolved "
            "but no coupon has been exposed"
        )
        return {
            "standard_key": standard_key,
            "coupon_category": category,
            "referenced_cycles": reconciliation["required_cycles"],
            "required_cycles": required,
            "overtest_cycles": reconciliation["overtest_cycles"],
            "coupons": [],
            "coupons_exposed": 0,
            "verdict": EXPOSURE_NOT_RUN,
            "findings": findings,
        }
    if not isinstance(coupons, (list, tuple)):
        raise ValueError("case coupons must be a list of coupon records")
    graded = [grade_coupon_exposure(record, required, policy) for record in coupons]
    seen = set()
    for entry in graded:
        if entry["coupon_id"] in seen:
            raise ValueError(
                "coupon_id %r appears twice in the set" % (entry["coupon_id"],)
            )
        seen.add(entry["coupon_id"])
        findings.extend(entry["findings"])
    exposed = sum(1 for entry in graded if entry["verdict"] == COUPON_EXPOSED)
    minimum = int(policy["minimum_coupons_per_category"])
    if len(graded) < minimum:
        findings.append(
            "%d coupons submitted for category %s against a minimum of %d"
            % (len(graded), category, minimum)
        )
    complete = exposed >= minimum and exposed == len(graded)
    return {
        "standard_key": standard_key,
        "coupon_category": category,
        "referenced_cycles": reconciliation["required_cycles"],
        "required_cycles": required,
        "overtest_cycles": reconciliation["overtest_cycles"],
        "coupons": graded,
        "coupons_exposed": exposed,
        "verdict": EXPOSURE_COMPLETE if complete else EXPOSURE_SHORT,
        "findings": findings,
    }
