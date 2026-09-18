---
name: q7080-powder-reuse-and-blending
description: "Manage the reuse and blending of metallic powder feedstock for powder bed fusion under ECSS-Q-ST-70-80C: build a blend from virgin and previously used lots, compute the mass-weighted oxygen content, particle size, fines fraction and virgin fraction alongside the worst-case reuse count, compare each against the declared reuse limits, derive the characterisation the blend owes from its cadence and the triggers that fired, and close with an accept, accept-after-test or reject disposition. Use when powder is recovered from a build, topped up with virgin material, or presented for the next build. Trigger: ecss, q-st-70-80c, powder-reuse-limit-control, powder-blend-composition, powder-oxygen-pickup, powder-recharacterisation-cadence, powder-lot-disposition."
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
  tags: [ecss, q-st-70-80c-powder-bed-fusion, q-st-70-80c, q7080-powder-reuse-and-blending, powder-reuse-limit-control, powder-blend-composition, powder-oxygen-pickup, powder-recharacterisation-cadence, powder-lot-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Powder Bed Fusion — Powder Reuse and Blending (space-systems/ecss/q7080-powder-reuse-and-blending)

Use when the task is the powder reuse and blending control of ECSS-Q-ST-70-80C:
whether a drum built from recovered and virgin material may be loaded, what it
has to be tested for first, and how many builds it has left.

## Domain quick reference

- A build does not consume powder evenly. What comes back off the plate has
  been through the process atmosphere, has lost part of its fine fraction to
  spatter and the filter, and has picked up interstitial oxygen. Recovered
  powder is therefore a different material from the drum it came out of, and
  it is controlled as one.
- A blend has a composition of its own, taken by mass: the oxygen content, the
  median particle size and the fines fraction all weight by lot mass, so a
  small drum of badly degraded powder is diluted and a large one is not.
- Reuse is counted twice and the two counts answer different questions. The
  mass-weighted count describes the bulk and is what most of the material has
  seen. The worst-case count describes the oldest particle in the drum, and it
  is the one the cycle limit is applied to, because the limit exists to bound
  the most degraded fraction present.
- Oxygen pickup is the usual binding constraint on a reactive alloy, and it is
  one-way. A blend can be brought back under a limit by adding virgin powder,
  but nothing removes what the previous builds already put in.
- Particle size drifts in both directions. The fines are preferentially lost,
  which pushes the median up and the flowability with it, while satellites and
  partly sintered agglomerates push the coarse tail out. A window, not a
  ceiling, is the right control.
- Characterisation is owed on a cadence and on triggers. Blending two lots is
  itself a trigger, because the blend has never been measured as a blend; so
  is reaching the interval since the last full characterisation, approaching
  the oxygen or fines limit, and any exposure of the powder to atmosphere.
- The disposition has three states, not two. Outside a limit is a rejection;
  inside every limit but owing a test is an acceptance conditional on that
  test; inside every limit with the tests closed is an acceptance. Loading on
  the second state without closing the test is the failure this control exists
  to prevent.

## Workflow

1. Declare every lot going into the drum: identifier, mass, reuse count,
   oxygen content, median size, fines fraction, cycles since its last full
   characterisation, and whether it has seen atmosphere. Reject an undeclared
   value rather than defaulting it.
2. Compute the blend composition by mass, and keep the worst-case reuse count
   next to the mass-weighted one.
3. Grade every property against the declared policy: the cycle limit, the
   oxygen ceiling, the virgin floor, the fines cap and the size window.
4. Derive the test set from the triggers that actually fired, and subtract the
   tests already closed to leave what is outstanding.
5. Project the reuse count one build forward, and say so when this build is
   the last one the drum is allowed.
6. Close with the disposition and the findings, so the store and the shop
   floor read the same answer.

## Pitfalls

- Applying the cycle limit to the mass-weighted count. The average is always
  lower than the worst case, so a drum topped up with virgin powder appears to
  reset while the oldest fraction is still in it, and the limit stops bounding
  anything.
- Treating a virgin top-up as a reset. It dilutes the oxygen and the fines and
  buys the drum more builds, but it does not remove a single degraded particle
  and it does not restart the cycle count.
- Grading a blend against the certificate of its largest lot. The blend was
  never measured as a blend; the certificate describes material that no longer
  exists in that form, which is precisely why blending is itself a trigger for
  characterisation.
- Comparing a mass-weighted property with a limit by bare arithmetic. The
  property is a sum of quotients, so a blend that sits exactly on its limit can
  land a few units in the last place above it; the comparison absorbs that
  representation error while the limit stays untouched.
- Controlling particle size with a ceiling alone. The fines are lost first, so
  the median drifts upward as well as downward and a one-sided limit misses
  the flowability change entirely.
- Loading on a conditional acceptance. An accept-after-test disposition is not
  an acceptance, and the outstanding test list is the part of the record the
  next build has to close.

## Behavior contract (gate 3)

The policy validation, lot validation, mass-weighted blend composition, limit
grading, trigger-driven test selection, forward reuse projection and
disposition are exercised by the gate 3 contract test:
scripts/test_q7080_powder_reuse_and_blending.py against
scripts/q7080_powder_reuse_and_blending_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7080_powder_reuse_and_blending.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
