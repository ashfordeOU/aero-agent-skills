"""Whether corrective work is open on a partly assembled hybrid.

Anchor: ECSS-Q-ST-60-05C clause 10.5 (the general permission for, and limits
on, corrective work carried out on partially assembled hybrid microcircuits).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the assembly sequence in worked order and, for each repair action,
   the last stage at which that work can still be reached.
2. Decide the route for a request: direct, if the unit has not passed the
   action's window; through lid removal, if the only thing in the way is the
   seal; closed otherwise, because the area the work needs is buried under
   later assembly, or the unit has left the line.
3. Bound what lid removal can recover. Opening a sealed unit reverts it to
   its pre-cap state and no further, so it reopens only the work whose window
   ran to pre-cap. Anything buried earlier stays buried.
4. Make lid removal expensive on purpose. Everything the seal certified has
   to be earned again, and the customer has to agree before it is started.
5. Derive the re-screen that the accepted route drags with it, which is what
   makes a repair a controlled operation rather than a local fix.
6. Return the permission, the blockers by name, the route, the re-screen
   steps and the approvals the request needs.
"""

__all__ = [
    "ACTION_WINDOWS",
    "ASSEMBLY_SEQUENCE",
    "DELIVERED_STAGE",
    "REVERTED_STAGE",
    "SEAL_STAGE",
    "action_window_stage",
    "assess_repair_request",
    "repair_route",
    "requires_lid_removal",
    "rescreen_steps",
    "stage_index",
    "within_repair_window",
]

# The assembly sequence of a hybrid microcircuit, in the order it is worked.
ASSEMBLY_SEQUENCE = (
    "substrate-preparation",
    "substrate-metallization",
    "passive-element-attach",
    "active-die-attach",
    "wire-bonding",
    "pre-cap-inspection",
    "lid-sealing",
    "post-seal-screening",
    "delivered",
)

SEAL_STAGE = "lid-sealing"
DELIVERED_STAGE = "delivered"

# Removing the lid puts the unit back into its pre-cap state, and no further
# back than that: the elements stay attached and the bonds stay made.
REVERTED_STAGE = "pre-cap-inspection"

# The last assembly stage at which each repair action can still reach what it
# needs to work on.
ACTION_WINDOWS = {
    "substrate-metallization-touch-up": "substrate-metallization",
    "passive-element-replacement": "wire-bonding",
    "active-die-replacement": "wire-bonding",
    "wire-rebond": "pre-cap-inspection",
    "particle-removal-and-cleaning": "pre-cap-inspection",
    "lid-reseal": "lid-sealing",
    "external-lead-repair": "post-seal-screening",
}


