---
name: e2001-multipactor-test-procedure
description: "Use when audit the multipactor test procedure that ECSS-E-ST-20-01C clause 8.6 puts to the customer for approval before radio-frequency testing starts: confirm the procedure carries every expected content item, that the declared chamber-pressure and pump-down duration hold the article clear of the gas-discharge regime, that a recognised free-electron seeding arrangement and its declared flux are named, that the radio-frequency drive-schedule climbs in bracketing steps to the power the required power-margin-db demands over declared operating-power, and that one global-detection technique and one local-detection technique both appear. Compute the required test-power from operating-power and margin, and refuse a procedure whose declared content is incomplete. Trigger: ecss, e-st-20-01c, multipactor-test-procedure, test-procedure-content, customer-approval-before-test, rf-drive-schedule, power-margin-db, bracketing-step-size, procedure-content-audit."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-test-procedure, multipactor-test-procedure, test-procedure-content, customer-approval-before-test, rf-drive-schedule, power-margin-db]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Test Procedure Content (space-systems/ecss/e2001-multipactor-test-procedure)

Use when the task is the clause 8.6 content audit of ECSS-E-ST-20-01C -- the
document the customer approves before multipactor testing of a
radio-frequency unit may start. The leaf checks what the procedure declares,
not what the article does: content completeness, chamber conditions, seeding
arrangement, drive-schedule and detection coverage.

## Domain quick reference

- Clause 8.6 makes the procedure a customer-approved deliverable, so its
  content is the gate, not the later result. A procedure that leaves a
  content item unstated cannot be approved, because nothing in the as-run
  test would then be traceable to an agreed intent. The expected items are
  the test-item identification and configuration, the objectives, the
  facility description, the vacuum conditions, the seeding arrangement, the
  radio-frequency drive-schedule, the power-margin, the detection coverage,
  the pass-fail criteria, the instrumentation calibration, the test sequence
  and the non-conformance route.
- The chamber must sit well below the pressure at which a gas discharge
  ignites, otherwise the event the test hunts -- a vacuum electron
  resonance -- is masked by, or confused with, an ionised-gas breakdown. A
  stabilisation period under vacuum precedes the drive-schedule so that the
  article's own outgassing has decayed before power is applied.
- A susceptible gap only breaks down once a free electron is present, so an
  unseeded test can return a clean result purely by luck. The procedure
  therefore names a recognised seeding arrangement (a beta radioactive
  source, an ultraviolet lamp or an electron gun) together with the
  electron flux it delivers at the gap.
- The drive-schedule is an ascending ladder of power levels. It starts at or
  below the declared operating-power, rises in steps fine enough to bracket
  a threshold rather than step over it, and finishes at or above the power
  that the required margin demands: required test-power equals
  operating-power multiplied by ten raised to the margin in dB over ten.
- Detection is split by what it observes. A global technique reads the
  discharge out of the radio-frequency signal itself -- nulling of forward
  against reflected power, third-harmonic growth, close-to-carrier noise,
  phase modulation -- and covers the whole article at reduced sensitivity.
  A local technique -- an electron probe, a photomultiplier, an electron
  current probe, a local pressure rise -- is sensitive but only watches the
  gap it faces. Two techniques of the same kind share a blind spot, so the
  procedure declares at least one of each.

## Workflow

1. Compare the declared section list against the expected content items;
   every absent item is a finding. Extra annexes are recorded, not faulted.
2. Read the declared chamber-pressure and pump-down duration; flag a
   pressure at which a gas discharge could pre-empt the vacuum event, and
   flag a stabilisation period shorter than the agreed floor.
3. Confirm the seeding arrangement names a recognised source and declares
   its electron flux; reject an unrecognised source outright and flag a
   flux below the agreed floor.
4. Compute the required test-power from the declared operating-power and
   the required margin, then check the drive-schedule: strictly ascending,
   starting at or below operating-power, no step coarser than the agreed
   bracketing limit, and topping out at or above the required test-power.
5. Categorize each declared detection technique as global or local; flag
   fewer than two independent techniques, no global technique, or no local
   technique.
6. Aggregate the findings. The procedure is approvable only when every
   sub-audit is clean -- a partial pass is a rejection with a shorter list.

## Pitfalls

- Reading a completed section list as an approvable procedure: the content
  items are necessary, not sufficient, and a procedure can name a vacuum
  section while declaring a chamber pressure that would ignite a gas
  discharge.
- Letting the drive-schedule jump to the final level in one step because it
  reaches the required power: a ladder that steps over the threshold proves
  only that the article survived the top rung, and records no threshold.
- Crediting two global techniques, or two local ones, as independent
  coverage: they share the blind spot of their kind, so the pair is not
  equivalent to one of each.
- Treating an unseeded procedure as conservative: without a declared
  electron source the article may pass because no starting electron was
  ever available, which understates risk rather than overstating it.
- Rejecting a schedule that lands one unit-in-the-last-place under the
  required test-power: the margin target is a computed power, so an exact
  boundary is absorbed by the tolerance rather than by widening the limit.

## Behavior contract (gate 3)

The section-completeness, vacuum-condition, seeding, drive-schedule and
detection-coverage logic is exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_test_procedure.py against
scripts/e2001_multipactor_test_procedure_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_multipactor_test_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
