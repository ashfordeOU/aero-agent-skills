---
name: q6013-legacy-class-1-screening-table
description: "Assess a legacy screening test list for active commercial parts bought to the highest assurance class against the ECSS-Q-ST-60-13C Table 8-10 programme: confirm every required screen is declared once and in the canonical order, prove burn-in is bracketed by an electrical reading either side of it, walk the whole lot through the sequence so each screen receives what the previous one passed, reduce the bracket into a per-part parameter drift against its band, and compare the cumulative percent defective with the allowable before the lot may go on. Use when a heritage active part lot's screening list has to become a release or reject verdict. Trigger: ecss, q-st-60-13c-table-8-10, legacy-part-screening-test-list, screening-sequence-ordering, burn-in-parameter-drift-band, legacy-screening-percent-defective-allowable, whole-lot-screening-coverage."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-legacy-class-1-screening-table, legacy-part-screening-test-list, screening-sequence-ordering, burn-in-parameter-drift-band, legacy-screening-percent-defective-allowable, whole-lot-screening-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Legacy Screening Test List, Highest Assurance Class (space-systems/ecss/q6013-legacy-class-1-screening-table)

Use when the task is the Table 8-10 screening test list of ECSS-Q-ST-60-13C:
a delivered lot of active commercial parts with legacy standing is being
screened to the highest assurance class, and the question is whether the
declared sequence is the right sequence and what the lot looks like once it
has been through it.

## Domain quick reference

- Screening is not sampling. Every screen is applied to every part that
  reached it, so the quantity entering the sequence is the lot and the
  quantity leaving it is what can be delivered. A screen with a sample size
  is an acceptance test that has been put in the wrong list.
- Order carries meaning. A stress applied after the measurement that was
  supposed to catch its damage proves nothing, and a reading taken before
  the stress that moves it is not a post-stress reading. Membership of the
  list and position in the list are two separate requirements.
- Burn-in is only a screen when it is bracketed. A pre-reading and a
  post-reading of the same parameters either side of it are what turn a soak
  into a measurement; without the pair, burn-in removes only the parts that
  stopped working outright.
- The bracket is reduced per part, not per lot. Each parameter's change
  between the two readings, as a share of the pre-reading, is compared with
  a declared drift band. A part that passed every count-based screen and
  drifted outside a band is removed all the same.
- A removed part is a removal, not a verdict on the lot. The lot verdict is
  the cumulative percent defective against the allowable -- and over the
  allowable the lot is rejected as a whole, even though the survivors are
  individually good, because the lot has shown itself to be the wrong lot.
- Drift is a magnitude. A parameter that fell by more than its band is as
  much a removal as one that rose, and reading the band as an upper bound
  alone lets half the drifted population through.

## Workflow

1. Validate the delivered quantity; it is the number entering the first
   screen, and no screen may reject more parts than reached it.
2. Check coverage: every required screen present and declared once, with any
   additional screen reported as an addition rather than counted towards
   coverage.
3. Check the order of the required screens against the canonical sequence,
   allowing an extra screen to be inserted anywhere, and prove the burn-in
   bracket explicitly in both directions.
4. Walk the sequence cumulatively: each screen receives what the previous
   one passed, removes its rejects and hands the remainder on.
5. Reduce the burn-in bracket into a per-part drift for every banded
   parameter, refusing a part whose pre-reading is zero rather than
   reporting an unbounded drift, and remove every part outside a band.
6. Total the count-based rejects and the drift removals, refuse a drift
   count larger than the population that survived the counted screens, and
   express the total as a percent defective of the original lot.
7. Release the lot for acceptance testing only when coverage is complete,
   the order holds and the percent defective is inside the allowable;
   report a lot that used the allowable in full as an advisory.

## Pitfalls

- Treating a screen as a sample. Screening covers the whole population, and
  a percentage applied here silently delivers unscreened parts.
- Checking membership of the list and forgetting position. A sequence that
  holds every required screen in the wrong order is a coverage pass and a
  screening failure.
- Accepting burn-in without both readings. A single post-reading gives no
  drift, and the parts that shifted but still function stay in the lot.
- Reading the drift band as an upper bound. Drift is a magnitude, so a
  parameter that fell below its band has to be removed too.
- Judging the lot on the survivors. The percent defective is taken against
  the original quantity, and dividing by what survived makes every lot look
  better the worse it performed.
- Widening the allowable to release a lot that just crossed it. An equality
  at the allowable is absorbed by the tolerance inside the comparison; the
  declared allowable stays as specified.

## Behavior contract (gate 3)

The lot validation, sequence coverage, canonical ordering and burn-in
bracket, the cumulative walk through the screens, the per-part drift
reduction, the percent-defective calculation and the overall
release-or-reject disposition are exercised by the gate 3 contract test:
scripts/test_q6013_legacy_class_1_screening_table.py against
scripts/q6013_legacy_class_1_screening_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_legacy_class_1_screening_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
