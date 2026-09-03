# Wave-26 leaf spec: goal-structuring-notation (systems-engineering-safety, safety-case pack - NEW PACK)

- Path: skills/systems-engineering-safety/safety-case/goal-structuring-notation/
- Pack: safety-case (NEW pack; first leaf in it)
- Standards ids: arp4754a  (Ledger Standard: arp4754a)
  NOTE: the GSN Community Standard is NOT in standards-map.yaml; name
  it in prose only (reference-only) and use arp4754a as the mapped
  frontmatter id (the argument documents development-assurance
  evidence).
- Family: systems-engineering-safety

## Claim

Build and validate a Goal Structuring Notation (GSN) safety argument
for an aircraft or system certification claim: decompose the top-level
claim (goal) into sub-goals through strategies, attach solutions
(evidence nodes: FHA/PSSA/SSA outputs, test reports, analysis results),
record context, assumptions, and justifications, and run the argument
validity checks (acyclicity, full support of every leaf goal by a
solution, every strategy decomposed, exactly one top goal, no dangling
references, away-goal justification). Produces the validated argument
graph with the support coverage score, the issue list, and the
argument metrics that gate the safety-case submission.

Does NOT do: model the system structure (mbse sysml-modeling and
n2-diagram leaves own system models; GSN is an argument about the
system, not a system model), run the safety assessment process
(arp4761a safety-assessment owns the FHA/PSSA/SSA analyses whose
outputs appear here as solutions), score design alternatives
(mbse trade-study-analysis), or author the engineering report
(cross-cutting documentation engineering-report). This leaf is the
argument-structure notation and validation math only.

## Model (implement exactly)

Node input model: nodes = list of dicts {id (str), type (one of:
goal, strategy, solution, context, assumption, justification),
text (str)}; edges = list of dicts {from (str), to (str), kind (one
of: supported-by, in-context-of, assumption-of)}. Semantics:
- goal -> strategy or goal (supported-by): a claim decomposed.
- strategy -> goal (supported-by): a strategy is supported by its
  sub-goals.
- solution -> goal or strategy (supported-by): evidence supports a
  claim. Solutions have no outgoing supported-by edges.
- context/assumption/justification attach with in-context-of /
  assumption-of edges to any node.
Away-goal convention: a goal node may be marked
{"away": true} when its support is deferred; a module rule
REQUIRE_AWAY_JUSTIFICATION = True requires every away goal to have at
least one incoming justification edge from a justification node (the
GSN away-goal rule, documented as the standard convention).
Functions:
- node_map(nodes) -> {id: node} with ValueError on duplicate ids.
- validate_ids(nodes, edges) -> issues list (dangling from/to).
- detect_cycles(nodes, edges, kind="supported-by") -> cycles list
  (DFS over supported-by edges only; ignore in-context-of for cycle
  detection).
- top_goals(nodes, edges) -> goals with no incoming supported-by edge.
- leaf_goals(nodes, edges) -> goals with no outgoing supported-by edge
  to a strategy or goal.
- unsupported_leaves(nodes, edges) -> leaf goals with no incoming
  supported-by solution edge (and not away, or away without
  justification when REQUIRE_AWAY_JUSTIFICATION).
- support_coverage(nodes, edges) -> fraction of leaf goals that are
  supported or justified-away.
- argument_metrics(nodes, edges) -> dict {node_count, depth (longest
  supported-by path from top goal to a solution), goal_count,
  strategy_count, solution_count, context_count, evidence_types
  (tally of solution text keyword prefixes: "FHA", "PSSA", "SSA",
  "test", "analysis", "inspection", "similarity" - module constant
  EVIDENCE_KEYWORDS)}.
- validate_argument(nodes, edges) -> dict {valid (bool), issues:
  [...], coverage: float}: valid when exactly one top goal, no cycles
  in supported-by, no unsupported leaf goals, no dangling ids, and no
  strategy without an outgoing supported-by edge; coverage computed
  regardless.
- instantiate_skeleton(top_claim_text, strategy_text,
  leaf_claims=[...]) -> (nodes, edges): builds the standard two-level
  argument skeleton (top goal -> strategy -> one goal per leaf claim)
  used by the SKILL workflow example (no solutions attached).
ValueError on: unknown node type, unsupported edge kind, duplicate
node ids, empty node list.

## Worked example

Argument for "the flight control system is acceptably safe" (top goal
G1):
- G1 goal "the flight control system is acceptably safe to operate"
- S1 strategy "argument over the safety assessment evidence"
- G2 goal "all catastrophic failure conditions meet the 1e-9 target"
  (supported by S1)
- G3 goal "all hazardous failure conditions meet the 1e-7 target"
  (supported by S1)
- G4 goal "development assurance evidence exists" (supported by S1)
- Sn1 solution "SSA report FCS-1" -> G2
- Sn2 solution "FHA worksheet rev C" -> G3
- Sn3 solution "DAL assignment record" -> G4
- C1 context "certification basis FAR-25" in-context-of G1
Assertions:
- validate_argument returns valid True, coverage 1.0, one top goal,
  no issues.
- Remove Sn1 -> unsupported_leaves lists G2 and validate_argument
  valid False with the G2 reason.
- Add a supported-by cycle G2 -> S2 -> G2 (create S2 strategy) ->
  detect_cycles returns the cycle and valid False.
- Away goal: mark G4 away True without justification -> issue; add a
  justification node "the DAL record is the certified artifact" with
  an assumption-of edge to G4 -> issue clears when the rule reads the
  justification edge kind (assumption-of or in-context-of from a
  justification node counts; implement as: incoming edge from a
  justification-type node with any kind).
- argument_metrics on the full graph: assert the counts.
- ValueError on an unknown node type and a duplicate id.
Keep at least 18 test methods (validation branches, cycle detection
incl. self-loop, coverage math, away-goal rule, metrics, skeleton
instantiation, ValueErrors).

## Corpus tasks (ids w26-goal-structuring-notation-1/2)

Distinctive tokens: goal structuring notation, GSN, safety argument,
safety case, claim decomposition, strategy, solution node, away goal,
argument validation, support coverage, evidence node. Avoid: sysml
diagram, n2 diagram, state machine (mbse siblings), FHA severity
rating / PSSA / SSA process (arp4761a safety-assessment), trade study
(mbse trade-study-analysis).

1. "build the goal structuring notation safety argument for the flight
   control certification claim: decompose the top goal through a
   strategy into per-severity sub-goals, attach the SSA report and FHA
   worksheet as solution nodes, and validate that every leaf goal is
   supported"
2. "validate the GSN argument graph from the safety case submission:
   check for cycles, unsupported leaf goals, dangling references, and
   the away goal justification rule, then report the support coverage"

## SKILL body notes

Pair with arp4761a safety-assessment leaves (their outputs are the
solution nodes), mbse sysml-modeling (system model vs argument
distinction), and certification equivalent-level-of-safety (findings
cited inside the argument). Compliance: GSN notation rules summarized
at reference level from the public GSN Community Standard description;
no reproduced figures or tables; standards referenced not reproduced.
This leaf opens the safety-case pack.
