"""Goal Structuring Notation (GSN) safety argument model and validation.

Pure stdlib, deterministic. Implements the argument-structure notation and
validation math for the goal-structuring-notation leaf skill: node and edge
model, cycle detection over supported-by edges, top/leaf goal identification,
leaf support coverage, the away-goal justification rule, argument metrics, and
the standard two-level argument skeleton.

Node model: list of dicts {id, type, text} where type is one of goal,
strategy, solution, context, assumption, justification. A goal may carry an
optional "away": true flag when its support is deferred to another module.

Edge model: list of dicts {from, to, kind} where kind is one of
supported-by, in-context-of, assumption-of. Supported-by edges point from the
supporting element to the claim it supports (solution -> goal for evidence,
goal -> strategy for a decomposition, strategy -> goal for a sub-goal).

ValueError is raised for an empty node list, an unknown node type, a
duplicate node id, or an unsupported edge kind. Dangling ids are reported as
issues by validate_ids, never as exceptions.
"""

NODE_TYPES = ("goal", "strategy", "solution", "context", "assumption",
              "justification")
EDGE_KINDS = ("supported-by", "in-context-of", "assumption-of")
# Away-goal rule switch: every away goal must carry an incoming justification
# edge when this module constant is True (the GSN away-goal convention).
REQUIRE_AWAY_JUSTIFICATION = True
# Keyword prefixes tallied in solution node text by argument_metrics.
EVIDENCE_KEYWORDS = ("FHA", "PSSA", "SSA", "test", "analysis", "inspection",
                     "similarity")


def _check_nodes(nodes):
    """Raise ValueError on an empty node list, unknown type, or duplicate id."""
    if not nodes:
        raise ValueError("node list is empty")
    seen = set()
    for node in nodes:
        nid = node.get("id")
        if nid is None:
            raise ValueError("node missing id")
        if nid in seen:
            raise ValueError("duplicate node id: %s" % nid)
        seen.add(nid)
        if node.get("type") not in NODE_TYPES:
            raise ValueError("unknown node type: %s" % node.get("type"))


def _check_edges(edges):
    """Raise ValueError on an unsupported edge kind or a malformed edge."""
    for edge in edges:
        if edge.get("from") is None or edge.get("to") is None:
            raise ValueError("edge missing from or to")
        if edge.get("kind") not in EDGE_KINDS:
            raise ValueError("unsupported edge kind: %s" % edge.get("kind"))


def _validate(nodes, edges):
    """Run the shared input checks; raise ValueError on any violation."""
    _check_nodes(nodes)
    _check_edges(edges)


def _by_id(nodes):
    """Return {id: node} for the node list (input already validated)."""
    return {node["id"]: node for node in nodes}


def _supported_by_edges(edges):
    """Return the edges whose kind is supported-by (any valid endpoints)."""
    return [e for e in edges if e["kind"] == "supported-by"]


def _incoming(node_id, edges):
    """Return the ids of nodes with a supported-by edge into node_id."""
    return [e["from"] for e in _supported_by_edges(edges) if e["to"] == node_id]


def _outgoing(node_id, edges):
    """Return the ids of nodes reached by a supported-by edge from node_id."""
    return [e["to"] for e in _supported_by_edges(edges) if e["from"] == node_id]


def node_map(nodes):
    """Map node ids to node dicts; ValueError on duplicates or bad input."""
    _check_nodes(nodes)
    return _by_id(nodes)


def validate_ids(nodes, edges):
    """Return issue strings for every dangling edge endpoint (empty if none)."""
    _validate(nodes, edges)
    ids = set(node["id"] for node in nodes)
    issues = []
    for edge in edges:
        if edge["from"] not in ids:
            issues.append("dangling edge from %s: node not found" % edge["from"])
        if edge["to"] not in ids:
            issues.append("dangling edge to %s: node not found" % edge["to"])
    return issues


def _cycle_key(cycle):
    """Canonical key for a closed cycle path so duplicates collapse."""
    body = cycle[:-1]
    rotations = [tuple(body[i:] + body[:i]) for i in range(len(body))]
    return min(rotations)


def detect_cycles(nodes, edges, kind="supported-by"):
    """Return closed directed cycles over edges of the given kind.

    DFS over the directed edges whose kind matches (supported-by by default;
    in-context-of and assumption-of edges never create argument cycles).
    Each cycle is a list of node ids that starts and ends on the same node.
    """
    _validate(nodes, edges)
    ids = set(node["id"] for node in nodes)
    adjacency = {}
    for edge in edges:
        if edge["kind"] != kind:
            continue
        if edge["from"] in ids and edge["to"] in ids:
            adjacency.setdefault(edge["from"], []).append(edge["to"])
    white = set(ids)
    grey = set()
    cycles = []
    found = set()

    def dfs(node_id, stack):
        white.discard(node_id)
        grey.add(node_id)
        stack.append(node_id)
        for nxt in adjacency.get(node_id, []):
            if nxt in grey:
                start = stack.index(nxt)
                cycle = stack[start:] + [nxt]
                key = _cycle_key(cycle)
                if key not in found:
                    found.add(key)
                    cycles.append(cycle)
            elif nxt in white:
                dfs(nxt, stack)
        stack.pop()
        grey.discard(node_id)

    for node in nodes:
        if node["id"] in white:
            dfs(node["id"], [])
    return cycles


