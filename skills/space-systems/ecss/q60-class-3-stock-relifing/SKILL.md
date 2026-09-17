---
name: q60-class-3-stock-relifing
description: "Determine which time-expired Class 3 EEE stock lots can have their storage validity restored under clause 6.3.10 of ECSS-Q-ST-60C: read the date code to fix the manufacture point, measure elapsed storage against the period the lot was issued, compute the decaying period each further relife cycle earns, trim that grant to the total life left from manufacture, assemble the evidence the package seal and moisture level owe, separate absent evidence from failed evidence, and spend a limited relife test capacity where it releases the most build demand. Use when an expired store has to become a relife campaign rather than a scrap list. Trigger: ecss, q-st-60c-clause-6-3-10, q60-c3-expired-stock-relife-campaign, q60-c3-relife-cycle-decay-grant, q60-c3-total-life-headroom-cap, q60-c3-owed-relife-evidence-set, q60-c3-relife-capacity-allocation."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c-clause-6-3-10, q60-class-3-stock-relifing, q60-c3-expired-stock-relife-campaign, q60-c3-relife-cycle-decay-grant, q60-c3-total-life-headroom-cap, q60-c3-owed-relife-evidence-set, q60-c3-relife-capacity-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Expired Stock Relifing (space-systems/ecss/q60-class-3-stock-relifing)

Use when the task is clause 6.3.10 of ECSS-Q-ST-60C: Class 3 parts were bought,
accepted and put away, the build slipped, and the storage period those lots were
issued has run out. The leaf turns a shelf of expired lots into a campaign —
which lots earn a renewed period, what each owes before it gets one, which are
finished, and which of the survivors the available test capacity should reach.

## Domain quick reference

- Relifing renews the evidence behind a lot, not the parts. Nothing about the
  parts changed on the day the period lapsed; what lapsed is the currency of the
  acceptance evidence, and restoring validity means taking that evidence again.
- The date code is the anchor, not the receipt. The receipt says when the lot
  reached this store; the date code says when the part was made, and the total
  life a part is entitled to runs from the second. A lot that changed hands
  twice can be inside its storage period and out of its life at the same time.
- A renewed period is smaller than the one before it. Treating each relife as a
  fresh full period is how a lot gets kept alive indefinitely on paper, so the
  grant decays with every cycle already spent and stops when the allowance is.
- Two ceilings apply and the lower one wins. The cycle-decay grant is what the
  operation earns; the life headroom from the date code is what the part has
  left. Granting the first without trimming it to the second relifes a lot past
  the total life it was ever entitled to.
- The evidence owed depends on how the lot was actually packaged. A sealed dry
  pack owes the base set; an opened one on a moisture-sensitive part reopens the
  bake; an uncontrolled bag reopens electrical re-verification as well, because
  nothing about the store is known.
- Absent evidence and failed evidence are different answers. Absent means the
  work has not been done and the grant is conditional on doing it; failed means
  the work was done and the lot did not pass, which is a disposition.
- A failed solderability sample is recoverable and the rest are not. Surfaces
  can be re-tinned and re-screened; a leaking package or a part that no longer
  meets its electrical limits at ambient has no route back.
- Capacity is the real constraint on a stock of any size. Ordering the campaign
  by lot size spends the whole capacity on the biggest lot; ordering it by the
  build demand each test slot releases spends it where the programme feels it.

## Workflow

1. Validate every stored lot record and reject a stock that names one lot twice.
2. Read each date code to a manufacture week and take the life headroom left
   against the total life the part is entitled to.
3. Compare elapsed storage with the issued period, treating a lot sitting
   exactly on its period as still inside it and leaving it alone.
4. Compute the decaying grant the next cycle earns, then trim it to the headroom.
5. Assemble the owed evidence from the package seal, the moisture level and
   whether the package is hermetic, and split the records into absent and failed.
6. Decide a disposition per lot, letting a failure outrank a shortfall and a
   spent allowance outrank a clean evidence file.
7. Order the workable lots by demand released per test slot, spend the capacity
   down that order, and report what the campaign covers and what it defers.

## Pitfalls

- Relifing from the receipt date. The storage period starts at acceptance but
  the total life starts at manufacture, and a lot bought from stock elsewhere
  can have most of its life already gone before it arrived.
- Granting a full fresh period every cycle. The arithmetic looks generous and
  the lot never dies; the standard's intent is that each renewal buys less.
- Ignoring the life headroom because the grant looked modest. The trim is what
  stops a third relife from carrying a part past the life it ever had.
- Reading an owed test with no record as a pass. An empty row is the commonest
  cause of a lot going back to stores with evidence nobody actually took.
- Sending a failed solderability sample to scrap. It is the one failure with a
  route back, and scrapping it throws away parts that a re-tin would recover.
- Treating an uncontrolled bag as an opened dry pack. The bag reopens electrical
  re-verification too, because nothing about where it sat is known.
- Ordering the campaign by lot size. The largest lot is frequently the one with
  the least demand behind it, and it will eat a whole test capacity unnoticed.

## Behavior contract (gate 3)

The date-code parsing, life-headroom arithmetic, storage-period comparison,
cycle-decay grant, headroom trim, owed-evidence assembly, absent-versus-failed
split, per-lot disposition, priority ordering and capacity allocation are
exercised by the gate 3 contract test:
scripts/test_q60_class_3_stock_relifing.py against
scripts/q60_class_3_stock_relifing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q60_class_3_stock_relifing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
