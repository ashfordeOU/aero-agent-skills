---
name: e2008-diode-acceptance-testing-general
description: "Evaluate a protection diode acceptance record against clause 9.4.1 of ECSS-E-ST-20-08C, where two diode populations owe acceptance at once: the parts being delivered and the parts the qualification campaign consumes. Split the per-diode activities from the lot-sampled ones, score each sampled activity on the share of its population actually drawn, hold missing records, unrun work and recorded failures apart, flag a population carrying no acceptance work at all, and roll the lot into one verdict with ranked findings. Use when a diode acceptance matrix, lot traveller set or diode sampling plan is under review. Trigger: ecss, e-st-20-08c, diode-acceptance-testing-general, diode-delivery-population-acceptance, diode-qualification-population-acceptance, diode-sampled-activity-share, diode-acceptance-record-state, diode-lot-acceptance-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-diode-acceptance-testing-general, diode-acceptance-testing-general, diode-delivery-population-acceptance, diode-qualification-population-acceptance, diode-sampled-activity-share, diode-acceptance-record-state, diode-lot-acceptance-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Diodes — Acceptance Testing, General (space-systems/ecss/e2008-diode-acceptance-testing-general)

Use when the task is clause 9.4.1 of ECSS-E-ST-20-08C: acceptance testing is
applied to the diodes being delivered and to the diodes used as qualification
hardware. This leaf grades a diode lot record on whether both populations carry
the acceptance activity set, on the basis each activity is applied on.

## Domain quick reference

- The qualification population is the half that gets dropped. A diode mounted
  into a qualification coupon is not being shipped, so acceptance reads like an
  obligation somebody else carries. It is the other way round: a qualification
  result only means something if the diode it was produced on was a sound diode
  to begin with.
- An unaccepted diode that opens during a qualification thermal run has settled
  nothing. The result cannot separate a mounting process that does not hold from
  a part that was already degraded, and the campaign is repeated at full cost.
- Diodes split their acceptance work by basis. The visual inspection, the
  forward voltage measurement and the reverse leakage measurement are carried by
  every diode; the thermal endurance, the mechanical shock and the terminal
  strength work are drawn on a sample. The basis decides what a blank field in
  the traveller actually means.
- A sampled activity is graded on the share of its population reached, never on
  one part. Grading it part by part reports almost every diode as missing a
  record it never owed; grading a per-diode activity as a sample closes a lot of
  thousands on a handful of measurements nobody agreed to substitute.
- A failure found in a drawn sample speaks for the population it was drawn from,
  not for the one part it landed on, so it is carried as a population finding.
- Absence, non-execution and failure are three separate states. No record at all
  is the worst of them, because it cannot be dispositioned: nobody can say
  whether the work was skipped, lost or never scheduled. An activity marked as
  not yet run is a schedule item. A recorded failure is known and actionable.
- A population with every record blank is a decision, not an accident. One thin
  traveller is paperwork; a whole population with nothing in it is reported as
  its own finding rather than as a long run of incomplete parts.
- Carrying a dispositioned failure is a project position read from policy. Both
  answers are defensible, and assuming either one silently accepts or rejects
  hardware on the leaf's opinion instead of the project's.

## Workflow

1. Validate each diode entry: a unique identifier, one of the two populations,
   and acceptance records naming only activities this clause owes. Refuse an
   activity outside the acceptance set rather than counting it as coverage.
2. Grade each diode against the per-diode activities only: what carries no
   record, what is marked not run, what failed, what passed. A diode that was
   never drawn into a sample is not missing anything.
3. Rank the part verdict -- absent record first, then unrun, then failed -- so
   the lot report names the root cause ahead of its consequence.
4. Grade each sampled activity across its population: how many parts were drawn,
   what share of the population that is against the declared minimum, and how
   many of the drawn parts failed.
5. Summarise each population: how many diodes it holds, how many are clear, the
   cleared share against the policy minimum, and the sampled results.
6. Detect a population present in the lot whose parts carry no acceptance work
   at all, and a population absent from the lot entirely; report each as its own
   finding.
7. Report the lot: diodes grouped by verdict, both population summaries, the
   weakest part and every finding in rank order.

## Pitfalls

- Running the acceptance matrix over the delivery lot alone. The qualification
  diodes sit inside the clause, and leaving them out is the single defect this
  leaf exists to catch.
- Grading a sampled activity part by part. Almost every diode then reads as
  undocumented, and the parts that genuinely carry no record disappear into the
  noise.
- Grading a per-diode activity as a sample. A lot of thousands closes on a
  handful of leakage measurements that were never agreed as a substitute.
- Reading a blank acceptance record as a pass. A diode with no record has not
  been shown sound; it has been shown undocumented.
- Collapsing absence into failure. The two are dispositioned by different people
  through different paperwork, so the verdict keeps them apart.
- Folding a sampled failure into the verdict of the one part it was found on.
  The sample was drawn to speak for the population, so the finding belongs there.
- Assuming a failed diode closes the lot. Whether a dispositioned failure is
  carried is a project position read from policy.
- Judging a sampled share or a cleared share that lands exactly on its declared
  minimum by bare arithmetic. Both are quotients of two part counts, so a lot
  drawn to exactly the declared share can evaluate a unit in the last place
  below it; the comparison absorbs that while the minimum stays as declared.

## Behavior contract (gate 3)

The diode record validation, the per-diode and sampled activity split, the
sampled share against the declared minimum, the four record states, the ranked
part verdict, the per-population summaries, the wholly untested and absent
population detectors, the failure policy and the rolled-up lot verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_diode_acceptance_testing_general.py against
scripts/e2008_diode_acceptance_testing_general_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_diode_acceptance_testing_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
