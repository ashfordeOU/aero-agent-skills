"""Required contents of the device architecture definition report.

Anchor: ECSS-E-ST-20-40C Annex G (architecture definition report data item --
the block structure of the device, the partitioning of functions onto those
blocks, and the design trade offs behind the chosen partitioning).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Check the supplied section list against the required contents.
2. Validate the blocks and the function-to-block allocation, and grade the
   partitioning for unallocated functions, doubly allocated functions and
   blocks hosting nothing.
3. Validate the connection list, split it into within-block and across-block
   links using the allocation, and compute the coupling ratio and the
   external degree of every block.
4. Validate the trade study (weights positive and summing to one, scores in
   the declared scale), compute the weighted score of every option, rank
   them, take the margin to the runner-up and perturb each weight to find a
   criterion whose movement reverses the recommendation.
"""

import math

__all__ = [
    "REQUIRED_SECTIONS",
    "WEIGHT_SUM_TOLERANCE",
    "SCORE_TIE_TOLERANCE",
    "DEFAULT_SENSITIVITY_STEP",
    "missing_sections",
    "validate_blocks",
    "validate_functions",
    "allocation_map",
    "partitioning_findings",
    "validate_connections",
    "split_connections",
    "coupling_ratio",
    "external_degree",
    "most_connected_block",
    "validate_trade_study",
    "option_scores",
    "rank_options",
    "decision_margin",
    "sensitivity_flips",
    "assess_architecture_report",
]

REQUIRED_SECTIONS = (
    "scope",
    "architecture-overview",
    "block-structure",
    "function-allocation",
    "interface-definition",
    "design-trade-offs",
)

# Declared criterion weights have to sum to one; absorb representation error
# in the sum rather than rescaling the designer's weights.
WEIGHT_SUM_TOLERANCE = 1e-9

# Two option scores closer than this are a tie, not a ranking.
SCORE_TIE_TOLERANCE = 1e-12

DEFAULT_SENSITIVITY_STEP = 0.05


