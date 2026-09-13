---
name: e20-radiating-element-characterisation
description: "Use when determine whether an isolated radiating-element characterisation is adequate to feed a whole-antenna-performance-prediction under ECSS-E-ST-20C clause 7.2.2.3.1: categorize the element as an aperture-type, resonant-printed or travelling-wave radiator, check the characterisation record carries every quantity its family needs, convert aperture area and aperture-efficiency into isolated directivity, subtract mismatch-loss and dissipative-loss to reach realised element-gain, fit the cosine-q element-pattern from a measured half-power-beamwidth, verify cross-polar-discrimination and phase-centre-defocus against their limits, and decide when element-mutual-coupling forces an embedded-element-pattern instead. Trigger: ecss, e-st-20-electrical-scope, e-st-20c-clause-7-2-2-3-1, radiating-element-characterisation, isolated-element-pattern, embedded-element-pattern, cross-polar-discrimination, element-phase-centre, aperture-efficiency, realised-element-gain."
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
  tags: [ecss, e-st-20-electrical-scope, e20-radiating-element-characterisation, isolated-element-pattern, embedded-element-pattern, cross-polar-discrimination, element-phase-centre, aperture-efficiency, realised-element-gain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Radiating Element Characterisation (space-systems/ecss/e20-radiating-element-characterisation)

Use when the task is the clause 7.2.2.3.1 radiating-element step of
ECSS-E-ST-20C -- characterising one isolated radiating element well
enough that the whole-antenna-performance-prediction built on top of
it is believable, and saying plainly when the isolated characterisation
stops being a valid input because the element no longer behaves in
isolation.

## Domain quick reference

- Every element is categorized once into a radiator family, because
  the family fixes what the characterisation record must contain.
  Aperture-type radiators (pyramidal, conical and corrugated horns,
  open-ended waveguides, septum-polariser horns) radiate from a
  physical mouth, so their record carries aperture-efficiency and the
  aperture-field taper. Resonant-printed radiators (microstrip and
  stacked patches, printed dipoles, annular and crossed slots) live on
  a substrate, so their record carries impedance-bandwidth and the
  surface-wave efficiency the substrate steals. Travelling-wave
  radiators (axial-mode and quadrifilar helices, Archimedean spirals,
  dielectric rods, tapered-slot radiators) build the beam along a
  structure, so their record carries the axial-ratio pattern and the
  radiation phase progression. Every family also carries the common
  four: co-polar pattern, cross-polar pattern, input reflection
  coefficient and phase-centre location. An element type outside the
  three families is rejected rather than defaulted.
- Isolated directivity for an aperture-type radiator follows from its
  physical mouth area and its aperture-efficiency against the square
  of the wavelength; for the other two families directivity is a
  measured quantity, not a derived one, and a record that omits it
  cannot be completed by an aperture formula. Realised element-gain is
  that directivity reduced by two independent efficiencies: the
  mismatch-loss set by the input standing-wave-ratio and the
  dissipative-loss set by the radiation efficiency. Keeping them apart
  matters, because a re-match fixes only the first.
- The shape of the isolated element-pattern is usefully modelled as a
  cosine raised to an exponent fitted to the measured
  half-power-beamwidth; that single exponent then predicts the element
  contribution at any scan angle, which is what the array or
  reflector-illumination step consumes. The model is only defined
  inside the forward hemisphere.
- Cross-polar-discrimination is the separation between the co-polar
  peak and the worst cross-polar peak, and phase-centre-defocus is the
  round-trip phase error a phase-centre offset produces across the
  angle the element subtends; both are pass or fail against a stated
  limit rather than free parameters.
- The isolated characterisation is only a legitimate input to the
  whole-antenna-performance-prediction while the element is
  electrically alone. Close lattice spacing or strong
  element-mutual-coupling changes the active pattern and the active
  input match, and at that point the prediction needs an
  embedded-element-pattern measured in the real lattice; the isolated
  record then documents the element, it does not predict the antenna.

## Workflow

1. Categorize the element type into its radiator family; reject an
   element type that belongs to none of them.
2. Compare the characterisation record against the quantity list that
   family demands and list every missing quantity; reject a record
   carrying an unrecognised quantity token.
3. Establish isolated directivity: compute it from mouth area,
   aperture-efficiency and wavelength for an aperture-type radiator,
   or take the measured value for the other two families.
4. Reduce directivity to realised element-gain by the mismatch
   efficiency from the standing-wave-ratio and by the radiation
   efficiency, and compare the result against the required
   element-gain.
5. Fit the cosine exponent to the measured half-power-beamwidth and
   evaluate the element-pattern at the angles the antenna step needs.
6. Check cross-polar-discrimination and phase-centre-defocus against
   their limits.
7. Decide whether lattice spacing or measured element-mutual-coupling
   forces an embedded-element-pattern; if it does, the isolated record
   is not sufficient for the prediction.
8. Aggregate the findings; the element characterisation supports the
   whole-antenna-performance-prediction only when the list is empty.

## Pitfalls

- Applying the aperture-area directivity formula to a printed patch or
  a helix. The formula needs a radiating mouth; for the other families
  directivity is measured, and inventing an equivalent area produces a
  confident number with no physical basis.
- Folding mismatch-loss and dissipative-loss into one efficiency. They
  have different fixes and different temperature behaviour, and a
  single lumped number hides which one is eating the element-gain.
- Fitting the cosine exponent to the beamwidth of one principal plane
  and using it in both. An element with unequal principal-plane
  beamwidths needs one exponent per plane or the off-axis prediction
  is wrong in the narrower plane.
- Reading a good isolated cross-polar-discrimination as the array
  value. Lattice truncation and element-mutual-coupling degrade
  cross-polar behaviour, so the isolated figure is an upper bound.
- Ignoring the phase-centre offset because the element is small. The
  defocus error scales with the offset in wavelengths, so an offset of
  a few millimetres is negligible at low frequency and a real pattern
  error in a high-frequency band.
- Treating tight lattice spacing as a small correction on the isolated
  pattern. Below the spacing threshold the active element behaviour is
  a different measurement, not a scaled one.

## Behavior contract (gate 3)

The radiator-family categorization, record-completeness,
isolated-directivity, realised-element-gain, cosine-exponent
element-pattern, cross-polar-discrimination, phase-centre-defocus and
embedded-element-pattern trigger logic is exercised by the gate 3
contract test:
scripts/test_e20_radiating_element_characterisation.py against
scripts/e20_radiating_element_characterisation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_radiating_element_characterisation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
