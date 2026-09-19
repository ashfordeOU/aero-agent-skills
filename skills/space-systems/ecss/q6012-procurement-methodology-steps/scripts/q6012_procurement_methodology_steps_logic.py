"""Buyer working method for microwave die acquisition, step by step.

Anchor: ECSS-Q-ST-60-12C clause 10.1.2 -- the defined working method the
buyer follows through each stage of acquiring a microwave die, expressed as
an ordered set of steps, each with the record it produces, the record it
consumes, and where the method goes when the step passes and when it fails.
Paraphrased into an implementable method-integrity procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate every declared step: a recognised step name, a pass target and a
   fail target, and the records it produces and consumes.
2. Build the step graph and walk it from the entry step, so a step no path
   can reach is reported rather than assumed to run.
3. Refuse a branch pointing at a step that was never declared, and report a
   decision point offering no fail route -- a method that can only succeed
   has no method for the case that matters.
4. Walk the pass chain in order and report a step whose consumed record is
   produced only later, or produced by nobody at all.
5. Score the method maturity over step coverage, reachability, fail-path
   completeness and record coverage, and return a verdict.
"""

import math

__all__ = [
    "SCORE_TOLERANCE",
    "MANDATED_STEPS",
    "TERMINALS",
    "validate_step",
    "build_method",
    "pass_chain",
    "reachable_steps",
    "dangling_targets",
    "steps_without_fail_route",
    "record_gaps",
    "precondition_order_violations",
    "method_maturity_score",
    "assess_procurement_methodology",
]

# The maturity score is an average of quotients of counts; an exact 1.0 can
# land a few units in the last place low. Absorb that here.
SCORE_TOLERANCE = 1e-12

MANDATED_STEPS = (
    "define_requirement",
    "survey_sources",
    "issue_enquiry",
    "evaluate_offers",
    "place_order",
    "monitor_fabrication",
    "witness_acceptance",
    "receive_and_verify",
    "disposition",
)

# Where a branch is allowed to leave the method entirely.
TERMINALS = ("complete", "abandon")

_MANDATED = frozenset(MANDATED_STEPS)


