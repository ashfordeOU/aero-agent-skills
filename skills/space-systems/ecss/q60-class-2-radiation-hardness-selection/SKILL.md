---
name: q60-class-2-radiation-hardness-selection
description: "Determine whether a Class 2 part's radiation tolerance covers the environment it sees across the whole declared mission under ECSS-Q-ST-60C clause 5.2.2.4: accumulate ionising dose and displacement fluence phase by phase behind the design shielding, set the design margin from how the capability was evidenced, grade both accumulated mechanisms, refuse a destructive single event threshold at or below the environment with no rate credit, then report the mission months the part supports, the phase its capability runs out in, and whether a lot radiation test or a shielding uplift closes the gap. Use when a Class 2 design has to tie a part choice to its radiation lifetime. Trigger: ecss, q-st-60c-class-2-selection-scope, class-2-radiation-tolerance-matching, evidence-pedigree-radiation-design-margin, mission-phase-dose-accumulation, class-2-supported-radiation-lifetime, destructive-single-event-let-threshold, shielding-uplift-disposition."
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
  tags: [ecss, q-st-60c-class-2-selection-scope, q60-class-2-radiation-hardness-selection, class-2-radiation-tolerance-matching, evidence-pedigree-radiation-design-margin, mission-phase-dose-accumulation, class-2-supported-radiation-lifetime, destructive-single-event-let-threshold, shielding-uplift-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Radiation Hardness Selection (space-systems/ecss/q60-class-2-radiation-hardness-selection)

Use when the task is the radiation matching of ECSS-Q-ST-60C clause
5.2.2.4 -- deciding, for a Class 2 design, whether a candidate part's
tolerance covers the environment behind its shielding for the whole
declared lifetime, and what each shortfall is worth buying back with.

## Domain quick reference

- The part is not matched against a radiation number in the abstract.
  It is matched against the environment it actually sees behind the
  shielding the design gives it, accumulated across the declared
  mission, phase by phase.
- Lifetime enters twice: once as duration, because a long phase at a
  low rate can outweigh a short one at a high rate, and once as the
  rate each phase runs at behind its own shielding.
- The design margin is set by how the capability was evidenced, not by
  the mechanism. A figure measured on the delivered lot carries a small
  margin; one read off a maker's datasheet carries a large one, because
  the spread it hides is the project's to cover.
- Three mechanisms are graded separately because they are bought off in
  different currencies: accumulated ionising dose, accumulated
  displacement fluence, and single event effects against a threshold
  linear energy transfer the environment either does or does not
  exceed.
- A destructive single event mechanism takes no rate credit. A
  mechanism that ends the part cannot be traded against how seldom it
  is expected to happen, so it is refused rather than margined. A
  recoverable one is graded against the mission's upset rate budget
  after mitigation and asks for more mitigation when it is over.
- The output a Class 2 design needs is not a pass or a fail. It is the
  mission months the part supports at its margin and the phase its
  capability runs out in, because a part that covers the declared
  mission with two months to spare and one that covers it twice over
  are both compliant and are not the same decision.
- A shortfall has two different prices. Where the margin is large only
  because the evidence is generic, a radiation test on the delivered
  lot cuts the margin and can close the gap with no design change.
  Where the evidence is already lot specific, only more shielding or a
  different part is left.

## Workflow

1. Declare the mission profile phase by phase, each with its duration
   and the dose and fluence rates the part sees behind its shielding.
   Reject a phase with no duration rather than skipping it.
2. Accumulate dose and fluence across the profile and keep the running
   total per phase, so the phase a capability dies in can be named.
3. Set the radiation design margin from the evidence pedigree, and
   raise both accumulated quantities by it.
4. Grade each accumulated mechanism against the declared capability.
   Report a requirement sitting exactly on the capability as covered,
   not as a shortfall.
5. Grade the single event mechanisms: destructive immunity strictly
   above the environment linear energy transfer, recoverable rate
   against the mission budget after mitigation.
6. Walk the profile again against the capability to get the months the
   part supports and the phase it runs out in.
7. Close with one disposition: accepted, accepted on a lot radiation
   test, accepted on a shielding uplift, mitigation required, evidence
   incomplete, or refused.

## Pitfalls

- Matching the part against the unshielded environment. The clause is
  about what the part sees, so the shielding the design already gives
  it is in the rate before anything is accumulated.
- Taking one margin for every part. The margin covers the spread the
  evidence hides, so a lot measurement and a datasheet claim cannot
  carry the same number and the pedigree is the input that sets it.
- Reporting a pass rather than a supported lifetime. A pass hides
  whether the part survives a six month extension, which is the
  question that gets asked next.
- Margining a destructive single event mechanism. Dose margins and
  event thresholds are not the same kind of quantity, and a destructive
  mechanism above threshold is refused however good the dose case is.
- Treating every shortfall as a refusal. Where the margin is large only
  because the evidence is generic, a lot radiation test buys the gap
  back without touching the design.
- Treating a missing capability as a zero capability. A part with no
  declared figure is unproven, not weak, and the two lead to different
  actions.
- Comparing a required capability with a declared one by bare
  arithmetic. The requirement is a rate, a duration and a margin
  multiplied together while the capability is one number, so a
  requirement built to sit exactly on it can land a few units in the
  last place above; the comparison absorbs that representation error
  while the capability stays untouched.

## Behavior contract (gate 3)

The margin policy validation, mission profile validation, phase-by-phase
accumulation, evidence-pedigree margin lookup, accumulated mechanism
grading, destructive and recoverable single event grading, supported
lifetime walk and disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_2_radiation_hardness_selection.py against
scripts/q60_class_2_radiation_hardness_selection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_2_radiation_hardness_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
