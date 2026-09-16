---
name: e2008-substrate-integrity-inspection-process
description: "Use when a cycled coupon substrate has been surveyed and the record has to stand up. Assess the structural integrity of a photovoltaic-assembly coupon substrate once its thermal cycling is credited, under ECSS-E-ST-20-08C clause 5.5.3.10.1: refuse a survey run before the cycling completes or inside the post-chamber stabilisation period, flag one left past the recording window, test every substrate zone against the methods that can actually see its failure modes and the corroboration a subsurface zone owes, capture each indication with its kind, zone, method and size, reject a size the method used cannot resolve, and hand a complete set on to the drawing-sourced disposition step. Trigger: ecss, e-st-20-08c, clause-5-5-3-10-1, post-cycling-substrate-integrity-inspection, cycled-coupon-substrate-survey, substrate-inspection-zone-coverage, substrate-inspection-method-admissibility, substrate-disbond-indication-capture."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-substrate-integrity-inspection-process, post-cycling-substrate-integrity-inspection, cycled-coupon-substrate-survey, substrate-inspection-zone-coverage, substrate-inspection-method-admissibility, substrate-disbond-indication-capture]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Substrate Integrity Inspection Process (space-systems/ecss/e2008-substrate-integrity-inspection-process)

Use when the task is the substrate integrity survey of ECSS-E-ST-20-08C
clause 5.5.3.10.1 -- looking at the substrate of a coupon that has come
out of thermal cycling, as a structure rather than as a surface, and
producing a record the disposition step can actually run on.

## Domain quick reference

- The subject is the substrate after cycling, not the cells on it and
  not the panel at incoming inspection. Cycling drives a thin
  facesheet, an adhesive layer and a honeycomb core through repeated
  expansion mismatch, and what it leaves behind is mostly subsurface: a
  bondline that has let go, a core cell that has crushed, a dielectric
  that has delaminated under an intact facesheet.
- Sequence is part of the result. The survey follows the cycling being
  credited, not the chamber door opening, and it waits out a
  stabilisation period: inspected while the coupon is still returning
  to ambient, a disbond can be held closed and read as sound. Left too
  long afterwards it is a different question, because the record no
  longer describes the coupon as it left the chamber.
- Every zone has methods that can see it and methods that cannot. A
  bondline or a core surveyed by eye is an unsurveyed bondline or core,
  and recording the attempt as coverage is how a blind survey comes
  back clean.
- The zones that hide their damage owe corroboration. A bondline and an
  insert region each carry a minimum of two admissible methods, because
  a single subsurface method has its own blind spots and a second one
  fails differently.
- An indication is only usable downstream when it carries kind, zone,
  method and size together. A size the method used cannot resolve is
  not a small indication, it is a number the instrument could not have
  produced, and it is rejected rather than recorded small.
- An indication found by a method the zone does not admit is not
  discarded either. It is held as unconfirmed and sent back for a
  re-survey with a method that can see that zone, which is a different
  outcome from both accept and reject.
- This step stops before the disposition. The thresholds that decide
  accept or reject are not in the standard: they sit in the assembly
  control drawing and are applied in the pass/fail criteria step. What
  this step owes is completeness, sequence and method validity.

## Workflow

1. Validate the policy: every required zone has admissible methods, no
   zone demands more methods than exist for it, every method carries a
   detection threshold, and the recording window sits outside the
   stabilisation period.
2. Check readiness against the coupon state. Refuse a survey while
   credited cycles fall short of the required count. Mark a survey
   inside the stabilisation period as not ready, and flag one past the
   recording window without blocking it.
3. Work the coverage: for each required zone, keep the applied methods
   the policy admits, count them against that zone's minimum, and
   separate zones that are uncovered, under-covered and surveyed by a
   method that cannot see them.
4. Capture each indication. Categorize it by kind and zone, name the
   method, take its size, and reject a size below that method's
   detection threshold or an indication carrying no identifier.
5. Mark as unconfirmed any indication whose method is not admissible
   for its zone, and group the survey by zone and kind with the total
   damaged area and the largest single indication.
6. Close with the completeness verdict. Not-ready outranks everything;
   a coverage gap or an unconfirmed indication leaves the survey
   incomplete; a covered, sequenced survey with nothing on it says so
   explicitly rather than returning silence.
7. Hand the indication set to the pass/fail criteria step. Do not
   disposition here, and do not carry an implied limit forward.

## Pitfalls

- Surveying the coupon as soon as the chamber opens. The stabilisation
  period is what lets a disbond open up; before it, the survey reports
  a substrate that is still partly holding itself together.
- Counting a visual pass over a bondline or a core as coverage. The
  method cannot resolve those failure modes, so the zone is unsurveyed
  and the clean record is an artefact of the instrument.
- Treating one subsurface method as sufficient everywhere. The zones
  that owe two owe them because a single method's blind spots are not
  random, and a second method that fails differently is the point.
- Recording an indication below the detection threshold of the method
  that found it. That number did not come from the instrument, and it
  will be compared against a drawing limit as though it had.
- Discarding an indication found by an inadmissible method. It is
  evidence that something is there; what it is not is a measurement,
  so it is re-surveyed rather than dropped or dispositioned.
- Dispositioning inside this step. The limits live in the assembly
  control drawing, and a limit assumed here is a limit nobody in the
  programme approved.
- Comparing an elapsed time with a policy bound by bare arithmetic. A
  survey landing exactly on the stabilisation bound can evaluate a few
  units in the last place under it; the comparison absorbs that
  representation error while the bound stays untouched.

## Behavior contract (gate 3)

The policy validation, sequencing readiness, zone and method coverage,
indication capture and detection-threshold refusal, survey summary and
completeness verdict are exercised by the gate 3 contract test:
scripts/test_e2008_substrate_integrity_inspection_process.py against
scripts/e2008_substrate_integrity_inspection_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_substrate_integrity_inspection_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
