---
name: e2040-device-development-lifecycle-overview
description: "Derive the functional, performance and environmental needs a device supplier carries through the development phases under ECSS-E-ST-20-40C clause 4.1: fold the phase and category spellings onto one ordered set, walk each need back to the higher-level need it came from so an orphan or a circular derivation surfaces, refuse a need derived before its own parent, and track maturity per category across the phases so a regression or a phase gate it never reached is reported. Use when a device specification is being built up, or when a phase gate asks what the supplier has actually derived. Trigger: ecss, e-st-20-40c, device-need-derivation, device-development-phase-sequence, functional-performance-environmental-needs, need-maturity-progression, orphan-derived-need, device-phase-gate-maturity."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-development-lifecycle-overview, device-need-derivation, device-development-phase-sequence, functional-performance-environmental-needs, need-maturity-progression, orphan-derived-need, device-phase-gate-maturity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Development Lifecycle Overview (space-systems/ecss/e2040-device-development-lifecycle-overview)

Use when the task is the lifecycle overview of ECSS-E-ST-20-40C clause
4.1 -- how a device supplier turns the needs handed down from the level
above into its own functional, performance and environmental needs, and
how those needs harden as the development moves from one phase to the
next.

## Domain quick reference

- A device need is never free-standing. Each one comes from a need at
  the level above, and the value of writing that link down is that the
  device can later show why every requirement it carries exists. A need
  with no parent recorded is either a genuine top-level need or a
  requirement somebody invented, and the two look identical afterwards.
- The clause names three need families the supplier has to address:
  what the device does, how well it does it, and what it has to survive
  while doing it. Addressing two of the three is the commonest
  incomplete device specification, and the missing family is usually
  the environmental one because nothing in the functional chain asks
  for it.
- Derivation has a direction in time. A need cannot be derived in an
  earlier phase than the need it was derived from, so a device need
  dated before its parent is either a wrong date or a requirement that
  was written first and given a parent later to make the tree look
  complete.
- Needs harden rather than appear. The same need is stated, then
  derived, then budgeted, then specified, then verified, and the phase
  at which each step is expected is what a phase gate actually checks.
- Maturity does not go backwards. A category that was budgeted in one
  phase and only stated in the next has lost work, and that is visible
  only when maturity is tracked per category across the phase order
  rather than per need.
- The categories are grouped, not ranked. An environmental need is not
  subordinate to a functional one; it constrains the same design from a
  different direction and is derived on the same footing.

## Workflow

1. Fold every phase and category spelling onto the canonical ordered
   sets. Refuse an unrecognised spelling instead of defaulting it,
   because a silently defaulted category lands the need in the wrong
   family and the coverage count still looks right.
2. Index the needs and refuse a repeated identifier. Two needs sharing
   an identifier means one of them is invisible to every later check.
3. Walk each need back to its root. Report a parent that is not a
   declared need, and refuse a derivation that closes on itself.
4. Compare each need's phase with its parent's and report anything
   derived earlier than the need it came from.
5. Group the needs by category and report any of the three mandatory
   families that was never addressed at any phase.
6. Build the maturity table: the highest maturity each category reached
   at each phase. Walk the phase order and report a category that went
   backwards.
7. Apply the phase gates: for each phase with a required maturity,
   report every mandatory category that has not reached it by then.

## Pitfalls

- Recording a derivation tree with no parents at all. It satisfies a
  format check and carries none of the information the clause is
  after, and nothing downstream can tell a top-level need from an
  unjustified one.
- Folding an unrecognised category onto a default. The coverage count
  stays complete while the need sits in the wrong family, so the
  missing family is never reported.
- Tracking maturity per need instead of per category. A single mature
  need hides a family that never advanced, because the maximum across
  needs is not the state of the category.
- Reading a phase gate as a date. The gate asks for a maturity, so a
  device that reached the phase on schedule with stated-only
  performance needs has not passed it.
- Assuming the environmental family follows from the functional one.
  Nothing in the functional chain asks what the device has to survive,
  so environmental needs are derived from the environment specification
  or they are not derived at all.
- Dating a need by when it was written down rather than when it was
  derived. That is what produces a need apparently older than its
  parent, and the fix is the date, not the tree.

## Behavior contract (gate 3)

The phase and category folding, need indexing, derivation chain walk,
orphan and cycle detection, derivation ordering in time, category
coverage, maturity table and phase gate check are exercised by the gate
3 contract test:
scripts/test_e2040_device_development_lifecycle_overview.py against
scripts/e2040_device_development_lifecycle_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_development_lifecycle_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
