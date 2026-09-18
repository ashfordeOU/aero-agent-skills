---
name: e2007-spacecraft-magnetic-emission-verification
description: "Verify the steady magnetic emission of a spacecraft against its vehicle limit under ECSS-E-ST-20-07C clause 5.3.6, where analysis and test together carry the verification. Use when a unit dipole budget has to be reconciled with a measured system residual moment: vector-sum the contributor moments so that cancelling axes really cancel, root-sum-square their independent uncertainties, expand by the declared coverage factor, expand the measured moment by its own measurement uncertainty, project the governing moment to the far-field flux density at the evaluation radius and polar angle, and refuse a case resting on one leg alone or on a budget with no measured contributor. Trigger: ecss, e-st-20-07c, spacecraft-steady-magnetic-emission, residual-dipole-budget, magnetic-moment-uncertainty, dipole-far-field-flux-density, analysis-test-reconciliation, magnetic-cleanliness-verification, vehicle-magnetic-limit."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-spacecraft-magnetic-emission-verification, spacecraft-steady-magnetic-emission, residual-dipole-budget, dipole-far-field-flux-density, analysis-test-reconciliation, magnetic-moment-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Spacecraft Magnetic Emission Verification (space-systems/ecss/e2007-spacecraft-magnetic-emission-verification)

Use when the task is the steady magnetic emission verification of
ECSS-E-ST-20-07C clause 5.3.6 -- showing that the vehicle stays under
its steady magnetic limit, with the analysis budget and the system
measurement each doing the part the other cannot.

## Domain quick reference

- The quantity under control is the steady residual magnetic moment of
  the whole vehicle, in A*m^2, not the field measured at one probe. A
  field number only means something once the radius and the orientation
  it was taken at are attached to it.
- Moments are vectors. Two units with equal and opposite dipoles leave
  almost nothing behind, and a budget that sums magnitudes destroys
  exactly the cancellation the layout was designed to buy. The sum is
  taken per axis; the magnitude is taken last.
- Contributor uncertainties are independent, so they combine in
  quadrature and are then expanded by the declared coverage factor. An
  arithmetic sum of the same uncertainties produces a worst case no
  achievable design can meet, and the usual response to that is to
  quietly relax the limit instead.
- The far-field of a dipole falls as the inverse cube of the radius and
  varies with polar angle as sqrt(1 + 3cos^2), so the axial field is
  twice the equatorial field at the same radius. Carrying the result in
  nanotesla keeps significant digits that a tesla-valued float does not.
- Analysis and test are not alternatives here. The measurement covers
  the contributors the budget never knew about; the budget covers the
  configurations, deployments and operating currents the facility could
  not reproduce. Either leg missing is a verification gap, and so is a
  budget assembled entirely from similarity with nothing measured.
- The two legs are also checked against each other. A measurement above
  the analysis worst case means a contributor was missed. An analysis
  worst case far above the measurement is conservative but tells you
  the model is not representative, which matters the moment a flight
  configuration outside the tested one has to be defended.

## Workflow

1. Validate every contributor record: identifier, evidence method,
   three-component moment, uncertainty, compensation flag. Reject an
   unknown method, a short moment vector, a non-finite component, a
   negative uncertainty, or a repeated identifier.
2. Vector-sum the contributor moments per axis and take the magnitude
   of the sum; root-sum-square the uncertainties.
3. Expand the summed magnitude by the coverage factor times the
   combined uncertainty to obtain the analysis worst case.
4. Expand the measured system residual moment by its own measurement
   uncertainty at the same coverage factor.
5. Reconcile the legs: flag a measurement above the analysis worst
   case, and flag an analysis worst case outside the reconciliation
   band above the measurement, absorbing summation representation error
   at the boundary with a named tolerance rather than by moving the
   limit.
6. Take the governing moment as the larger of the two expanded values,
   project it to the far-field flux density at the declared evaluation
   radius and polar angle, and compare with the vehicle limit under the
   named field tolerance.
7. Report the summed moment, budget uncertainty, both worst cases, the
   governing moment, the field and every finding: limit exceedance,
   reconciliation gap, missing leg, missing measurement, or a budget
   with no measured contributor behind it.

## Pitfalls

- Summing dipole magnitudes instead of vectors. It converts a
  deliberately cancelled layout into a false exceedance, and the fix
  applied is usually a compensation magnet that was never needed.
- Adding uncertainties arithmetically. Independent contributions
  combine in quadrature; the arithmetic sum is not conservative, it is
  wrong, and it pushes a compliant vehicle into a redesign.
- Verifying on the measurement alone. A system test sees the
  configuration on the facility that day, not the deployed appendages,
  the operating currents or the units substituted later.
- Verifying on the budget alone. Harness loops, residual magnetisation
  from handling and units whose dipole was taken from a datasheet are
  exactly what the measurement is there to catch.
- Quoting a field without its radius and orientation. The inverse cube
  and the axial-to-equatorial factor of two mean an unqualified
  nanotesla figure can be made to pass or fail at will.
- Treating a large conservative margin between budget and measurement
  as good news. It is an unvalidated model, and it is the state in
  which an out-of-test configuration gets defended on paper.

## Behavior contract (gate 3)

The contributor validation, vector summation, quadrature uncertainty,
coverage expansion, far-field projection, analysis-test reconciliation,
evidence coverage and limit comparison are exercised by the gate 3
contract test:
scripts/test_e2007_spacecraft_magnetic_emission_verification.py against
scripts/e2007_spacecraft_magnetic_emission_verification_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_spacecraft_magnetic_emission_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
