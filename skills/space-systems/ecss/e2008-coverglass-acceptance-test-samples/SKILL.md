---
name: e2008-coverglass-acceptance-test-samples
description: "Use when a coverglass lot sampling plan, draw record or shipment acceptance traveller has to be reviewed. Evaluate whether the coverglass acceptance sample drawn from each shipment lot under clause 8.5.1 of ECSS-E-ST-20-08C is both large enough and genuinely random: grade the draw against the declared floor of forty pieces, refuse a sample pooled across lots or carrying more pieces than the lot held, measure each stratum's share of the draw against that stratum's share of the lot, catch a convenience draw taken off one carrier, handle a lot smaller than the floor, and return one shipment verdict with ranked findings. Trigger: ecss, e-st-20-08c, coverglass-acceptance-sample-draw, coverglass-lot-sample-floor, coverglass-random-draw-evidence, coverglass-stratum-proportional-spread, coverglass-convenience-sample-draw, coverglass-shipment-lot-sampling-verdict."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c, e2008-coverglass-acceptance-test-samples, coverglass-acceptance-sample-draw, coverglass-lot-sample-floor, coverglass-random-draw-evidence, coverglass-stratum-proportional-spread, coverglass-convenience-sample-draw, coverglass-shipment-lot-sampling-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses — Acceptance Test Samples (space-systems/ecss/e2008-coverglass-acceptance-test-samples)

Use when the task is clause 8.5.1 of ECSS-E-ST-20-08C: the coverglasses that
acceptance testing is run on are drawn at random from each shipment lot, and
at least forty pieces are drawn. This leaf grades a draw record on both
conditions the clause puts on it, lot by lot.

## Domain quick reference

- The clause puts two conditions on the sample, not one. Size is the one that
  gets recorded, because a count is easy to write down; the draw method is the
  one that gets lost, and a lot arrives with forty pieces that all came off
  the end of one carrier with a traveller that reads as compliant.
- A sample that is large but not random is the defect worth catching. Forty
  pieces off a single tray answer one question about one tray. They say
  nothing about the lot the shipment is being accepted on, and speaking for
  the lot is the entire reason the draw exists.
- Coverglass lots carry real internal structure -- carriers, trays, boat
  positions, coating runs -- and the structure is where the variation lives. A
  coating run that drifted shows up in one stratum before it shows up
  anywhere, so a draw that skips a stratum is blind to exactly the failure a
  lot sample is there to find.
- Spread is graded against the lot's own composition, never against an even
  split. A lot built from an eighty-piece carrier and a twenty-piece carrier
  should return four pieces from the first for every one from the second;
  grading it evenly reports a correct draw as clustered and an actually
  clustered draw as correct.
- Each shipment lot stands alone. A sample pooled from two lots is a sample of
  neither, so pooling is refused at validation rather than absorbed into a
  score where it reads as a slightly imperfect spread.
- A lot smaller than the floor is a real case, not a malformed one. No draw
  can reach forty pieces, so the lot closes only by being drawn whole, and
  whether that substitution is accepted is a project position.
- Absence and thinness are different states. A lot with no draw at all has not
  been sampled; a lot with a thin draw has been sampled badly, and the two
  reach different people through different paperwork.

## Workflow

1. Validate each lot: an identifier, declared strata with their sizes, and a
   draw naming only declared strata. Refuse a pooled piece, a repeated piece
   and a draw carrying more pieces than the lot ever held.
2. Grade the draw size against the floor. Where the lot itself is smaller than
   the floor, fall back to the lot size and record that the lot can only close
   on an exhaustive draw.
3. Compute each stratum's expected share from its size against the lot, and
   its observed share from the draw, and take the largest deviation between
   the two as the spread measure.
4. Count the strata the draw reached against the strata the lot declared, and
   name any stratum that contributed nothing.
5. Rank the lot verdict -- no draw first, then short, then clustered -- so the
   report names the root cause before the consequence.
6. Roll the lots up: lots grouped by verdict, the weakest lot, the shipment
   draw fraction and every finding in rank order.

## Pitfalls

- Grading the sample on its count alone. Forty pieces is half the clause, and
  it is the half that a convenience draw satisfies effortlessly.
- Grading spread against an even split. An unevenly built lot then reports a
  correctly proportional draw as clustered, and the finding is dismissed the
  first time somebody checks it by hand.
- Absorbing a pooled draw into a score. Two lots sampled as one produce a
  number for a population that does not exist, and it reads as a near miss
  rather than as a sample of neither lot.
- Treating a lot smaller than the floor as malformed input. Short lots ship,
  and refusing them moves the decision out of the report and into whoever is
  holding the traveller.
- Reading an exhaustive draw on a short lot as automatic compliance. It is a
  substitution, and whether a project carries it is a position to be read
  rather than assumed.
- Collapsing an undrawn lot into a thin one. The first has no evidence at all;
  the second has evidence of the wrong size, and the dispositions differ.
- Judging a stratum deviation or a coverage fraction that lands exactly on its
  declared limit by bare arithmetic. Both are quotients of piece counts, so a
  draw allocated exactly in proportion can evaluate a unit in the last place
  either side of its own target; the comparison absorbs that while the
  declared limit stays as declared.

## Behavior contract (gate 3)

The lot record validation, the refusals of pooled, repeated and over-sized
draws, the sample floor, the short-lot fallback and its policy position, the
proportional spread against the lot's own strata, the missed stratum, the
tolerance boundary a float lands on, the ranked lot verdict and the rolled-up
shipment verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_acceptance_test_samples.py against
scripts/e2008_coverglass_acceptance_test_samples_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_acceptance_test_samples.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