def top_goals(nodes, edges):
    """Return the goals with no incoming supported-by edge, in node order."""
    _validate(nodes, edges)
    ids = set(node["id"] for node in nodes)
    incoming = set()
    for edge in _supported_by_edges(edges):
        if edge["to"] in ids and edge["from"] in ids:
            incoming.add(edge["to"])
    return [n["id"] for n in nodes
            if n["type"] == "goal" and n["id"] not in incoming]


def leaf_goals(nodes, edges):
    """Return the goals with no sub-claims, in node order.

    A goal is a leaf when it has no outgoing supported-by edge to a strategy
    or goal, meaning its claim is not decomposed any further.
    """
    _validate(nodes, edges)
    ids = set(node["id"] for node in nodes)
    by_id = _by_id(nodes)
    decomposed = set()
    for edge in _supported_by_edges(edges):
        if edge["from"] not in ids or edge["to"] not in ids:
            continue
        target = by_id[edge["to"]]
        if target["type"] in ("strategy", "goal"):
            decomposed.add(edge["from"])
    return [n["id"] for n in nodes
            if n["type"] == "goal" and n["id"] not in decomposed]


def _justification_of(node_id, nodes, edges):
    """True when an incoming edge from a justification node reaches node_id."""
    by_id = _by_id(nodes)
    for edge in edges:
        if edge["to"] != node_id:
            continue
        source = by_id.get(edge["from"])
        if source is not None and source["type"] == "justification":
            return True
    return False


def _has_solution_support(node_id, nodes, edges):
    """True when an incoming supported-by edge from a solution exists."""
    by_id = _by_id(nodes)
    for edge in _supported_by_edges(edges):
        if edge["to"] != node_id:
            continue
        source = by_id.get(edge["from"])
        if source is not None and source["type"] == "solution":
            return True
    return False


def _is_away(node_id, nodes):
    """True when the goal carries the away flag."""
    for node in nodes:
        if node["id"] == node_id:
            return bool(node.get("away", False))
    return False


def unsupported_leaves(nodes, edges):
    """Return leaf goals with no supporting solution, in node order.

    A leaf goal is supported when a solution node points into it. An away
    goal may defer its support instead: when REQUIRE_AWAY_JUSTIFICATION is
    True it must carry an incoming justification edge, and when the constant
    is False the deferral needs no justification at all.
    """
    _validate(nodes, edges)
    unsupported = []
    for leaf in leaf_goals(nodes, edges):
        if _has_solution_support(leaf, nodes, edges):
            continue
        if _is_away(leaf, nodes):
            if not REQUIRE_AWAY_JUSTIFICATION:
                continue
            if _justification_of(leaf, nodes, edges):
                continue
        unsupported.append(leaf)
    return unsupported


def _leaf_covered(leaf, nodes, edges):
    """True when the leaf goal is supported or justified away."""
    if _has_solution_support(leaf, nodes, edges):
        return True
    if _is_away(leaf, nodes):
        if not REQUIRE_AWAY_JUSTIFICATION:
            return True
        return _justification_of(leaf, nodes, edges)
    return False


def support_coverage(nodes, edges):
    """Return the fraction of leaf goals that are supported or justified away.

    Returns 0.0 when the graph has no leaf goals.
    """
    _validate(nodes, edges)
    leaves = leaf_goals(nodes, edges)
    if not leaves:
        return 0.0
    covered = sum(1 for leaf in leaves if _leaf_covered(leaf, nodes, edges))
    return covered / float(len(leaves))


def _depth_from(node_id, adjacency, by_type, memo, in_path):
    """Longest supported-by path from node_id to a solution, or None.

    Returns None when no solution is reachable from node_id, so chains that
    dead-end at an unsupported claim never inflate the depth. in_path guards
    cyclic graphs from looping forever.
    """
    if node_id in memo:
        return memo[node_id]
    if by_type.get(node_id) == "solution":
        memo[node_id] = 0
        return 0
    in_path.add(node_id)
    best = None
    for nxt in adjacency.get(node_id, []):
        if nxt in in_path:
            continue
        rest = _depth_from(nxt, adjacency, by_type, memo, in_path)
        if rest is not None:
            length = 1 + rest
            if best is None or length > best:
                best = length
    in_path.discard(node_id)
    memo[node_id] = best
    return best


