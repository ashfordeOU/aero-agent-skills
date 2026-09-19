#!/usr/bin/env python3
"""Material selection for a mechanism.

Anchor: ECSS-E-ST-33-01C clause 4.5.2.1, which routes the selection
through ECSS-Q-ST-70 clause 5 and takes the design-allowable guidance
of ECSS-E-ST-32-08. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

Selecting a material for a moving assembly is four questions asked of
every candidate, and a candidate is only in once all four are answered.

    route         is the material already on the declared list, is it
                  qualified by a test programme, or is it new and owed
                  an approval before it goes anywhere
    cleanliness   does it stay inside the vacuum mass-loss and
                  condensable-volatile limits, which matter twice over
                  in a mechanism because the condensate lands on the
                  surfaces that have to slide
    durability    is its stress-corrosion susceptibility acceptable,
                  and if it is the susceptible category, is there a
                  written justification rather than a habit
    strength      what design allowable may be used, and is the basis
                  admissible for the load path it sits in -- a
                  statistical basis that assumes a redundant path is
                  not available to a single-string fitting

Each candidate leaves with one of three outcomes: accepted, accepted
with an action still owed, or rejected.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

SELECTION_ROUTES = ("declared-list", "qualified-by-test", "new-material")
ALLOWABLE_BASES = ("a-basis", "b-basis", "s-basis", "typical")
SCC_CATEGORIES = ("low", "moderate", "high")
LOAD_PATHS = ("single", "redundant")

OUTCOME_ACCEPTED = "accepted"
OUTCOME_ACTION = "accepted-with-action"
OUTCOME_REJECTED = "rejected"

DEFAULT_SELECTION_POLICY = {
    "max_total_mass_loss_percent": 1.0,
    "max_collected_volatile_condensable_percent": 0.1,
    "max_recovered_mass_loss_percent": 1.0,
    "allowable_knockdown": {
        "a-basis": 1.0,
        "b-basis": 1.0,
        "s-basis": 0.9,
        "typical": 0.75,
    },
    "bases_allowed_on_a_single_load_path": ("a-basis", "s-basis"),
    "scc_categories_needing_justification": ("high",),
    "minimum_justification_characters": 20,
    "new_material_needs_approval": True,
}

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
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_non_negative(name, value)
    if value == 0.0:
        raise ValueError("%s must be greater than zero" % name)
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_selection_policy(policy):
    """Check the selection policy carries every limit the screening uses."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "max_total_mass_loss_percent",
        "max_collected_volatile_condensable_percent",
        "max_recovered_mass_loss_percent",
    ):
        _require_positive(key, policy.get(key))
    knockdown = policy.get("allowable_knockdown")
    if not isinstance(knockdown, dict):
        raise ValueError("allowable_knockdown must be a mapping")
    missing = set(ALLOWABLE_BASES) - set(knockdown)
    if missing:
        raise ValueError(
            "allowable_knockdown is missing %s" % ", ".join(sorted(missing))
        )
    for basis in ALLOWABLE_BASES:
        factor = _require_positive("allowable_knockdown[%s]" % basis, knockdown[basis])
        if factor > 1.0:
            raise ValueError("allowable_knockdown[%s] cannot exceed unity" % basis)
    allowed = policy.get("bases_allowed_on_a_single_load_path")
    if not isinstance(allowed, (list, tuple)) or not allowed:
        raise ValueError("bases_allowed_on_a_single_load_path must be non-empty")
    for basis in allowed:
        _require_choice("single-load-path basis", basis, ALLOWABLE_BASES)
    needing = policy.get("scc_categories_needing_justification")
    if not isinstance(needing, (list, tuple)):
        raise ValueError("scc_categories_needing_justification must be a sequence")
    for category in needing:
        _require_choice("scc category", category, SCC_CATEGORIES)
    if (
        not isinstance(policy.get("minimum_justification_characters"), int)
        or isinstance(policy.get("minimum_justification_characters"), bool)
        or policy["minimum_justification_characters"] < 1
    ):
        raise ValueError("minimum_justification_characters must be a positive integer")
    if not isinstance(policy.get("new_material_needs_approval"), bool):
        raise ValueError("new_material_needs_approval must be a boolean")
    return policy


