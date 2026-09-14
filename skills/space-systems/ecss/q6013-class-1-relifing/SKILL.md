---
name: q6013-class-1-relifing
description: "Determine whether a stored lot of commercial EEE parts has outrun its permitted storage period and what relifing it needs under ECSS-Q-ST-60-13C clause 4.3.10. Use when computing a storage expiry date from the package family and storage environment, testing it against the assessment date, sizing the relifing sample, judging visual, solderability, hermeticity and electrical re-verification results, and extending or refusing the storage period. Refuses an unknown storage condition, an exhausted extension count, and cumulative storage beyond the declared ceiling. Trigger: ecss, q-st-60-13c, commercial-part-storage-expiry, commercial-lot-relifing, storage-period-extension, relifing-sample-solderability, stored-eee-re-verification, cumulative-storage-ceiling."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-relifing, commercial-part-storage-expiry, commercial-lot-relifing, storage-period-extension, stored-eee-re-verification, cumulative-storage-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Relifing (space-systems/ecss/q6013-class-1-relifing)

Use when the task is the relifing of ECSS-Q-ST-60-13C clause 4.3.10 —
deciding whether a lot of commercial EEE parts sitting in the store has
outrun the storage period it was accepted under, and what has to be
re-verified before the lot may be used on a Class 1 build.

## Domain quick reference

- A storage period is granted against a **pair**: the package family and
  the environment the lot is actually stored in. The same ceramic
  hermetic lot carries a long period under dry nitrogen and a much
  shorter one in controlled ambient, because what runs the clock is
  moisture ingress and surface degradation, not shelf time as such. A
  pair that the project register never granted is refused, not defaulted
  to the nearest one.
- The clock restarts at the **last acceptance or relifing operation**,
  not at the original goods-in date. The original date is still needed,
  separately, for the cumulative ceiling.
- Expiry is calendar-month arithmetic, not a day count. A lot accepted
  on 31 January with a one-month period expires at the end of February,
  and a lot assessed on the expiry date itself is still in date — the
  period runs out after that day, not on it.
- Relifing is a sample re-verification, not a re-purchase. The sample is
  a fraction of the lot rounded up, never below a floor, capped by the
  lot. The test set is visual, solderability and electrical for every
  package, plus a seal integrity check where the package is hermetic —
  a plastic-encapsulated commercial part cannot be given one.
- Two ceilings stop a lot being extended forever: the number of relifing
  operations already performed, and the cumulative storage since
  original acceptance. Either one reached sends the lot to full
  re-screening rather than to another extension, and both are tested
  **before** any re-verification result is read, because a lot past its
  ceiling is not made eligible by a clean solderability result.
- Solderability is the test that usually decides a commercial relifing.
  Tin-lead and pure-tin finishes on commercial parts age differently
  from the controlled finishes of space-grade parts, which is exactly
  why the storage period on a commercial lot is shorter.

## Workflow

1. Resolve the permitted period from the storage register for the
   package family and the storage environment; refuse an unlisted pair.
2. Compute the expiry date by adding the permitted months to the last
   acceptance or relifing date, clamping the day into shorter months.
3. Compare the assessment date with the expiry date. A lot still inside
   its period is reported in date and nothing further is done to it.
4. For an expired lot, compute the elapsed months since the last
   operation and the cumulative months since original acceptance.
5. Test both ceilings. If the extension count is exhausted or the
   cumulative storage has reached its limit, dispose of the lot to
   re-screening and stop; do not read the re-verification results.
6. Size the relifing sample and evaluate every required test against its
   pass fraction. A required test with no result is refused, never
   treated as a pass.
7. On a clean re-verification, extend the period from the assessment
   date and report the new expiry; on any failed test, reject the lot.

## Pitfalls

- Counting the storage period from goods-in on a lot that has already
  been relifed once. The clock restarted at that operation; counting
  from goods-in retires a lot that is still in date.
- Using day arithmetic for a period quoted in months. Thirty-day months
  drift by days per year, and the drift always falls on the side that
  keeps an expired lot in stock.
- Treating the expiry date itself as expired. The lot is in date through
  that day; an assessment run on it is an in-date result.
- Reading re-verification results before the ceilings. A lot past its
  cumulative limit cannot be relifed however well it tests, and
  evaluating first invites the result to be argued against the ceiling.
- Skipping a required test because it is not applicable, without saying
  so. A missing result is a refusal; the way to drop a seal check is to
  record the package as non-hermetic, which the required-test set then
  reflects.
- Extending by the original period without checking that any extension
  is still permitted. The extension count exists precisely so the second
  and third relifing are not automatic.

## Behavior contract (gate 3)

The storage-register lookup, calendar-month expiry arithmetic, expiry
comparison, ceiling tests, sample sizing, required-test derivation and
re-verification evaluation are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_relifing.py against
scripts/q6013_class_1_relifing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_1_relifing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
