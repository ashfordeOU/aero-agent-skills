---
name: q7001-cleanliness-budget
description: "Allocate an end-of-life contamination allowance down the system, subsystem and unit levels of a programme under ECSS-Q-ST-70-01C. Use when one deposition figure on a critical surface has to become allocations each supplier can be held to, and the tree then has to close. Holds a system reserve back before anything is split, divides the remainder by declared weight, rolls the tree up from the units with deposited masses adding directly and uncertainty bands combining in quadrature, then closes every node against its own allocation. Flags over-subscription, a root beyond the allocatable pot, and allocation left largely unspent. Trigger: ecss, q-st-70-01, cleanliness-budget-allocation, contamination-budget-closure, system-subsystem-unit-allocation, deposition-budget-reserve, contamination-allocation-rollup, cleanliness-headroom-reporting."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-cleanliness-budget, cleanliness-budget-allocation, contamination-budget-closure, system-subsystem-unit-allocation, deposition-budget-reserve, contamination-allocation-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Budget Allocation Across Levels (space-systems/ecss/q7001-cleanliness-budget)

Use when the task is the allocation half of the ECSS-Q-ST-70-01C levels
clause — taking the contamination allowance a critical surface has at
end of life and splitting it into allocations the system, each
subsystem and each unit can be held to, then showing the split closes.

## Domain quick reference

- A cleanliness level on its own cannot be flowed down. What a
  subsystem can be held to is a share of the allowance, expressed in
  the same quantity as the top-level figure — deposited areal mass, or
  obscured area fraction — so that the shares are comparable and can be
  added.
- Contamination contributions superpose. Deposited mass from a
  lubricant, an adhesive and a vent plume land on the same surface and
  add directly; there is no cancellation to exploit. Quadrature belongs
  to the uncertainty band around a contribution, never to the
  contributions themselves.
- The reserve is held at the top, before the split. A contributor that
  appears late in the programme has to be funded from somewhere, and
  the only alternative to a reserve is taking allocation back from a
  subsystem that has already designed against it.
- Closure is per node, not just at the root. A root that closes can
  still hide a subsystem whose units demand more than it was given; the
  overrun is real and merely offset by headroom somewhere else in the
  tree, which its owner has no right to spend.
- Unspent allocation is information. A subsystem sitting at a third of
  its allocation is either over-designed or has not yet accounted for
  everything it will contribute, and both are worth surfacing before
  the reserve gets spent elsewhere.
- Decomposition order is part of the validation. A subsystem hanging
  under a unit means the tree does not describe the hardware, and any
  roll-up through it is meaningless however well it adds up.

## Workflow

1. Validate the top-level allowance and the reserve fraction, then hold
   the reserve back. A reserve fraction that leaves nothing to allocate
   is an input error.
2. Split the remaining pot over the contributors by declared weight, or
   accept allocations the project has already fixed by other means.
3. Validate the allocation tree: every node named, levelled and given a
   non-negative allocation; no two siblings sharing a name; every child
   strictly lower in the decomposition than its parent.
4. Roll each node up from the leaves. A node without children demands
   its own allocation; a node with children demands the combination of
   what they demand, linear for contributions and in quadrature only
   where the quantity is an uncertainty.
5. Close every node: compare demand with allocation, absorb an exact
   closure with a named tolerance, and record the headroom signed so an
   overrun is visible rather than clipped at zero.
6. Compare the root allocation against the pot left after the reserve,
   and report a root that has quietly spent the reserve.
7. Report per-node allocation, demand and headroom, plus findings:
   over-subscribed nodes, a root beyond the pot, and nodes leaving more
   than a stated fraction of their allocation unallocated.

## Pitfalls

- Combining contributions in quadrature because the numbers look like a
  budget. Deposited masses are not independent error terms; quadrature
  on them understates the total and the surface finds the difference.
- Allocating the whole allowance with no reserve. The first
  late-identified source then has to be paid for by an existing
  allocation, which means re-opening a design that was already closed
  against it.
- Checking closure only at the root. Offsetting a subsystem overrun
  against another subsystem's headroom hands one owner's margin to
  another with nobody recording the transfer.
- Clipping negative headroom to zero when reporting. An over-subscribed
  node then presents as exactly closed, which is the one state a
  reviewer will not question.
- Reading a level as an allocation. A level is a state a surface is
  verified in at a moment; an allocation is a quantity a contributor
  may add over a phase, and the two are only equal at the point where
  the budget is checked.
- Allocating against a decomposition that does not match the hardware.
  The arithmetic still closes, so the error survives until a supplier
  is held to an allocation nobody can trace to what they build.

## Behavior contract (gate 3)

The reserve hold-back, weighted split, tree and level-order validation,
linear and quadrature roll-up, per-node closure with signed headroom,
root-versus-pot comparison and the unspent-allocation report are
exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_budget.py against
scripts/q7001_cleanliness_budget_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7001_cleanliness_budget.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
