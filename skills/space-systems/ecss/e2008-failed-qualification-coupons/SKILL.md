---
name: e2008-failed-qualification-coupons
description: "Determine how a qualification coupon that showed one or more failure modes is treated under ECSS-E-ST-20-08C clause 5.6.2. Use when a failed solar-array coupon needs a disposition rather than an opinion: withdraw the coupon as qualification evidence whatever the cause, hold the disposition open while any mode is still unattributed, map each attributed cause onto the retest scope it forces, let the widest scope govern when several modes are present, and keep the retest inadmissible until corrective action is implemented and verified. Trigger: ecss, e-st-20-08c, clause-5-6-2, failed-qualification-coupon-disposition, solar-array-coupon-retest-scope, coupon-root-cause-attribution, qualification-evidence-withdrawal, coupon-corrective-action-verification, photovoltaic-requalification-trigger."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-failed-qualification-coupons, e-st-20-08c, clause-5-6-2, failed-qualification-coupon-disposition, solar-array-coupon-retest-scope, coupon-root-cause-attribution, qualification-evidence-withdrawal, photovoltaic-requalification-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Failed Qualification Coupons (space-systems/ecss/e2008-failed-qualification-coupons)

Use when the task is the clause 5.6.2 disposition of ECSS-E-ST-20-08C: a
qualification coupon has presented one or more of the failure modes the
standard lists, and what happens to that coupon, to its subgroup and to
the qualification behind it has to be settled.

## Domain quick reference

- Two decisions sit inside this clause and they run on different clocks.
  The coupon stops being qualification evidence the moment it fails, and
  that does not wait on anything. How far the retest reaches waits on the
  investigation, because it is the cause, not the mode, that decides it.
- A coupon that failed cannot also stand as proof the design passed.
  Withdrawing it is not a penalty and it is not conditional on the cause
  turning out to be the coupon's fault; a failed article is simply not
  evidence of success.
- While any mode is still without an attributed cause the disposition is
  open, not narrow. The tempting move is to assume the cause is confined
  to the article in hand and repeat only that article — which is exactly
  how a systematic process cause gets repaired as a one-off and reappears
  in flight hardware.
- Once attributed, the cause maps onto a reach. A failure traced to the
  test installation touches the coupon alone. An isolated build escape
  reaches its subgroup. A systematic process cause or a cause inherent to
  the design reaches the whole qualification, and the work already done
  under that design or that process no longer stands.
- A coupon carrying several modes takes the widest reach any of them
  forces. The narrow ones do not dilute the wide one, and averaging
  across them is how a design-inherent finding leaves the record as a
  subgroup repeat.
- A retest run before the corrective action is in place repeats the
  failure at best and hides it at worst, so the action has to be both
  implemented and independently verified before the retest is admissible.

## Workflow

1. Validate the failure record: at least one recognized mode, each
   carrying its cause category. An unrecorded cause is recorded as
   undetermined, never left out, and a repeated mode is a record defect.
2. Withdraw the coupon as qualification evidence immediately, before any
   scope question is asked.
3. If any mode is still undetermined, report it, set the scope to none
   and leave the disposition open. Nothing further is decidable yet.
4. Otherwise map every attributed cause to the reach it forces and take
   the widest, naming the mode and cause that govern it.
5. Translate that reach into the standing of work already done: the
   coupon result, the subgroup result, or the qualification itself.
6. Check the corrective action for the governing cause. Not implemented,
   or implemented but unverified, blocks the retest; only both complete
   authorizes it. Report the findings beside the disposition.

## Pitfalls

- Waiting for the investigation before withdrawing the coupon. The two
  decisions are independent, and holding the evidence question open lets
  a failed article keep counting toward a pass in the interim.
- Reading an undetermined cause as a minor one. It forces no scope at
  all; treating it as the narrowest is a guess wearing a verdict's
  clothes.
- Letting the narrowest attributed cause set the scope. The widest
  governs, and a coupon with both a set-up artefact and a design-inherent
  mode is a design problem that also had a set-up problem.
- Calling a failure a test-installation artefact without evidence. It is
  the one attribution that leaves the design untouched, which is exactly
  why it needs the strongest evidence rather than the weakest.
- Authorizing the retest on an implemented-but-unverified action.
  Implementation is a claim; verification is what makes the retest mean
  something.
- Treating a systematic process cause as narrower than a design cause.
  Both reach the whole qualification — the process built every article,
  not only this one.

## Behavior contract (gate 3)

The failure-record validation, the unconditional evidence withdrawal, the
undetermined-cause hold, the cause-to-scope mapping with its widest-scope
rule, the qualification-status translation and the corrective-action
admissibility check are exercised by the gate 3 contract test:
scripts/test_e2008_failed_qualification_coupons.py against
scripts/e2008_failed_qualification_coupons_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_failed_qualification_coupons.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
