---
name: e2008-thermal-cycle-acceptance-process
description: "Use when planning or auditing an acceptance cycling run on photovoltaic-assembly coupons. Perform the acceptance thermal-cycle exposure of solar-array coupons under ECSS-E-ST-20-08C clause 5.5.3.7.3: resolve the acceptance cycle count from the referenced testing standard and the coupon category instead of deriving one locally, refuse a declared count that falls below that reference, record an overtest that runs past it, credit each coupon only with the cycles that survived its interruptions, invalidate a coupon whose run was broken more often than the allowance permits, and close the set only when enough coupons have each reached the count. Trigger: ecss, e-st-20-08c, clause-5-5-3-7-3, pva-acceptance-thermal-cycle-exposure, referenced-testing-standard-cycle-count, solar-array-coupon-acceptance-cycling, coupon-cycle-exposure-credit, cycling-interruption-invalidation."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-thermal-cycle-acceptance-process, pva-acceptance-thermal-cycle-exposure, referenced-testing-standard-cycle-count, solar-array-coupon-acceptance-cycling, coupon-cycle-exposure-credit, cycling-interruption-invalidation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Thermal-cycle Acceptance Process (space-systems/ecss/e2008-thermal-cycle-acceptance-process)

Use when the task is the acceptance thermal-cycle exposure of
ECSS-E-ST-20-08C clause 5.5.3.7.3 -- putting a set of photovoltaic-assembly
coupons through the number of cycles the referenced testing standard
defines, and deciding afterwards whether they actually took them.

## Domain quick reference

- This is the acceptance exposure, not the qualification campaign, and
  the difference is where the number comes from. A qualification count
  is derived from the mission: eclipse rate, duration, a qualification
  factor. An acceptance count is not derived at all. It is read out of
  the testing standard the assembly documentation references, against
  the category of coupon being exposed.
- The programme's job is therefore to name the reference, not to pick a
  number. A count invented locally, or carried over from a previous
  programme, is the defect this step exists to catch: the lot then
  carries an acceptance stamp for an exposure it never had.
- Coupon category changes the count under one and the same reference. A
  cell-stack coupon and a harness-termination coupon do not share a
  fatigue mechanism, and reading one category's count across to another
  is the same defect wearing a more plausible face.
- Running more cycles than the reference defines is not a failure, but
  it is not free either. Overtest consumes coupon life and chamber
  weeks, so it is recorded as a finding rather than absorbed silently,
  and an overtest well past the declared allowance is called out
  separately.
- Cycles run and cycles credited are different numbers. An interruption
  -- a chamber excursion out of the profile, a power loss, a coupon
  removed and re-installed -- invalidates the cycles run since the last
  valid checkpoint. Only the credited number is compared against the
  requirement.
- A run broken too often is not short, it is unrepresentative. Past the
  interruption allowance the coupon's exposure stops being a
  continuous thermal history at all, and the answer is a re-run rather
  than more cycles bolted onto the end.
- The set carries a rule of its own. A category is represented by a
  minimum number of coupons, so one perfectly exposed coupon does not
  close a category that owes two.

## Workflow

1. Validate the policy: every referenced standard in the catalogue
   covers every coupon category with a positive whole cycle count, and
   the coupon minimum, interruption allowance and overtest allowance
   are present. A catalogue missing a category is an input error.
2. Resolve the required count from the named reference and the coupon
   category. Refuse a reference the catalogue does not carry rather
   than falling back on a neighbouring one.
3. Reconcile any locally declared count against the resolved one.
   Refuse a declaration below the reference; record one above it, and
   flag the part of it that runs past the overtest allowance.
4. Credit each coupon: take the cycles run, subtract what each
   interruption invalidated, and reject a record whose interruptions
   are logged past the end of the run or take back cycles that were
   never run.
5. Grade each coupon. Too many interruptions makes it invalid; too few
   credited cycles makes it short; otherwise it is exposed, and a
   coupon that lost cycles and still met the count says so in its
   findings.
6. Close the set. It is complete only when every submitted coupon is
   exposed and the category minimum is met, and the completion
   fraction of each coupon shows how far a short one has to go.

## Pitfalls

- Treating the acceptance count as something to derive. The mission
  drives the qualification campaign; the referenced testing standard
  drives this one, and deriving here produces a defensible-looking
  number with no authority behind it.
- Reading one coupon category's count across to another. The counts
  differ under the same reference precisely because the mechanisms do.
- Counting chamber cycles rather than credited cycles. A run logged as
  complete with an interruption in the middle of it has delivered
  fewer cycles than its log states.
- Bolting extra cycles onto a run that was broken too often. The
  allowance exists because a fragmented thermal history stops being
  representative, and topping it up does not reassemble it.
- Accepting a category on one excellent coupon. The minimum is a
  separate rule, and a single coupon demonstrates nothing about the
  spread of the process that produced the lot.
- Comparing an overtest against a fractional allowance by bare
  arithmetic. The allowance is a product of a fraction and a whole
  count, so an overtest exactly on it can evaluate a few units in the
  last place above; the comparison absorbs that representation error.

## Behavior contract (gate 3)

The policy validation, referenced-count resolution, declared-count
reconciliation, interruption crediting, coupon grading and the set
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_thermal_cycle_acceptance_process.py against
scripts/e2008_thermal_cycle_acceptance_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_thermal_cycle_acceptance_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
