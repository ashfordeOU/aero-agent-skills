---
name: e20-antenna-performance-parameter-set
description: "Use when determine the antenna characterisation parameter-set demanded by ECSS-E-ST-20C clause 7.2.2.5: confirm every mandatory radiative parameter is declared for the antenna-function at hand, sort each declared entry into its beam-coverage, directivity-and-antenna-gain, polarisation-purity, boresight-pointing or port-matching family, derive directivity from the half-power-beamwidth pair, convert directivity into antenna-gain through radiation-efficiency, translate axial-ratio into cross-polar-discrimination, root-sum-square the boresight-pointing-error contributors against the allowable, and judge each declared value against its specified bound. Trigger: ecss, e-st-20-electrical-scope, antenna-characterisation, antenna-parameter-set, half-power-beamwidth, axial-ratio, cross-polar-discrimination, boresight-pointing-error, radiation-efficiency, edge-of-coverage-level."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-performance-parameter-set, antenna-characterisation, antenna-parameter-set, half-power-beamwidth, axial-ratio, cross-polar-discrimination, boresight-pointing-error, edge-of-coverage-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical and Optical Engineering — Antenna Characterisation Parameter-Set (space-systems/ecss/e20-antenna-performance-parameter-set)

Use when the task is the parameter-set of ECSS-E-ST-20C clause 7.2.2.5 --
deciding which antenna-characterisation quantities a given antenna-function
must declare, from beam-coverage and directivity through to boresight, then
deriving the dependent quantities and judging each declared value against its
specified bound.

## Domain quick reference

- Clause 7.2.2.5 fixes the *vocabulary* of an antenna characterisation, not a
  single number. The declared quantities fall into five families: beam-coverage
  (coverage-area, edge-of-coverage-level, half-power-beamwidth, scan-range),
  directivity-and-antenna-gain (directivity, peak-antenna-gain,
  radiation-efficiency, side-lobe-level), polarisation-purity (axial-ratio,
  cross-polar-discrimination, polarisation-sense), boresight-pointing
  (boresight-direction, boresight-pointing-error, beam-pointing-stability) and
  port-matching (input-vswr, operating-bandwidth, port-isolation). Every entry
  is sorted into exactly one family; an entry that matches no canonical name
  or alias is rejected rather than silently carried.
- Which quantities are *mandatory* depends on the antenna-function. A
  telecommand-reception antenna is judged on its edge-of-coverage-level over a
  wide coverage-area and is largely insensitive to side-lobe-level; a
  payload-downlink antenna is judged on peak-antenna-gain, side-lobe-level and
  boresight-pointing-error; a navigation-signal antenna adds axial-ratio and
  cross-polar-discrimination because polarisation-purity drives the ranging
  error; an inter-satellite-link antenna adds beam-pointing-stability and
  scan-range. The completeness check is therefore function-relative.
- Several declared quantities are not independent. Directivity follows from
  the two principal half-power-beamwidths through the beam-solid-angle
  approximation; peak-antenna-gain is directivity reduced by
  radiation-efficiency expressed in decibels; cross-polar-discrimination
  follows from axial-ratio through the ratio of the co-polar and cross-polar
  field components. Declaring both members of such a pair without checking
  consistency is how a characterisation contradicts itself.
- The boresight-pointing-error is an error budget, not a measurement: thermal
  distortion, deployment repeatability, alignment residual, structural
  stability and attitude knowledge combine root-sum-square and the total is
  compared with the allowable. A single dominant contributor left out of the
  list is the usual cause of an optimistic budget.

## Workflow

1. Normalise each declared parameter name to its canonical form (resolving the
   common aliases such as the abbreviated beamwidth, axial-ratio and
   discrimination tokens). Reject an unrecognised name before it enters the
   assessment.
2. Look up the mandatory parameter-set for the declared antenna-function and
   difference it against the normalised declared set; report the missing
   entries. A missing mandatory entry is a finding in its own right, however
   compliant the declared entries are.
3. Sort each declared entry into its family and record which of the five
   families the characterisation actually covers; an uncovered family for a
   function that needs it is reported alongside the missing entries.
4. Derive the dependent quantities that the declared set allows: directivity
   from the half-power-beamwidth pair, peak-antenna-gain from directivity and
   radiation-efficiency, cross-polar-discrimination from axial-ratio. Where a
   derived value and a declared value coexist, compare them and flag a
   disagreement beyond the stated consistency tolerance.
5. Combine the boresight-pointing-error contributors root-sum-square and
   compare the total with the allowable. Treat a total that equals the
   allowable to within representation error as compliant.
6. Judge every declared record against its bound in the stated direction
   (an upper bound for side-lobe-level, axial-ratio, input-vswr and
   boresight-pointing-error; a lower bound for edge-of-coverage-level,
   peak-antenna-gain, radiation-efficiency, cross-polar-discrimination and
   port-isolation). The parameter-set is complete and compliant only when the
   missing list and the non-compliant list are both empty.

## Pitfalls

- Treating the parameter list as function-independent and accepting whatever
  the supplier declared -- a wide-beam telecommand-reception antenna and a
  narrow-beam payload-downlink antenna need different mandatory entries, and a
  single fixed list either over-constrains one or under-constrains the other.
- Reading a compliant declared set as a complete characterisation. Absence of
  a mandatory entry is not a pass; it means the quantity was never
  characterised, which is the finding.
- Confusing directivity with peak-antenna-gain. They differ by the
  radiation-efficiency in decibels, and quoting the directivity value against
  an antenna-gain bound silently buys back the ohmic and mismatch losses.
- Quoting a low axial-ratio as if it were the polarisation-purity requirement
  itself. The requirement is usually written on cross-polar-discrimination, and
  the conversion is strongly non-linear near a small axial-ratio -- a modest
  axial-ratio degradation collapses the discrimination.
- Summing boresight-pointing-error contributors arithmetically, or
  root-sum-squaring a list that omits the deployment and thermal terms. The
  first over-states the budget, the second under-states it.

## Behavior contract (gate 3)

The name-normalisation, function-relative completeness, family sorting,
derived-quantity, error-budget and bound-judging logic is exercised by the
gate 3 contract test: scripts/test_e20_antenna_performance_parameter_set.py
against scripts/e20_antenna_performance_parameter_set_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_antenna_performance_parameter_set.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