def _normalise_key(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not key:
        raise ValueError("%s must not be blank" % label)
    return key


def validate_step(step, index=0):
    """Return one declared method step in canonical form."""
    if not isinstance(step, dict):
        raise ValueError("step %d must be a mapping" % index)
    if "step" not in step:
        raise ValueError("step %d must name a 'step'" % index)
    key = _normalise_key(step["step"], "step %d name" % index)
    if key not in _MANDATED:
        raise ValueError("step %d names an unrecognised method step %r"
                         % (index, step["step"]))
    on_pass = step.get("on_pass")
    on_fail = step.get("on_fail")
    targets = {}
    for label, value in (("on_pass", on_pass), ("on_fail", on_fail)):
        if value is None or (isinstance(value, str) and not value.strip()):
            targets[label] = ""
            continue
        targets[label] = _normalise_key(value, "step '%s' %s" % (key, label))
    produces = step.get("produces")
    requires = step.get("requires")
    for label, value in (("produces", produces), ("requires", requires)):
        if value is not None and not isinstance(value, str):
            raise ValueError("step '%s' %s must be text" % (key, label))
    return {
        "step": key,
        "on_pass": targets["on_pass"],
        "on_fail": targets["on_fail"],
        "produces": (produces or "").strip(),
        "requires": (requires or "").strip(),
        "position": index,
    }


def build_method(steps, entry=None):
    """Return the declared method as a step map plus its entry step."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("steps must be a non-empty sequence")
    records = {}
    order = []
    for index, step in enumerate(steps):
        record = validate_step(step, index)
        if record["step"] in records:
            raise ValueError("step '%s' is declared twice" % record["step"])
        records[record["step"]] = record
        order.append(record["step"])
    if entry is None:
        entry_key = order[0]
    else:
        entry_key = _normalise_key(entry, "entry step")
        if entry_key not in records:
            raise ValueError("entry step '%s' is not declared" % entry_key)
    return {"steps": records, "order": tuple(order), "entry": entry_key}


def pass_chain(method):
    """Return the ordered steps a passing run visits, and whether it loops."""
    if not isinstance(method, dict) or "steps" not in method:
        raise ValueError("method must be a built method map")
    steps = method["steps"]
    current = method["entry"]
    chain = []
    seen = set()
    looped = False
    while current and current not in TERMINALS:
        if current not in steps:
            break
        if current in seen:
            looped = True
            break
        seen.add(current)
        chain.append(current)
        current = steps[current]["on_pass"]
    return {"chain": tuple(chain), "looped": looped, "ends_at": current}


def reachable_steps(method):
    """Return the declared steps some path from the entry can reach."""
    if not isinstance(method, dict) or "steps" not in method:
        raise ValueError("method must be a built method map")
    steps = method["steps"]
    frontier = [method["entry"]]
    seen = set()
    while frontier:
        current = frontier.pop()
        if current in TERMINALS or current in seen or current not in steps:
            continue
        seen.add(current)
        for target in (steps[current]["on_pass"], steps[current]["on_fail"]):
            if target and target not in seen:
                frontier.append(target)
    return frozenset(seen)


def dangling_targets(method):
    """Return the branches pointing at neither a declared step nor a terminal."""
    steps = method["steps"]
    dangling = []
    for key in method["order"]:
        record = steps[key]
        for label in ("on_pass", "on_fail"):
            target = record[label]
            if not target:
                continue
            if target in steps or target in TERMINALS:
                continue
            dangling.append({"step": key, "branch": label, "target": target})
    return tuple(dangling)


def steps_without_fail_route(method):
    """Return the steps offering no route for the case where they fail."""
    steps = method["steps"]
    return tuple(key for key in method["order"] if not steps[key]["on_fail"])


def record_gaps(method):
    """Return the steps producing no record and the records nobody produces."""
    steps = method["steps"]
    produced = {steps[key]["produces"] for key in method["order"] if steps[key]["produces"]}
    silent = tuple(key for key in method["order"] if not steps[key]["produces"])
    unsourced = tuple(
        sorted(
            {
                steps[key]["requires"]
                for key in method["order"]
                if steps[key]["requires"] and steps[key]["requires"] not in produced
            }
        )
    )
    return {"steps_producing_no_record": silent, "records_with_no_producer": unsourced}


def precondition_order_violations(method):
    """Return the steps whose consumed record is only produced later on the chain."""
    steps = method["steps"]
    chain = pass_chain(method)["chain"]
    position = {key: index for index, key in enumerate(chain)}
    producer = {}
    for key in method["order"]:
        record = steps[key]["produces"]
        if record and record not in producer:
            producer[record] = key
    violations = []
    for key in chain:
        needed = steps[key]["requires"]
        if not needed:
            continue
        source = producer.get(needed)
        if source is None:
            continue
        if source not in position:
            violations.append({"step": key, "record": needed, "produced_by": source})
        elif position[source] >= position[key]:
            violations.append({"step": key, "record": needed, "produced_by": source})
    return tuple(violations)


def method_maturity_score(method):
    """Return the method maturity as the mean of its four coverage ratios."""
    steps = method["steps"]
    declared = method["order"]
    total = len(declared)
    if total == 0:
        raise ValueError("a method must declare at least one step")
    coverage = sum(1 for name in MANDATED_STEPS if name in steps) / len(MANDATED_STEPS)
    reached = reachable_steps(method)
    reach = len(reached) / total
    with_fail = sum(1 for key in declared if steps[key]["on_fail"]) / total
    with_record = sum(1 for key in declared if steps[key]["produces"]) / total
    return {
        "step_coverage": coverage,
        "reachability": reach,
        "fail_path_completeness": with_fail,
        "record_coverage": with_record,
        "score": (coverage + reach + with_fail + with_record) / 4.0,
    }


def assess_procurement_methodology(declaration):
    """Grade a declared buyer working method for microwave die acquisition.

    declaration keys: steps (sequence of {step, on_pass, on_fail, produces,
    requires}), optional entry (the step the method starts at).
    """
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be a mapping")
    if "steps" not in declaration:
        raise ValueError("declaration missing required key 'steps'")
    method = build_method(declaration["steps"], declaration.get("entry"))
    chain = pass_chain(method)
    reached = reachable_steps(method)
    unreachable = tuple(key for key in method["order"] if key not in reached)
    dangling = dangling_targets(method)
    no_fail = steps_without_fail_route(method)
    records = record_gaps(method)
    order_faults = precondition_order_violations(method)
    maturity = method_maturity_score(method)
    absent = tuple(name for name in MANDATED_STEPS if name not in method["steps"])

    findings = []
    for name in absent:
        findings.append("mandated method step '%s' is not declared" % name)
    for key in unreachable:
        findings.append("step '%s' cannot be reached from the entry step" % key)
    for item in dangling:
        findings.append(
            "step '%s' branches on %s to '%s', which is neither a declared step "
            "nor a terminal" % (item["step"], item["branch"], item["target"])
        )
    for key in no_fail:
        findings.append("step '%s' offers no route for the case where it fails" % key)
    for key in records["steps_producing_no_record"]:
        findings.append("step '%s' names no record, so its outcome leaves no evidence"
                        % key)
    for name in records["records_with_no_producer"]:
        findings.append("record '%s' is consumed but produced by no declared step" % name)
    for item in order_faults:
        findings.append(
            "step '%s' consumes record '%s', which '%s' only produces later on the "
            "pass chain" % (item["step"], item["record"], item["produced_by"])
        )
    if chain["looped"]:
        findings.append("the pass chain revisits a step instead of reaching a terminal")

    unworkable = bool(dangling) or bool(unreachable) or chain["looped"]
    if unworkable:
        verdict = "method-unworkable"
    elif findings:
        verdict = "method-gapped"
    else:
        verdict = "method-sound"
    sound = math.isclose(maturity["score"], 1.0, rel_tol=0.0, abs_tol=SCORE_TOLERANCE)

    return {
        "method": method,
        "pass_chain": chain,
        "absent_steps": absent,
        "unreachable_steps": unreachable,
        "dangling_targets": dangling,
        "steps_without_fail_route": no_fail,
        "record_gaps": records,
        "precondition_order_violations": order_faults,
        "maturity": maturity,
        "fully_mature": sound,
        "findings": findings,
        "verdict": verdict,
    }
