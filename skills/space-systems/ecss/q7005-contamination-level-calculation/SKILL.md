---
name: q7005-contamination-level-calculation
description: "Compute the organic contamination level of a surface in mass per unit area from measured infrared band signals under ECSS-Q-ST-70-05C. Use when bands have been read for one or more species, a calibration exists for each, and the readings have to become a single areal figure with a cleanliness level attached. Holds every species to the band measure its own curve was built on, carries the dilution, recovery and sampled area through, reports a sub-limit species as a bounded pair instead of a point value, and categorizes the total against the supplied level bands. Trigger: ecss, q-st-70-05, contamination-level-calculation, baseline-corrected-band-signal, peak-height-versus-band-area, multi-species-contamination-sum, cleanliness-level-categorization, surface-areal-mass."
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
  tags: [ecss, q-st-70-contamination-infrared-scope, q7005-contamination-level-calculation, contamination-level-calculation, baseline-corrected-band-signal, peak-height-versus-band-area, multi-species-contamination-sum, cleanliness-level-categorization]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Organic Contamination by IR — Level Calculation (space-systems/ecss/q7005-contamination-level-calculation)

Use when the task is the arithmetic between a spectrum and a cleanliness
statement — turning measured band signals into a mass per unit area for
each species present, a defensible total, and the level band that total
falls in.

## Domain quick reference

- A band signal is a peak height above a local baseline or an integrated
  band area, and the two are not interchangeable. A calibration built on
  one and applied to the other is wrong by the band's shape factor,
  which no amount of care in the rest of the chain recovers.
- Each identified species carries its own calibration. Summing signals
  before inverting them treats different absorptivities as equal; the
  inversion happens per species and the masses are what get summed.
- The sampling chain sits between the measured deposit and the surface:
  the dilution of an extract, the fraction the sampling recovered, and
  the area sampled. Any of them left at an implied unity moves the
  answer by that whole factor.
- A species whose signal sits below its quantification limit is not
  zero and is not its limit either. The honest total is a pair — a lower
  bound that omits it and an upper bound that counts it at its limit —
  and a single number hides which side of a level band the result may
  really be on.
- A level band is an upper bound on areal mass. The result is categorized
  into the tightest band whose bound it satisfies, and a result above
  every supplied band has no level, which is a finding rather than a
  silent fall-through to the loosest one.
- A total above the top calibration standard of any contributing species
  is an extrapolated total. The level attached to it is provisional
  until that species is re-run inside its curve.

## Workflow

1. Validate the sampling chain: sampled area, dilution factor of at
   least unity, and a recovery fraction in the open-to-unity range.
2. Validate each species record: name, the band measure used, its
   calibration slope and intercept, the measure kind that calibration
   was built on, and its quantification limit.
3. Refuse any species whose reading measure differs from the measure its
   calibration was built on.
4. Invert each species signal through its own calibration to a deposit
   mass, then carry the dilution, recovery and area to an areal mass.
5. Mark a species whose signal is at or below its quantification limit
   as sub-limit and exclude it from the lower-bound total while counting
   it at its limit in the upper-bound total.
6. Sum the species into the bounded total pair and categorize both
   bounds against the supplied level bands.
7. Report the per-species masses, the bounded total, the level of each
   bound, and every finding: a measure mismatch refused, a sub-limit
   contributor, a signal past the top standard, or a total above every
   band.

## Pitfalls

- Applying a peak-height calibration to an integrated band area. The two
  differ by the band width, so the result is wrong by a factor that
  looks like a plausible contamination level.
- Adding absorbances across species and inverting once. Absorptivities
  differ between a silicone and a hydrocarbon by a large factor, so the
  single inversion attributes the whole signal to whichever species the
  slope belonged to.
- Dropping a sub-limit species from the total silently. It reads as a
  clean result when the honest statement is an interval, and the
  interval can straddle the level boundary the hardware is accepted on.
- Categorizing against the loosest band because the total exceeded them
  all. A result off the top of the scale is not the bottom level; it is
  an out-of-scale finding.
- Quoting a level for a total whose largest contributor was read above
  its top calibration standard. Saturation biases that contributor low,
  so the level is optimistic in exactly the case that matters.

## Behavior contract (gate 3)

The sampling-chain validation, band-measure matching, per-species
inversion, dilution and recovery carry-through, sub-limit bounding, total
summation and level categorization are exercised by the gate 3 contract
test: scripts/test_q7005_contamination_level_calculation.py against
scripts/q7005_contamination_level_calculation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7005_contamination_level_calculation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
