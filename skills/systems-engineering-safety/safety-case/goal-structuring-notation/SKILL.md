---
name: goal-structuring-notation
description: "Use when you must build or validate a Goal Structuring Notation (GSN) safety argument for a certification claim: decompose the top goal into sub-goals through a strategy, attach safety assessment evidence as solution nodes, record context, assumptions and justifications, and run the argument validity checks (acyclicity, exactly one top goal, every leaf goal supported by a solution, no dangling references, strategies decomposed, away-goal justification). Produces the validated argument graph with the support coverage score and issue list, and the metrics that gate the safety-case submission. Trigger: goal structuring notation, GSN, safety argument, safety case, claim decomposition, strategy, solution node, away goal, argument validation, support coverage."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: safety-case
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: safety-case
  tags: [goal-structuring-notation, gsn, safety-argument, safety-case, claim-decomposition, solution-node, evidence-node, away-goal, argument-validation, support-coverage]
  version: 0.1.0
  author: AeroSkills
---

# Goal Structuring Notation (systems-engineering-safety/safety-case/goal-structuring-notation)

Use when the task is building or validating a GSN safety argument for a
certification claim: stating the top-level claim as a goal, breaking it into
sub-goals through one or more strategies, and attaching the safety
assessment evidence (SSA reports, FHA worksheets, analysis results, test
records) as solution nodes so every leaf goal is supported. This leaf is the
argument-structure notation and validation math only: it opens the safety-case
pack and implements the goal_structuring_notation_logic module in pure Python,
stdlib only. It pairs with the arp4761a pack leaves whose safety-assessment
outputs arrive here as solution nodes, and with the mbse sysml-modeling leaf
for the distinction between a system model and an argument about the system.
The GSN Community Standard notation rules are summarized here at reference
level, never reproduced.

## Domain quick reference

- Node kinds: a goal states a claim to be argued, a strategy states the
  inference that decomposes a claim, a solution is an evidence node that
  directly supports a claim, and context, assumption and justification nodes
  attach supporting statements to any node.
- Relations: supported-by edges carry the claim decomposition and the
  evidence attachment; in-context-of edges attach context and assumption-of
  edges attach assumptions and justifications. In this module the edge points
  from the supporting element to the claim it supports, so a solution node
  points into the goal it evidences.
- Top goal: a goal with no incoming supported-by edge. A valid argument has
  exactly one.
- Leaf goal: a goal whose claim is not decomposed further (no outgoing
  supported-by edge to a strategy or goal). Every leaf goal must be supported
  by at least one solution node, or be a justified away goal.
- Away-goal convention: a goal marked away defers its support to another
  module. With REQUIRE_AWAY_JUSTIFICATION = True every away goal must carry an
  incoming edge from a justification node (any edge kind), the standard
  away-goal rule.
- Support coverage: fraction of leaf goals that are supported by a solution
  or justified away. A valid submission needs coverage 1.0.
- Depth: longest supported-by chain from the top goal to a solution, counting
  the evidence hop at the leaf.
- Evidence types: solution texts are tallied by their first-token keyword
  against the EVIDENCE_KEYWORDS constant (FHA, PSSA, SSA, test, analysis,
  inspection, similarity).
- The supported-by graph must be acyclic; context and assumption edges are
  ignored for cycle detection.

## Workflow

1. Enumerate the argument as node dicts {id, type, text} and edge dicts
   {from, to, kind}, or start from the standard skeleton with
   instantiate_skeleton(top_claim_text, strategy_text, leaf_claims), which
   builds top goal G1, strategy S1, and one goal per leaf claim.
2. Check the input model with node_map (duplicate ids raise ValueError) and
   confirm every type and edge kind is supported, since unknown node types,
   unsupported edge kinds and an empty node list raise ValueError.
3. Find dangling references with validate_ids and fix them before anything
   else.
4. Run detect_cycles for supported-by cycles (self-loops included) and break
   any cycle found; context and assumption edges never create argument
   cycles.
5. Identify top_goals and leaf_goals, then read unsupported_leaves to see
   which leaf claims still lack a solution node or a justified away deferral.
6. Attach solution nodes for the remaining leaves and re-check
   unsupported_leaves until empty, then confirm support_coverage equals 1.0.
7. Run validate_argument for the verdict {valid, issues, coverage}: it flags
   more than one top goal, cycles, dangling ids, undecomposed strategies,
   away goals without justification, and unsupported leaf goals.
8. Summarize the submission with argument_metrics (node counts, depth,
   evidence_types tally) as the safety-case gating record.
9. Confirm the deterministic checks with the contract test
   scripts/test_goal_structuring_notation.py.

## Worked example

