---
name: e2001-electromagnetic-field-analysis
description: "Use when analyse the internal electromagnetic-field distribution of ECSS-E-ST-20-01C clause 5.2 inside a radio-frequency item before any worst-case multipactor-threshold is established: categorize the model against the recognized field-solver list, validate its mesh-convergence evidence and its frequency-sampling density across the operating band, scale each region's reference peak-field to the operating carrier-power by the square-root-power law, convert it through the field-uniformity-factor into an equivalent gap-voltage, then select the governing region together with every region inside the closeness band and refuse a threshold claim resting on an unconverged or under-sampled model. Trigger: ecss, e-st-20-electrical-scope, internal-field-analysis, field-solver-convergence, frequency-sampling-density, gap-voltage-derivation, field-uniformity-factor, peak-field-location, worst-case-multipactor-threshold."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-electromagnetic-field-analysis, internal-field-analysis, field-solver-convergence, frequency-sampling-density, gap-voltage-derivation, field-uniformity-factor, worst-case-multipactor-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Internal Field Analysis (space-systems/ecss/e2001-electromagnetic-field-analysis)

Use when the task is the internal field analysis of ECSS-E-ST-20-01C
clause 5.2 -- the computed description of the electromagnetic field
inside a radio-frequency item that has to exist, and has to be sound,
before a worst-case multipactor threshold can be established from it.
This leaf stops at the field description; it decides whether a
threshold may be established, not what the threshold is.

## Domain quick reference

- A multipactor threshold is a statement about a gap voltage, and the
  gap voltage is an output of the field analysis. Running the
  susceptibility comparison on a field model that has not converged, or
  that never sampled the frequency where the item resonates, produces a
  confident number resting on nothing.
- The solver has to be able to represent what the item contains. A
  mode-matching, method-of-moments or boundary-integral formulation
  describes metal boundaries; a dielectric-loaded region -- a support
  ring, a tuning puck, a window -- needs a formulation that carries
  dielectric material, such as a finite-element frequency-domain or a
  finite-difference time-domain solver. Analysing a loaded region with
  a metal-only solver returns a field for a different item.
- Convergence is demonstrated by repeating the run at successively
  finer discretization -- mesh refinement, or mode truncation for a
  modal solver -- and showing the peak field settling. Two levels is
  the minimum that can show anything, and a differential solver needs
  three; the criterion is the relative change of the peak field between
  the two finest levels, not agreement with an expectation.
- Frequency sampling has to resolve the narrowest loaded resonance the
  item supports. The resonance width is the centre frequency divided by
  the loaded quality-factor, so a high-quality-factor filter sets a far
  denser sampling requirement than its bandwidth alone suggests. A
  sparse sweep walks straight past the peak that governs.
- Fields scale with the square root of delivered power, because power
  goes as the square of the field. A model run at a convenient
  reference power -- one watt is common -- is therefore scaled to the
  operating condition by the square root of the power ratio, never
  linearly.
- The equivalent parallel-plate gap voltage is the line integral of the
  field across the separation. It never exceeds the peak field times
  the gap, and the field-uniformity factor is the ratio of the two:
  unity for a uniform gap, lower where the peak is a local corner or
  edge enhancement.
- The worst case is a region, not a number. Where a second region sits
  within a closeness band of the highest gap voltage, both regions
  govern and both are carried into threshold establishment -- the
  ranking is not precise enough to discard the runner-up.

## Workflow

1. Categorize the model against the recognized field-solver list. An
   unrecognized solver stops the assessment; there is no default
   convergence behaviour to assume.
2. Check convergence: enough refinement levels for that solver class,
   and a relative change of the peak field between the two finest
   levels inside the convergence tolerance. A change landing exactly on
   the tolerance is converged -- the comparison absorbs representation
   error rather than tightening the criterion.
3. Check frequency sampling: derive the number of samples needed from
   the band width, the centre frequency and the loaded quality-factor,
   subject to an absolute floor, and compare it with the sweep actually
   run. Absorb representation error before rounding the requirement up,
   so an exactly adequate sweep is not rejected for one missing sample
   that the physics never asked for.
4. Scale each region's reference peak field to the operating power by
   the square-root-power law.
5. Convert the scaled peak field into the equivalent gap voltage
   through the region's field-uniformity factor, and record the
   frequency-gap product the region sits at, which is what the
   susceptibility comparison downstream is indexed on.
6. Flag any dielectric-loaded region analysed with a solver that
   carries metal boundaries only.
7. Select the governing region by the highest equivalent gap voltage,
   and add every region within the closeness band of it.
8. Permit threshold establishment only when the model is converged,
   adequately sampled, and free of region findings. Otherwise the
   output is a list of what the field analysis still owes.

## Pitfalls

- Scaling the field linearly with power. The field goes as the square
  root, so a model run at one watt and scaled linearly to two hundred
  watts overstates the field by more than an order of magnitude and
  turns every region into a false finding.
- Accepting a single solver run as a field description. Without a
  second, finer run there is no evidence the peak field is a property
  of the item rather than of the discretization.
- Reading agreement with an expected value as convergence. The
  criterion is the change between successive refinements; a model can
  sit comfortably on the expected number and still be moving.
- Sampling the band uniformly at a handful of points because the band
  is narrow. A high-quality-factor resonance is far narrower than the
  band, and a coarse sweep reports the field between resonances as if
  it were the peak.
- Taking the peak field times the gap as the voltage everywhere. That
  is the uniform-gap limit; a corner or edge enhancement peaks locally
  and integrates to less, and using the limit as the value inflates
  every enhanced region.
- Carrying one worst-case region forward when a second sits a fraction
  of a decibel behind. The ranking is not that precise, and the
  runner-up is often the region whose material or surface treatment
  makes it the real driver.
- Establishing a threshold from a model with an open finding. The
  threshold inherits every weakness of the field it was computed from,
  and the finding then disappears from the record.

## Behavior contract (gate 3)

The solver categorization, mesh and mode convergence check, frequency
sampling requirement with its tolerance-absorbing rounding,
square-root-power field scaling, field-uniformity gap-voltage
conversion, frequency-gap product, dielectric-solver consistency check,
governing-region selection with its closeness band and the
threshold-establishment verdict are exercised by the gate 3 contract
test: scripts/test_e2001_electromagnetic_field_analysis.py against
scripts/e2001_electromagnetic_field_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_electromagnetic_field_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
