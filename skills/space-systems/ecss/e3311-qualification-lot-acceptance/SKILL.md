---
name: e3311-qualification-lot-acceptance
description: "Run the qualification and lot-acceptance programme for an explosive device under ECSS-E-ST-33-11C clause 4.14.4 and its Annex A mapping. Use when the task is sizing or auditing a sample plan for initiators, cartridges or separation devices: proving the lot is one explosive batch, one manufacturing period and one build standard, sizing the attribute sample from the reliability and confidence with an exact binomial tail rather than a normal approximation, reporting the reliability a completed zero-failure run actually demonstrates, deriving qualification levels from acceptance levels through the qualification factor, and applying the accept or reject rule to the run performed. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-lot-acceptance-sampling, zero-failure-sample-size, reliability-confidence-demonstration, explosive-lot-homogeneity, qualification-test-level-factor, annex-a-requirement-mapping."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-qualification-lot-acceptance, explosive-lot-acceptance-sampling, zero-failure-sample-size, reliability-confidence-demonstration, explosive-lot-homogeneity, qualification-test-level-factor, annex-a-requirement-mapping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Qualification and Lot Acceptance (space-systems/ecss/e3311-qualification-lot-acceptance)

Use when the task is the qualification and lot-acceptance requirement of
ECSS-E-ST-33-11C Rev.1 clause 4.14.4 and the Annex A requirement
mapping -- deciding how many units a lot owes to the test programme, at
what levels, and whether the run that was performed supports the
acceptance it claims.

## Domain quick reference

- An explosive device cannot be acceptance-tested unit by unit, because
  the test consumes the unit. Everything rests on a sample standing in
  for a lot, and that only holds while the lot is genuinely one
  population: one explosive batch, one manufacturing period, one build
  standard.
- The sample size comes from the reliability and the confidence
  together, and neither alone means anything. A zero-failure attribute
  plan needs ln(1-C)/ln(R) units rounded up: twenty-two units for 0.90
  reliability at 0.90 confidence, two hundred and ninety-nine for 0.99
  at 0.95.
- Allowing a failure is not a small concession. Once the plan tolerates
  one failure the binomial tail has two terms, and the sample roughly
  doubles to hold the same consumer risk. The exact tail is cheap to
  evaluate, so a normal approximation buys nothing and misleads at the
  small sample sizes this hardware runs at.
- The reliability a completed run demonstrates is the useful number to
  report back: n zero-failure trials at confidence C demonstrate
  (1-C)^(1/n). It is what a shortened run should be judged by, instead
  of being reported as a plain pass.
- Qualification levels sit above acceptance levels by the qualification
  factor. A factor below unity is not a tailoring choice; it inverts
  the relationship the two programmes exist to hold.
- A run that tested fewer units than the plan is a finding even when
  nothing failed, and a run that tested more units than the lot holds
  is an evidence-traceability failure regardless of outcome.

## Workflow

1. Walk the unit register and confirm the lot is one lot, reporting
   every batch, period and build-standard split separately so the
   reader can see which one broke homogeneity.
2. Size the sample from the specified reliability, confidence and
   allowed-failure count, using the exact binomial tail whenever a
   failure is allowed and the closed log form when none is.
3. Snap a log-ratio sample size to a neighbouring integer before taking
   the ceiling, so a mathematically exact ratio does not gain a unit
   from the last bit of a logarithm.
4. Compare the sample against the lot size and refuse a plan the lot
   cannot supply, rather than silently truncating it.
5. Derive the qualification level from the acceptance level and the
   factor, refusing a factor below unity, and grade any declared
   qualification level against it.
6. Apply the accept or reject rule to the observed failures, and
   separately report whether the run followed the plan at all.
7. For a clean run, report the reliability actually demonstrated at the
   stated confidence alongside the accept verdict.

## Pitfalls

- Sampling across a batch boundary. Two batches of the same drawing are
  two populations; a sample spanning both demonstrates the reliability
  of neither, and this is invisible in the test report because every
  unit passed.
- Quoting a reliability without its confidence, or a confidence without
  its reliability. Either alone can be met by any sample size, so a
  specification carrying only one of them cannot size a plan.
- Substituting a normal approximation for the binomial tail. At the
  twenty-to-forty unit sizes this hardware runs at the approximation
  is wrong in the direction that shrinks the sample.
- Reading a short run as a pass because no unit failed. Fewer units
  demonstrate less reliability; the run has to be reported against the
  reliability it actually reached, not against the plan it abandoned.
- Setting the qualification factor below unity to make an existing test
  campaign cover qualification. That does not tailor the programme, it
  deletes it.
- Failing an exactly-on-limit declared level on the last bit of a
  multiplication. Equality at the boundary is a representation
  question, absorbed by the tolerance inside the comparison; the
  required level itself stays as derived.

## Behavior contract (gate 3)

The lot-homogeneity check, zero-failure and allowed-failure sample
sizing, exact binomial acceptance probability, demonstrated-reliability
report, qualification-level derivation and accept or reject rule are
exercised by the gate 3 contract test:
scripts/test_e3311_qualification_lot_acceptance.py against
scripts/e3311_qualification_lot_acceptance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3311_qualification_lot_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
