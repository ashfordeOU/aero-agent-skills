---
name: e2021-actuator-electronics-redundancy
description: "Evaluate whether duplicating the actuator electronics into a nominal and a redundant chain really buys single fault tolerance under ECSS-E-ST-20-21C clause 5.2.2. Use when the task is separating a second box from real duplication: categorize every block by function and by the chain it sits in, name the functions only one chain carries, collect the shared blocks no downstream duplication rescues, multiply the series blocks inside each chain and place the two chains in parallel behind the shared ones, then report the fault tolerance order and the reliability that duplicating the shared blocks would recover. Trigger: ecss, e-st-20-21-actuation-scope, actuator-electronics-redundancy, nominal-redundant-chain-duplication, actuation-single-point-failure, shared-block-reliability-penalty, actuation-fault-tolerance-order."
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
  tags: [ecss, e-st-20-21-actuation-scope, e2021-actuator-electronics-redundancy, nominal-redundant-chain-duplication, actuation-single-point-failure, shared-block-reliability-penalty, actuation-fault-tolerance-order, actuator-chain-series-parallel-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuation Electronics — Actuator Electronics Redundancy (space-systems/ecss/e2021-actuator-electronics-redundancy)

Use when the task is the duplication requirement of ECSS-E-ST-20-21C
clause 5.2.2 -- deciding whether a declared nominal and redundant
actuator electronics set actually tolerates a single failure, or
whether a shared block or an unduplicated function has left the single
point of failure exactly where it was before the second chain was
drawn.

## Domain quick reference

- Duplication is a property of the function set, not of the box count.
  Two boxes that both draw their firing enable from one sequencer, or
  that both depend on one secondary supply, are one chain in two
  housings for every failure of that shared element.
- The architecture has three populations, and they behave differently.
  A block assigned to the nominal chain and a block assigned to the
  redundant chain are alternatives; a block marked shared sits in
  series with the pair, so its failure probability multiplies the
  parallel result and no downstream duplication rescues it.
- A function that appears in one chain and not the other is the same
  defect in a different disguise. The chain that carries it alone is
  the only chain that can perform it, so the block holding it is a
  single point of failure even though it sits inside a duplicated
  architecture.
- A shared block escapes the finding only when it is internally
  redundant -- two elements inside one housing, each able to carry the
  function. That is a declared property of the block and is refused on
  a block that is not shared, because a chain block's redundancy is
  already the other chain.
- The reliability model is series inside a chain, parallel across the
  chains, and the shared blocks in series with the whole. It is not
  the verdict, but it prices the verdict: it says what the declared
  architecture reaches and what it would reach if the shared blocks
  were duplicated too.
- That difference is the engineering case. A shared sequencer at a
  five in ten failure probability caps the whole architecture at a
  half, and the number that quantifies the cap is what moves a
  duplication into the budget.

## Workflow

1. Declare every block with its function, its chain assignment, its
   failure probability and, for a shared block only, whether it is
   internally redundant. Refuse a probability outside zero to one, a
   duplicate identifier and an internal-redundancy claim on a chain
   block.
2. Partition the set into the nominal chain, the redundant chain and
   the shared blocks, and report the three populations by identifier
   so the reviewer sees the architecture the numbers came from.
3. Compare the function sets of the two chains. Name the functions
   present in both and, separately, the functions present in one only.
4. Collect the single points of failure: every shared block that is
   not internally redundant, plus every chain block holding a function
   the other chain does not carry. The fault tolerance order is one
   only when that collection is empty.
5. Compute the reliability: multiply within each chain, put the two
   chain results in parallel, and multiply by the shared blocks in
   series. Then recompute with the shared blocks duplicated and report
   the difference as the gain available.
6. Close with a verdict and the findings that block it, each naming
   the block or the function at fault.

## Pitfalls

- Reading a second box as a redundant chain. The question is which
  functions each chain can perform alone; a duplicate housing that
  still routes through one shared decoder is a single chain for every
  failure of that decoder.
- Leaving one function undoubled and calling the architecture
  single-fault tolerant. One unduplicated fire driver takes actuation
  away on its own failure, and it does so from inside a design whose
  block count looks symmetric.
- Putting a shared block in parallel with the chains in the
  reliability model. It sits in series with them, so its failure
  probability multiplies rather than being masked, and modelling it the
  wrong way reports a number the architecture cannot reach.
- Claiming internal redundancy for a block that sits in one chain. Its
  redundancy is the other chain; a second claim double counts the same
  alternative and hides the real single point.
- Reporting the reliability without the gain available. The declared
  figure says where the design is; only the difference against a fully
  duplicated shared set says what the next change is worth.

## Behavior contract (gate 3)

Block validation, chain partitioning, duplicated and unduplicated
function sets, single point of failure collection, the series parallel
reliability model, the gain from duplicating shared blocks and the
compliance verdict are exercised by the gate 3 contract test:
scripts/test_e2021_actuator_electronics_redundancy.py against
scripts/e2021_actuator_electronics_redundancy_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_actuator_electronics_redundancy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
