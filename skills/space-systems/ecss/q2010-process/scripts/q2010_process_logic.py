"""Off-the-shelf item selection process, scoped against the product tree.

Anchor: ECSS-Q-ST-20-10C clause 4, informative (the shape of the off-the-shelf
item utilisation process: market investigation, then characterization and
selection, then procurement and qualification, carried out against the
project's own product tree). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the project product tree: each node with the make-or-buy
   decision recorded against it.
2. Normalise the off-the-shelf candidates: each attached to a product tree
   node, carrying the evidence artefacts produced so far and the
   qualification state claimed for it.
3. Decide the stage each candidate has actually reached. A stage counts only
   when every artefact it owes is present and every earlier stage is
   complete, so evidence cannot be produced out of sequence and read as
   progress.
4. Apply the conditional rule on the last stage: an item that is not already
   qualified for this application owes a delta qualification plan before its
   procurement and qualification stage is complete.
5. Reconcile the candidates with the product tree in both directions: a
   candidate on a node the tree does not carry, a candidate on a node the
   project decided to make, and a node decided as an off-the-shelf buy with
   no candidate against it.
6. Return the per-candidate stage, the process maturity across the tree and
   the decision.
"""

__all__ = [
    "STAGES",
    "STAGE_ORDER",
    "CONDITIONAL_ARTEFACT",
    "QUALIFICATION_STATES",
    "MAKE_OR_BUY",
    "KNOWN_ARTEFACTS",
    "normalise_identifier",
    "stage_index",
    "required_artefacts",
    "validate_product_tree",
    "validate_candidates",
    "stage_completion",
    "stage_reached",
    "sequence_findings",
    "product_tree_findings",
    "assess_ots_process",
]

# The process stages in order, with the evidence each one owes.
STAGES = (
    ("market-investigation", (
        "requirement-baseline",
        "market-survey-record",
        "candidate-list",
    )),
    ("characterization-and-selection", (
        "evaluation-criteria",
        "characterization-data",
        "trade-off-record",
        "selection-justification",
    )),
    ("procurement-and-qualification", (
        "procurement-specification",
        "qualification-status-statement",
    )),
)

STAGE_ORDER = tuple(name for name, _artefacts in STAGES)

# Owed by the last stage only when the item is not already qualified for the
# application it is being bought for.
CONDITIONAL_ARTEFACT = "delta-qualification-plan"

QUALIFICATION_STATES = (
    "qualified-for-this-application",
    "qualified-for-another-application",
    "not-qualified",
)

MAKE_OR_BUY = ("make", "buy-ots", "buy-custom")

KNOWN_ARTEFACTS = tuple(sorted(
    {artefact for _name, artefacts in STAGES for artefact in artefacts}
    | {CONDITIONAL_ARTEFACT}
))

_STAGE_INDEX = {name: position for position, (name, _a) in enumerate(STAGES)}


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def stage_index(stage):
    """Return the position of a stage in the process."""
    name = normalise_identifier(stage, "stage")
    if name not in _STAGE_INDEX:
        raise ValueError(
            "unknown stage %r; the process runs %s" % (name, " -> ".join(STAGE_ORDER))
        )
    return _STAGE_INDEX[name]


def required_artefacts(stage, qualification_status=None):
    """Return the artefacts a stage owes for a candidate in this state."""
    index = stage_index(stage)
    artefacts = list(STAGES[index][1])
    if STAGE_ORDER[index] != "procurement-and-qualification":
        return tuple(artefacts)
    if qualification_status is None:
        return tuple(artefacts)
    state = normalise_identifier(qualification_status, "qualification_status")
    if state not in QUALIFICATION_STATES:
        raise ValueError(
            "unknown qualification state %r; known states are %s"
            % (state, "/".join(QUALIFICATION_STATES))
        )
    if state != "qualified-for-this-application":
        artefacts.append(CONDITIONAL_ARTEFACT)
    return tuple(artefacts)


def validate_product_tree(product_tree):
    """Return the normalised product tree keyed by node."""
    if not isinstance(product_tree, (list, tuple)) or not product_tree:
        raise ValueError("product_tree must be a non-empty sequence of nodes")
    nodes = {}
    for position, item in enumerate(product_tree):
        if not isinstance(item, dict):
            raise ValueError("product_tree[%d] must be a mapping" % position)
        node = normalise_identifier(item.get("node"), "product_tree[%d].node" % position)
        if node in nodes:
            raise ValueError("product tree node %r appears twice" % node)
        decision = normalise_identifier(
            item.get("make_or_buy"), "product_tree[%d].make_or_buy" % position
        )
        if decision not in MAKE_OR_BUY:
            raise ValueError(
                "product_tree[%d].make_or_buy must be one of %s, got %r"
                % (position, "/".join(MAKE_OR_BUY), decision)
            )
        nodes[node] = {"node": node, "make_or_buy": decision}
    return nodes


