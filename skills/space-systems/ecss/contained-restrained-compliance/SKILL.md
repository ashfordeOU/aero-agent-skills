---
name: contained-restrained-compliance
description: "Use when verify all contained and restrained items on a spacecraft structure satisfy ECSS-E-ST-32C clause 6.3.4: categorize each item as container, restrained, latched, or tethered, confirm the load path is defined and sized for static and dynamic load cases, check that limit and ultimate factors of safety meet clause minimums, verify failure modes and their consequences are documented for every item, confirm that catastrophic or critical consequence items carry redundant restraint provisions, and flag any item failing a check before structural acceptance. Trigger: ecss, e-st-32c, e-st-32-structures-scope, contained-item, restrained-item, tether, latch, factor-of-safety, load-path, failure-mode, structural-verification."
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
  tags: [ecss, e-st-32c, e-st-32-structures-scope, contained-item, restrained-item, tether, factor-of-safety, structural-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Contained/Restrained Item Compliance (space-systems/ecss/contained-restrained-compliance)

Use when the task is verifying that every contained and restrained item
on a spacecraft structure meets ECSS-E-ST-32C clause 6.3.4 — categorizing
each item, tracing its load path to the primary structure, checking factors
of safety against clause minimums, and confirming that failure modes,
consequence categories, and redundancy provisions are in place before the
structure is accepted.

## Domain quick reference

- Clause 6.3.4 covers four item categories: a **container** is an
  enclosure (sealed vessel, pressurized bottle, battery housing) that
  holds its contents by a physical boundary; a **restrained** item is held
  in place by a mechanical element (strap, bracket, clip, band) that
  forms a discrete load path; a **latched** item is secured by a latch
  mechanism whose engagement state must be verified; a **tethered** item
  hangs from or is connected by a flexible element (wire, cord, cable) with
  a defined break load. Every item must fall into exactly one of these
  categories before its structural check proceeds.
- For each item the load path from the item mass through its
  containment/restraint element to the primary structure must be defined
  and sized for all applicable design load cases: quasi-static (limit and
  ultimate), dynamic (vibration, shock), and thermal where relevant. An
  undocumented load path is a finding regardless of the FoS values
  computed; the assessment cannot proceed without it.
- Two factor-of-safety thresholds apply to every restraint element (anchor:
  ECSS-E-ST-32C clause 6.3.4): the limit FoS (actual allowable at limit
  load divided by the limit applied load) must not fall below 1.0, and the
  ultimate FoS (allowable at failure divided by the ultimate applied load)
  must not fall below 1.5. Failure modes of the restraint element are
  documented with a consequence category (catastrophic, critical, marginal,
  negligible). Items whose release or failure consequence is catastrophic or
  critical must carry a redundant load path so that loss of any single
  restraint element does not result in uncontrolled release.

## Workflow

1. Inventory all items on the structure that require containment or
   restraint — loose hardware, batteries, pressure vessels, cable
   harnesses, deployable mechanisms — and categorize each one as
   container, restrained, latched, or tethered. Reject any item whose
   type cannot be assigned to one of these four categories; do not carry
   an unrecognized item type into the structural check.
2. For each item, confirm the load path documentation exists: the path
   from the item's centre of mass through the containment or restraint
   element to the primary structure attachment must be identified, and
   the design load cases (at minimum quasi-static limit and ultimate)
   must be listed. Flag any item without a defined load path; do not
   proceed to the FoS check for that item.
3. Compute or verify the limit and ultimate factors of safety for each
   restraint element along the load path. Confirm that the limit FoS is
   at or above 1.0 and the ultimate FoS is at or above 1.5. Record both
   values; a margin below zero (FoS below the threshold) is a structural
   finding and must be resolved before acceptance.
4. For each item document the primary failure mode of its containment or
   restraint (e.g. "strap buckle fractures under shock overload") and
   assign a consequence category to that failure. A failure mode with no
   documented text or an unrecognized consequence category is itself a
   finding; an empty record must not be read as "no finding".
5. For every item whose failure consequence is catastrophic or critical,
   confirm that a redundant restraint provision is in place — a second
   independent load path that keeps the item secured if the primary
   element fails. The absence of a redundant path for a catastrophic or
   critical item is a blocking finding.
6. Aggregate findings per item. An item is compliant only when all of the
   following are clear: load path defined, limit and ultimate FoS both
   pass, failure mode documented with a valid consequence category, and
   redundancy provision present when required. Report non-compliant items
   before the structure proceeds to acceptance review.

## Pitfalls

- Treating a tethered item as structurally trivial because the tether
  is flexible — the tether break load and its attachment fitting are
  restraint elements that require a full FoS check under the applicable
  dynamic and quasi-static cases. A tether that meets the static load
  but is never checked against shock can fail at a fraction of its
  nominal break load.
- Using the same numeric value for both the limit and ultimate FoS
  checks — these are different load levels against different material
  properties (yield vs. failure); conflating them can produce a false
  pass on the ultimate check when the two allowables differ
  significantly.
- Reading a blank or unset failure-mode field as "no identified failure
  mode" and therefore compliant — the blank field means the consequence
  analysis was never done, which is itself a finding. Every item must
  have a documented failure mode before the assessment closes.
- Skipping the redundancy check for an item whose consequence was
  previously logged as "to be determined" — a TBD consequence must be
  resolved before acceptance; in the meantime the item should be treated
  as critical to prevent a gap in the redundancy verification.

## Behavior contract (gate 3)

The item categorization, FoS gate, restraint margin calculation,
failure-mode documentation check, redundancy requirement, and full
per-item compliance evaluator are exercised by the gate 3 contract test:
scripts/test_contained_restrained_compliance.py against
scripts/contained_restrained_compliance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_contained_restrained_compliance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
