---
name: e2008-blocking-diode-acceptance-general
description: "Use when a blocking diode acceptance matrix, lot traveller set or sampling plan is under review. Evaluate a blocking diode lot record against clause 12.4.1 of ECSS-E-ST-20-08C, where two populations owe acceptance at once: the diodes being delivered and the diodes the qualification work consumes. Split the per-unit activities from the lot-sampled ones, score each sampled activity on the share of its population actually drawn, hold absent records, unrun work and recorded failures apart, flag a population carrying no acceptance at all, and roll the lot into one verdict with ranked findings. Trigger: ecss, e-st-20-08c, blocking-diode-acceptance-testing-general, blocking-diode-delivery-population-acceptance, blocking-diode-qualification-population-acceptance, blocking-diode-sampled-activity-share, blocking-diode-acceptance-record-state, blocking-diode-lot-acceptance-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-acceptance-general, blocking-diode-acceptance-testing-general, blocking-diode-delivery-population-acceptance, blocking-diode-qualification-population-acceptance, blocking-diode-sampled-activity-share, blocking-diode-acceptance-record-state, blocking-diode-lot-acceptance-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes — Acceptance Testing, General (space-systems/ecss/e2008-blocking-diode-acceptance-general)

Use when the task is clause 12.4.1 of ECSS-E-ST-20-08C: acceptance testing is
applied to the blocking diodes being delivered and to the blocking diodes used
during the qualification work. This leaf grades a lot record on whether both
populations carry the acceptance activity set, on the basis each activity is
applied on.

## Domain quick reference

- The qualification population is the half that gets dropped. A diode consumed
  by a qualification coupon is not being shipped, so acceptance reads like an
  obligation somebody else carries. It is the other way round: a qualification
  result only means something if the diode it was produced on was a sound diode
  before the campaign touched it.
- An unaccepted blocking diode that leaks during a qualification run has settled
  nothing. The result cannot separate a mounting process that does not hold from
  a part that was already degraded, and the campaign is repeated at full cost.
- Blocking diodes split their acceptance work by basis. The visual inspection,
  the forward voltage measurement and the reverse leakage measurement are
  carried by every unit; the thermal shock, the solderability check and the seal
  leak test are drawn on a sample of the lot. The basis decides what a missing
  record even means.
- A sampled activity is graded on the share of its population actually drawn,
  never on any single unit. Graded unit by unit it reports nearly every diode as
  missing a record it never owed, and the genuinely undocumented units are lost
  in the noise.
- A failure found in a sample speaks for the lot rather than for the unit it was
  found on, which is why it is carried as a population finding and not folded
  into one diode's verdict.
- Absent, not-run and failed are three different states and they are
  dispositioned by different people through different paperwork. No record at
  all is the worst, because nobody knows whether the work was skipped, lost or
  never scheduled. Work recorded as not yet run is a schedule item. A recorded
  failure is known and can be dispositioned.
- Exemption is a population-level defect and not a unit-level one. One diode
  with a thin traveller is a paperwork problem; a whole population with empty
  records is a decision somebody made, and it is reported as its own finding
  rather than as a run of individually incomplete units.
- Whether a dispositioned failure leaves the lot open is a project position, and
  it is read from policy twice over: once as the position itself, and once as
  the cleared share the project will still carry. Assuming either answer
  silently accepts or silently rejects hardware.

## Workflow

1. Resolve the policy: which activities every unit carries, which are drawn on
   a sample, the sampling floor, the cleared floor and the failure position.
   Refuse an activity placed on both bases at once.
2. Validate each unit: a unique identifier, one of the two populations, and
   records naming only activities this clause owes.
3. Grade each unit against the every-unit activities only -- what has no record,
   what is recorded as not run, what failed and what passed. A unit never drawn
   into a sample is not missing anything.
4. Rank the unit verdict -- absent record first, then unrun, then failed -- so
   the lot report names the root cause before the consequence.
5. Grade each sampled activity over its population: how many units were drawn,
   what share of the population that is against the floor, and which drawn units
   failed.
6. Summarise each population: how many units it holds, how many are clear, the
   cleared share against its floor, the sampled results and the weakest unit.
7. Detect a population absent from the lot and a population present whose units
   carry no acceptance work at all; report each as its own finding.
8. Report the lot: units in rank order, both population summaries, and one
   verdict with every finding ranked.

## Pitfalls

- Running the acceptance matrix over the delivery lot only. The qualification
  diodes are inside the clause, and leaving them out is the single defect this
  leaf exists to catch.
- Grading a sampled activity unit by unit. Nearly every diode then looks as
  though it is missing a record, and the real gaps disappear into the noise.
- Grading an every-unit activity as a sample. A lot of thousands closes on a
  handful of visual inspections nobody agreed to substitute.
- Reading an empty acceptance record as a pass. A diode with no record has not
  been shown sound; it has been shown undocumented.
- Collapsing absence into failure. They reach different desks through different
  paperwork, so the verdict keeps them apart.
- Folding a sampled failure into one unit's verdict. The sample was drawn to
  speak for the population, so the finding belongs to the population.
- Assuming a failed diode closes the lot. Both answers are legitimate project
  positions, and assuming either produces a verdict nobody agreed to.
- Judging a drawn share or a cleared share that lands exactly on its floor by
  bare arithmetic. Both are quotients of counted units, so a lot drawn to
  exactly the declared fraction can land a unit in the last place below it; the
  comparison absorbs that while the floor stays as declared.

## Behavior contract (gate 3)

The policy resolution with its two-basis split, the per-unit grading over the
every-unit set, the four record states and the ranked unit verdict, the sampled
activity share against its floor, the per-population roll-up with its cleared
share, the absent and untouched population detectors, the failure position and
the single lot verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_acceptance_general.py against
scripts/e2008_blocking_diode_acceptance_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_acceptance_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