def screen_outgassing(
    total_mass_loss_percent,
    collected_volatile_condensable_percent,
    recovered_mass_loss_percent=None,
    policy=DEFAULT_SELECTION_POLICY,
):
    """Grade a candidate against the vacuum outgassing limits."""
    validate_selection_policy(policy)
    tml = _require_non_negative(
        "total_mass_loss_percent", total_mass_loss_percent
    )
    cvcm = _require_non_negative(
        "collected_volatile_condensable_percent",
        collected_volatile_condensable_percent,
    )
    findings = []
    tml_ok = _at_most(tml, policy["max_total_mass_loss_percent"])
    if not tml_ok:
        findings.append(
            "total mass loss %.3f%% exceeds the limit %.3f%%"
            % (tml, policy["max_total_mass_loss_percent"])
        )
    cvcm_ok = _at_most(cvcm, policy["max_collected_volatile_condensable_percent"])
    if not cvcm_ok:
        findings.append(
            "collected volatile condensable material %.3f%% exceeds the limit "
            "%.3f%%" % (cvcm, policy["max_collected_volatile_condensable_percent"])
        )
    rml_ok = None
    if recovered_mass_loss_percent is not None:
        rml = _require_non_negative(
            "recovered_mass_loss_percent", recovered_mass_loss_percent
        )
        if rml > tml and not math.isclose(
            rml, tml, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            raise ValueError(
                "recovered mass loss %.3f%% cannot exceed total mass loss %.3f%%"
                % (rml, tml)
            )
        rml_ok = _at_most(rml, policy["max_recovered_mass_loss_percent"])
        if not rml_ok:
            findings.append(
                "recovered mass loss %.3f%% exceeds the limit %.3f%%"
                % (rml, policy["max_recovered_mass_loss_percent"])
            )
    return {
        "total_mass_loss_ok": tml_ok,
        "condensable_ok": cvcm_ok,
        "recovered_mass_loss_ok": rml_ok,
        "passes": tml_ok and cvcm_ok and rml_ok is not False,
        "findings": findings,
    }


def assess_stress_corrosion(category, justification="", policy=DEFAULT_SELECTION_POLICY):
    """Decide whether a stress-corrosion category is carried or refused."""
    validate_selection_policy(policy)
    _require_choice("category", category, SCC_CATEGORIES)
    if not isinstance(justification, str):
        raise ValueError("justification must be a string")
    if category not in policy["scc_categories_needing_justification"]:
        return {"category": category, "acceptable": True, "findings": []}
    text = justification.strip()
    if len(text) >= policy["minimum_justification_characters"]:
        return {
            "category": category,
            "acceptable": True,
            "findings": [
                "susceptible category %s carried against a written "
                "justification" % category
            ],
        }
    return {
        "category": category,
        "acceptable": False,
        "findings": [
            "stress-corrosion category %s carries no written justification"
            % category
        ],
    }


def design_allowable_mpa(
    typical_strength_mpa, basis, load_path, policy=DEFAULT_SELECTION_POLICY
):
    """Design allowable from a typical strength, given the basis and path.

    A basis that leans on load redistribution is not available to a
    fitting that has nowhere to redistribute into.
    """
    validate_selection_policy(policy)
    strength = _require_positive("typical_strength_mpa", typical_strength_mpa)
    _require_choice("basis", basis, ALLOWABLE_BASES)
    _require_choice("load_path", load_path, LOAD_PATHS)
    if (
        load_path == "single"
        and basis not in policy["bases_allowed_on_a_single_load_path"]
    ):
        raise ValueError(
            "%s is not admissible on a single load path; use %s"
            % (basis, " or ".join(policy["bases_allowed_on_a_single_load_path"]))
        )
    return strength * policy["allowable_knockdown"][basis]


def temperature_rating_holds(
    min_service_temperature_c, max_service_temperature_c, envelope
):
    """Whether a material covers the qualification temperature range."""
    low = _require_number("min_service_temperature_c", min_service_temperature_c)
    high = _require_number("max_service_temperature_c", max_service_temperature_c)
    if high <= low:
        raise ValueError("max service temperature must exceed the minimum")
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping, got %r" % (envelope,))
    cold = _require_number(
        "qualification_min_temperature_c", envelope.get("qualification_min_temperature_c")
    )
    hot = _require_number(
        "qualification_max_temperature_c", envelope.get("qualification_max_temperature_c")
    )
    findings = []
    cold_ok = _at_most(low, cold)
    hot_ok = _at_least(high, hot)
    if not cold_ok:
        findings.append(
            "service floor %.1f C does not reach the cold case %.1f C" % (low, cold)
        )
    if not hot_ok:
        findings.append(
            "service ceiling %.1f C does not reach the hot case %.1f C" % (high, hot)
        )
    return {"cold_ok": cold_ok, "hot_ok": hot_ok, "holds": cold_ok and hot_ok,
            "findings": findings}


def evaluate_candidate(candidate, envelope, policy=DEFAULT_SELECTION_POLICY):
    """Run one candidate material through all four selection questions."""
    validate_selection_policy(policy)
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping, got %r" % (candidate,))
    name = candidate.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("candidate name must be a non-empty string")
    route = _require_choice("route", candidate.get("route"), SELECTION_ROUTES)
    findings = []
    actions = []
    outgassing = screen_outgassing(
        candidate.get("total_mass_loss_percent"),
        candidate.get("collected_volatile_condensable_percent"),
        candidate.get("recovered_mass_loss_percent"),
        policy,
    )
    findings.extend(outgassing["findings"])
    scc = assess_stress_corrosion(
        candidate.get("stress_corrosion_category"),
        candidate.get("stress_corrosion_justification", ""),
        policy,
    )
    findings.extend(scc["findings"])
    basis = _require_choice("basis", candidate.get("allowable_basis"), ALLOWABLE_BASES)
    load_path = _require_choice("load_path", candidate.get("load_path"), LOAD_PATHS)
    allowable = None
    basis_admissible = True
    try:
        allowable = design_allowable_mpa(
            candidate.get("typical_strength_mpa"), basis, load_path, policy
        )
    except ValueError as problem:
        if "not admissible on a single load path" not in str(problem):
            raise
        basis_admissible = False
        findings.append("%s: %s" % (name, problem))
    thermal = temperature_rating_holds(
        candidate.get("min_service_temperature_c"),
        candidate.get("max_service_temperature_c"),
        envelope,
    )
    findings.extend(thermal["findings"])
    if route == "new-material" and policy["new_material_needs_approval"]:
        actions.append(
            "%s is a new material and owes a selection approval before use" % name
        )
    if basis == "typical":
        actions.append(
            "%s is carried on a typical strength with a knockdown and owes a "
            "statistical allowable" % name
        )
    rejected = (
        not outgassing["passes"]
        or not scc["acceptable"]
        or not basis_admissible
        or not thermal["holds"]
    )
    if rejected:
        outcome = OUTCOME_REJECTED
    elif actions:
        outcome = OUTCOME_ACTION
    else:
        outcome = OUTCOME_ACCEPTED
    return {
        "name": name,
        "route": route,
        "outgassing_passes": outgassing["passes"],
        "stress_corrosion_acceptable": scc["acceptable"],
        "allowable_basis": basis,
        "basis_admissible": basis_admissible,
        "design_allowable_mpa": allowable,
        "temperature_rating_holds": thermal["holds"],
        "outcome": outcome,
        "actions": actions,
        "findings": findings,
    }


def assess_material_selection(case, policy=DEFAULT_SELECTION_POLICY):
    """Full clause 4.5.2.1 verdict over a candidate material list."""
    validate_selection_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    candidates = case.get("candidates")
    if not isinstance(candidates, (list, tuple)) or not candidates:
        raise ValueError("case must carry a non-empty candidates sequence")
    envelope = case.get("envelope")
    if not isinstance(envelope, dict):
        raise ValueError("case must carry an envelope mapping")
    seen = set()
    results = []
    findings = []
    for candidate in candidates:
        result = evaluate_candidate(candidate, envelope, policy)
        if result["name"] in seen:
            raise ValueError("duplicate candidate name %r" % result["name"])
        seen.add(result["name"])
        results.append(result)
        findings.extend(result["findings"])
    grouped = {
        OUTCOME_ACCEPTED: [r["name"] for r in results if r["outcome"] == OUTCOME_ACCEPTED],
        OUTCOME_ACTION: [r["name"] for r in results if r["outcome"] == OUTCOME_ACTION],
        OUTCOME_REJECTED: [r["name"] for r in results if r["outcome"] == OUTCOME_REJECTED],
    }
    open_actions = [a for r in results for a in r["actions"]]
    if grouped[OUTCOME_REJECTED]:
        verdict = "selection-not-acceptable"
        compliant = False
    elif grouped[OUTCOME_ACTION]:
        verdict = "selection-open-actions"
        compliant = False
    else:
        verdict = "selection-acceptable"
        compliant = True
    return {
        "candidates": results,
        "grouped": grouped,
        "open_actions": open_actions,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