def _identifier(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    out = value.strip()
    if not out:
        raise ValueError("%s must not be empty" % label)
    return out


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def missing_sections(sections):
    """Return the required sections absent from the supplied section list."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list or tuple of section names")
    present = set()
    for i, name in enumerate(sections):
        present.add(_identifier(name, "sections[%d]" % i).lower())
    return [name for name in REQUIRED_SECTIONS if name not in present]


def validate_blocks(blocks):
    """Return the ordered block identifiers, rejecting duplicates."""
    if not isinstance(blocks, (list, tuple)) or not blocks:
        raise ValueError("blocks must be a non-empty sequence of block identifiers")
    out = []
    for i, block in enumerate(blocks):
        identifier = _identifier(block, "blocks[%d]" % i)
        if identifier in out:
            raise ValueError("duplicate block identifier %r" % identifier)
        out.append(identifier)
    return out


def validate_functions(functions, block_ids):
    """Return normalized function records with their allocation lists."""
    if not isinstance(functions, (list, tuple)) or not functions:
        raise ValueError("functions must be a non-empty sequence")
    known = set(block_ids)
    records = []
    seen = set()
    for item in functions:
        if not isinstance(item, dict):
            raise ValueError("function must be a mapping")
        for key in ("id", "allocated_to"):
            if key not in item:
                raise ValueError("function missing required key '%s'" % key)
        identifier = _identifier(item["id"], "function id")
        if identifier in seen:
            raise ValueError("duplicate function identifier %r" % identifier)
        seen.add(identifier)
        targets = item["allocated_to"]
        if isinstance(targets, str):
            targets = [targets]
        if not isinstance(targets, (list, tuple)):
            raise ValueError("allocated_to of %s must be a block id or a sequence" % identifier)
        resolved = []
        for j, target in enumerate(targets):
            block = _identifier(target, "%s allocated_to[%d]" % (identifier, j))
            if block not in known:
                raise ValueError(
                    "function %s is allocated to %r, which the block list does not declare"
                    % (identifier, block)
                )
            if block not in resolved:
                resolved.append(block)
        records.append({"id": identifier, "allocated_to": resolved})
    return records


def allocation_map(functions):
    """Return function identifier -> the single block it sits on, where unique."""
    mapping = {}
    for record in functions:
        if len(record["allocated_to"]) == 1:
            mapping[record["id"]] = record["allocated_to"][0]
    return mapping


def partitioning_findings(functions, block_ids):
    """Return the unallocated functions, doubly allocated functions and empty blocks."""
    unallocated = [r["id"] for r in functions if not r["allocated_to"]]
    doubled = [r["id"] for r in functions if len(r["allocated_to"]) > 1]
    hosted = set()
    for record in functions:
        for block in record["allocated_to"]:
            hosted.add(block)
    empty = [block for block in block_ids if block not in hosted]
    return {
        "unallocated_functions": unallocated,
        "doubly_allocated_functions": doubled,
        "empty_blocks": empty,
    }


def validate_connections(connections, function_ids):
    """Return the deduplicated connection pairs, rejecting dangling endpoints."""
    if not isinstance(connections, (list, tuple)):
        raise ValueError("connections must be a sequence of function pairs")
    known = set(function_ids)
    out = []
    seen = set()
    for i, item in enumerate(connections):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("connections[%d] must be a pair of function identifiers" % i)
        a = _identifier(item[0], "connections[%d][0]" % i)
        b = _identifier(item[1], "connections[%d][1]" % i)
        for endpoint in (a, b):
            if endpoint not in known:
                raise ValueError(
                    "connection endpoint %r is not a declared function" % endpoint
                )
        if a == b:
            raise ValueError("connection %d joins function %r to itself" % (i, a))
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        out.append((a, b))
    return out


def split_connections(connections, allocation):
    """Return (within_block, across_block) connection lists for an allocation."""
    within = []
    across = []
    for a, b in connections:
        if a not in allocation or b not in allocation:
            raise ValueError(
                "connection %s-%s touches a function with no single block allocation" % (a, b)
            )
        if allocation[a] == allocation[b]:
            within.append((a, b))
        else:
            across.append((a, b))
    return (within, across)


def coupling_ratio(within, across):
    """Return the across-block share of all connections."""
    total = len(within) + len(across)
    if total == 0:
        raise ValueError("cannot compute a coupling ratio with no connections")
    return float(len(across)) / float(total)


def external_degree(block_ids, across, allocation):
    """Return block identifier -> number of across-block connections touching it."""
    degree = dict((block, 0) for block in block_ids)
    for a, b in across:
        degree[allocation[a]] += 1
        degree[allocation[b]] += 1
    return degree


def most_connected_block(degree):
    """Return the block with the highest external degree (lowest id wins ties)."""
    if not isinstance(degree, dict) or not degree:
        raise ValueError("degree must be a non-empty mapping")
    best = None
    for block in sorted(degree):
        if best is None or degree[block] > degree[best]:
            best = block
    return best


def validate_trade_study(study):
    """Return a normalized trade study with validated weights and scores."""
    if not isinstance(study, dict):
        raise ValueError("trade study must be a mapping")
    for key in ("criteria", "options", "score_scale"):
        if key not in study:
            raise ValueError("trade study missing required key '%s'" % key)
    criteria = study["criteria"]
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("trade study criteria must be a non-empty mapping of weights")
    weights = {}
    total = 0.0
    for name, weight in criteria.items():
        key = _identifier(name, "criterion name")
        value = _real(weight, "weight of %s" % key)
        if value <= 0.0:
            raise ValueError("weight of %s must be positive, got %g" % (key, value))
        weights[key] = value
        total += value
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=WEIGHT_SUM_TOLERANCE):
        raise ValueError("criterion weights must sum to 1, they sum to %.9f" % total)
    scale = study["score_scale"]
    if not isinstance(scale, (list, tuple)) or len(scale) != 2:
        raise ValueError("score_scale must be a (low, high) pair")
    low = _real(scale[0], "score_scale low")
    high = _real(scale[1], "score_scale high")
    if high <= low:
        raise ValueError("score_scale high must exceed low")
    options = study["options"]
    if not isinstance(options, dict) or len(options) < 2:
        raise ValueError("a trade study needs at least two options")
    normalized = {}
    for name, scores in options.items():
        key = _identifier(name, "option name")
        if not isinstance(scores, dict):
            raise ValueError("scores of option %s must be a mapping" % key)
        row = {}
        for criterion in weights:
            if criterion not in scores:
                raise ValueError("option %s has no score for criterion %s" % (key, criterion))
            value = _real(scores[criterion], "score of %s on %s" % (key, criterion))
            if value < low or value > high:
                raise ValueError(
                    "score of %s on %s is %g, outside the scale [%g, %g]"
                    % (key, criterion, value, low, high)
                )
            row[criterion] = value
        for criterion in scores:
            if _identifier(criterion, "score criterion") not in weights:
                raise ValueError(
                    "option %s carries a score for %r, which is not a declared criterion"
                    % (key, criterion)
                )
        normalized[key] = row
    return {"criteria": weights, "options": normalized, "score_scale": (low, high)}


def option_scores(study, weights=None):
    """Return option identifier -> weighted score under the given weights."""
    normalized = validate_trade_study(study)
    use = weights if weights is not None else normalized["criteria"]
    out = {}
    for name, row in normalized["options"].items():
        out[name] = sum(use[criterion] * row[criterion] for criterion in use)
    return out


def rank_options(scores):
    """Return option identifiers ordered by descending score (lowest id wins ties)."""
    if not isinstance(scores, dict) or not scores:
        raise ValueError("scores must be a non-empty mapping")
    return sorted(scores, key=lambda name: (-scores[name], name))


def decision_margin(scores):
    """Return the score gap between the winner and the runner-up."""
    order = rank_options(scores)
    if len(order) < 2:
        raise ValueError("a decision margin needs at least two options")
    return scores[order[0]] - scores[order[1]]


def sensitivity_flips(study, step=DEFAULT_SENSITIVITY_STEP):
    """Return the criteria whose weight shift reverses the recommendation."""
    normalized = validate_trade_study(study)
    delta = _real(step, "step")
    if delta <= 0.0 or delta >= 1.0:
        raise ValueError("sensitivity step must lie in (0, 1), got %g" % delta)
    base_winner = rank_options(option_scores(normalized))[0]
    flips = []
    for criterion in sorted(normalized["criteria"]):
        weights = dict(normalized["criteria"])
        raised = weights[criterion] + delta
        if raised >= 1.0:
            continue
        remainder = 1.0 - raised
        others_total = sum(w for name, w in weights.items() if name != criterion)
        if others_total <= 0.0:
            continue
        shifted = {criterion: raised}
        for name, weight in weights.items():
            if name != criterion:
                shifted[name] = weight * remainder / others_total
        winner = rank_options(option_scores(normalized, shifted))[0]
        if winner != base_winner:
            flips.append(criterion)
    return flips


def assess_architecture_report(report):
    """Run the full Annex G architecture definition report content assessment.

    report keys: sections, blocks, functions, connections, trade_study,
    max_coupling_ratio, optional sensitivity_step.
    """
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping")
    required = (
        "sections",
        "blocks",
        "functions",
        "connections",
        "trade_study",
        "max_coupling_ratio",
    )
    for key in required:
        if key not in report:
            raise ValueError("report missing required key '%s'" % key)
    limit = _real(report["max_coupling_ratio"], "max_coupling_ratio")
    if limit < 0.0 or limit > 1.0:
        raise ValueError("max_coupling_ratio must lie in [0, 1], got %g" % limit)

    absent = missing_sections(report["sections"])
    blocks = validate_blocks(report["blocks"])
    functions = validate_functions(report["functions"], blocks)
    defects = partitioning_findings(functions, blocks)
    allocation = allocation_map(functions)
    connections = validate_connections(report["connections"], [r["id"] for r in functions])

    findings = []
    for name in absent:
        findings.append("required section %r is absent from the report" % name)
    for ref in defects["unallocated_functions"]:
        findings.append("function %s is allocated to no block" % ref)
    for ref in defects["doubly_allocated_functions"]:
        findings.append("function %s is allocated to more than one block" % ref)
    for ref in defects["empty_blocks"]:
        findings.append("block %s hosts no function" % ref)

    if defects["unallocated_functions"] or defects["doubly_allocated_functions"]:
        ratio = None
        degree = None
        hub = None
    else:
        within, across = split_connections(connections, allocation)
        ratio = coupling_ratio(within, across)
        degree = external_degree(blocks, across, allocation)
        hub = most_connected_block(degree)
        if ratio > limit and not math.isclose(ratio, limit, rel_tol=0.0, abs_tol=SCORE_TIE_TOLERANCE):
            findings.append(
                "coupling ratio %.4f exceeds the declared limit %.4f" % (ratio, limit)
            )

    study = validate_trade_study(report["trade_study"])
    scores = option_scores(study)
    order = rank_options(scores)
    margin = decision_margin(scores)
    flips = sensitivity_flips(study, report.get("sensitivity_step", DEFAULT_SENSITIVITY_STEP))
    if margin <= SCORE_TIE_TOLERANCE:
        findings.append(
            "trade study separates %s and %s by no usable margin" % (order[0], order[1])
        )
    for criterion in flips:
        findings.append(
            "trade study recommendation flips when the weight of %s is shifted" % criterion
        )
    return {
        "missing_sections": absent,
        "blocks": blocks,
        "functions": functions,
        "partitioning": defects,
        "connections": connections,
        "coupling_ratio": ratio,
        "external_degree": degree,
        "most_connected_block": hub,
        "max_coupling_ratio": limit,
        "option_scores": scores,
        "ranking": order,
        "recommended_option": order[0],
        "decision_margin": margin,
        "sensitivity_flips": flips,
        "compliant": not findings,
        "findings": findings,
    }
