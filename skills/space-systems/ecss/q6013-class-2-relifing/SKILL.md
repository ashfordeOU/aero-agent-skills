---
name: q6013-class-2-relifing
description: "Use when an expired storage period has to become a disposition. Determine whether a stored lot of commercial EEE parts may have its usable life extended at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.3.10: grade the store the parts actually sat in, scale the package family baseline period by it, test the elapsed storage against that period, check the relifing cycle ceiling before any test is considered, assemble the test set the lot owes, apply the single re-tinning allowance this class grants a lone solderability failure, and compute the decaying extension each further cycle earns. Trigger: ecss, q-st-60-13c-clause-5-3-10, class-two-relifing, stored-part-storage-period-grading, relifing-cycle-ceiling, solderability-retinning-allowance, decaying-storage-extension, stored-lot-re-screening-referral."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-relifing, class-two-relifing, stored-part-storage-period-grading, relifing-cycle-ceiling, solderability-retinning-allowance, decaying-storage-extension, stored-lot-re-screening-referral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Relifing (space-systems/ecss/q6013-class-2-relifing)

Use when the task is the clause 5.3.10 storage question of
ECSS-Q-ST-60-13C at the intermediate assurance class: parts bought for a
build have sat in store while the build slipped, the period granted when
the lot was accepted has run out, and the question is whether the life of
those parts can be extended and on what evidence.

## Domain quick reference

- An expired lot is neither scrap nor usable. Relifing is the operation
  that decides which, and it is an operation with an outcome, not a
  stamp applied to keep the build moving.
- The storage period a lot earned depends on where it actually sat, not
  on where the procurement paperwork said it would sit. The package
  family sets a baseline and the graded store scales it, so the same
  lot earns a long period in dry nitrogen and half of it in controlled
  ambient.
- A store with no credited factor grants no period at all. That is not a
  harsh reading: the record then says where the box was, not what the
  atmosphere did to the leads, and there is nothing to extend. Such a
  lot goes for re-screening.
- A lot sitting exactly on its permitted period is inside it. The
  scaling can leave the two sides a few ULP apart, which is
  representation error rather than an expired lot, and the comparison
  absorbs it instead of the period being padded.
- The cycle ceiling is checked before any test is considered. A lot that
  has used its cycles is not relifed however well it tests, because the
  question at that point is whether the part is still the part that was
  accepted, and that is a re-screening question.
- The test set is assembled from the lot, not from a fixed list.
  External visual and solderability are owed by every family, a seal
  test by a hermetic one, moisture preconditioning by a
  moisture-sensitive plastic one, and electrical re-verification from
  the declared cycle onwards. A test that is missing from the record is
  missing, not passed.
- This class grants one allowance the class above does not: a
  solderability failure standing alone, on a lot that has not already
  used the allowance, permits one re-tin and retest. Any other failure,
  or a solderability failure alongside another, disposes of the lot.
- Each cycle grants less than the one before it, and the decay is what
  stops a lot being relifed indefinitely a few months at a time. Once
  the grant falls under the minimum useful extension the lot goes for
  re-screening rather than being relifed for a fortnight.

## Workflow

1. Validate the relifing policy: the extension decay, the minimum useful
   extension, the cycle ceiling, the cycle from which electrical
   re-verification is owed, and whether the re-tinning allowance is open.
   A decay above unity or a zero ceiling is refused rather than used.
2. Grade the store and resolve the package family, refusing an
   unregistered environment or family rather than assuming a period that
   was never granted. A store crediting nothing closes the assessment.
3. Scale the baseline period by the graded store and test the elapsed
   storage against it. A lot inside its period is reported as still in
   date and nothing further is done to it.
4. Check the cycle ceiling before assembling any test set.
5. Assemble the test set the lot owes and validate the record against
   it, refusing a record that carries a test the lot does not owe and
   reporting every owed test the record does not carry.
6. Apply the re-tinning allowance to a lone solderability failure where
   the allowance is open and unused; report every other failure and
   close on the failure.
7. Compute the extension this cycle grants, compare it against the
   minimum useful extension, and return the new permitted period with
   the findings that produced it.

## Pitfalls

- Reading the storage period off the package family alone. The family
  sets the baseline; the store the parts actually sat in is what scales
  it, and the two are routinely different from the procurement plan.
- Treating an ungraded store as merely a paperwork gap. A period that
  was never earned cannot be extended, and relifing such a lot puts
  unexamined leads into the build.
- Testing first and checking the cycle ceiling afterwards. A lot at its
  ceiling is a re-screening case whatever the tests say, and running
  them first invites the result to be argued with.
- Reading a missing test as a pass. An owed test absent from the record
  is the most common way a relifing record reads complete, and it is
  reported by name rather than inferred.
- Using the re-tinning allowance on a lot with a second failure. The
  allowance exists for a storage-induced surface condition standing on
  its own; alongside a seal or visual failure it is covering for
  something else.
- Granting a fixed extension every cycle. The decay is the mechanism
  that ends the sequence, and a flat grant relifes a lot forever in
  small steps.

## Behavior contract (gate 3)

The policy validation, the store grading and family lookup, the scaled
storage period and its boundary, the cycle ceiling, the assembled test
set including the electrical re-verification cycle, the test record
validation and missing-test report, the re-tinning allowance, the
decaying extension and the minimum useful extension, and the relifing
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_relifing.py against
scripts/q6013_class_2_relifing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_2_relifing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
