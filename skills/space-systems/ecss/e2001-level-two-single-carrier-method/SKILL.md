---
name: e2001-level-two-single-carrier-method
description: "Use when compute the single-carrier multipactor-threshold of a susceptible gap by three-dimensional field solution and electron-tracking under ECSS-E-ST-20-01C clause 5.3.2.3.3: rescale the field-model amplitude to a trial carrier-power, seed electrons across the radio-frequency launch-phase, integrate every trajectory to its wall-impact, apply the secondary-electron-yield curve at each impact, and walk the amplitude upward until the tracked population first sustains itself - the lower edge of the susceptibility-band, since a two-point bracket misses a band that closes again above it. Convert that threshold-field into a threshold-power, form the multipactor-margin, and grade seed-count and field-mesh convergence separately. Trigger: ecss, e-st-20-electrical-scope, electron-tracking, single-carrier-threshold, susceptibility-band-edge, secondary-electron-yield, threshold-gap-voltage, field-mesh-convergence."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-level-two-single-carrier-method, electron-tracking, single-carrier-threshold, susceptibility-band-edge, threshold-gap-voltage, field-mesh-convergence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Second-Level Single-Carrier Tracking (space-systems/ecss/e2001-level-two-single-carrier-method)

Use when the task is the detailed single-carrier multipactor-threshold
computation of ECSS-E-ST-20-01C clause 5.3.2.3.3 — a three-dimensional field
solution rescaled with carrier-power, electron trajectories integrated over
the radio-frequency cycle, a secondary-electron-yield curve applied at each
wall-impact, and the threshold taken where the tracked population stops
decaying.

## Domain quick reference

- The three-dimensional field solution is computed once and normalised to a
  reference carrier-power. Field amplitude scales as the square root of
  power, so every trial power reuses the same solution instead of re-solving
  the geometry; power at the threshold comes back as the reference power
  times the squared amplitude ratio.
- Electrons are seeded over the launch-phase of one radio-frequency cycle
  with a small initial energy. Each trajectory is integrated under the
  time-varying field until it reaches the opposite wall, returns to the wall
  it left, or runs out of tracked cycles. An electron still in flight when
  the tracking window closes contributed no secondaries and must be counted
  as a loss, not silently dropped from the average.
- At each impact the secondary-electron-yield curve converts impact energy
  into secondaries. The mean secondaries per seeded electron over one tracked
  generation is the growth indicator: below unity the population decays,
  above unity it sustains and grows.
- The single-carrier threshold is the lower edge of the susceptibility-band,
  not simply "the field where growth appears". The band is bounded on both
  sides — below it electrons arrive too slowly to multiply, above it they
  arrive beyond the second cross-over energy and the yield falls back under
  unity — so a plain two-point bracket over the whole amplitude range can
  return no sign change at all, or bracket the wrong edge. Walk upward from
  an amplitude that demonstrably decays, stop at the first amplitude that
  sustains, then bisect that interval.
- Convergence is a separate grade from the number. A threshold that still
  moves when the seed-count or the field mesh is refined is not a result yet,
  and an unrecorded convergence study is a finding in its own right.

## Workflow

1. Take the three-dimensional field amplitude at the susceptible gap together
   with the power it was normalised to, and the yield curve selected for the
   electrode material in its flight surface condition.
2. Seed a deterministic set of launch-phases across one cycle; too few phases
   under-samples the resonant window and moves the threshold.
3. For a trial amplitude, integrate every seeded trajectory to its impact,
   read the impact energy, and evaluate the yield curve there.
4. Average the secondaries per seeded electron. Below unity the trial
   amplitude sits outside the band; at or above unity it sits inside.
5. Walk the amplitude upward on a geometric ladder from a decaying start
   until the first sustaining rung appears, then bisect between the last
   decaying rung and it to the required relative tolerance.
6. Convert the threshold amplitude to a gap voltage and, through the squared
   amplitude ratio, to a threshold power; form the multipactor-margin in
   decibel against the operating carrier-power.
7. Grade convergence — seed-count, tracked cycles, field-mesh sensitivity,
   threshold sensitivity to seed-count — and report the margin and the
   convergence findings together. The gap is not cleared while either is open.

## Pitfalls

- Bracketing the threshold between one very low and one very high amplitude.
  The susceptibility-band closes again at high amplitude, so that bracket can
  report no growth at all, or converge on the upper edge and overstate the
  threshold by an order of magnitude.
- Averaging secondaries only over the electrons that happened to impact. The
  ones still in flight are real losses; excluding them inflates the growth
  indicator and lowers the reported threshold.
- Tracking for too few cycles. A trajectory that needs more than one cycle to
  cross the gap is a legitimate higher-order resonance, and truncating the
  window removes exactly the electrons that carry it.
- Re-solving the field for every trial power instead of rescaling the stored
  amplitude by the square root of power — slower, and it invites a different
  mesh at each trial, which destroys the convergence evidence.
- Comparing the achieved decibel margin against its requirement with a bare
  inequality. A margin formed from a logarithm of a ratio can land a unit in
  the last place below an exactly compliant value; absorb the representation
  error in the comparison, never by relaxing the required margin.

## Behavior contract (gate 3)

The field-power scaling, trajectory integration, yield evaluation, band-edge
search, power conversion, margin and convergence grading are exercised by the
gate 3 contract test:
scripts/test_e2001_level_two_single_carrier_method.py against
scripts/e2001_level_two_single_carrier_method_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_level_two_single_carrier_method.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
