---
name: dynamic-response-analysis
description: "Use when compute the dynamic response of a spacecraft structure to sine, random, or shock loading per ECSS-E-ST-32C clause 4.6.2.5: apply the dynamic amplification factor to a swept-sine excitation, derive the RMS and 3-sigma acceleration response to a random-vibration input via Miles' equation, evaluate the shock response spectrum for a half-sine pulse, or identify which analysis type applies to a given load event. Categorize each load event as sine, random, shock, or transient before selecting the response model; flag any load event that does not map to a recognized category. Trigger: ecss, e-st-32-structures-scope, dynamic-response-analysis, random-vibration-analysis, shock-response-spectrum, sine-response, miles-equation, sdof-oscillator."
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
  tags: [ecss, e-st-32-structures-scope, dynamic-response-analysis, random-vibration-analysis, shock-response-spectrum, sine-response, miles-equation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Dynamic Response Analysis (space-systems/ecss/dynamic-response-analysis)

Use when the task is computing the dynamic response of a spacecraft structural
element under sine, random, or shock loading per ECSS-E-ST-32C clause 4.6.2.5.
The leaf covers swept-sine response using the dynamic amplification factor,
broadband random-vibration response via Miles' equation, and shock response
spectrum evaluation for half-sine pulse inputs.

## Domain quick reference

- Clause 4.6.2.5 addresses three excitation families that a spacecraft structure
  must be assessed against: **sine** (deterministic swept or fixed-frequency
  loading), **random** (broadband stochastic loading expressed as a power
  spectral density), and **shock** (transient impulsive loading characterized
  by a shock response spectrum). Each load event is categorized into exactly
  one family before a response model is selected.
- **Sine response** uses the single-DOF dynamic amplification factor (DAF):
  DAF = 1 / sqrt[(1 − r²)² + (2ζr)²], where r = f/fn is the tuning ratio
  and ζ is the critical damping ratio. At resonance (r = 1) the DAF equals
  1/(2ζ). The peak dynamic response equals the static response multiplied by
  the DAF at the excitation frequency of interest.
- **Random vibration response** is derived via Miles' equation for a
  single-DOF oscillator: RMS = sqrt(π/2 · fn · Q · W), where fn is the
  natural frequency, Q = 1/(2ζ) is the quality factor, and W is the input
  power spectral density (g²/Hz) evaluated at fn. The design limit is the
  3-sigma level (3 × RMS), assuming a Gaussian amplitude distribution.
- **Shock response spectrum (SRS)** quantifies the peak response of a
  single-DOF oscillator to a transient pulse as a function of natural
  frequency. For a half-sine pulse of amplitude A and duration D, the
  response is governed by the dimensionless product τ = fn · D. In the
  residual region (τ < 0.5) the SRS rises approximately as 2π·τ·A; in the
  transitional and primary regions the SRS approaches a maximum near 2A.
- A load event that does not match sine, random, shock, or transient is
  flagged as unrecognized and rejected before any response computation begins.

## Workflow

1. Categorize each load event in the mechanical environment specification
   as sine, random, shock, or transient. Reject any event whose type is not
   one of the four recognized categories before proceeding.
2. For **sine** loading: identify the excitation frequency f and the static
   response under the equivalent quasi-static load. Compute the tuning ratio
   r = f/fn, evaluate the DAF, and multiply by the static response to obtain
   the peak dynamic response. Flag any case where r falls within 10 % of
   unity (near-resonance) for additional damping verification.
3. For **random** loading: read the input PSD level W at the natural frequency
   fn. Compute Q = 1/(2ζ). Apply Miles' equation: RMS = sqrt(π/2 · fn · Q · W).
   Multiply by 3 to obtain the 3-sigma design acceleration. Compare against
   the structural allowable.
4. For **shock** loading: identify the pulse amplitude A and duration D.
   Compute τ = fn · D. Select the SRS region (residual τ < 0.5, transitional
   0.5 ≤ τ < 1, or primary τ ≥ 1) and evaluate the half-sine SRS
   approximation. Compare the resulting SRS peak against the structural
   allowable.
5. For **transient** loading: note that a time-domain solver is required;
   Miles' equation and the DAF formula do not apply. Flag the event for
   numerical time-integration analysis outside the scope of this leaf.
6. Aggregate results per load event: report the governing response value,
   the analysis method used, and whether the structural allowable is met.
   A load event is compliant only when the computed response is within the
   allowable and no error flags remain.

## Pitfalls

- Applying Miles' equation when the PSD is not flat in the vicinity of fn:
  the equation assumes a constant (white-noise) spectrum at the resonance
  frequency; a strongly shaped spectrum requires the PSD value evaluated at
  fn, or a more general integration method.
- Collapsing the residual and primary SRS regions into one formula: the
  half-sine SRS in the residual region is much lower than in the primary
  region, and applying the primary-region approximation below τ = 0.5
  significantly overestimates the response.
- Using the DAF formula at r ≈ 1 without verifying damping: near resonance
  the DAF is controlled entirely by 2ζ; an incorrect damping value produces
  large errors in the predicted peak response.
- Treating 3-sigma as a conservative bound without noting that real
  structural loads may exhibit non-Gaussian statistics (pyrotechnic events,
  limit cycles), in which case additional margin or peak-factor correction
  is required.

## Behavior contract (gate 3)

The DAF computation, Miles' equation, SRS approximation, load-type
categorization, and error-path logic are exercised by the gate 3 contract
test: scripts/test_dynamic_response_analysis.py against
scripts/dynamic_response_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_dynamic_response_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
