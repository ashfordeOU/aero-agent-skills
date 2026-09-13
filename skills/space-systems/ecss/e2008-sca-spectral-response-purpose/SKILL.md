---
name: e2008-sca-spectral-response-purpose
description: "Verify a sun simulator against the reference spectrum using solar cell assembly spectral response data, and carry the result into the current measurement error budget as ECSS-E-ST-20-08C clause 6.4.3.5.1 intends: check all four curves cover the response band on one wavelength grid at a fine enough step, combine the reference and simulator spectra with the test and reference cell responses into the spectral mismatch factor, correct the measured short-circuit current by it, then add its departure from unity to the uncertainty terms as a root sum of squares. Use when spectral response data is about to justify a sun simulator or an error calculation. Trigger: ecss, e-st-20-08c-clause-6-4-3-5-1, solar-cell-spectral-response-purpose, sun-simulator-spectral-mismatch-factor, solar-cell-reference-spectrum-coverage, short-circuit-current-spectral-correction, solar-cell-measurement-error-budget."
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
  tags: [ecss, e-st-20-08-solar-cell-assembly-scope, e2008-sca-spectral-response-purpose, solar-cell-spectral-response-purpose, sun-simulator-spectral-mismatch-factor, solar-cell-reference-spectrum-coverage, short-circuit-current-spectral-correction, solar-cell-measurement-error-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies -- Spectral Response Purpose (space-systems/ecss/e2008-sca-spectral-response-purpose)

Use when the task is clause 6.4.3.5.1 of ECSS-E-ST-20-08C -- stating
and defending what the spectral response data of a solar cell assembly
is for. It is not an end in itself. The data exists so that a sun
simulator can be shown fit for the article it is about to illuminate,
and so that the error calculation behind every current measurement made
under that simulator has the one term it cannot get from anywhere else.

## Domain quick reference

- No simulator reproduces the reference spectrum. The question is never
  whether it departs, but whether the departure matters for this pair of
  cells, and that depends entirely on where the test article and the
  reference cell put their response.
- The spectral mismatch factor is the quantity that answers it: a ratio
  of four integrals over the reference spectrum, the simulator spectrum,
  the test article's response and the reference cell's response. Two
  cells with identical response curves cancel any lamp error exactly;
  two with different curves do not, and the factor says by how much.
- A factor of one is not a claim about the lamp. It says the lamp's
  departure affects both cells the same way. A poor simulator can give
  a factor of one with a well-matched reference cell, and an excellent
  one can give a large factor with a badly chosen one.
- The factor is a correction and an uncertainty at the same time. The
  measured current is divided by it to land on the reference spectrum,
  and the residual departure from unity is a term in the current
  measurement budget -- usually the largest one an otherwise careful
  illuminated measurement carries.
- The integrals can only see what the grid samples. A grid that stops
  short of the article's long-wavelength edge silently discards the part
  of the spectrum a lower junction lives on, and the factor comes back
  looking confident.
- Step size matters as much as span. Lamp spectra carry line structure
  and response curves carry band edges; a coarse grid straightens both,
  and the straightening moves the factor in a direction nobody can
  predict from the data that survived.
- All four curves have to sit on one grid. Interpolating one onto
  another quietly invents the samples that decide the answer, so a
  mismatched pair is a data problem to fix upstream rather than a
  numerical inconvenience to smooth over.

## Workflow

1. Validate the spectral policy first: the sample floor, the coarsest
   step allowed, the band the data has to cover, the mismatch tolerance
   and the ceiling on the combined uncertainty. A band whose end does
   not stand above its start is refused rather than used.
2. Validate each of the four curves on its own: ordered by increasing
   wavelength, no repeated wavelength, no negative value, enough samples
   to describe a curve. An absent curve stops the assessment, since the
   factor needs all four.
3. Check coverage and step for every curve before computing anything.
   Report each curve that leaves part of the band unsampled or steps
   too coarsely, and name all of them rather than the first, because a
   data set is repaired once.
4. Combine the curves into the mismatch factor as a ratio of four
   weighted integrals on the shared grid, refusing a pair of curves that
   do not share the grid rather than interpolating between them.
5. Hold the factor's departure from unity against the tolerance. A
   departure landing exactly on the tolerance is inside it; the
   comparison absorbs representation error and the tolerance itself does
   not move.
6. Divide the measured short-circuit current by the factor to place it
   on the reference spectrum, and report the corrected value alongside
   the measured one.
7. Add the residual departure to the declared uncertainty terms as a
   root sum of squares and hold the total against the budget ceiling.
   Close on one verdict -- spectral data insufficient, simulator
   spectrum not accepted, error budget exceeded, or spectral response
   supported.

## Pitfalls

- Reading a mismatch factor near unity as a verdict on the simulator.
  It is a verdict on the simulator, the reference cell and the article
  together; change the reference cell and the same lamp gives a
  different number.
- Correcting the current by the factor and then leaving the factor out
  of the uncertainty budget. The correction removes the bias, not the
  uncertainty in the curves the correction came from, and the budget
  then understates the measurement exactly where it is weakest.
- Sampling only where the article responds strongly. The tails carry
  little response but multiply a spectrum that can be large there, and
  truncating them moves the integrals in one direction every time.
- Interpolating one curve onto another curve's grid to make the
  integrals line up. The interpolated samples are the ones that decide
  the factor, and nothing downstream records that they were invented.
- Comparing a derived departure or a combined uncertainty against its
  limit by bare arithmetic. Both are sums and roots of many float
  terms, so either side can land a few units in the last place from the
  bound; the comparison absorbs that error while the bound itself is
  never relaxed.
- Carrying a mismatch factor from a previous campaign. It belongs to
  one lamp state, one reference cell and one article; a re-lamped
  simulator invalidates it without changing anything visible in the
  test setup.

## Behavior contract (gate 3)

The policy validation, per-curve ordering and value rules, band
coverage and step checks, shared-grid enforcement, trapezoidal and
weighted integrals, the four-integral spectral mismatch factor, its
departure from unity, the short-circuit current correction, the root
sum of squares uncertainty budget and the purpose verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_sca_spectral_response_purpose.py against
scripts/e2008_sca_spectral_response_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_spectral_response_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
