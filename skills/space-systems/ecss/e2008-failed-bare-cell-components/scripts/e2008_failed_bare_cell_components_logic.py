#!/usr/bin/env python3
"""Treatment of a bare cell component that exhibits a listed failure mode.

Anchor: ECSS-E-ST-20-08C clause 7.6.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The preceding criteria decide which components are failed. This clause
decides what then happens to one. The invariant it turns on is short and
easy to erode in practice: a component exhibiting any one of the listed
failure modes is a failed component, and a failed component leaves the
deliverable population. Not the worst mode, not two modes, not a mode
somebody judges significant -- any single listed mode.

What follows from that is a treatment, and the treatment is decided by
three things:

    the modes   a mode the policy places beyond repair rules the
                component out permanently; a mode it places in the
                reworkable set opens rework, once the cycles already
                spent are counted
    the role    a failed deliverable is removed from the delivered
                quantity; a failed test article is retained instead,
                because it carries the evidence the investigation needs
                and scrapping it destroys the finding
    the record  segregation and a non-conformance entry travel with the
                component, so the lot count and the paperwork agree

A component is never returned to the lot by re-testing it until it
passes. Re-test after rework is a check on the repair; re-test instead
of rework is a search for a favourable reading.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

POWER_DEGRADATION = "maximum-power-degradation"
CURRENT_DEGRADATION = "short-circuit-current-degradation"
VOLTAGE_DEGRADATION = "open-circuit-voltage-degradation"
ELECTRICAL_OPEN_CIRCUIT = "electrical-open-circuit"
CONTACT_DELAMINATION = "contact-delamination"
CELL_CRACK = "cell-crack"
COATING_DAMAGE = "coating-damage"

DEFAULT_LISTED_FAILURE_MODES = (
    POWER_DEGRADATION,
    CURRENT_DEGRADATION,
    VOLTAGE_DEGRADATION,
    ELECTRICAL_OPEN_CIRCUIT,
    CONTACT_DELAMINATION,
    CELL_CRACK,
    COATING_DAMAGE,
)

DELIVERABLE = "deliverable"
TEST_ARTICLE = "test-article"
COMPONENT_ROLES = (DELIVERABLE, TEST_ARTICLE)

RELEASED_TO_LOT = "released-to-deliverable-lot"
SEGREGATED_FOR_REWORK = "segregated-for-rework"
SEGREGATED_FOR_INVESTIGATION = "segregated-for-investigation"
WITHDRAWN_AND_SCRAPPED = "withdrawn-and-scrapped"

TREATMENT_NOT_ESTABLISHED = "component-treatment-not-established"
LOT_QUANTITY_SHORTFALL = "deliverable-lot-quantity-shortfall"
FAILED_COMPONENTS_TREATED = "failed-components-treated"

DEFAULT_TREATMENT_POLICY = {
    # modes a repair can credibly reverse
    "reworkable_modes": (CONTACT_DELAMINATION, COATING_DAMAGE),
    # modes that put a component beyond repair whatever else it shows
    "irreversible_modes": (
        POWER_DEGRADATION,
        CURRENT_DEGRADATION,
        VOLTAGE_DEGRADATION,
        ELECTRICAL_OPEN_CIRCUIT,
        CELL_CRACK,
    ),
    "max_rework_cycles": 1,
    "segregation_required": True,
    "nonconformance_required": True,
    "retest_after_rework_required": True,
}


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %r" % (name, minimum, value))
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def validate_listed_failure_modes(modes):
    """Check the mode list the criteria leaf handed over is usable."""
    if not isinstance(modes, (list, tuple)) or not modes:
        raise ValueError(
            "the listed failure modes must be a non-empty sequence; with no "
            "list there is nothing for a component to exhibit"
        )
    grouped = []
    for mode in modes:
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("each listed failure mode must be a name, got %r" % (mode,))
        token = mode.strip()
        if token in grouped:
            raise ValueError("failure mode %r is listed twice" % (token,))
        grouped.append(token)
    return tuple(grouped)


def validate_treatment_policy(policy, listed_modes=DEFAULT_LISTED_FAILURE_MODES):
    """Check the policy fixes a treatment for every listed mode, exactly once."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    listed = validate_listed_failure_modes(listed_modes)
    reworkable = validate_listed_failure_modes(policy.get("reworkable_modes")) \
        if policy.get("reworkable_modes") else ()
    irreversible = validate_listed_failure_modes(policy.get("irreversible_modes")) \
        if policy.get("irreversible_modes") else ()
    for mode in reworkable + irreversible:
        if mode not in listed:
            raise ValueError(
                "policy places %r, which is not a listed failure mode, into a "
                "treatment category" % (mode,)
            )
    both = [mode for mode in reworkable if mode in irreversible]
    if both:
        raise ValueError(
            "policy puts %s in both the reworkable and the irreversible set; a "
            "mode cannot have two treatments" % (", ".join(sorted(both)),)
        )
    unplaced = [
        mode for mode in listed if mode not in reworkable and mode not in irreversible
    ]
    if unplaced:
        raise ValueError(
            "policy fixes no treatment for %s; a component exhibiting an "
            "unplaced mode could not be dispositioned"
            % (", ".join(sorted(unplaced)),)
        )
    _require_count("policy max_rework_cycles", policy.get("max_rework_cycles"))
    for key in (
        "segregation_required",
        "nonconformance_required",
        "retest_after_rework_required",
    ):
        _require_flag("policy %s" % key, policy.get(key))
    return {
        "listed_modes": listed,
        "reworkable_modes": reworkable,
        "irreversible_modes": irreversible,
        "max_rework_cycles": policy["max_rework_cycles"],
        "segregation_required": policy["segregation_required"],
        "nonconformance_required": policy["nonconformance_required"],
        "retest_after_rework_required": policy["retest_after_rework_required"],
    }


