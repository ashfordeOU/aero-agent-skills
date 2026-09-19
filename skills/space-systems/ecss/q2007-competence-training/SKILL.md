---
name: q2007-competence-training
description: "Manage test-centre personnel competence and training under ECSS-Q-ST-20-07C clause 5.4. Use when a person has to be cleared for a test role rather than merely assigned to it: fix the competence need per role on a level scale, measure each person against it, separate the four ways a competence fails - absent, below level, certificate lapsed, level asserted with no training behind it - check the assessment record against the retention window, order the remaining work into a stable training plan worst shortfall first, and report the per-role clearance ratio. Trigger: ecss, q-st-20-07-test-centre, q2007-competence-training, test-role-competence-need, test-personnel-certification-validity, test-centre-training-record-retention, test-role-clearance-ratio, competence-gap-training-plan."
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
  tags: [ecss, q-st-20-07-test-centre, q2007-competence-training, test-role-competence-need, test-personnel-certification-validity, test-centre-training-record-retention, test-role-clearance-ratio, competence-gap-training-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Competence and Training (space-systems/ecss/q2007-competence-training)

Use when the task is the personnel step of ECSS-Q-ST-20-07C clause 5.4 --
stating what each test role has to be able to do, measuring the people
proposed for it against that, and turning the difference into training and
a record that survives the next audit.

## Domain quick reference

- The competence need belongs to the role, not to the person. The schedule
  assigns roles; a person is then measured against the role they are about
  to fill. Writing the need per person is how a centre ends up with a
  competence set shaped around whoever happens to be available.
- A level scale only works if the top of it means something. Here 0 is no
  exposure and 4 is able to set the practice for others, and a role asks
  for the level at which a person can be left alone with the test article --
  not the level at which they can be supervised through it.
- A competence fails in four separate ways and the remedy differs for each,
  so they are never merged into one "not qualified" flag: absent (no
  assessment at all), below level, certificate lapsed, and level asserted
  with no training event behind it. The last one is the common finding in a
  centre that has been running a long time: the competence is real, the
  evidence for it never existed.
- A certificate and an assessment record are different objects with
  different clocks. The certificate has a validity window and expires; the
  assessment record has a retention window and stops supporting a clearance
  once it falls out of it. A current certificate over a record that has
  aged out is still a gap.
- Clearance is binary and has no near miss. One gap blocks the role,
  because the level asked for is the level the unsupervised work needs.
- The training plan is ordered by shortfall, worst first, and
  alphabetically inside an equal shortfall, so two runs of the same register
  produce the same plan and a review can diff this month against last.
- The evaluation day is an input, never the clock. A competence report that
  changes because it was re-run on a different afternoon cannot be attached
  to a test readiness review.

## Workflow

1. State the competence need per test role as a set of named competences
   each with a minimum level. Keep it in one place; the roles share
   competences and a divergent copy is how two roles come to disagree about
   what the same safety competence means.
2. Build the personnel register. Per person give the role proposed and, per
   competence held, the level, the day of assessment, the certificate expiry
   day and whether a training event is on record.
3. Refuse the register when a role or competence name is unrecognised, a
   level sits outside the scale, a day is not an integer, or an identifier
   repeats.
4. Derive the gaps for each person at an explicit evaluation day, one entry
   per failure reason, keeping the shortfall magnitude on each.
5. Clear only the people with no gap. Collapse each person's gaps into a
   training plan, one line per competence carrying every reason it failed.
6. Roll the centre up: cleared, blocked, and the clearance ratio per role.
   The register is compliant only when nobody is blocked.

## Pitfalls

- Treating a certificate as the whole story. The level, the training
  evidence and the record age are three further facts and each can fail on
  its own.
- Merging "no assessment" with "assessed too low". The first needs an
  assessment, the second needs training, and reporting them as one number
  hides which one the centre owes.
- Clearing a person one level short because the campaign starts Monday.
  The level is the point at which supervision stops being needed.
- Reading the clock inside the assessment. The evaluation day has to be an
  input or the same register grades differently on two afternoons.
- Sorting the training plan by competence name and losing the priority. The
  worst shortfall is the one that blocks the most roles soonest.
- Keeping a role-specific copy of a shared competence definition, so the
  safety level a conductor needs quietly drifts from the one an operator
  needs.

## Behavior contract (gate 3)

The role-need lookup, record validation, certificate and retention clocks,
four-reason gap derivation, training-plan ordering and register roll-up are
exercised by the gate 3 contract test:
scripts/test_q2007_competence_training.py against
scripts/q2007_competence_training_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_competence_training.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
