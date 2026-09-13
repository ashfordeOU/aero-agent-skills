---
name: e2001-analysis-frequency-selection
description: "Use when compute the worst-case in-band frequency for the multipaction design-analysis of an RF component under ECSS-E-ST-20-01C clause 5.3.1: sweep the operating band, form the frequency-gap product of the critical gap at each candidate frequency, interpolate the surface susceptibility-curve for the breakdown-voltage threshold, convert that threshold into a breakdown-power through the local characteristic-impedance and the voltage-magnification factor, then keep the frequency giving the lowest breakdown-power and compare its achieved multipaction-margin in dB with the required value. Refuses a frequency-gap product outside the tabulated curve and flags a candidate set that samples the band edges only. Trigger: ecss, e-st-20-01c, multipaction-design-analysis, frequency-gap-product, breakdown-voltage-threshold, breakdown-power, susceptibility-curve, worst-case-frequency, voltage-magnification, multipaction-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-analysis-frequency-selection, multipaction, frequency-gap-product, breakdown-power, susceptibility-curve, voltage-magnification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — In-Band Frequency Selection (space-systems/ecss/e2001-analysis-frequency-selection)

Use when the task is the frequency-selection step of the multipaction
design-analysis of ECSS-E-ST-20-01C clause 5.3.1 — deciding which
frequency inside the operating band of an RF component is the one the
breakdown analysis has to be carried out at, because it is the frequency
whose breakdown-power is lowest.

## Domain quick reference

- Multipaction onset in a gap is governed by the frequency-gap product
  f*d (GHz*mm), not by frequency alone. A surface susceptibility-curve
  maps that product to a breakdown-voltage threshold for a given
  material and surface condition. Two components with the same band but
  different critical gaps therefore sit at different points of the same
  curve.
- The analysis quantity of interest is power, not voltage. The gap
  voltage of a travelling or standing wave is
  V = M * sqrt(2 * Z * P), where Z is the local characteristic-impedance
  seen at the gap and M is the voltage-magnification factor produced by
  the standing-wave pattern or field concentration at that frequency.
  Inverting at the threshold gives the breakdown-power
  P = V_th^2 / (2 * Z * M^2).
- Because V_th, Z and M all move with frequency, the lowest
  breakdown-power is not generally at a band edge. A filter resonance, a
  higher-order-mode cut-on or a tuning-element peak inside the band can
  raise M sharply and pull the worst case into the middle of the band,
  so those singular frequencies are analysed explicitly and not left to
  a uniform sweep to find.
- A frequency-gap product outside the tabulated span of the
  susceptibility-curve is not a small extrapolation: the curve shape
  changes on both sides of its span, so the correct response is to
  refuse the point and obtain curve data that covers it.
- The selected frequency is the one carried into the rest of the design
  analysis; its achieved margin in dB is what the component's required
  multipaction-margin is applied to.

## Workflow

1. Validate the operating band and the critical gap dimension of the
   component; a zero or inverted band, or a non-positive gap, is an
   input error, not a degenerate case to be clamped.
2. Build the candidate frequency set: both band edges, a uniform sweep
   of at least three points across the band, plus every declared in-band
   singular frequency. Reject a singular frequency that falls outside
   the band; collapse duplicates so a singular frequency landing on a
   sweep point is analysed once.
3. For each candidate, form f*d for the critical gap and read the
   breakdown-voltage threshold off the susceptibility-curve by log-log
   interpolation between tabulated points.
4. Interpolate the local characteristic-impedance, and the
   voltage-magnification factor when one is tabulated, at the same
   frequency; default the magnification to unity only when the component
   has no declared field-concentration data.
5. Convert each threshold to a breakdown-power and retain the candidate
   with the lowest value; break an exact tie on the lower frequency so
   the selection is reproducible.
6. Compute the achieved margin as 10*log10(P_breakdown / P_operating)
   and compare it with the required multipaction-margin, absorbing
   floating-point representation error at the boundary with a named
   tolerance rather than by relaxing the required value.
7. Report the retained frequency, its f*d, threshold, breakdown-power
   and margin, plus any finding: margin shortfall, or a candidate set
   that never sampled the band interior.

## Pitfalls

- Analysing only the band edges. The edges are necessary but not
  sufficient; an in-band magnification peak can make the worst case
  interior, and an edge-only candidate set is a coverage finding in its
  own right, not a pass.
- Selecting the frequency on lowest threshold voltage instead of lowest
  breakdown-power. Impedance and magnification both enter the power
  conversion, so the lowest-voltage point and the lowest-power point are
  different frequencies whenever Z or M varies across the band.
- Extrapolating the susceptibility-curve past its tabulated span to keep
  a candidate in the sweep. That silently invents threshold data; the
  candidate must be refused until curve data covering the product is
  available.
- Treating the frequency-gap product as a frequency. Changing the gap
  moves the component along the curve just as changing the frequency
  does, so a gap tolerance stack has to be re-run through the same
  selection, not assumed to keep the same worst-case frequency.
- Widening the required margin to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the required value stays as
  specified.

## Behavior contract (gate 3)

The band validation, candidate-set construction, susceptibility-curve
interpolation, breakdown-power conversion, worst-case selection and
margin comparison are exercised by the gate 3 contract test:
scripts/test_e2001_analysis_frequency_selection.py against
scripts/e2001_analysis_frequency_selection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_analysis_frequency_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
