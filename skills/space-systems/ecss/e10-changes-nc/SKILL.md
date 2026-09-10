---
name: e10-changes-nc
description: "Use when controlling an engineering change or nonconformance that may affect requirements or design under ECSS-E-ST-10C: assess whether it impacts the approved baseline, route it to the right approval authority, and gate implementation on an approved disposition with the baseline updated, consistent with M-ST-40 (configuration management) and Q-ST-10-09 (nonconformance control). Trigger: ecss, e-st-10c, engineering change, change request, nonconformance, ncr, m-st-40, q-st-10-09, baseline impact, ccb, nrb, disposition."
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
  tags: [ecss, e-st-10c, engineering-change, nonconformance, m-st-40, q-st-10-09, configuration-management, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Engineering Changes & Nonconformances (space-systems/ecss/e10-changes-nc)

Use when the task is controlling an engineering change or a
nonconformance under ECSS-E-ST-10C clause 5.6.9: determine whether it
affects the requirements or design baseline, route it to the right
approval authority, and gate implementation on an approved disposition
with the baseline updated, consistent with M-ST-40 and Q-ST-10-09.

## Domain quick reference

- ECSS-E-ST-10C clause 5.6.9 requires engineering changes and
  nonconformances that affect requirements or design to be controlled
  before they are implemented: assess baseline impact, obtain an
  approved disposition, and update the baseline before proceeding.
- Two item types: `change` (engineering change request) and
  `nonconformance` (departure from an approved requirement/design
  found in a product or process).
- An item "requires a baseline change" when it affects requirements,
  design, or both. Baseline-impacting changes route to the CCB
  (M-ST-40 configuration change control); baseline-impacting
  nonconformances route to the NRB (Q-ST-10-09 disposition). Items
  that do not touch the baseline may be handled and closed locally.
- An item may only be implemented/closed as approved once its
  disposition is `approved` and, for baseline-impacting items, the
  baseline has been updated to reflect it.
- This leaf scopes the systems-engineering control point (impact
  assessment, authority routing, implementation gate) only. The full
  nonconformance lifecycle (detection, containment, major/minor
  classification, root-cause analysis, CAPA, NCR database, trend
  analysis) is owned by the Q-ST-10-09 `q1009-*` leaves; baseline
  establishment mechanics are owned by the sibling `e10-config-baselines`
  leaf (10C clause 5.4.2.2).

## Workflow

1. Raise the item (`change` or `nonconformance`) with a description
   and flag whether it affects requirements, design, or both.
2. Compute whether it requires a baseline change (affects requirements
   or design) and determine the approval authority: CCB for
   baseline-impacting changes, NRB for baseline-impacting
   nonconformances, local authority otherwise.
3. Record the disposition (`approved` or `rejected`) from the
   authority, with a rationale.
4. If approved and the item requires a baseline change, update the
   baseline before closing it. If approved and no baseline change is
   required, or if rejected, close it directly.
5. Check the register: no item may be treated as implementable until
   it is closed (and, if baseline-impacting and approved, the baseline
   update is recorded).

## Pitfalls

- Implementing a baseline-impacting change or nonconformance before
  its disposition is approved and the baseline has been updated (the
  gate is skipped).
- Closing an approved baseline-impacting item without going through
  the baseline update step, leaving the configuration baseline out of
  sync with what was approved.
- Re-dispositioning an item that has already been dispositioned
  instead of raising a new item or reopening it explicitly.
- Confusing this leaf's control-point scope (impact assessment,
  authority routing, implementation gate) with the full Q-ST-10-09
  nonconformance lifecycle (detection, classification, CAPA,
  closeout, database/trend analysis) — see the sibling `q1009-*`
  leaves — or with baseline-establishment mechanics — see the sibling
  `e10-config-baselines` leaf (10C clause 5.4.2.2).

## Behavior contract (gate 3)

The impact-assessment, authority-routing, disposition, and
implementation-gate logic is exercised by the gate 3 contract test:
scripts/test_e10_changes_nc.py against
scripts/e10_changes_nc_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_changes_nc.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
