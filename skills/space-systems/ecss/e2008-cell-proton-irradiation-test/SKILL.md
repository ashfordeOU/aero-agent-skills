---
name: e2008-cell-proton-irradiation-test
description: "Use when a bare-cell proton irradiation run is planned or reviewed. Monitor the performance a bare solar cell loses to energetic proton fluence under ECSS-E-ST-20-08C clause 7.5.14: weight every energy's delivered fluence by its relative damage coefficient and its beam path factor into one reference-energy equivalent fluence, confirm the coefficient table is normalised, check each energy's projected range reaches past the junction instead of stopping ahead of it, hold the beam near normal incidence, track the maximum power lost after each exposure and refuse a loss that shrinks, then compare the end loss with its allowance. Trigger: ecss, e-st-20-08c-clause-7-5-14, bare-cell-proton-irradiation-test, ten-mev-equivalent-proton-fluence, proton-relative-damage-coefficient, proton-range-junction-depth-coverage, bare-cell-proton-power-loss-track."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-cell-proton-irradiation-test, bare-cell-proton-irradiation-test, ten-mev-equivalent-proton-fluence, proton-relative-damage-coefficient, proton-range-junction-depth-coverage, bare-cell-proton-power-loss-track]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Proton Irradiation Test (space-systems/ecss/e2008-cell-proton-irradiation-test)

Use when the task is the bare-cell proton irradiation test of ECSS-E-ST-20-08C
clause 7.5.14 -- following what a cell's maximum power does as proton exposures
accumulate, and turning a run made up of several proton energies into one
equivalent fluence the loss can honestly be plotted against.

## Domain quick reference

- Proton damage is strongly energy dependent, which is what separates this test
  from its electron counterpart. A proton of a few megaelectronvolts displaces
  far more lattice atoms per particle than one of tens, so fluences at
  different energies cannot be added until each is weighted.
- The weighting is a relative damage coefficient referred to one energy, and
  the coefficient at that reference energy is unity by construction. A table
  that gives it any other value is scaled to a different reference, and summing
  it with this one silently mixes two scales.
- Range is the second energy effect, and it works the opposite way. A low
  energy proton deposits everything it has, but if its projected range stops
  ahead of the junction it deposits it in material the cell does not collect
  current from, and the fluence buys nothing where it matters.
- Incidence is not cosmetic. A beam arriving off the cell normal crosses more
  active material per incident proton, so the damage per unit delivered fluence
  rises with the tilt; the path factor belongs in the equivalent fluence, and a
  large tilt belongs in the findings.
- Displacement damage does not anneal back during a run. A tracked loss that
  shrinks between exposures, or a cell reading above its own starting power, is
  a contact, a probe or a bench temperature, and it makes the loss track
  unusable rather than encouraging.

## Workflow

1. Validate every exposure: positive energy, positive delivered fluence, a
   relative damage coefficient, the projected range at that energy, the beam
   incidence, and the maximum power measured after it.
2. Check the coefficient table is normalised by testing the exposure that sits
   at the reference energy against unity.
3. Compare each energy's projected range with the junction depth, treating a
   range exactly at the junction as reaching it, and raise a finding for any
   energy that stops short.
4. Compare each exposure's incidence with the allowance and convert the tilt
   into a path length factor, treating an angle exactly on the allowance as
   conformant.
5. Weight each delivered fluence by its damage coefficient and path factor, and
   accumulate the reference-energy equivalent fluence across the run so every
   power measurement carries the equivalent fluence it belongs to.
6. Turn each post-exposure power reading into a loss fraction against the
   unirradiated power, and check the track only rises: a dip beyond the noise
   allowance, or a negative loss, is a finding.
7. Compare the accumulated equivalent fluence with what the mission asks for
   and the end loss with its allowance, then report the per-exposure
   contributions, the track, every finding and the verdict.

## Pitfalls

- Adding fluences from different energies. The sum has no physical meaning
  until each term is weighted, and the unweighted total is always the
  optimistic one when the run is low-energy heavy.
- Taking a damage coefficient table from one source and a reference energy from
  another. The two only combine when the table's own reference reads unity, and
  that check costs one comparison.
- Treating a low energy exposure as the most damaging without checking its
  range. Below the energy that reaches the junction the damage per proton
  climbs while the damage that matters falls to nothing.
- Correcting a tilted beam only in the fluence and not reporting it. The path
  factor recovers the average, but a large tilt also changes which depth the
  damage lands at, so the tilt itself is a finding.
- Reading a recovered loss as genuine annealing. Room-temperature annealing
  during a short run is far smaller than the dips a warm probe produces, so the
  measurement is suspect long before the cell is.
- Comparing the end loss with the allowance and stopping there. A run that
  never reached the mission equivalent fluence passes that comparison while
  leaving the mission's real exposure untested.

## Behavior contract (gate 3)

The exposure validation, damage coefficient normalisation check, projected
range against junction depth, incidence allowance and path length factor,
equivalent fluence weighting and accumulation, power loss track monotonicity,
mission fluence coverage and the end-loss comparison are exercised by the gate
3 contract test: scripts/test_e2008_cell_proton_irradiation_test.py against
scripts/e2008_cell_proton_irradiation_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_cell_proton_irradiation_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