def _depth(nodes, edges):
    """Longest supported-by chain from a top goal to a solution.

    Solution edges are stored solution -> goal, so the evidence hop at a leaf
    is traversed goal -> solution. Returns 0 when no solution is reachable.
    """
    ids = set(node["id"] for node in nodes)
    by_type = {node["id"]: node["type"] for node in nodes}
    adjacency = {}
    for edge in _supported_by_edges(edges):
        if edge["from"] not in ids or edge["to"] not in ids:
            continue
        if by_type[edge["from"]] == "solution":
            adjacency.setdefault(edge["to"], []).append(edge["from"])
        else:
            adjacency.setdefault(edge["from"], []).append(edge["to"])
    tops = top_goals(nodes, edges)
    if not tops:
        return 0
    lengths = [_depth_from(t, adjacency, by_type, {}, set()) for t in tops]
    lengths = [length for length in lengths if length is not None]
    return max(lengths) if lengths else 0


def _evidence_tally(nodes):
    """Count solution nodes whose first text token matches a keyword."""
    tally = {}
    for node in nodes:
        if node["type"] != "solution":
            continue
        text = (node.get("text") or "").strip()
        if not text:
            continue
        token = text.split()[0].strip(".,;:!?()")
        for keyword in EVIDENCE_KEYWORDS:
            if token.casefold() == keyword.casefold():
                tally[keyword] = tally.get(keyword, 0) + 1
                break
    return tally


def argument_metrics(nodes, edges):
    """Return the argument metrics dict for the graph."""
    _validate(nodes, edges)
    counts = {"goal": 0, "strategy": 0, "solution": 0, "context": 0}
    for node in nodes:
        if node["type"] in counts:
            counts[node["type"]] += 1
    return {
        "node_count": len(nodes),
        "depth": _depth(nodes, edges),
        "goal_count": counts["goal"],
        "strategy_count": counts["strategy"],
        "solution_count": counts["solution"],
        "context_count": counts["context"],
        "evidence_types": _evidence_tally(nodes),
    }


def _away_rule_issues(nodes, edges):
    """Issue strings for away goals without justification (rule on)."""
    if not REQUIRE_AWAY_JUSTIFICATION:
        return []
    issues = []
    for node in nodes:
        if node["type"] == "goal" and node.get("away", False):
            if not _justification_of(node["id"], nodes, edges):
                issues.append(
                    "away goal %s lacks an incoming justification edge "
                    "(away-goal rule)" % node["id"])
    return issues


def validate_argument(nodes, edges):
    """Return {valid, issues, coverage} for the whole argument graph.

    Valid requires exactly one top goal, no supported-by cycles, no dangling
    ids, no undecomposed strategy, no away-goal rule violation, and no
    unsupported leaf goals. Coverage is computed regardless of validity.
    """
    _validate(nodes, edges)
    issues = []
    tops = top_goals(nodes, edges)
    if len(tops) != 1:
        issues.append("exactly one top goal required, found %d "
                      "(top goals: %s)" % (len(tops), ", ".join(tops)))
    dangling = validate_ids(nodes, edges)
    issues.extend(dangling)
    for cycle in detect_cycles(nodes, edges):
        issues.append("supported-by cycle: %s" % " -> ".join(cycle))
    by_type = {node["id"]: node["type"] for node in nodes}
    outgoing = {}
    for edge in _supported_by_edges(edges):
        outgoing.setdefault(edge["from"], []).append(edge["to"])
    for node in nodes:
        if node["type"] == "strategy" and not outgoing.get(node["id"]):
            issues.append("strategy %s is not decomposed "
                          "(no supported-by sub-goals)" % node["id"])
    issues.extend(_away_rule_issues(nodes, edges))
    for leaf in unsupported_leaves(nodes, edges):
        issues.append("unsupported leaf goal %s: no solution node supports "
                      "it" % leaf)
    return {
        "valid": not issues,
        "issues": issues,
        "coverage": support_coverage(nodes, edges),
    }


def instantiate_skeleton(top_claim_text, strategy_text, leaf_claims=None):
    """Build the two-level argument skeleton as (nodes, edges).

    The skeleton is a top goal G1, one strategy S1, and one leaf goal per
    entry of leaf_claims (G2, G3, ...), connected G1 -> S1 -> each leaf goal.
    No solution nodes are attached; validation of the bare skeleton reports
    every leaf goal as unsupported, which is the workflow signal to attach
    evidence nodes.
    """
    claims = list(leaf_claims) if leaf_claims is not None else []
    if not top_claim_text or not str(top_claim_text).strip():
        raise ValueError("top claim text must be a non-empty string")
    if not strategy_text or not str(strategy_text).strip():
        raise ValueError("strategy text must be a non-empty string")
    for claim in claims:
        if not claim or not str(claim).strip():
            raise ValueError("leaf claim text must be a non-empty string")
    nodes = [
        {"id": "G1", "type": "goal", "text": str(top_claim_text).strip()},
        {"id": "S1", "type": "strategy", "text": str(strategy_text).strip()},
    ]
    edges = [{"from": "G1", "to": "S1", "kind": "supported-by"}]
    for index, claim in enumerate(claims, start=2):
        gid = "G%d" % index
        nodes.append({"id": gid, "type": "goal", "text": str(claim).strip()})
        edges.append({"from": "S1", "to": gid, "kind": "supported-by"})
    return nodes, edges
