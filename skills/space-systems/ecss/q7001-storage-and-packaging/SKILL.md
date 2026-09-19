---
name: q7001-storage-and-packaging
description: "Derive the packaging and storage provisions that hold a cleanliness level while hardware waits, and the interval at which the package must be opened and re-verified. Use when flight hardware leaves an integration hall for a store and somebody must state how it is bagged, purged and shelved, and when it has to be checked again. Validates barrier layers against the sensitivity, refuses packaging materials not permitted in contact with flight hardware, demands desiccant and purge state where the item needs them, projects residue accumulation across the planned storage, computes the days until the requirement or the purge margin runs out, and reports the earliest limit and what bound it. Trigger: ecss, q-st-70-01, cleanliness-preserving-packaging, barrier-bag-layer-count, storage-purge-pressure-hold, residue-accumulation-projection, cleanliness-re-verification-interval."
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
  tags: [ecss, q-st-70-cleanliness-control-scope, q7001-storage-and-packaging, cleanliness-preserving-packaging, barrier-bag-layer-count, storage-purge-pressure-hold, residue-accumulation-projection, cleanliness-re-verification-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Control — Storage and Packaging (space-systems/ecss/q7001-storage-and-packaging)

Use when the task is putting cleaned hardware away and keeping it at
the level it was cleaned to — the barrier configuration, the purge, the
store it sits in, and the date on which the package has to be opened
and the level demonstrated again.

## Domain quick reference

- Packaging is a barrier count, not a bag. The layer against the
  hardware is the one that matters, and it is also the one that gets
  handled every time the item is moved, so a sensitivity demanding
  three layers is not satisfied by one good bag inside a crate.
- Materials are qualified for contact, not for convenience.
  Plasticised films, untreated foams, board and sulphur-cured
  elastomers transfer onto the surface they were bought to protect, and
  they do it slowly enough that nobody later connects the residue to
  the packaging that caused it.
- Cleanliness degrades in store. Residue accumulates inside a sealed
  bag at a slow, roughly linear rate over the intervals hardware
  actually waits, so the level at the end of storage is projected
  rather than assumed equal to the level at packing.
- A purge is a consumable, not a state. Positive pressure decays
  through the seam and through the film, and the day it reaches its
  floor is the day the bag stops being a barrier and becomes a cover.
- The re-verification interval is the earliest of the residue
  projection, the purge hold and the programme policy ceiling. Naming
  which one bound it is the whole output: it says whether the answer is
  to re-bag, to re-purge, or to go and argue with the policy.
- The store is graded as well as the package. An item bagged to a level
  it cannot be unbagged into has to travel somewhere else to be opened,
  and that is discovered on the day somebody urgently needs the item.
- An item already at or past its limit cannot be stored at all. Putting
  it away is not a neutral act; it consumes the interval and the
  problem resurfaces later with less time to fix it.

## Workflow

1. Validate the item: sensitivity, residue limit, level at packing, the
   accumulation rate in store, and whether it is humidity sensitive or
   purge dependent.
2. Grade the packaging: barrier layers against the minimum the
   sensitivity demands, and every contact material against the refused
   list, naming what is refused.
3. Demand desiccant where the item is humidity sensitive, and a
   declared purge state — sealing pressure, floor and decay rate —
   where a purge is required.
4. Project the residue level across the planned storage and compare it
   with the requirement.
5. Compute the days until the residue projection reaches the limit, and
   refuse outright an item already past it.
6. Compute the days the purge holds before it reaches its floor,
   treating a non-leaking bag as unbounded rather than as zero.
7. Take the earliest of residue, purge and policy as the
   re-verification interval, report which limit bound it, and flag a
   planned storage longer than that interval.
8. Compare the store's class with the class the item needs to be
   unbagged into, and report the verdict with every finding.

## Pitfalls

- Counting the shipping container as a barrier layer. It protects
  against forklifts, and the layer against the hardware is still one
  bag deep.
- Choosing packaging film on availability. The refused materials are
  the ones that look most like the permitted ones on the shelf, and the
  transfer they cause is found months later as an unexplained residue.
- Treating the level at packing as the level in store. A slow
  accumulation rate over an eighteen-month wait consumes more of the
  budget than the cleaning recovered.
- Recording a purge as done rather than as a pressure with a decay
  rate. "Purged with dry nitrogen" is not a state that can be projected
  forward to a date.
- Reporting an interval without saying what bound it. Re-bagging an
  item whose interval was set by the policy ceiling changes nothing,
  and the effort is spent again at the next review.
- Storing an item in a hall it cannot be opened in. The package is
  perfect and the item is unusable without a transport that was never
  planned.

## Behavior contract (gate 3)

Barrier-layer minima, refused contact materials, the desiccant and
purge-state demands, the linear residue projection and its
already-past-the-limit refusal, the purge hold with its unbounded and
at-the-floor cases, the earliest-limit interval with its binding reason,
and the store-class check are exercised by the gate 3 contract test:
scripts/test_q7001_storage_and_packaging.py against
scripts/q7001_storage_and_packaging_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_storage_and_packaging.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