Argument for "the flight control system is acceptably safe to operate" (top
goal G1), with strategy S1 "argument over the safety assessment evidence",
sub-goals G2 (1e-9 catastrophic target), G3 (1e-7 hazardous target) and G4
(development assurance evidence), solutions Sn1 "SSA report FCS-1" to G2,
Sn2 "FHA worksheet rev C" to G3, Sn3 "DAL assignment record" to G4, and
context C1 "certification basis FAR-25" in context of G1.

- validate_argument returns valid True with an empty issue list and coverage
  1.0; top_goals is [G1] and leaf_goals are G2, G3, G4.
- argument_metrics reports node_count 9, goal_count 4, strategy_count 1,
  solution_count 3, context_count 1, depth 3 (goal to strategy to sub-goal to
  evidence), and evidence_types {SSA: 1, FHA: 1} since the DAL record text
  matches no keyword.
- Removing solution Sn1 makes unsupported_leaves list G2 and validate_argument
  return valid False with the G2 reason; coverage drops to 2/3.
- Adding strategy S2 with supported-by edges G2 to S2 and S2 to G2 makes
  detect_cycles return the G2-S2 cycle and validation fail.
- Marking G4 away without a justification fails validation with the away-goal
  rule issue; adding justification node J1 "the DAL record is the certified
  artifact" with an assumption-of edge to G4 clears the issue (any edge kind
  from a justification node counts), and coverage stays 1.0.
- A bare skeleton from instantiate_skeleton validates as invalid with all
  leaf goals unsupported and coverage 0.0, which is the signal to attach the
  solution nodes from the safety assessment evidence.

## Verification

- Confirm validate_argument on the worked example returns valid True,
  coverage 1.0 and an empty issue list.
- Confirm removing a solution node makes unsupported_leaves name that leaf
  goal and drops the coverage below 1.0.
- Confirm the G2-S2 supported-by cycle is detected and invalidates the
  argument, and that in-context-of and assumption-of edges never create
  argument cycles.
- Confirm an away goal without an incoming justification edge is an issue and
  that a justification edge of any kind clears it (away-goal rule).
- Confirm every leaf goal needs an incoming solution edge: strategy support
  alone never covers a leaf goal.
- Confirm ValueError rejection of an unknown node type, an unsupported edge
  kind, duplicate node ids and an empty node list.
- Run the contract test offline: python3
  scripts/test_goal_structuring_notation.py (33 tests, deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/safety-assessment: the FHA/PSSA/SSA
  analysis outputs that arrive in this argument as solution nodes.
- systems-engineering-safety/arp4761a/functional-hazard-assessment: severity
  findings cited as evidence inside the sub-goals.
- systems-engineering-safety/mbse/sysml-modeling: the system model, which the
  safety argument references rather than replaces.
- systems-engineering-safety/arp4754a/development-assurance-levels: the DAL
  assignments recorded as evidence nodes for the development assurance goals.
- systems-engineering-safety/certification/certification-basis: the
  certification basis stated as context for the top goal.

## Pitfalls

- Supporting a leaf goal with a strategy: every leaf goal needs an
  incoming solution edge (or a justified away deferral), and strategy
  support alone never covers it - a bare skeleton validates invalid
  with coverage 0.0 until the evidence nodes are attached.
- Deferring an away goal without justification: with the away-goal
  rule on, every away goal must carry an incoming edge from a
  justification node (any edge kind), and an away goal marked without
  one is an issue even when its support is deferred elsewhere.
- Leaving a cycle in the supported-by graph: supported-by cycles
  (self-loops included, as in the G2-S2 case) invalidate the argument,
  and only supported-by edges count for cycle detection - context and
  assumption edges never create argument cycles.
- Submitting with more than one top goal or dangling ids: a valid
  argument has exactly one goal with no incoming supported-by edge,
  and references to nodes outside the model must be fixed before
  validation, not after.
- Reporting coverage without checking the issues list: coverage 1.0 is
  necessary but the verdict is {valid, issues, coverage} - undecomposed
  strategies, away-goal violations and multiple top goals keep valid
  False even when every leaf is covered.
- Reproducing GSN figures or standard text: the notation rules here
  are a reference-level summary of the GSN Community Standard, and
  ARP4754A frames the evidence only - no figures, tables or standard
  text are reproduced.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_goal_structuring_notation.py

The test covers the valid worked example and its metrics, the removed-solution
unsupported-leaf case, supported-by cycle detection including self-loops, the
away-goal justification rule with any justification edge kind and with the
rule toggled off, support coverage math, depth on deeper chains and with no
solutions, evidence keyword tallies, dangling id reporting, undecomposed
strategies, multiple top goals, skeleton instantiation and the attach-
solutions round trip, and ValueError rejection of malformed input.

## Compliance

- Standards referenced, not reproduced: ARP4754A (SAE) frames the
  development-assurance evidence the argument records; the GSN notation rules
  are summarized at reference level from the public description of the GSN
  Community Standard, with no reproduced figures or tables.
- compliance: STANDARDS-REF, gated: false.
