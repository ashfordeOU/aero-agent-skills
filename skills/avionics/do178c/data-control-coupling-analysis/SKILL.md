---
name: data-control-coupling-analysis
description: "Use when you must analyze data coupling and control coupling between airborne software components: identify the data-coupling items between component pairs from their written and read variable sets with declared synchronization suppression, identify the control-coupling items across call edges where a caller-written variable is read by the callee, compute the coupling coverage ratio against declared evidence, and return the PASS or FAIL verdict with the uncovered item list. Produces the data-coupling item list, the control-coupling item list, the coupling coverage ratio and the evidence verdict that gate the level A inter-component coupling objective. Trigger: data coupling analysis, control coupling analysis, shared-variable pairs, call-edge coupling items, coupling coverage evidence, level-a coupling objectives, inter-component coupling."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: do178c
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [data-control-coupling-analysis, data-coupling-analysis, control-coupling-analysis, shared-variable-pairs, coupling-coverage-evidence, level-a-objectives]
  version: 0.1.0
  author: AeroSkills
---

# Data and Control Coupling Analysis (avionics/do178c/data-control-coupling-analysis)

Use when the task is DO-178C level A inter-component coupling analysis:
identifying the shared-variable data-coupling items and the call-edge
control-coupling items between airborne software components, then grading
the declared evidence against the identified items. This leaf implements
the coupling item model and the coupling coverage verdict in pure Python,
stdlib only, deterministic and offline. It pairs with
avionics/do178c/verification for intra-component structural analysis and
avionics/do178c/software-testing for the execution-based testing that
supplies coupling evidence.

## Domain quick reference

- Data coupling: two components couple through a shared variable when one
  writes it and the other reads it. A data-coupling item (A, B, var)
  exists for every ordered pair (A, B), A != B, with var in writes(A)
  intersect reads(B).
- Declared synchronization: a declared handshake or protected port
  suppresses the item it names. Declaring the synchronization (A, C, X)
  removes exactly the (A, C, X) item and nothing else.
- Control coupling: a caller transfers data to a callee through the call.
  A control-coupling item (A, B, var) exists on a declared call edge
  (A, B) for every var in writes(A) intersect reads(B).
- Data coupling is pairwise over all components; control coupling exists
  only along the declared call edges, so an item can appear in one list
  and not the other.
- Coupling coverage ratio: covered / total over the combined item lists,
  0.0 when no items are identified, always in [0, 1].
- Evidence verdict: PASS when the ratio is 1.0, that is every identified
  inter-component coupling item has declared evidence; otherwise FAIL with
  the sorted uncovered item list. No items identified is PASS at ratio
  0.0, because nothing is uncovered.
- Items sort by (A, B, var) tuple order in every output list.

## Workflow

1. Declare the components: each comp_id maps to {"writes": set,
   "reads": set}, the variables the component writes and reads.
2. Declare the call edges as directed (caller, callee) pairs and any
   declared synchronization triples (A, B, var) that suppress data items.
3. Run data_coupling_items to get the pairwise shared-variable items, with
   the sync declarations applied.
4. Run control_coupling_items over the call edges to get the call-edge
   items.
5. Collect the evidence flags: one item key (A, B, var) per item with
   evidence present (execution-based test evidence, analysis result or
   declared review record).
6. Run coupling_coverage_ratio and coverage_verdict over the combined
   data and control item lists, or run analyze_coupling once for the full
   result dict.
7. Take the verdict: PASS closes the coupling objective input for level A;
   FAIL names the uncovered_items list that the evidence campaign must
   still address.
8. Confirm the deterministic checks with the contract test
   scripts/test_data_control_coupling_analysis.py.

## Worked example

Components: A writes {X}; B reads {X} and writes {Y}; C reads {X, Y};
D writes {Y}. Call edges (A, B), (B, C). No sync declarations. Real
module outputs:

- data_coupling_items -> [(A,B,X), (A,C,X), (B,C,Y), (D,C,Y)], 4 items.
  The D-C item exists even though D has no call edge to C, because the
  data model is pairwise over all components.
- With sync_declarations {(A,C,X)}: [(A,B,X), (B,C,Y), (D,C,Y)], 3 items.
  The declared A-C handshake suppresses exactly that item.
- control_coupling_items over the two edges -> [(A,B,X), (B,C,Y)],
  2 items. No (A,C,X) control item: there is no A to C call edge.
- Evidence for all 6 combined items: ratio 1.0, verdict PASS.
- Evidence missing (A,C,X): ratio 5/6 = 0.833, verdict FAIL with
  uncovered [(A,C,X)].
- analyze_coupling returns component_count 4, total_items 6 and the same
  verdict; empty evidence on an empty item list returns ratio 0.0 with
  verdict PASS.

## Verification

- Run python3 scripts/test_data_control_coupling_analysis.py: all tests
  pass offline (34 methods, deterministic, no network, no RNG).
- Confirm data items sort by (A, B, var): [(A,B,X), (A,C,X), (B,C,Y),
  (D,C,Y)].
- Confirm the suppression rule removes exactly the declared item.
- Confirm the directional rule: (A, B, X) exists, (B, A, X) does not.
- Confirm ValueError on a sync declaration or call edge naming an unknown
  component, and on evidence for an item that was not identified.
- Confirm the empty-list verdict is PASS at ratio 0.0.

## Related leaves

- avionics/do178c/verification: intra-component structural analysis
  sibling. This leaf owns inter-component data and control coupling; that
  leaf owns the control-flow structural metrics inside a component.
- avionics/do178c/development: requirement-to-code linkage ownership, the
  input side of the level A evidence.
- avionics/do178c/software-testing: execution-based testing that supplies
  the coupling evidence this leaf grades.
- avionics/do178c/planning: the software planning artifacts that declare
  the coupling analysis approach.
- flight-test-operations/envelope/structural-coupling-test: the distinct
  airframe coupling domain of the flight control system with the
  airframe, not software inter-component coupling.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_data_control_coupling_analysis.py

It covers the four-component worked example with its exact item lists and
bounds, synchronization suppression, pairwise data coupling direction,
call-edge-only control coupling, tuple sorting, coupling coverage ratio,
PASS and FAIL verdicts with the sorted uncovered list, empty-list PASS at
ratio 0.0, ValueError rejection of unknown components and foreign
evidence, the exact analyze_coupling dict keys, and determinism.

## Compliance

- Standards referenced, not reproduced: DO-178C is a gated RTCA standard.
  This leaf names the standard and paraphrases the coupling objective as
  the requirement that every identified inter-component coupling item has
  evidence; it never reproduces the gated objective tables or appendix
  text. Name and paraphrase only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
