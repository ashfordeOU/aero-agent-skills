"""Reconfiguration of an already initialised simulator.

Anchor: ECSS-E-ST-40-08C clause 5.5.3 (simulator reconfiguration).
Paraphrased into an implementable procedure; no standard text is
reproduced. The clause carries two normative items.

Procedure implemented here
--------------------------
Item RC-01 -- a reconfiguration is entered from a state that is allowed
to give up the published model tree, and it returns to standby through
the same states the first start-up used. A simulator asked to
reconfigure while it is executing, storing, restoring or unwinding has
no quiescent tree to rebuild from, so the request is refused rather than
queued.

Item RC-02 -- the reconfiguration re-applies the configuration set and
keeps the identities the previous configuration established. A field
that disappears from the new set, a field that appears without ever
having been declared, a Schedule that comes back with a different
identity, or a model whose path changed are all identity breaks: the
saved state and the recorded telemetry of the previous run can no longer
be matched to the new tree.
"""

__all__ = [
    "NORMATIVE_ITEM_COUNT",
    "NORMATIVE_ITEMS",
    "RECONFIGURABLE_FROM",
    "RECONFIGURATION_SEQUENCE",
    "validate_entry_state",
    "validate_reconfiguration_walk",
    "diff_configuration",
    "check_identity_preservation",
    "assess_reconfiguration",
]

NORMATIVE_ITEM_COUNT = 2

NORMATIVE_ITEMS = (
    ("RC-01", "reconfiguration is entered from a quiescent state and walks back to standby"),
    ("RC-02", "the re-applied configuration preserves the established identities"),
)

# Only a simulator that is holding still may give up its published tree.
RECONFIGURABLE_FROM = ("standby",)

# The walk a reconfiguration repeats to get back to standby.
RECONFIGURATION_SEQUENCE = ("building", "connecting", "initialising", "standby")

_KNOWN_STATES = (
    "building",
    "connecting",
    "initialising",
    "standby",
    "executing",
    "storing",
    "restoring",
    "reconnecting",
    "exiting",
    "aborting",
)


