---
name: q7002-specimen-preparation
description: "Prepare the test items for a thermal-vacuum outgassing screening under ECSS-Q-ST-70-02C: size one specimen inside the working mass window, work out how many cut pieces of the stock reach it from geometry and density, check a piece fits the sample holder in some orientation, count the replicates and the carrier blanks a liquid or paste needs, net the carrier out of the balance reading, and grade the conditioning duration, temperature and humidity actually achieved. Use when cutting specimens, writing a test request or reviewing a laboratory preparation record. Trigger: ecss, q-st-70-02c, outgassing-specimen-mass-window, outgassing-specimen-replicate-count, outgassing-carrier-blank, outgassing-specimen-conditioning, outgassing-sample-holder-fit."
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
  tags: [ecss, q-st-70-02c-outgassing-screening-test, q-st-70-02c, q7002-specimen-preparation, outgassing-specimen-mass-window, outgassing-specimen-replicate-count, outgassing-carrier-blank, outgassing-specimen-conditioning, outgassing-sample-holder-fit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Specimen Preparation (space-systems/ecss/q7002-specimen-preparation)

Use when the task is the test-item clause of ECSS-Q-ST-70-02C: how many
specimens the screening needs, what each one weighs, how bulk stock is cut so
it sits in the sample holder, and the conditioning the specimens see before
they go into the chamber.

## Domain quick reference

- The specimen mass is bounded at both ends for different reasons. Too little
  material and the mass loss being measured sits down among the balance's own
  resolution; too much and it does not fit the holder or outgas evenly. A
  working window, not a single figure, is what the preparation aims at.
- The screening is read across replicates. A single specimen cannot separate a
  material property from a preparation accident, so a replicate minimum is part
  of the test item, not of the statistics done afterwards.
- A material that is not homogeneous needs more replicates, not a bigger
  specimen. A filled or laminated stock varies from piece to piece, and extra
  specimens sample that variation while one large specimen simply averages it
  away and hides it.
- Cutting is a fitting problem in three dimensions. A piece may be turned, so a
  piece fits when its sorted dimensions are each within the holder's sorted
  dimensions; comparing axis by axis rejects strips that would go in sideways.
- Liquids, pastes, greases and freshly mixed two-part systems cannot stand up
  in the holder. They are applied to a carrier, and the carrier outgasses too,
  so a blank carrier goes through the same run for every specimen.
- The balance sees the carrier and the material together. The figure the
  screening is computed on is the net material mass, and a preparation that
  loses track of the carrier mass silently divides the loss by the wrong
  denominator.
- Conditioning is part of the specimen, not part of the test. The water a
  material has taken up from the room is exactly what the recovered mass loss
  argument later depends on, so a short or off-band conditioning invalidates
  the result before the chamber is pumped down.

## Workflow

1. Take the target specimen mass from the working window, defaulting to the
   nominal figure, and raise a finding when a requested target sits outside it
   at either end.
2. Compute the mass of one cut piece from its dimensions and the stock density,
   then the number of pieces needed to reach the target, rounding up with a
   tolerance so an exact multiple does not gain a spurious extra piece.
3. Check the piece against the sample holder on sorted dimensions, and report a
   piece that cannot be made to fit in any orientation.
4. Count the specimens: the replicate minimum, plus extra replicates where the
   material is not homogeneous, and never fewer than the minimum even when
   fewer were requested.
5. Where the form needs a carrier, plan one blank per specimen and require a
   declared carrier mass; net the carrier out to get the material mass the
   screening is computed on.
6. Grade the conditioning actually achieved against the specified duration,
   temperature and humidity windows, treating longer conditioning as acceptable
   and shorter as a finding.
7. Return the plan — specimens, blanks, pieces per specimen, target, gross and
   net mass, total material required — with every finding, and mark it ready
   only when there are none.

## Pitfalls

- Making one big specimen instead of the replicates. The screening reads across
  specimens; a single large one cannot tell a material property from a cutting
  or handling accident, and it is the accidents that produce the surprising
  results.
- Comparing the cut piece to the holder axis by axis. A long thin strip that
  would drop straight in when turned gets rejected, and the stock is cut
  smaller than it needed to be for no gain.
- Forgetting the carrier blank on a paste or a liquid. The carrier's own mass
  loss is then attributed to the material, and a clean material is refused on
  the strength of the tape it was spread on.
- Computing the loss against the gross balance reading. Dividing by the carrier
  plus the material understates the loss by whatever fraction of the reading
  the carrier was.
- Cutting the conditioning short to make a schedule. The absorbed water is what
  the recovered mass loss argument rests on later, so a short conditioning
  quietly removes the only route a high total-loss material had.
- Averaging an inhomogeneous stock into one specimen. The variation is the
  result; extra replicates expose it, and a single averaged specimen reports a
  number no piece of the material actually has.

## Behavior contract (gate 3)

The mass window, piece geometry and holder fit, piece count, replicate and
carrier-blank counting, carrier netting and conditioning grading are exercised
by the gate 3 contract test:
scripts/test_q7002_specimen_preparation.py against
scripts/q7002_specimen_preparation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_specimen_preparation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