def _clean_token(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def stage_index(stage):
    """Return the position of an assembly stage in the worked sequence."""
    token = _clean_token(stage, "assembly stage")
    if token not in ASSEMBLY_SEQUENCE:
        raise ValueError("unknown assembly stage %r" % (stage,))
    return ASSEMBLY_SEQUENCE.index(token)


def action_window_stage(action):
    """Return the last assembly stage at which a repair action can be worked."""
    token = _clean_token(action, "repair action")
    if token not in ACTION_WINDOWS:
        raise ValueError("unknown repair action %r" % (action,))
    return ACTION_WINDOWS[token]


def within_repair_window(action, stage):
    """Return whether the unit has not yet passed the action's window."""
    return stage_index(stage) <= stage_index(action_window_stage(action))


def requires_lid_removal(action, stage):
    """Return whether reaching the work needs a sealed unit to be opened.

    Lid removal recovers exactly one band of work: the actions whose window
    ran to the pre-cap state the unit reverts to, and that were shut out only
    by the seal. Work whose window closed earlier is buried under assembly
    that de-lidding does not undo, and work whose window extends past sealing
    was never blocked by the seal in the first place.
    """
    if within_repair_window(action, stage):
        return False
    window = stage_index(action_window_stage(action))
    return (
        stage_index(stage) >= stage_index(SEAL_STAGE)
        and stage_index(REVERTED_STAGE) <= window < stage_index(SEAL_STAGE)
    )


def repair_route(action, stage):
    """Return how the work would be reached: direct, lid-removal or closed."""
    if within_repair_window(action, stage):
        return "direct"
    if requires_lid_removal(action, stage):
        return "lid-removal"
    return "closed"


def rescreen_steps(action, stage):
    """Return the re-screening a repair by this route drags with it.

    Opening a sealed unit undoes everything the seal certified, so the whole
    screening sequence is earned again. Work inside the window costs the
    inspection of what was touched, plus the seal tests when the seal itself
    could have been disturbed.
    """
    route = repair_route(action, stage)
    if route == "closed":
        return ()
    if route == "lid-removal":
        return (
            "repeat-internal-visual",
            "repeat-pre-cap-inspection",
            "re-seal-and-repeat-seal-tests",
            "repeat-the-full-screening-sequence",
        )
    steps = ["inspect-the-repaired-area"]
    if stage_index(stage) >= stage_index("pre-cap-inspection"):
        steps.append("repeat-pre-cap-inspection")
    if stage_index(stage) >= stage_index(SEAL_STAGE):
        steps.append("repeat-seal-tests")
        steps.append("repeat-external-visual")
    return tuple(steps)


def assess_repair_request(spec):
    """Run the full clause 10.5 permission assessment for one repair request.

    spec keys: action, assembly_stage, and the optional booleans
    approved_repair_procedure_exists and customer_approval_granted.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("action", "assembly_stage"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    action = _clean_token(spec["action"], "action")
    if action not in ACTION_WINDOWS:
        raise ValueError("unknown repair action %r" % (spec["action"],))
    stage = _clean_token(spec["assembly_stage"], "assembly_stage")
    if stage not in ASSEMBLY_SEQUENCE:
        raise ValueError("unknown assembly stage %r" % (spec["assembly_stage"],))
    flags = {}
    for key in ("approved_repair_procedure_exists", "customer_approval_granted"):
        value = spec.get(key, False)
        if not isinstance(value, bool):
            raise ValueError("%s must be a boolean, got %r" % (key, value))
        flags[key] = value

    route = repair_route(action, stage)
    lid_removal = requires_lid_removal(action, stage)
    blockers = []
    approvals = ["manufacturer-quality-authorization"]
    if route == "closed":
        blockers.append(
            "%s cannot be reached at %s; its window closed at %s and lid removal "
            "does not reopen it" % (action, stage, action_window_stage(action))
        )
    if not flags["approved_repair_procedure_exists"]:
        blockers.append("no approved repair procedure covers this action")
    if lid_removal:
        approvals.append("customer-approval-for-lid-removal")
        if not flags["customer_approval_granted"]:
            blockers.append(
                "opening a sealed unit needs customer approval, which has not been given"
            )
    if stage == DELIVERED_STAGE:
        approvals.append("customer-approval-for-work-on-delivered-hardware")
        if not flags["customer_approval_granted"]:
            blockers.append(
                "the unit has been delivered; work on it needs customer approval"
            )

    findings = []
    if lid_removal:
        findings.append(
            "lid removal reverts the unit to its pre-cap state; every screening "
            "result obtained after sealing is void"
        )
    if route == "direct" and stage_index(stage) >= stage_index(SEAL_STAGE):
        findings.append(
            "work on a sealed unit can disturb the seal, so the seal tests are repeated"
        )
    return {
        "action": action,
        "assembly_stage": stage,
        "window_closes_at": action_window_stage(action),
        "route": route,
        "within_window": within_repair_window(action, stage),
        "requires_lid_removal": lid_removal,
        "permitted": not blockers,
        "blockers": blockers,
        "approvals_required": approvals,
        "rescreen": list(rescreen_steps(action, stage)),
        "findings": findings,
    }
