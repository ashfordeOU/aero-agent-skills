---
name: e2008-sca-qualification-general
description: "Use when a lot qualification status list, supplier procurement record or heritage justification has to be assessed. Verify the clause 6.4.1 requirement of ECSS-E-ST-20-08C that every procurement lot of cell assemblies is qualified in its own right: resolve the evidence each lot declares, hold a campaign to coupons drawn from that same lot, close the required activity set on enough of them, test any heritage claim against the configuration it leans on, and roll the procurement up into one verdict naming the lots that would ship unqualified. Trigger: ecss, e-st-20-08c, sca-qualification-general, procurement-lot-qualification-coverage, sca-qualification-coupon-provenance, sca-lot-heritage-claim-admissibility, solar-cell-assembly-lot-qualification."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-qualification-general, e-st-20-08c, sca-qualification-general, procurement-lot-qualification-coverage, sca-qualification-coupon-provenance, sca-lot-heritage-claim-admissibility, solar-cell-assembly-lot-qualification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Qualification, General (space-systems/ecss/e2008-sca-qualification-general)

Use when the task is clause 6.4.1 of ECSS-E-ST-20-08C: qualification of
cell assemblies attaches to the procurement lot, so every lot delivered
carries a qualification of its own. This leaf reads the evidence each
lot declares, decides whether that evidence belongs to the lot at all,
and returns the lots that would otherwise ship on somebody else's
campaign.

## Domain quick reference

- The obligation is per lot, not per design. What moves between lots is
  the cell batch, the coverglass batch, the interconnector reel, the
  operator and the line setting, and those are exactly the variables the
  qualification activities are sensitive to. A design qualified once and
  spent across every later delivery leaves each of those changes unseen.
- Evidence has to belong to the lot. A campaign run on coupons drawn
  from a different lot is a real campaign about a different population,
  so it is reported as a provenance fault and not as a thin campaign.
- A heritage claim is examined, not dismissed and not waved through.
  Naming the attributes that differ from the lot being leaned on is what
  turns an argument into a delta-qualification scope; finding no
  difference still leaves the clause obligation standing unless project
  policy has explicitly taken that position.
- Policy carries the heritage position, the code does not. Admitting a
  matching claim in place of a campaign is a project decision with
  consequences, so it is read from policy and refused by default.
- The arms are ranked, not merged. No campaign at all is reported ahead
  of a provenance fault, and a provenance fault ahead of an incomplete
  activity set, because closing activities on coupons from the wrong lot
  is wasted effort.
- Declared and delivered are two different lists. A lot that is
  delivered and appears nowhere in the qualification status list is the
  worst finding available, because every other finding at least means
  somebody looked.
- A lot declared but not delivered is not a finding. Holding a
  procurement open on a lot that never shipped sends the supplier back
  for evidence nobody needs.

## Workflow

1. Read every declared lot with its identity attributes, its campaign
   if it has one and any heritage claim. Reject a lot with no
   identifier or a missing identity attribute rather than carrying it.
2. Index the lots so a heritage claim can be resolved against the lot
   it names, and reject a claim a lot makes on itself.
3. For a lot with a campaign: test the coupon provenance against the
   lot, close the required activity set, size the coupon count, and
   read whether the campaign is closed.
4. For a lot without one: resolve the heritage claim, name the
   configuration attributes that differ, and admit it only where policy
   says a matching claim may stand in for a campaign.
5. Rank the arms into one lot verdict: no campaign first, then
   provenance fault, then incomplete campaign.
6. Roll the procurement up over the delivered lots: name the delivered
   lots nobody declared, group the rest by verdict, report the qualified
   share, and return a verdict that is clean only when no delivered lot
   is open.

## Pitfalls

- Reading a qualification as a property of the design. It is held
  against the lot, so a second lot from the same drawing starts with no
  qualification at all.
- Accepting a campaign because the coupons were qualification coupons.
  The question is which lot they came from, and a coupon from an
  earlier lot carries that lot's cells and that lot's line setting.
- Treating a matching configuration as a discharged obligation. Nothing
  differing is a good argument for a reduced campaign, not evidence
  that a campaign happened.
- Dismissing a heritage claim without naming the delta. The list of
  differing attributes is the scope of the work that would make the
  claim stand, and dropping it sends the supplier back with nothing to
  act on.
- Rolling up over the declared lots instead of the delivered ones. A
  status list that simply omits a lot then reads as fully qualified,
  which is the one failure the rollup exists to catch.
- Merging the arms into one pass or fail. A lot with no campaign and a
  lot with a campaign short of two activities need different responses,
  and a merged verdict asks for the same one twice.

## Behavior contract (gate 3)

The identity attributes, the configuration delta, the campaign coupon
provenance and completeness test, the heritage admissibility rule, the
ranked lot verdict and the rolled-up procurement coverage over delivered
lots are exercised by the gate 3 contract test:
scripts/test_e2008_sca_qualification_general.py against
scripts/e2008_sca_qualification_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_qualification_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
