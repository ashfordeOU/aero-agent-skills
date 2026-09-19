---
name: q7004-mass-property-checks
description: "Evaluate the mass change an item shows across an ECSS thermal exposure, and say whether the weighings support a verdict at all. Use when the ECSS-Q-ST-70-04C evaluation clauses ask for post-exposure mass: take the change relative to the initial mass so a coupon and an assembly are judged alike, combine the resolution of both weighings into the smallest change that measurement can resolve, return indeterminate when that figure does not sit under the category limit, keep a gain apart from a small loss because uptake is its own finding, then roll the specimens into one batch verdict. Trigger: ecss, q-st-70-04-thermal-testing-scope, post-exposure-mass-change-check, relative-mass-loss-limit, balance-resolution-uncertainty, mass-gain-uptake-finding, mass-check-batch-verdict."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-mass-property-checks, post-exposure-mass-change-check, relative-mass-loss-limit, balance-resolution-uncertainty, mass-gain-uptake-finding, mass-check-batch-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Mass Property Checks (space-systems/ecss/q7004-mass-property-checks)

Use when the task is the mass side of the ECSS-Q-ST-70-04C evaluation — two
weighings across an exposure, what the difference between them is allowed to
be for the kind of item on the balance, and whether the balance used was ever
capable of answering the question.

## Domain quick reference

- The finding is relative, not absolute. A milligram off a coupon and a
  milligram off an assembly are different results, so the change is carried
  as a percentage of the initial mass and compared against a per-category
  allowance.
- A difference carries the resolution of both weighings, not one. The
  smallest change the measurement can resolve is the balance resolution
  combined across two readings and scaled by the coverage factor, expressed
  against the specimen mass.
- That combined figure decides whether a verdict exists. When it does not sit
  under the limit the item is judged against, a reading below the limit
  demonstrates nothing: the honest answer is indeterminate, and the fix is a
  finer balance or a larger specimen, not a softer limit.
- A gain is not a small loss. Moisture uptake or transferred contamination
  reads as a gain, and it is a finding in its own right with its own
  allowance; netting it against losses elsewhere in the batch erases it.
- A change smaller than what the weighings resolve is reported as no
  measurable change. Quoting it as a loss to four decimal places dresses
  balance noise up as a material property.
- The batch verdict is not an average. One specimen over the limit fails the
  batch; one specimen the balance could not judge leaves the batch
  indeterminate even when every other specimen passed.

## Workflow

1. Take the category of each specimen and read its loss allowance from the
   policy. Reject a specimen below the mass floor rather than quoting a
   relative change the balance cannot support.
2. Compute the signed relative change, keeping a loss positive and a gain
   negative so the two never collapse into one number.
3. Compute the resolvable change from the balance resolution, the coverage
   factor and the initial mass.
4. Compare the resolvable change against the category allowance first. If it
   is not clearly smaller, stop and return indeterminate with that reason.
5. Test a gain against the gain allowance and a loss against the category
   allowance, absorbing representation error at both boundaries.
6. Roll the specimens up: fail on any failure, indeterminate on any
   unjudgeable specimen, and carry the duties about gains and about weighing
   in the same conditioned state on the same balance.

## Pitfalls

- Quoting the balance datasheet resolution as the measurement resolution. The
  result is a difference of two readings, so the figure that matters is the
  combined one and it is larger.
- Reading "below the limit" as a pass on a specimen too small for the
  balance. The limit was never resolvable; the number is noise with a verdict
  attached.
- Averaging the batch. A mean change hides both the specimen that failed and
  the specimen that gained, which are the two results anyone reads the report
  for.
- Comparing a computed percentage against the allowance by bare arithmetic. A
  loss built to land on the allowance can fall either side of it in the last
  place, and the comparison, not the allowance, has to absorb that.
- Weighing on a different balance or in a different conditioned state after
  exposure. The difference then contains a handling artefact that no amount
  of care in the analysis can separate out.
- Treating a duplicated specimen identifier as harmless. The batch counts
  that weighing twice and the worst-case specimen can be reported as the one
  that was duplicated.

## Behavior contract (gate 3)

The relative change, the combined measurement resolution, the indeterminate
branch, the gain and loss allowances with their boundary handling, and the
batch roll-up are exercised by the gate 3 contract test:
scripts/test_q7004_mass_property_checks.py against
scripts/q7004_mass_property_checks_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_mass_property_checks.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
