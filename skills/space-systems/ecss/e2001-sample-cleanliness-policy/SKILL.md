---
name: e2001-sample-cleanliness-policy
description: "Use when verify that the contamination-control policy referenced by ECSS-E-ST-20-01C clause 9.4.1.2 is genuinely applied to a secondary-electron-emission-yield sample and to every environment it passes through: categorize each preparation, transfer, storage, mounting and measurement step of the handling-chain, credit a purged or evacuated enclosure against the room cleanliness-class, compare every step against the class the sample yield-sensitivity demands, accrue settled-particle surface-obscuration across the chain, and check it against the sample allowable-obscuration budget. Flags an uncontrolled environment, a contact step with no tooling-control, and a missing policy-reference or an unrecorded obscuration budget. Trigger: ecss, e-st-20-electrical-scope, e2001-sample-cleanliness-policy, emission-yield-sample, contamination-control-policy, sample-cleanliness-level, surface-obscuration-budget, handling-chain-conformance, multipactor-sample-preparation."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-sample-cleanliness-policy, emission-yield-sample, contamination-control-policy, sample-cleanliness-level, surface-obscuration-budget, handling-chain-conformance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Emission-Yield Sample Cleanliness Policy (space-systems/ecss/e2001-sample-cleanliness-policy)

Use when the task is the clause 9.4.1.2 check of ECSS-E-ST-20-01C: the
contamination-control policy the standard points to has to reach the
emission-yield sample itself and the environment that sample sits in
between preparation and measurement, and the evidence for that has to be
checkable rather than asserted.

## Domain quick reference

- Secondary-electron-emission yield is a surface property. A settled or
  adsorbed overlayer a few molecules thick moves the measured yield
  curve, and with it the multipactor threshold the whole analysis rests
  on. Clause 9.4.1.2 therefore binds the sample and its environment to
  the project contamination-control policy, not just the test facility.
- The handling-chain is the object under check: every preparation,
  transfer, storage, mounting and measurement step between coupon
  release and the yield scan. Each step carries an environment, a
  duration, and a flag for whether the sample surface is touched. A step
  that matches no handling family stays uncategorized and is rejected
  before it can enter the accrual.
- Cleanliness demand follows the yield-sensitivity of the sample: a
  high-sensitivity coupon (bare metal, conversion-coated, or an
  as-deposited film) demands the strictest room class, a
  moderate-sensitivity coupon one step looser, a low-sensitivity coupon
  looser again. The demand is on the class the sample actually sees, not
  on the nominal room.
- A purged or evacuated enclosure earns credit against the room class: a
  dry-nitrogen purge counts one class better, a sealed evacuated
  container two classes better, floored at the cleanest class. An
  environment with no cleanliness control on record earns no credit at
  all and is a finding by itself.
- Settled-particle surface-obscuration accrues with exposure time. The
  module carries a documented still-air settling model — one decade of
  obscuration rate per cleanliness class, scaled by the purge factor —
  so the accrued percentage across a chain is reproducible and can be
  set against the sample allowable-obscuration budget.
- Contact steps (tweezers, gloves, wand, dedicated fixture) are
  controlled procedurally, not numerically. The check is presence of a
  declared tooling-control on every contact step; an unrecognised
  control is a bad input, an absent one is a finding.

## Workflow

1. Categorize each step of the handling-chain into exactly one family —
   preparation, transfer, storage, mounting, measurement. Reject an
   uncategorized step before the assessment continues.
2. Derive the required cleanliness class from the sample
   yield-sensitivity, then compute the effective class each step
   delivers after purge or evacuation credit.
3. Flag any step whose effective class is dirtier than the requirement,
   and flag separately any step run in an environment with no
   cleanliness control on record.
4. Accrue surface-obscuration step by step: class-derived rate times
   purge factor times exposure duration, summed over the chain with an
   exact running sum.
5. Compare the accrued obscuration with the sample allowable budget. An
   exceedance is a finding; an absent budget is a different finding, and
   never a pass.
6. Confirm every contact step declares a tooling-control, then aggregate
   all findings. The sample is policy-conformant only when the finding
   list is empty.

## Pitfalls

- Reading the nominal room class off the facility datasheet and calling
  the step compliant — the sample sees the enclosure, so a coupon inside
  an evacuated container in a looser room can conform while a bare
  coupon in the same room does not.
- Treating the purge credit as unconditional — an environment with no
  cleanliness control on record gets no credit, because there is no
  baseline class to credit against.
- Summing exposure time alone and comparing hours against hours —
  obscuration is rate times time, and an hour in a loose room is worth
  three decades of an hour in a tight one.
- Leaving the allowable-obscuration budget unset and reading the absence
  of an exceedance as conformance — an unset budget means the policy
  linkage was never captured, which is the finding.
- Letting a boundary case fail on representation: an accrued total that
  lands a few units in the last place above a budget it physically
  equals is conformant, and the tolerance belongs in the comparison, not
  in a widened budget.
- Assuming a contact step is safe because the room is clean — the
  particulate risk at contact is the tool and the glove, which is why
  the check is presence of a declared tooling-control.

## Behavior contract (gate 3)

The step-categorization, cleanliness-class, purge-credit,
obscuration-accrual, budget-comparison and tooling-control logic is
exercised by the gate 3 contract test:
scripts/test_e2001_sample_cleanliness_policy.py against
scripts/e2001_sample_cleanliness_policy_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_sample_cleanliness_policy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
