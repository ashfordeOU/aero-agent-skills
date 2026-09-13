---
name: e20-electromagnetic-effects-verification-report
description: "Use when audit an electromagnetic-effects verification report against the ECSS-E-ST-20C Annex C data-requirement: categorize every verification activity into its electromagnetic family (conducted-emission, radiated-emission, conducted-susceptibility, radiated-susceptibility, electrostatic-discharge-immunity, magnetic-moment, bonding-and-isolation), recompute the demonstrated-margin from the applicable-limit and the measured-level in the correct sense, grade each demonstrated-margin against the required-margin, register every deviation with a disposition and demand a waiver-reference where one is claimed, and refuse a report whose mandated sections or mandated activity coverage are incomplete. Trigger: ecss, e-st-20-electrical-scope, electromagnetic-effects-verification-report, demonstrated-margin, deviation-register, radiated-emission-limit, conducted-susceptibility-level, magnetic-moment-characterisation, annex-c-data-requirement."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electromagnetic-effects-verification-report, electromagnetic-effects-verification-report, demonstrated-margin, deviation-register, radiated-emission-limit, conducted-susceptibility-level, annex-c-data-requirement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Electromagnetic-Effects Verification Report (space-systems/ecss/e20-electromagnetic-effects-verification-report)

Use when the task is the content check of the electromagnetic-effects
verification report of ECSS-E-ST-20C Annex C -- the deliverable that
closes the electromagnetic-effects verification campaign by stating,
activity by activity, the applicable-limit, the measured-level, the
demonstrated-margin that follows from them, and every deviation with
its disposition.

## Domain quick reference

- Annex C is a data-requirement, not an engineering method: it fixes
  what the report must contain, so the check is a completeness and
  self-consistency check, not a re-analysis of the hardware. The
  mandated sections are identification of the item and its
  configuration, the verification matrix tying each requirement to the
  activity that discharges it, the results, the deviation register,
  and the conclusion.
- Every activity belongs to one electromagnetic family, and the family
  fixes the sense of the demonstrated-margin. Emission families
  (conducted-emission on power and signal leads, radiated-emission in
  electric and magnetic field), the magnetic-moment
  characterisation, and the bonding/isolation resistance measurements
  are lower-is-better: the demonstrated-margin is applicable-limit
  minus measured-level. Susceptibility families (conducted-
  susceptibility by lead injection or bulk-current-injection,
  radiated-susceptibility in electric and magnetic field) and
  electrostatic-discharge-immunity are higher-is-better: the
  demonstrated-margin is the level actually applied without
  degradation minus the required-level. Applying one sense to both
  inverts the verdict on half the campaign.
- A demonstrated-margin is graded in three bands, never two:
  compliant when it reaches the required-margin, marginal when it is
  non-negative but short of the required-margin (the item passed the
  limit but not the required-margin, which is a finding), and
  non-compliant when it is negative. A margin that lands on the
  required-margin is compliant -- the equality is physical, so the
  comparison absorbs floating-point representation error rather than
  moving the engineering limit.
- A deviation is only closed by a disposition: corrective-action and
  retest return the item to the campaign, accepted-as-is and waiver
  close it on paper, and a waiver disposition without a
  waiver-reference is an open deviation dressed as a closed one.
- Units stay in the record. Emission and susceptibility levels are
  reported in decibel quantities, magnetic moment in ampere-square-
  metre, bonding and isolation in resistance units; the
  demonstrated-margin is computed in the same unit as the pair it came
  from, so the required-margin must be expressed in that unit too.

## Workflow

1. Confirm the mandated sections are present. A missing verification
   matrix or a missing deviation register is a report-level refusal;
   do not grade the activities of an incomplete report as if the
   absent section were empty-and-therefore-clean.
2. Categorize each activity by its method into its electromagnetic
   family. Reject an unrecognized method before it enters the
   assessment -- an activity whose method is not one of the recognized
   set cannot have its margin sense determined.
3. Recompute the demonstrated-margin per activity from the
   applicable-limit and the measured-level using the family's sense.
   Recompute it; never carry the reported number through, because the
   whole point of the check is to catch a margin computed with the
   wrong sign.
4. Grade each demonstrated-margin against the activity's
   required-margin (falling back to the report-level default when the
   activity does not carry its own) into compliant, marginal or
   non-compliant.
5. Check coverage against the mandated activity list for the product
   type: every mandated method must appear at least once, and a
   mandated method with no activity is a coverage gap, distinct from a
   failed activity.
6. Validate the deviation register: each entry names an activity that
   exists in the report, carries a recognized disposition, and carries
   a waiver-reference when the disposition is a waiver.
7. Aggregate. The report is acceptable only when the sections are
   complete, no coverage gap remains, no activity is non-compliant,
   and every deviation is closed by a valid disposition. Marginal
   activities do not block acceptance on their own but must each be
   carried in the deviation register.

## Pitfalls

- Reading the reported margin instead of recomputing it. A sign error
  in a susceptibility activity reports a comfortable margin for an
  item that failed; only the recomputation from limit and measured
  level exposes it.
- Applying the emission sense to a susceptibility activity. The
  susceptibility result is the level survived, so subtracting it from
  the requirement inverts every susceptibility verdict in the report.
- Collapsing marginal into compliant. An activity that clears the
  applicable-limit but not the required-margin has consumed the whole
  design allowance; it is a finding that belongs in the deviation
  register, not a pass.
- Treating an absent activity as a pass. A mandated method that never
  ran leaves a requirement undischarged; the verification matrix shows
  it as a coverage gap, and an empty results row is not evidence.
- Accepting a waiver disposition with no waiver-reference. Without the
  reference the deviation has no authority behind it and the report
  claims a closure that does not exist.
- Mixing units between the pair and the required-margin -- comparing a
  decibel margin against a resistance requirement produces a verdict
  with no physical meaning.

## Behavior contract (gate 3)

The family categorization, margin recomputation and sense selection,
three-band grading, coverage check, deviation-register validation and
report-level verdict are exercised by the gate 3 contract test:
scripts/test_e20_electromagnetic_effects_verification_report.py against
scripts/e20_electromagnetic_effects_verification_report_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_electromagnetic_effects_verification_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
