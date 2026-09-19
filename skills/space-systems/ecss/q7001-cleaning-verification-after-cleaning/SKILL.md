---
name: q7001-cleaning-verification-after-cleaning
description: "Verify that a cleaning operation actually reached the level it was run for, from the measurements taken afterwards. Use when particle counts per size band, a residue rinse sample and its witness blank come back from a cleaned surface and someone has to say accept, re-clean or re-sample. Converts counts over the sampled area into an obscuration figure and a ladder position, subtracts the blank and refuses a run whose blank exceeded the sample, treats a net mass under the balance floor as a bound rather than a value, tests whether the sampled fraction and site count represent the surface, and returns the verdict with the finding behind it. Trigger: ecss, q-st-70-01, post-cleaning-verification, particle-count-size-band, nvr-blank-subtraction, cleanliness-sampling-adequacy, below-detection-nvr-bound, re-clean-disposition."
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
  tags: [ecss, q-st-70-01-cleanliness-contamination-control, q7001-cleaning-verification-after-cleaning, post-cleaning-verification, particle-count-size-band, nvr-blank-subtraction, cleanliness-sampling-adequacy, below-detection-nvr-bound, re-clean-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Contamination Control — Verification After Cleaning (space-systems/ecss/q7001-cleaning-verification-after-cleaning)

Use when the task is the post-cleaning verification step of ECSS-Q-ST-70-01 —
deciding from the measurements whether a cleaned surface may be accepted, has
to go back through the process, or was simply not sampled well enough to say.
This leaf grades one measurement set; the verification-records leaf decides
whether the resulting records close out the hardware.

## Domain quick reference

- Two independent results are needed, because cleaning removes two different
  things. The particle counts per size band say what is sitting on the surface;
  the non-volatile-residue sample says what is smeared across it. Passing one
  says nothing about the other.
- The particulate ladder is set by the largest particle found, not by the
  total count. One 400-micrometre fibre puts the surface on a lower rung than
  ten thousand 5-micrometre particles, because the level bounds size. The
  obscuration figure is reported alongside as the area actually covered.
- A residue figure only exists after the witness blank is subtracted. The blank
  carries the solvent, the beaker and the handling, and a blank that comes out
  heavier than the sample is an invalid run — not an unusually clean surface.
- Under the balance resolution there is no value, only a bound. Reporting a net
  mass smaller than the instrument can resolve as if it were a measurement is
  how a surface acquires a cleanliness it was never shown to have.
- Sampling adequacy is a precondition, not a caveat. A sample covering a
  fraction of a percent of the surface, or taken at a single site, describes
  that patch; on a non-uniform surface it neither passes nor fails the item,
  so the verdict is to sample again before grading anything.
- A result landing exactly on a level bound belongs on that level. The
  comparison carries a named tolerance, because a loading computed by division
  can miss an exact bound by the last bit.

## Workflow

1. Validate the counts: known size bands, non-negative integer counts, and a
   positive sampled area.
2. Compute the obscuration from the projected area of the counts at their band
   upper bounds, divided by the sampled area.
3. Place the surface on the particulate ladder by the largest populated band,
   treating an all-zero count set as the cleanest rung rather than as no result.
4. Subtract the blank from the residue sample, refusing a negative net; divide
   by the sampled area for the loading, and place that on the residue ladder.
5. Flag the loading as a bound when the net mass is at or under the balance
   resolution.
6. Test the sampled fraction against the minimum and the site count against the
   minimum number of sites; either shortfall makes the verdict re-sample before
   the levels are graded at all.
7. Grade both levels against their requirements and return accept, re-clean or
   re-sample with every finding that applied.

## Pitfalls

- Grading the particulate result on total count. The ladder bounds particle
  size; a high count of fine particles and a single large fibre are different
  failures and only one of them moves the level.
- Reporting a residue result without its blank. The blank is most of the mass
  on a well-cleaned part, so an unsubtracted figure fails a surface that was
  clean and hides the handling that was not.
- Turning a blank heavier than the sample into a zero. That combination means
  the run went wrong; zeroing it manufactures the cleanest possible result out
  of the least trustworthy data.
- Quoting a sub-resolution net mass as a value. It is an upper bound, and an
  allocation built on it inherits a precision the balance never had.
- Accepting a result from one wipe on a large panel. The sample has to be a
  real fraction of the surface and taken at more than one site, or the verdict
  is about the patch.
- Using a strict comparison for a loading that should sit exactly on a level
  bound. The placement carries a named tolerance instead, so the same sample
  does not change level between one machine and another.

## Behavior contract (gate 3)

The count validation, obscuration computation, ladder placement, blank
subtraction, balance-floor bounding, sampling adequacy and the accept /
re-clean / re-sample verdict are exercised by the gate 3 contract test:
scripts/test_q7001_cleaning_verification_after_cleaning.py against
scripts/q7001_cleaning_verification_after_cleaning_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleaning_verification_after_cleaning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
