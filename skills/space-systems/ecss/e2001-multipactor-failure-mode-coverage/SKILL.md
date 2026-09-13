---
name: e2001-multipactor-failure-mode-coverage
description: "Use when assess whether every credible degraded case of a critical payload radio-frequency unit is carried into both the multipactor design-case-set and the verification-case-set of ECSS-E-ST-20-01C clause 4.3.1.3: build each degraded case from a power-redistribution factor, a standing-wave voltage rise taken from the mismatch ratio and a secondary-emission threshold derating, convert the nominal and degraded operating points into peak-gap-voltage, compute the breakdown-margin in decibels, name the governing credible case, and flag every credible case absent from either set or short of its required-margin. Trigger: ecss, e-st-20-electrical-scope, e2001-multipactor-failure-mode-coverage, multipactor-failure-mode, credible-degraded-case, standing-wave-voltage-rise, secondary-emission-threshold, breakdown-margin-decibels, payload-equipment-criticality."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-failure-mode-coverage, multipactor-failure-mode, credible-degraded-case, standing-wave-voltage-rise, secondary-emission-threshold, breakdown-margin-decibels]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Failure-Mode Coverage (space-systems/ecss/e2001-multipactor-failure-mode-coverage)

Use when the task is the failure-mode obligation of ECSS-E-ST-20-01C clause
4.3.1.3 -- showing that a critical payload radio-frequency unit was designed
and verified against its credible degraded cases, not only against its nominal
operating point.

## Domain quick reference

- Multipaction is a vacuum resonant-discharge effect: free electrons driven by
  the radio-frequency field cross a gap in a half-period, strike a surface,
  and release more secondary electrons than they consume. The breakdown
  condition is a peak-gap-voltage level, so every degraded case matters only
  through what it does to that voltage or to the surface's
  secondary-emission threshold.
- Clause 4.3.1.3 is a coverage rule, not a new calculation: the credible
  degraded cases of a critical payload unit belong in the design-case-set that
  sizes the gaps, and in the verification-case-set that later demonstrates
  them. A case present in one set and missing from the other is the defect
  this leaf is built to catch.
- Six degraded-case families cover the field hardware sees:
  rf-power-redistribution (an amplifier drop-out or a hot-redundant branch
  re-routing carrier power onto one path), impedance-mismatch (a deployment
  failure or an unterminated port raising the standing-wave voltage),
  thermal-excursion (a hotter surface with a weaker secondary-emission
  threshold), carrier-configuration-change (carriers collapsing in phase or
  in number), pressure-transient (a slow vent path holding the unit near the
  worst gas-breakdown pressure), and command-configuration-error.
- Two multipliers turn a nominal point into a degraded one. A
  power-redistribution factor scales the carrier power, and the mismatch ratio
  raises the local peak by `1 + |gamma|`, with `|gamma| = (S - 1) / (S + 1)`.
  A matched port has a factor of one and contributes nothing. Where the
  degraded case and the nominal point both name a mismatch ratio, the worse of
  the two governs -- they are not multiplied.
- A separate derating factor in (0, 1] lowers the breakdown threshold for a
  case that attacks the surface rather than the field: contamination, a
  temperature rise, or a surface state not represented by the characterised
  secondary-emission data.
- Breakdown-margin is reported in decibels of power. Because peak voltage
  follows the square root of power, `20 * log10(Vth / Vpk)` and
  `10 * log10(Pth / Ppk)` are the same number; quoting one and comparing it
  against a requirement written in the other is a factor-of-two error in
  decibels.
- A case declared non-credible leaves the numeric assessment, but only with a
  recorded justification. An unjustified non-credible case is a finding, not a
  pass.

## Workflow

1. Fix the nominal operating point of the unit: carrier power, reference
   impedance, the mismatch ratio at the interface, the characterised
   breakdown-threshold power for the gap, and whether the unit is critical.
2. Enumerate the degraded cases. Give each one an identifier, one of the six
   families, a credibility state, a power-redistribution factor, a mismatch
   ratio, a threshold derating factor, and the two coverage flags: is it in
   the design-case-set, is it in the verification-case-set. Reject an
   unrecognised family and a duplicate identifier before any arithmetic.
3. For each case, compute the applied peak-gap-voltage from the redistributed
   power, the reference impedance and the governing mismatch ratio, and the
   derated threshold voltage from the characterised threshold power.
4. Compute the breakdown-margin in decibels for each case and compare it
   against the required value, absorbing representation error with a named
   tolerance rather than relaxing the requirement.
5. Raise the findings: a credible case missing from the design-case-set, a
   credible case missing from the verification-case-set of a critical unit, a
   credible case short of its required-margin, and a non-credible case with no
   justification on record.
6. Name the governing credible case -- the one with the least
   breakdown-margin -- and report the unit as covered only when the finding
   list is empty.

## Pitfalls

- Assessing the nominal point alone and reading its comfortable margin as
  compliance. A drop-out that re-routes four carriers onto one path costs
  6 dB, which is the whole margin on most designs.
- Carrying a degraded case in the design-case-set and quietly dropping it from
  the verification-case-set because it is awkward to reproduce on the bench.
  Clause 4.3.1.3 wants it in both; if it cannot be reproduced, it needs a
  recorded rationale, not silence.
- Multiplying the nominal mismatch ratio by the degraded one. Both describe
  the same interface, so the worse of the two governs; multiplying invents a
  standing-wave rise the hardware never sees.
- Applying a threshold derating factor above one to make a hot case look
  better. The derating is a loss of threshold, never a gain.
- Treating a non-credible case as free. Without a justification the label is
  an assertion, and the case has simply been dropped.
- Quoting a voltage-ratio decibel figure against a power-ratio requirement, or
  the reverse -- the conversion is already inside the margin definition.

## Behavior contract (gate 3)

The mismatch, peak-gap-voltage, threshold-derating, breakdown-margin and
coverage-audit logic is exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_failure_mode_coverage.py against
scripts/e2001_multipactor_failure_mode_coverage_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_multipactor_failure_mode_coverage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