def validate_component_record(component, listed_modes=DEFAULT_LISTED_FAILURE_MODES):
    """Read one component record back, refusing what cannot be treated."""
    listed = validate_listed_failure_modes(listed_modes)
    if not isinstance(component, dict):
        raise ValueError("each component record must be a mapping, got %r" % (component,))
    identifier = component.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("each component record needs a non-empty id")
    role = component.get("role", DELIVERABLE)
    if role not in COMPONENT_ROLES:
        raise ValueError(
            "%s has role %r; a component is either %s or %s"
            % (identifier, role, DELIVERABLE, TEST_ARTICLE)
        )
    modes = component.get("failure_modes", [])
    if not isinstance(modes, (list, tuple)):
        raise ValueError("%s failure_modes must be a list, got %r" % (identifier, modes))
    exhibited = []
    for mode in modes:
        if not isinstance(mode, str) or not mode.strip():
            raise ValueError("%s carries an unnamed failure mode %r" % (identifier, mode))
        token = mode.strip()
        if token not in listed:
            raise ValueError(
                "%s exhibits %r, which the criteria set does not list; a mode "
                "nobody declared fixes no treatment" % (identifier, token)
            )
        if token not in exhibited:
            exhibited.append(token)
    cycles = _require_count(
        "%s rework_cycles_done" % identifier, component.get("rework_cycles_done", 0)
    )
    return {
        "id": identifier.strip(),
        "role": role,
        "failure_modes": tuple(exhibited),
        "rework_cycles_done": cycles,
        "return_requested_by_retest": bool(component.get("return_requested_by_retest", False)),
    }


def treatment_for_component(
    component,
    listed_modes=DEFAULT_LISTED_FAILURE_MODES,
    policy=DEFAULT_TREATMENT_POLICY,
):
    """Treatment one component receives for the modes it exhibits.

    Any single listed mode makes the component a failed component, so the
    withdrawal, the segregation and the non-conformance entry follow from
    presence rather than from severity.
    """
    settings = validate_treatment_policy(policy, listed_modes)
    record = validate_component_record(component, listed_modes)
    findings = []

    if not record["failure_modes"]:
        return {
            "id": record["id"],
            "role": record["role"],
            "failure_modes": (),
            "disposition": RELEASED_TO_LOT,
            "withdrawn_from_lot": False,
            "segregation_required": False,
            "nonconformance_required": False,
            "rework_permitted": False,
            "retest_required": False,
            "counts_toward_delivery": record["role"] == DELIVERABLE,
            "findings": findings,
        }

    irreversible = [
        mode for mode in record["failure_modes"]
        if mode in settings["irreversible_modes"]
    ]
    cycles_left = settings["max_rework_cycles"] - record["rework_cycles_done"]

    if record["role"] == TEST_ARTICLE:
        disposition = SEGREGATED_FOR_INVESTIGATION
        rework_permitted = False
        findings.append(
            "%s is a test article and is retained rather than scrapped; it "
            "carries the evidence for %s" % (record["id"], ", ".join(record["failure_modes"]))
        )
    elif irreversible:
        disposition = WITHDRAWN_AND_SCRAPPED
        rework_permitted = False
        findings.append(
            "%s exhibits %s, which no repair reverses"
            % (record["id"], ", ".join(sorted(irreversible)))
        )
    elif cycles_left > 0:
        disposition = SEGREGATED_FOR_REWORK
        rework_permitted = True
        findings.append(
            "%s exhibits %s, reworkable with %d cycle(s) left"
            % (record["id"], ", ".join(record["failure_modes"]), cycles_left)
        )
    else:
        disposition = WITHDRAWN_AND_SCRAPPED
        rework_permitted = False
        findings.append(
            "%s has already used its %d rework cycle(s), so a reworkable mode "
            "is out of remedies" % (record["id"], settings["max_rework_cycles"])
        )

    if record["return_requested_by_retest"]:
        findings.append(
            "%s is put forward for return to the lot on a re-test alone; a "
            "failed component is not recovered by measuring it again"
            % (record["id"],)
        )

    return {
        "id": record["id"],
        "role": record["role"],
        "failure_modes": record["failure_modes"],
        "disposition": disposition,
        "withdrawn_from_lot": True,
        "segregation_required": settings["segregation_required"],
        "nonconformance_required": settings["nonconformance_required"],
        "rework_permitted": rework_permitted,
        "retest_required": rework_permitted and settings["retest_after_rework_required"],
        "rework_cycles_left": max(cycles_left, 0),
        "counts_toward_delivery": False,
        "findings": findings,
    }


