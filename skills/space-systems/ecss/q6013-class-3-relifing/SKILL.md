---
name: q6013-class-3-relifing
description: "Use when an expired storage period has to become a disposition at the lightest class. Determine whether a stored lot of commercial EEE parts may have its usable life renewed at the lowest assurance class under ECSS-Q-ST-60-13C clause 6.3.10: grade the store the parts actually sat in, scale the package family baseline by it, test elapsed storage against the earned period, size the attribute sample this class inspects in place of every unit, assemble the fuller test set an uncontrolled store reopens, apply the repeatable re-tinning allowance up to its ceiling, and end the sequence on a cumulative life cap rather than a cycle count. Trigger: ecss, q-st-60-13c-clause-6-3-10, class-three-relifing, earned-storage-period-grading, relife-attribute-sample-plan, cumulative-storage-life-cap, repeatable-retinning-allowance, stored-lot-re-screening-referral."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-relifing, class-three-relifing, earned-storage-period-grading, relife-attribute-sample-plan, cumulative-storage-life-cap, repeatable-retinning-allowance, stored-lot-re-screening-referral]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Relifing (space-systems/ecss/q6013-class-3-relifing)

Use when the task is the clause 6.3.10 storage question of ECSS-Q-ST-60-13C
at the lowest assurance class: parts bought for a build have sat in store
while the build slipped, the period the lot earned when it was accepted has
run out, and the question is whether the usable life of those parts can be
renewed and on what evidence.

## Domain quick reference

- An expired lot is neither scrap nor usable. Relifing is the operation that
  decides which, and it is an operation with an outcome rather than a stamp
  applied to keep the build moving.
- The period a lot earned depends on where it actually sat, not on where the
  procurement paperwork said it would sit. The package family sets a
  baseline and the graded store scales it, so the same lot earns a long
  period in dry nitrogen and a fraction of it on an open shelf.
- This class differs from the ones above in the store it will still credit.
  An uncontrolled store earns a short period here instead of nothing, and
  the relaxation is paid for rather than given: the same store reopens
  moisture preconditioning and electrical re-verification, which a graded
  store does not owe at this class.
- The evidence is taken on a sample, not on the lot. The plan is sized from
  the lot itself and held between a floor and a ceiling, so a small lot is
  inspected almost entirely and a reel of ten thousand is not. A record
  covering fewer units than the plan calls for has not run the plan.
- The sample is judged against an acceptance number, and the default
  acceptance number is zero. One defective unit in the sample is a failed
  test, not a percentage to be argued about.
- Re-tinning is repeatable here where the class above grants it once, but it
  is repeatable up to a declared ceiling. A lot that has used its re-tins
  and fails solderability again is telling you about the terminations, not
  about the tinning.
- What ends the sequence at this class is a cumulative cap on relifed months
  -- a multiple of the period the lot originally earned -- rather than a
  count of cycles. Each cycle grants a flat share of the earned period,
  trimmed to whatever headroom is left, and once the trimmed grant falls
  under the minimum useful extension the lot goes for re-screening.
- A lot sitting exactly on its permitted period is inside it. The scaling
  can leave the two sides a few ULP apart, which is representation error
  rather than an expired lot, and the comparison absorbs it instead of the
  period being padded.

## Workflow

1. Validate the relifing policy: the flat extension fraction, the minimum
   useful extension, the cumulative life multiple, the re-tin ceiling and
   the attribute sample bounds with their acceptance number. A fraction
   above unity, a non-positive multiple or a sample ceiling below its floor
   is refused rather than used.
2. Grade the store and resolve the package family, refusing an unregistered
   store or family rather than assuming a period that was never earned, and
   scale the baseline into the period the lot earned.
3. Test elapsed storage against that period. A lot inside its period is
   reported as still in date and nothing further is done to it.
4. Test the cumulative relifed months against the life cap before any
   evidence is considered. A lot with no headroom left is a re-screening
   case whatever the sample says.
5. Size the attribute sample from the lot, assemble the test set the lot
   owes, and refuse a record that covers fewer units than the plan or that
   is missing an owed test. Report every missing test by name.
6. Judge each owed test against the acceptance number, and apply the
   repeatable re-tinning allowance to a lone solderability failure while
   re-tins remain. Every other failure, or solderability alongside another,
   closes on the failure.
7. Compute the flat grant, trim it to the cap headroom, compare it against
   the minimum useful extension, and return the renewed period with the
   findings that produced it.

## Pitfalls

- Reading the storage period off the package family alone. The family sets
  the baseline; the store the parts actually sat in is what scales it, and
  the two are routinely different from the procurement plan.
- Reading the credit an uncontrolled store earns here as a general
  relaxation. It buys a short period and it costs two extra tests, so a lot
  relifed out of an uncontrolled store on the graded test set has been
  relifed on the wrong evidence.
- Inspecting whatever units came to hand. The plan is sized from the lot,
  and a record covering eight units where the plan calls for ten is short of
  the plan rather than close to it.
- Reading a missing test as a pass. An owed test absent from the record is
  the most common way a relifing record reads complete, and it is reported
  by name rather than inferred.
- Re-tinning a lot that has used its re-tins, or one carrying a second
  failure. The allowance exists for a storage-induced surface condition
  standing on its own; used twice over it is covering for terminations that
  are no longer recoverable.
- Granting the flat share without looking at the cap. The trim is the
  mechanism that ends the sequence, and an untrimmed grant relifes a lot
  past the total life it was ever entitled to.

## Behavior contract (gate 3)

The policy validation, the store grading and family lookup, the earned
storage period and its boundary, the cumulative life cap, the attribute
sample plan, the assembled test set including the tests an uncontrolled
store reopens, the sample record validation and missing-test report, the
acceptance number, the repeatable re-tinning allowance and its ceiling, the
flat grant trimmed to the cap headroom, the minimum useful extension and the
relifing verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_relifing.py against
scripts/q6013_class_3_relifing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_3_relifing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
