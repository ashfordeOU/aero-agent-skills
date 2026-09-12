---
name: e1024-lifecycle
description: "Use when run the interface management life cycles for a space project under ECSS-E-ST-10C §4.3: determine required lifecycle activities per project phase for generic, space-element–launch-segment, space–ground-segment, and OTS-product interface types; check that phase-gate agreements are in place; and verify interface documentation has reached the expected maturity level. Covers all four lifecycle streams and OTS-product involvement agreements. Trigger: ecss, e-st-10-system-scope, interface-management, lifecycle, phase-gate, launch-segment, space-ground, ots-product, agreements."
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
  tags: [ecss, e-st-10-system-scope, interface-management, lifecycle, phase-gate, launch-segment, space-ground, ots-product]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Life Cycle (space-systems/ecss/e1024-lifecycle)

Use when the task is to run the interface management life cycles defined in
ECSS-E-ST-10C §4.3 — identifying and executing the required activities per
project phase across the four interface lifecycle streams: generic, space
element–launch segment, space–ground segment, and OTS-product involvement.

## Domain quick reference

- ECSS-E-ST-10C §4.3 defines four interface management lifecycle streams:
  (1) **Generic** — applicable to all projects; covers the full sequence from
  interface identification in Phase 0 through to closure in Phase F.
  (2) **Space element – launch segment** — governs mechanical, electrical, and
  RF interfaces between the spacecraft and the launch vehicle, driven by launch
  service agreements and ICD freeze gates.
  (3) **Space – ground segment** — governs TM/TC, ranging, and data-relay
  interfaces between the space segment and the ground segment, with baselines
  set during Phase B and frozen during Phase C/D.
  (4) **OTS-product involvement** — addresses the specific agreements required
  when an OTS product participates in an interface: a preliminary technical
  interface agreement (Phase B), a formal technical interface agreement
  (Phase C), and an acceptance agreement (Phase D).

- Each lifecycle stream prescribes required activities at each project phase
  gate. An activity may be: identify (enumerate interface parties and
  documents), baseline (issue a controlled ICD version), freeze (lock the
  interface against change except via formal change control), verify
  (demonstrate that the implemented interface conforms to the ICD), or
  close-out (archive and formally close the ICD).

- Interface maturity levels rise with project phase: preliminary definition
  (Phases 0–A), initial ICD baseline (Phase B), frozen ICD (Phase C/D),
  verified ICD (Phase D/E), closed-out (Phase F).

## Workflow

1. Identify every interface and assign it to one or more lifecycle streams
   (generic applies to all; the stream-specific streams apply by interface
   type). Reject any interface that cannot be assigned to at least the
   generic stream.

2. For each interface and each lifecycle stream it belongs to, look up the
   required activities at the current project phase gate using the lifecycle
   activity table (see logic module `get_phase_activities` and
   `get_all_phase_activities`).

3. Compare the required activity list against the activities that have been
   completed; produce a gap list of missing activities. An interface phase gate
   is not closed until the gap list is empty.

4. For interfaces involving OTS products, additionally check that the required
   OTS agreements are in place for the current phase: preliminary agreement by
   Phase B, formal agreement by Phase C, acceptance agreement by Phase D.
   Missing agreements are a separate finding from the activity gap list.

5. Verify that the interface documentation has reached the expected maturity
   level for the current phase. Maturity level below the expected level is a
   finding even if all activities are complete on paper.

6. Confirm that phases were not skipped: all earlier phases must have their
   required activities completed before the current phase gate is assessed.
   A skipped-phase finding blocks the current-phase assessment.

## Pitfalls

- Applying only the generic lifecycle stream to a space–launch or space–ground
  interface and omitting the stream-specific activities — each stream adds
  mandatory activities on top of the generic baseline.
- Treating an OTS product's datasheet as a formal technical interface agreement
  — the ECSS stream requires a deliberate agreement document, not a commercial
  datasheet, by Phase C.
- Marking a phase gate complete when the interface is frozen but the ICD
  maturity level has not been formally raised — maturity level and activity
  completion are separate checks.
- Assessing a phase gate in isolation without verifying that all earlier phases
  have been closed — a gap in Phase B propagates silently to Phase C unless
  checked explicitly.

## Behavior contract (gate 3)

The phase-activity lookup, compliance checking, OTS agreement checking,
maturity-level determination, and phase-sequence validation logic are exercised
by the gate 3 contract test:
scripts/test_e1024_lifecycle.py against scripts/e1024_lifecycle_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1024_lifecycle.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
