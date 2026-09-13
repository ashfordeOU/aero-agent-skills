#!/usr/bin/env python3
"""Process validation of a photovoltaic assembly before production.

Anchor: ECSS-E-ST-20-08C clause 5.4.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Before a photovoltaic assembly goes into production, the manufacturing
and integration processes have to be validated against every design
configuration the project actually builds -- not against a
representative one. A panel programme rarely has a single configuration:
edge strings differ from field strings, a thicker coverglass appears
over the outer rows, a second substrate construction covers the yoke
panel. Each of those is its own configuration, and a validation run
covers it only when the run was carried out on the same governing
attributes.

Governing attributes
    cell-assembly-type      the cell and its assembly build
    interconnect-design     the interconnect geometry and material
    substrate-construction  the panel substrate the assembly lands on
    bonding-adhesive        the adhesive system used to attach it
    layout-edge-condition   field, edge or cut-out layout condition
    coverglass-thickness-um a numeric attribute, so a run validates a
                            range rather than a single value

A run also has to be admissible before it can validate anything: it has
to have passed, to have carried enough coupons, to be inside its
validity window, and not to have been superseded by a later process
change. What is left over is the work the project still owes, and
configurations that share a governing signature can be closed by a
single run -- that is the cheapest honest plan.

The validity window, the coupon minimum and the release rule are a
declared project policy, not physical constants; a project may
substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CATEGORICAL_ATTRIBUTES = (
    "cell-assembly-type",
    "interconnect-design",
    "substrate-construction",
    "bonding-adhesive",
    "layout-edge-condition",
)

NUMERIC_ATTRIBUTES = ("coverglass-thickness-um",)

GOVERNING_ATTRIBUTES = CATEGORICAL_ATTRIBUTES + NUMERIC_ATTRIBUTES

RUN_OUTCOMES = ("passed", "failed")

CURRENT = "current"
EXPIRED_BY_AGE = "expired-by-age"
SUPERSEDED_BY_PROCESS_CHANGE = "superseded-by-process-change"

PRODUCTION_RELEASE_PERMITTED = "production-release-permitted"
PRODUCTION_RELEASE_WITHHELD = "production-release-withheld"

DEFAULT_PROCESS_POLICY = {
    "max_validity_days": 365,
    "min_validation_coupons": 3,
    "require_current_validation": True,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("%s must be a non-negative integer, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_mapping(name, value):
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, value))
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverglass thickness that sits exactly on the edge of a validated
    range can land a few units in the last place outside it once it has
    been through a unit conversion. The range is never widened; only the
    comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_process_policy(policy):
    """Check a release policy carries sane numbers before it is used."""
    _require_mapping("policy", policy)
    days = _require_count("max_validity_days", policy.get("max_validity_days"))
    if days == 0:
        raise ValueError("max_validity_days must be greater than zero")
    coupons = _require_count(
        "min_validation_coupons", policy.get("min_validation_coupons")
    )
    if coupons == 0:
        raise ValueError("min_validation_coupons must be greater than zero")
    if not isinstance(policy.get("require_current_validation"), bool):
        raise ValueError("require_current_validation must be a boolean")
    return policy


def configuration_signature(configuration):
    """Governing-attribute signature used to group configurations.

    Two configurations with the same signature can be closed by one
    validation run, so the signature is what the outstanding-run plan is
    built on.
    """
    _require_mapping("configuration", configuration)
    missing = [
        attribute
        for attribute in GOVERNING_ATTRIBUTES
        if attribute not in configuration
    ]
    if missing:
        raise ValueError(
            "configuration must declare every governing attribute; missing: %s"
            % ", ".join(sorted(missing))
        )
    for attribute in NUMERIC_ATTRIBUTES:
        _require_positive(attribute, configuration[attribute])
    return tuple(
        (attribute, configuration[attribute]) for attribute in GOVERNING_ATTRIBUTES
    )


def run_covers_configuration(run, configuration):
    """Does one validation run speak for this design configuration."""
    _require_mapping("run", run)
    configuration_signature(configuration)
    mismatched = []
    for attribute in CATEGORICAL_ATTRIBUTES:
        if attribute not in run:
            raise ValueError("run must declare %s" % attribute)
        if run[attribute] != configuration[attribute]:
            mismatched.append(attribute)
    for attribute in NUMERIC_ATTRIBUTES:
        window = run.get(attribute)
        if not isinstance(window, dict) or "min" not in window or "max" not in window:
            raise ValueError(
                "run must declare %s as a validated range with min and max" % attribute
            )
        low = _require_positive("%s min" % attribute, window["min"])
        high = _require_positive("%s max" % attribute, window["max"])
        if high < low:
            raise ValueError("run %s range is inverted" % attribute)
        value = float(configuration[attribute])
        if not (_at_least(value, low) and _at_most(value, high)):
            mismatched.append(attribute)
    findings = []
    if mismatched:
        findings.append(
            "run %r does not speak for configuration %r on: %s"
            % (run.get("id"), configuration.get("id"), ", ".join(mismatched))
        )
    return {
        "covers": not mismatched,
        "mismatched_attributes": mismatched,
        "findings": findings,
    }


def validation_currency(run, process_change_index, policy=DEFAULT_PROCESS_POLICY):
    """Is a run still speaking for the process as it stands today."""
    validate_process_policy(policy)
    _require_mapping("run", run)
    age = _require_count("age_days", run.get("age_days"))
    run_index = _require_count("process_change_index", run.get("process_change_index"))
    current_index = _require_count("process_change_index", process_change_index)
    if run_index > current_index:
        raise ValueError(
            "run process_change_index %d is ahead of the current index %d"
            % (run_index, current_index)
        )
    if run_index < current_index:
        return {
            "status": SUPERSEDED_BY_PROCESS_CHANGE,
            "current": False,
            "findings": [
                "run %r predates process change %d and has to be repeated"
                % (run.get("id"), current_index)
            ],
        }
    if age > int(policy["max_validity_days"]):
        return {
            "status": EXPIRED_BY_AGE,
            "current": False,
            "findings": [
                "run %r is %d days old against a validity window of %d days"
                % (run.get("id"), age, int(policy["max_validity_days"]))
            ],
        }
    return {"status": CURRENT, "current": True, "findings": []}


def run_is_admissible(run, process_change_index, policy=DEFAULT_PROCESS_POLICY):
    """Can this run validate anything at all, before coverage is asked."""
    validate_process_policy(policy)
    _require_mapping("run", run)
    outcome = _require_choice("outcome", run.get("outcome"), RUN_OUTCOMES)
    coupons = _require_count("coupon_count", run.get("coupon_count"))
    currency = validation_currency(run, process_change_index, policy)
    reasons = list(currency["findings"]) if policy["require_current_validation"] else []
    if outcome != "passed":
        reasons.append("run %r did not pass" % run.get("id"))
    if coupons < int(policy["min_validation_coupons"]):
        reasons.append(
            "run %r carried %d coupon(s) against a required %d"
            % (run.get("id"), coupons, int(policy["min_validation_coupons"]))
        )
    return {
        "id": run.get("id"),
        "admissible": not reasons,
        "currency": currency["status"],
        "findings": reasons,
    }


def assess_configuration(
    configuration, runs, process_change_index, policy=DEFAULT_PROCESS_POLICY
):
    """Is one design configuration validated by the runs in hand."""
    validate_process_policy(policy)
    configuration_signature(configuration)
    if not isinstance(runs, (list, tuple)):
        raise ValueError("runs must be a sequence, got %r" % (runs,))
    findings = []
    covering_but_inadmissible = []
    for run in runs:
        coverage = run_covers_configuration(run, configuration)
        if not coverage["covers"]:
            continue
        admissibility = run_is_admissible(run, process_change_index, policy)
        if admissibility["admissible"]:
            return {
                "configuration_id": configuration.get("id"),
                "validated": True,
                "validating_run_id": run.get("id"),
                "reason": "covered by run %r" % run.get("id"),
                "findings": [],
            }
        covering_but_inadmissible.append(run.get("id"))
        findings.extend(admissibility["findings"])
    if covering_but_inadmissible:
        reason = "runs %s match the configuration but are not admissible" % ", ".join(
            repr(identifier) for identifier in covering_but_inadmissible
        )
    else:
        reason = "no validation run was carried out on this configuration"
    findings.append(
        "configuration %r is not validated: %s" % (configuration.get("id"), reason)
    )
    return {
        "configuration_id": configuration.get("id"),
        "validated": False,
        "validating_run_id": None,
        "reason": reason,
        "findings": findings,
    }


def plan_validation_runs(configurations):
    """Smallest honest set of runs that would close the open configurations.

    Configurations sharing a governing signature are closed by one run,
    so the plan is one entry per distinct signature rather than one per
    configuration.
    """
    if not isinstance(configurations, (list, tuple)):
        raise ValueError("configurations must be a sequence, got %r" % (configurations,))
    grouped = {}
    order = []
    for configuration in configurations:
        signature = configuration_signature(configuration)
        if signature not in grouped:
            grouped[signature] = []
            order.append(signature)
        grouped[signature].append(configuration.get("id"))
    return [
        {
            "governing_attributes": dict(signature),
            "configuration_ids": grouped[signature],
        }
        for signature in order
    ]


def assess_production_readiness(campaign, policy=DEFAULT_PROCESS_POLICY):
    """Full clause 5.4.1 process-validation coverage with a release verdict."""
    validate_process_policy(policy)
    _require_mapping("campaign", campaign)
    configurations = campaign.get("configurations")
    if not isinstance(configurations, (list, tuple)) or not configurations:
        raise ValueError("campaign must carry a non-empty configurations sequence")
    runs = campaign.get("validation_runs")
    if not isinstance(runs, (list, tuple)):
        raise ValueError("campaign must carry a validation_runs sequence")
    process_change_index = _require_count(
        "process_change_index", campaign.get("process_change_index", 0)
    )

    seen = set()
    for configuration in configurations:
        identifier = _require_mapping("configuration", configuration).get("id")
        if identifier in seen:
            raise ValueError("configuration id %r appears twice" % identifier)
        seen.add(identifier)

    statuses = [
        assess_configuration(configuration, runs, process_change_index, policy)
        for configuration in configurations
    ]
    findings = []
    for status in statuses:
        findings.extend(status["findings"])

    open_configurations = [
        configuration
        for configuration, status in zip(configurations, statuses)
        if not status["validated"]
    ]
    outstanding = plan_validation_runs(open_configurations)
    validated_count = len(statuses) - len(open_configurations)
    coverage = validated_count / len(statuses)
    compliant = not open_configurations
    if not compliant:
        findings.append(
            "%d of %d configuration(s) are unvalidated; %d further run(s) would "
            "close them" % (len(open_configurations), len(statuses), len(outstanding))
        )
    return {
        "configurations": statuses,
        "validated_count": validated_count,
        "configuration_count": len(statuses),
        "coverage_fraction": coverage,
        "outstanding_runs": outstanding,
        "compliant": compliant,
        "verdict": (
            PRODUCTION_RELEASE_PERMITTED if compliant else PRODUCTION_RELEASE_WITHHELD
        ),
        "findings": findings,
    }
