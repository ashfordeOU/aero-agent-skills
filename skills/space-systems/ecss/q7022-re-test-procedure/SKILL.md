---
name: q7022-re-test-procedure
description: "Prepare the re-test a stored material owes before its shelf life is extended under ECSS-Q-ST-70-22, and grade what comes back: take the property set from the material family, take the specimen count from the lot size, derive each acceptance threshold from the as-manufactured value and a declared retention fraction in the direction that property may drift, compare with a relative tolerance so a result on the limit passes everywhere, and keep a failed re-test distinct from an incomplete one. Use when an extension request needs test evidence. Trigger: ecss, q-st-70-22, shelf-life-re-test-plan, re-test-acceptance-threshold, re-test-property-retention, re-test-specimen-count, re-test-incomplete-versus-failed."
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
  tags: [ecss, q-st-70-22-limited-shelf-life-materials, q-st-70-22, q7022-re-test-procedure, shelf-life-re-test-plan, re-test-acceptance-threshold, re-test-property-retention, re-test-specimen-count, re-test-incomplete-versus-failed]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Re-Test Procedure and Acceptance (space-systems/ecss/q7022-re-test-procedure)

Use when the task is the re-test that carries a shelf-life extension under
ECSS-Q-ST-70-22: which properties to test, on how many specimens, against what
acceptance, and what the results entitle the lot to.

## Domain quick reference

- The property set comes from the material family, not from convenience. A
  paste adhesive is re-tested on the properties that move in storage —
  viscosity, gel time and a bonded strength — because those are the ones whose
  drift predicts a bad joint. Testing whatever the lab has a fixture for proves
  nothing about the mechanism that degrades.
- Every property has a direction. A strength may only fall so far, a viscosity
  or a volatile content may only rise so far, and a banded property such as gel
  time or resin content is out of family in either direction. One two-sided
  rule applied to all of them passes material that has thickened past use.
- The acceptance threshold is derived from the value recorded at manufacture
  for that lot, scaled by a declared retention fraction. It is not a fresh
  specification limit, because the question is drift in storage, not whether
  the material was ever any good.
- A result meant to sit exactly on the limit will not: the threshold is a
  product of a declared fraction and a recorded value, and it lands either side
  of the intended number depending on the platform. The comparison carries a
  relative tolerance so the same data gives the same verdict everywhere.
- A failed re-test and an incomplete one are different outcomes. A property
  tested and out of acceptance is evidence about the material; a property
  nobody tested, or tested on too few specimens, is a gap in the evidence. Only
  the first justifies scrapping the lot.

## Workflow

1. Take the required properties from the family and refuse an unknown family
   rather than falling back to a generic set.
2. Take the specimens owed per property from the lot size bracket.
3. For each property, derive the acceptance bounds from the as-manufactured
   value and the retention fraction, in that property's own direction.
4. Grade each reported specimen against its bounds with the relative tolerance;
   a single specimen outside acceptance fails that property.
5. Flag a property reported on fewer specimens than the plan requires, and do
   not read it as a pass.
6. Split the outcome into failed properties, missing properties, under-sampled
   properties and results reported outside the plan.
7. Close with failed, then incomplete, then passed, and report the extension
   period the re-test can carry — zero for anything but a pass.

## Pitfalls

- Applying one symmetric band to every property. A viscosity that has halved
  and a viscosity that has doubled are not the same finding.
- Grading against the original specification rather than the lot's recorded
  as-manufactured value. That measures the supplier, not the storage.
- Accepting a property because its mean is inside acceptance. The specimen
  outside it is the one that will be in the joint.
- Reading an under-sampled property as a pass because nothing failed. Too few
  specimens is missing evidence, and it belongs with the incomplete outcome.
- Comparing a result with a bare inequality against a computed threshold. A
  value intended to sit on the limit lands either side of it, and the same
  dataset then passes on one machine and fails on another.
- Reporting extension days off an incomplete re-test. Until the evidence is
  complete the supported period is zero, not the requested number.

## Behavior contract (gate 3)

The family property set, lot-size specimen brackets, direction-aware threshold
derivation, tolerance-carrying comparison, under-sampling detection and the
failed / incomplete / passed precedence are exercised by the gate 3 contract
test: scripts/test_q7022_re_test_procedure.py against
scripts/q7022_re_test_procedure_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7022_re_test_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