def validate_candidates(candidates):
    """Return the normalised off-the-shelf candidates keyed by identifier."""
    if not isinstance(candidates, (list, tuple)):
        raise ValueError("candidates must be a sequence")
    out = {}
    for position, item in enumerate(candidates):
        if not isinstance(item, dict):
            raise ValueError("candidates[%d] must be a mapping" % position)
        ref = normalise_identifier(item.get("candidate"), "candidates[%d].candidate" % position)
        if ref in out:
            raise ValueError("candidate %r appears twice" % ref)
        node = normalise_identifier(item.get("node"), "candidates[%d].node" % position)
        state = normalise_identifier(
            item.get("qualification_status"), "candidates[%d].qualification_status" % position
        )
        if state not in QUALIFICATION_STATES:
            raise ValueError(
                "candidates[%d].qualification_status must be one of %s, got %r"
                % (position, "/".join(QUALIFICATION_STATES), state)
            )
        evidence = item.get("evidence", [])
        if not isinstance(evidence, (list, tuple, set, frozenset)):
            raise ValueError("candidates[%d].evidence must be a collection" % position)
        held = set()
        for artefact in evidence:
            name = normalise_identifier(artefact, "candidates[%d].evidence item" % position)
            if name not in KNOWN_ARTEFACTS:
                raise ValueError(
                    "candidates[%d] carries unknown artefact %r; known artefacts are %s"
                    % (position, name, "/".join(KNOWN_ARTEFACTS))
                )
            held.add(name)
        out[ref] = {
            "candidate": ref,
            "node": node,
            "qualification_status": state,
            "evidence": frozenset(held),
        }
    return out


def stage_completion(candidate):
    """Return the per-stage completeness of one normalised candidate."""
    if not isinstance(candidate, dict) or "evidence" not in candidate:
        raise ValueError("candidate must be a normalised candidate mapping")
    held = candidate["evidence"]
    completion = []
    for stage in STAGE_ORDER:
        owed = required_artefacts(stage, candidate["qualification_status"])
        missing = tuple(a for a in owed if a not in held)
        completion.append({
            "stage": stage,
            "required": owed,
            "missing": missing,
            "complete": not missing,
        })
    return completion


def stage_reached(completion):
    """Return the last stage whose predecessors are all complete."""
    if not isinstance(completion, (list, tuple)) or not completion:
        raise ValueError("completion must be the per-stage completeness list")
    reached = None
    for entry in completion:
        if not entry["complete"]:
            break
        reached = entry["stage"]
    return reached


def sequence_findings(candidate_ref, completion):
    """Report evidence produced for a later stage while an earlier one is open."""
    if not isinstance(completion, (list, tuple)):
        raise ValueError("completion must be the per-stage completeness list")
    findings = []
    open_stage = None
    for entry in completion:
        if not entry["complete"]:
            if open_stage is None:
                open_stage = entry["stage"]
            continue
        if open_stage is not None:
            findings.append({
                "code": "stage-evidence-out-of-sequence",
                "severity": "advisory",
                "candidate": candidate_ref,
                "message": "%s has completed %s while %s is still open"
                           % (candidate_ref, entry["stage"], open_stage),
            })
    return findings


def product_tree_findings(nodes, candidates):
    """Reconcile the candidates with the product tree in both directions."""
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError("nodes must be the non-empty normalised product tree")
    if not isinstance(candidates, dict):
        raise ValueError("candidates must be the normalised candidate mapping")
    findings = []
    covered = set()
    for ref in sorted(candidates):
        candidate = candidates[ref]
        node = candidate["node"]
        if node not in nodes:
            findings.append({
                "code": "candidate-node-not-in-product-tree",
                "severity": "blocking",
                "candidate": ref,
                "message": "%s is attached to node %r, which the product tree does not carry"
                           % (ref, node),
            })
            continue
        covered.add(node)
        decision = nodes[node]["make_or_buy"]
        if decision == "make":
            findings.append({
                "code": "ots-candidate-on-make-node",
                "severity": "blocking",
                "candidate": ref,
                "message": "%s offers an off-the-shelf item for node %r, which the project "
                           "decided to make" % (ref, node),
            })
        elif decision == "buy-custom":
            findings.append({
                "code": "ots-candidate-on-custom-buy-node",
                "severity": "advisory",
                "candidate": ref,
                "message": "%s offers an off-the-shelf item for node %r, which is a custom "
                           "buy" % (ref, node),
            })
    for node in sorted(nodes):
        if nodes[node]["make_or_buy"] == "buy-ots" and node not in covered:
            findings.append({
                "code": "buy-ots-node-without-candidate",
                "severity": "blocking",
                "candidate": None,
                "message": "node %r is decided as an off-the-shelf buy with no candidate "
                           "against it" % node,
            })
    return findings


def assess_ots_process(spec):
    """Scope the off-the-shelf selection process across a project product tree.

    spec keys: product_tree (sequence of nodes), candidates (sequence of
    off-the-shelf candidates, may be empty).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "product_tree" not in spec:
        raise ValueError("spec missing required key 'product_tree'")
    nodes = validate_product_tree(spec["product_tree"])
    candidates = validate_candidates(spec.get("candidates", []))
    findings = product_tree_findings(nodes, candidates)
    records = {}
    depth_total = 0
    for ref in sorted(candidates):
        completion = stage_completion(candidates[ref])
        reached = stage_reached(completion)
        depth = 0 if reached is None else stage_index(reached) + 1
        depth_total += depth
        records[ref] = {
            "candidate": ref,
            "node": candidates[ref]["node"],
            "qualification_status": candidates[ref]["qualification_status"],
            "completion": completion,
            "stage_reached": reached,
            "stages_complete": depth,
        }
        findings.extend(sequence_findings(ref, completion))
    blocking = [f for f in findings if f["severity"] == "blocking"]
    if candidates:
        maturity = depth_total / float(len(candidates) * len(STAGE_ORDER))
    else:
        maturity = 0.0
    incomplete = [r for r in records.values() if r["stages_complete"] < len(STAGE_ORDER)]
    if blocking:
        decision = "process-not-integrated"
    elif not candidates or incomplete:
        decision = "process-incomplete"
    else:
        decision = "process-complete"
    return {
        "nodes": nodes,
        "candidates": records,
        "process_maturity": maturity,
        "incomplete_candidates": tuple(sorted(r["candidate"] for r in incomplete)),
        "findings": findings,
        "blocking_findings": blocking,
        "decision": decision,
    }
