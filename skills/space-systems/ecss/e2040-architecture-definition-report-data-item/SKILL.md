---
name: e2040-architecture-definition-report-data-item
description: "Review a device architecture definition report against the required contents of ECSS-E-ST-20-40C Annex G. Use when the report has to show the block structure, the partitioning of functions onto those blocks and the trade offs the design rests on: confirm every function lands on exactly one existing block and every block hosts at least one function, split the declared connections into within-block and across-block, compute the coupling ratio and the per-block external degree the partitioning produces, then score each trade-off option on weighted criteria, rank them, measure the margin to the runner-up and perturb each weight to see whether the recommendation flips. Trigger: ecss, e-st-20-40-device-scope, e2040-architecture-definition-report-data-item, device-function-partitioning, block-coupling-ratio, external-interface-degree, design-trade-off-weighting, trade-study-sensitivity-flip."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-40-device-scope, e2040-architecture-definition-report-data-item, device-function-partitioning, block-coupling-ratio, external-interface-degree, design-trade-off-weighting, trade-study-sensitivity-flip]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Architecture Definition Report Data Item (space-systems/ecss/e2040-architecture-definition-report-data-item)

Use when the task is the required contents of the device architecture
definition report of ECSS-E-ST-20-40C Annex G -- the report that states
what blocks the device is built from, which function each block carries,
and which design options were weighed to arrive at that partitioning.

## Domain quick reference

- **Partitioning** is a total, single-valued map from the function set
  onto the block set. A function on no block is unbuilt, a function on
  two blocks is undecided, and a block with no function is a box on a
  drawing rather than a part of the architecture.
- A **connection** between two functions is either within a block or
  across blocks, and which of the two it is depends entirely on the
  partitioning, not on the function pair. Moving one function across a
  boundary converts internal connections into interfaces.
- The **coupling ratio** is the across-block connections over all
  connections. It is the figure that makes two candidate partitionings
  of the same function set comparable, and it is the reason the report
  has to carry the connection list and not only the block diagram.
- The **external degree** of a block is how many across-block
  connections touch it. A low overall coupling ratio can still hide one
  block that every other block talks to, and that block is the
  integration risk the report should name.
- A **trade off** is a weighted sum over criteria whose weights sum to
  one. Its output is not only a winner but a **margin** to the runner
  up and a **sensitivity**: if a small, defensible shift in one weight
  reverses the recommendation, the study has found two comparable
  options, not a winner.

## Workflow

1. Check the report's section list against the required contents and
   name each absent section.
2. Validate the block list, rejecting a duplicate block identifier, and
   the function list, rejecting an allocation to a block the report
   does not declare.
3. Grade the partitioning: report every function allocated to more than
   one block, every function allocated to none, and every block hosting
   no function.
4. Validate the connection list against the function set, rejecting a
   dangling endpoint and a self-connection, and collapsing a duplicated
   pair so one link is not counted twice.
5. Split the connections into within-block and across-block using the
   allocation, and compute the coupling ratio and the external degree
   of each block.
6. Validate the trade study: criteria weights positive and summing to
   one within a named tolerance, and every option scored on every
   criterion inside the declared scale.
7. Compute the weighted score of each option, rank them, take the
   margin to the runner-up, and re-run the ranking with each weight
   shifted by the declared sensitivity step to find any criterion whose
   movement flips the recommendation.
8. Report the coupling ratio against its limit, the partitioning
   defects, the most-connected block and any sensitivity flip as
   separate findings.

## Pitfalls

- Grading the block diagram instead of the allocation. A diagram shows
  the blocks; only the function-to-block map says whether anything is
  unallocated or allocated twice, and only the connection list says
  what the partitioning costs in interfaces.
- Reading a low coupling ratio as a good partitioning. The ratio is an
  average over connections, and one hub block carrying most of the
  external degree is invisible in it.
- Renormalizing trade-off weights that do not sum to one. Weights that
  miss the sum are a content defect of the report; silently scaling
  them changes the recommendation on the assessor's authority instead
  of the designer's.
- Reporting only the winning option. Without the margin to the runner
  up, a study that separated two options by a rounding error reads
  exactly like one that separated them decisively.
- Declaring a study robust because the top score is high. Robustness is
  about whether the ORDER survives a weight shift, and a high-scoring
  winner can still flip when the criterion that carried it moves a
  little.

## Behavior contract (gate 3)

The section check, block and function validation, partitioning grading,
connection splitting, coupling-ratio and external-degree computation,
trade-study validation, weighted scoring, ranking, decision margin and
sensitivity flip are exercised by the gate 3 contract test:
scripts/test_e2040_architecture_definition_report_data_item.py against
scripts/e2040_architecture_definition_report_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_architecture_definition_report_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