def batch_treatments(
    components,
    listed_modes=DEFAULT_LISTED_FAILURE_MODES,
    policy=DEFAULT_TREATMENT_POLICY,
):
    """Treat every component in one batch, refusing a repeated identifier."""
    if not isinstance(components, (list, tuple)) or not components:
        raise ValueError(
            "a batch must carry at least one component record; an empty batch "
            "is not a treated batch"
        )
    seen = set()
    treatments = []
    for component in components:
        treatment = treatment_for_component(component, listed_modes, policy)
        if treatment["id"] in seen:
            raise ValueError("duplicate component id %r in the batch" % (treatment["id"],))
        seen.add(treatment["id"])
        treatments.append(treatment)
    return treatments


def delivered_quantity(treatments):
    """Components still countable toward the delivered quantity."""
    if not treatments:
        raise ValueError("an empty batch delivers no quantity to count")
    return sum(1 for item in treatments if item["counts_toward_delivery"])


def lot_quantity_shortfall(treatments, ordered_quantity):
    """How many deliverable components the withdrawals leave the lot short."""
    _require_count("ordered_quantity", ordered_quantity)
    return max(ordered_quantity - delivered_quantity(treatments), 0)


def nonconformance_records(treatments):
    """Identifiers that need a non-conformance entry raised against them."""
    return tuple(
        item["id"] for item in treatments if item["nonconformance_required"]
    )


def assess_failed_bare_cell_components(case, policy=DEFAULT_TREATMENT_POLICY):
    """Clause 7.6.2 treatment of every failed component in one batch."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    components = case.get("components")
    if components is None:
        raise ValueError("a treatment case needs a components list")
    listed_modes = case.get("listed_failure_modes", DEFAULT_LISTED_FAILURE_MODES)
    ordered = _require_count("ordered_quantity", case.get("ordered_quantity", 0))

    try:
        settings = validate_treatment_policy(policy, listed_modes)
    except ValueError as problem:
        return {
            "verdict": TREATMENT_NOT_ESTABLISHED,
            "findings": [str(problem)],
            "treatments": [],
            "withdrawn_components": [],
            "nonconformance_records": [],
        }

    treatments = batch_treatments(components, listed_modes, policy)
    findings = []
    for treatment in treatments:
        findings.extend(treatment["findings"])

    withdrawn = [item["id"] for item in treatments if item["withdrawn_from_lot"]]
    delivered = delivered_quantity(treatments)
    shortfall = lot_quantity_shortfall(treatments, ordered)
    if shortfall > 0:
        verdict = LOT_QUANTITY_SHORTFALL
        findings.append(
            "%d component(s) withdrawn leave the lot %d short of the %d ordered"
            % (len(withdrawn), shortfall, ordered)
        )
    else:
        verdict = FAILED_COMPONENTS_TREATED

    return {
        "verdict": verdict,
        "treatments": treatments,
        "component_count": len(treatments),
        "withdrawn_components": withdrawn,
        "scrapped_components": [
            item["id"] for item in treatments
            if item["disposition"] == WITHDRAWN_AND_SCRAPPED
        ],
        "rework_components": [
            item["id"] for item in treatments
            if item["disposition"] == SEGREGATED_FOR_REWORK
        ],
        "retained_components": [
            item["id"] for item in treatments
            if item["disposition"] == SEGREGATED_FOR_INVESTIGATION
        ],
        "delivered_quantity": delivered,
        "ordered_quantity": ordered,
        "quantity_shortfall": shortfall,
        "segregation_required": settings["segregation_required"] and bool(withdrawn),
        "nonconformance_records": list(nonconformance_records(treatments)),
        "findings": findings,
    }
