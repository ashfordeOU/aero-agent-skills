---
name: q7005-solvent-rinse-extraction
description: "Compute what a solvent rinse or wipe extraction actually recovers from a contaminated surface. Use when the ECSS-Q-ST-70-05C indirect method has to produce an areal contamination figure rather than a residue weight: build the cumulative recovery from the per-pass removal fraction over the pass count, size the rinse volume against the area it has to wet, take the concentration factor from the volume reduction, back out the surface level from the residue mass and that recovery, and confirm the residue reaching the cell clears the quantitation limit. Trigger: ecss, q-st-70-05-ir-contamination-scope, solvent-rinse-extraction-recovery, per-pass-removal-fraction, sampled-area-rinse-volume-ratio, areal-contamination-back-calculation, extraction-residue-quantitation-limit."
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
  tags: [ecss, q-st-70-05-ir-contamination-scope, q7005-solvent-rinse-extraction, solvent-rinse-extraction-recovery, per-pass-removal-fraction, sampled-area-rinse-volume-ratio, areal-contamination-back-calculation, extraction-residue-quantitation-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS IR Contamination Measurement — Solvent Rinse Extraction (space-systems/ecss/q7005-solvent-rinse-extraction)

Use when the task is the extraction step of the indirect method of
ECSS-Q-ST-70-05C — taking organic contamination off a surface into a
solvent by rinsing or wiping, and turning the residue that ends up in the
cell back into a level on the hardware.

## Domain quick reference

- A pass removes a fraction of what is there, not all of it. The next
  pass removes the same fraction of what is left, so the unremoved part
  shrinks geometrically and the cumulative recovery is one minus it. The
  first pass buys the most; the fourth buys very little, and the pass
  count needed for a target recovery falls out of the same expression.
- Complete recovery is not reachable in finitely many passes. A procedure
  that targets it is asking for an unbounded number of rinses, which is
  why the target is a declared fraction below one and the shortfall is
  corrected for rather than wished away.
- The rinse volume is sized against the area, not against the bottle. Too
  little solvent saturates before it has covered the surface; too much
  spreads the residue thinner than the concentration step can bring back.
  Both ends of that band are real and the check reports which one bit.
- Concentration has a ceiling of its own. Reducing the extract brings the
  contaminant up, and it brings the solvent's own residue up by exactly
  the same factor, so past a point the blank grows with the sample and
  nothing is gained.
- The areal level is the residue mass divided by the sampled area and by
  the cumulative recovery. Dropping the recovery correction is not a
  conservative simplification: it reports a surface cleaner than it is,
  which is the wrong direction for a cleanliness verification.
- A residue below the cell's quantitation limit is a detection, not a
  measurement. It can be reported as an upper bound; it cannot be
  reported as a number with a tolerance.
- Area and recovery are the two levers on sensitivity. Sampling more area
  puts more mass in the same extract; adding passes recovers more of what
  is on the area already sampled.

## Workflow

1. Validate the extraction policy: a volume band with the ceiling above
   the floor, an area floor, a recovery floor inside the unit interval,
   and a concentration ceiling of at least one.
2. Build the cumulative recovery from the per-pass fraction and the pass
   count, and compare it with the policy floor rather than accepting
   whatever the procedure happened to specify.
3. Check the rinse volume per unit area against both ends of the band and
   keep the reason when it fails, since the two failures call for
   opposite corrections.
4. Take the concentration factor from the initial and final volumes,
   refusing a final volume above the initial one.
5. Back out the areal level from the residue mass, the sampled area and
   the cumulative recovery, and keep the uncorrected level alongside it so
   the size of the correction is visible.
6. Confirm the residue reaching the cell clears the quantitation limit,
   and close with the findings and the reporting duties.

## Pitfalls

- Reporting the residue mass over the sampled area as the surface level.
  That is the uncorrected number, and at a recovery of one half it is
  wrong by a factor of two in the direction that passes a dirty article.
- Specifying a single rinse because the solvent came away visibly clean.
  Visible cleanliness is not a recovery fraction, and one pass at a
  typical removal fraction leaves a large minority of the load behind.
- Targeting a hundred per cent recovery. It is unreachable in finitely
  many passes, so the procedure either never terminates or quietly
  redefines the target at the bench.
- Concentrating harder to get above the quantitation limit. The solvent's
  own residue concentrates at the same rate, so past the ceiling the
  extra signal is blank, not sample.
- Shrinking the sampled area to save solvent. The residue mass falls with
  the area while the cell limit does not, so the measurement loses the
  ability to see the requirement it was run for.
- Comparing a recovery, a volume ratio or a residue against its bound with
  a bare strict inequality. Values built from repeated multiplication and
  division land a few units in the last place either side of a bound they
  should meet exactly; each comparison absorbs that while the bound stays
  as specified.

## Behavior contract (gate 3)

The policy validation, cumulative recovery and the pass count that reaches
a target, the rinse volume band check, the concentration factor, the
recovery-corrected areal level and its forward inverse, and the
quantitation-limit check are exercised by the gate 3 contract test:
scripts/test_q7005_solvent_rinse_extraction.py against
scripts/q7005_solvent_rinse_extraction_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7005_solvent_rinse_extraction.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