def _require_text(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def _state(value, label):
    text = _require_text(value, label).lower()
    if text not in _KNOWN_STATES:
        raise ValueError("%s names an unknown simulator state %r" % (label, value))
    return text


def validate_entry_state(state):
    """Return the verdict on entering a reconfiguration from this state."""
    resolved = _state(state, "entry state")
    permitted = resolved in RECONFIGURABLE_FROM
    findings = []
    if not permitted:
        findings.append(
            "a reconfiguration requested from %r has no quiescent model tree to give up; "
            "permitted entry state(s): %s" % (resolved, ", ".join(RECONFIGURABLE_FROM))
        )
    return {"state": resolved, "permitted": permitted, "findings": findings}


def validate_reconfiguration_walk(observed):
    """Return the verdict on the state walk a reconfiguration performed."""
    if not isinstance(observed, (list, tuple)):
        raise ValueError("observed walk must be a list or tuple")
    if not observed:
        raise ValueError("observed walk must not be empty")
    walk = [_state(s, "walk[%d]" % i) for i, s in enumerate(observed)]
    findings = []
    for state in RECONFIGURATION_SEQUENCE:
        if state not in walk:
            findings.append("reconfiguration never re-entered state %r" % state)
    foreign = [s for s in walk if s not in RECONFIGURATION_SEQUENCE]
    if foreign:
        findings.append("states outside the reconfiguration walk: %s" % ", ".join(sorted(set(foreign))))
    positions = {}
    for index, state in enumerate(walk):
        positions.setdefault(state, index)
    present = [s for s in RECONFIGURATION_SEQUENCE if s in positions]
    for i in range(1, len(present)):
        if positions[present[i]] < positions[present[i - 1]]:
            findings.append("state %r was re-entered before %r" % (present[i], present[i - 1]))
    if walk and walk[-1] != "standby":
        findings.append("reconfiguration ended in %r rather than standby" % walk[-1])
    return {"walk": walk, "compliant": not findings, "findings": findings}


def _as_mapping(config, label, allow_empty=False):
    if not isinstance(config, dict):
        raise ValueError("%s must be a mapping of field path to value" % label)
    out = {}
    for key, value in config.items():
        path = _require_text(key, "%s field path" % label)
        out[path] = value
    if not out and not allow_empty:
        raise ValueError("%s must not be empty" % label)
    return out


def diff_configuration(previous, reapplied):
    """Return the field-level difference between two configuration sets."""
    before = _as_mapping(previous, "previous configuration")
    after = _as_mapping(reapplied, "re-applied configuration", allow_empty=True)
    dropped = sorted(k for k in before if k not in after)
    introduced = sorted(k for k in after if k not in before)
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    retained = sorted(k for k in before if k in after and before[k] == after[k])
    return {
        "dropped": dropped,
        "introduced": introduced,
        "changed": changed,
        "retained": retained,
    }


def check_identity_preservation(previous_identities, new_identities):
    """Return the verdict on whether the reconfiguration kept its identities."""
    if not isinstance(previous_identities, dict) or not isinstance(new_identities, dict):
        raise ValueError("identities must be mappings of name to identity token")
    if not previous_identities:
        raise ValueError("previous identities must not be empty")
    findings = []
    for name in sorted(previous_identities):
        label = _require_text(name, "identity name")
        if label not in new_identities:
            findings.append("identity %r is absent after the reconfiguration" % label)
            continue
        before = previous_identities[label]
        after = new_identities[label]
        if before != after:
            findings.append(
                "identity %r changed from %r to %r across the reconfiguration"
                % (label, before, after)
            )
    for name in sorted(new_identities):
        if name not in previous_identities:
            findings.append("identity %r appeared without a previous counterpart" % name)
    return {"compliant": not findings, "findings": findings}


def assess_reconfiguration(spec):
    """Grade a reconfiguration against the two normative items.

    spec keys: entry_state, walk, previous_configuration, reapplied_configuration,
    previous_identities, new_identities, allow_value_changes (default True).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "entry_state",
        "walk",
        "previous_configuration",
        "reapplied_configuration",
        "previous_identities",
        "new_identities",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    allow_changes = spec.get("allow_value_changes", True)
    if not isinstance(allow_changes, bool):
        raise ValueError("allow_value_changes must be a boolean")

    entry = validate_entry_state(spec["entry_state"])
    walk = validate_reconfiguration_walk(spec["walk"])
    diff = diff_configuration(spec["previous_configuration"], spec["reapplied_configuration"])
    identity = check_identity_preservation(spec["previous_identities"], spec["new_identities"])

    rc01 = list(entry["findings"]) + list(walk["findings"])
    rc02 = list(identity["findings"])
    if diff["dropped"]:
        rc02.append(
            "field(s) dropped by the re-applied configuration: %s" % ", ".join(diff["dropped"])
        )
    if diff["introduced"]:
        rc02.append(
            "field(s) introduced without a previous declaration: %s"
            % ", ".join(diff["introduced"])
        )
    if diff["changed"] and not allow_changes:
        rc02.append(
            "field value(s) changed while the reconfiguration was declared value-preserving: %s"
            % ", ".join(diff["changed"])
        )

    items = [
        {
            "id": "RC-01",
            "title": NORMATIVE_ITEMS[0][1],
            "status": "satisfied" if not rc01 else "violated",
            "findings": rc01,
        },
        {
            "id": "RC-02",
            "title": NORMATIVE_ITEMS[1][1],
            "status": "satisfied" if not rc02 else "violated",
            "findings": rc02,
        },
    ]
    findings = rc01 + rc02
    return {
        "items": items,
        "item_count": len(items),
        "entry": entry,
        "walk": walk,
        "configuration_diff": diff,
        "identity": identity,
        "violations": [i["id"] for i in items if i["status"] == "violated"],
        "findings": findings,
        "compliant": not findings,
    }
