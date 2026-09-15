---
name: q60-class-1-stock-relifing
description: "Determine whether expired Class 1 EEE stock can have its storage validity restored under ECSS-Q-ST-60C clause 4.3.10. Use when testing stored parts against the expiry their last acceptance granted, measuring how much moisture-sensitivity floor life has been consumed to decide whether a bake precedes relifing, sizing the relifing sample, judging external visual, solderability and leak results against their accept numbers, and re-granting a shortened storage period from the relifing date. Refuses an unlisted moisture sensitivity level, a package thicker than the bake register covers, and stock that has used up its permitted relifing rounds. Trigger: ecss, q-st-60c, class-1-stock-storage-expiry, moisture-sensitivity-floor-life-budget, dry-pack-bake-recovery, relifing-solderability-sample, shortened-re-granted-storage-period, stored-stock-re-screening-ceiling."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-1-stock-relifing, class-1-stock-storage-expiry, moisture-sensitivity-floor-life-budget, dry-pack-bake-recovery, relifing-solderability-sample, shortened-re-granted-storage-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Stock Relifing (space-systems/ecss/q60-class-1-stock-relifing)

Use when the task is the relifing of ECSS-Q-ST-60C clause 4.3.10 —
restoring the storage validity of Class 1 parts that have sat in the
store past the period they were accepted under, so that stock already
paid for can go on a build instead of being re-purchased.

## Domain quick reference

- The period in force is **not** the period the parts were bought under.
  Every relifing round shortens it by a step, down to a floor, because
  stock kept once is not re-granted the period fresh parts get. The
  shortening is what stops relifing running forever on its own.
- The clock restarts at the **last acceptance or relifing operation**,
  never at goods-in. Counting from goods-in retires stock that a
  previous relifing already put back in date.
- Expiry is calendar-month arithmetic, not a day count, and the expiry
  day itself is still in date. The period runs out after that day.
- Two different clocks run at once. The storage period counts months in
  the store; the moisture-sensitivity **floor-life budget** counts hours
  outside the dry pack. Stock can be well inside its floor-life budget
  and still expired, or freshly accepted and already over-run.
- A floor-life over-run obliges a **bake before** the re-verification is
  worth running, and the bake duration comes from the package thickness
  band, not from the sensitivity level alone — a thick body holds
  moisture a thin one has already given up. A package thicker than the
  widest band has no established bake time and is refused.
- Solderability is the test that usually decides a relifing. Finish
  intermetallic growth is what the storage period is really limiting,
  and it is the one degradation a bake does nothing for.
- The round ceiling is read **before** any result. Stock past its
  permitted rounds goes to full re-screening whatever the sample did,
  because reading the result first invites it to be argued against the
  ceiling.

## Workflow

1. Compute the period in force from the base period and the rounds
   already used, floored at the minimum period.
2. Add it to the last acceptance or relifing date and compare the
   assessment date with the resulting expiry; in-date stock stops here.
3. Test the relifing round ceiling. Stock that has used its rounds goes
   to re-screening and no results are read.
4. Compute the consumed floor-life fraction from the exposure hours and
   the sensitivity level, and decide whether a bake is owed.
5. Where a bake is owed, read its duration from the package thickness
   band and add the post-bake moisture verification to the test set.
6. Size the relifing sample and judge every required test against its
   accept number; a required test with no result is refused, not passed.
7. On a clean re-verification, re-grant the shortened period from the
   assessment date and report the new expiry; on any failed test, reject
   the stock.

## Pitfalls

- Re-granting the base period at every relifing. The period has to
  shorten, or stock ages indefinitely on paper while degrading in fact.
- Counting months from goods-in on stock that has already been relifed.
  The clock restarted at that operation.
- Treating the expiry date itself as expired. Stock is in date through
  that day, and an assessment run on it is an in-date result.
- Conflating the storage period with the floor-life budget. They measure
  different degradations on different clocks, and passing one says
  nothing about the other.
- Baking to the sensitivity level and ignoring the package thickness. A
  thick body needs far longer, and a short bake leaves moisture in place
  under a clean-looking verification.
- Reading the re-verification before the round ceiling. Stock past its
  ceiling is not made eligible by a clean solderability result.
- Expecting a bake to rescue solderability. A bake drives moisture out;
  it does not undo intermetallic growth on the finish.

## Behavior contract (gate 3)

The period-in-force arithmetic, calendar-month expiry, round ceiling,
floor-life fraction, bake duration band, required-test derivation,
sample sizing and accept-number evaluation are exercised by the gate 3
contract test: scripts/test_q60_class_1_stock_relifing.py against
scripts/q60_class_1_stock_relifing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_1_stock_relifing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
