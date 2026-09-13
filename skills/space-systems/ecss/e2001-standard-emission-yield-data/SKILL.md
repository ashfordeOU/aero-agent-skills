---
name: e2001-standard-emission-yield-data
description: "Use when determine which secondary-electron-emission yield dataset applies under ECSS-E-ST-20-01C clause 9.6: decide whether a measured record is representative of the flight material, its surface-condition and the impact-energy span actually needed, and when it is not, fall back on the tabulated experimental yield-parameters held for common spacecraft metals -- aluminium, gold, silver, copper, nickel, titanium, magnesium, stainless-steel -- evaluate the universal yield-curve at any impact energy, locate the first and second crossover-energies where the yield reaches unity, derive the surface-charging disposition implied by an incident-electron energy, and record the fallback as declared provenance so tabulated data is never mistaken for measurement. Trigger: ecss, e-st-20-01c, secondary-electron-emission-yield, tabulated-yield-data, crossover-energy, yield-curve-evaluation, material-surface-condition, data-provenance-fallback."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-standard-emission-yield-data, secondary-electron-emission-yield, tabulated-yield-data, crossover-energy, yield-curve-evaluation, data-provenance-fallback]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Standard Emission-Yield Data Fallback (space-systems/ecss/e2001-standard-emission-yield-data)

Use when the task is the clause 9.6 decision of ECSS-E-ST-20-01C: a
multipaction assessment needs a secondary-electron-emission yield curve
for a surface, no representative measured record exists for that surface,
and the analysis therefore falls back on the tabulated experimental
yield-parameters held for the common spacecraft metals.

## Domain quick reference

- Clause 9.6 is a fallback rule, not a preference. Measured data for the
  actual material, in the actual surface-condition, across the impact
  energies the analysis needs, always wins. The tabulated set is what
  keeps an assessment moving when that measurement does not exist -- and
  the fallback is only legitimate if it is declared, because a tabulated
  curve and a measured curve carry very different confidence.
- Representativeness has four legs, and failing any one sends the
  analysis to the table: the record is for the same material, in the
  same surface-condition, covering at least the required impact-energy
  span, and drawn from more than a single specimen. A record for
  sputter-cleaned aluminium does not represent an as-received oxidized
  aluminium flight surface -- the oxide raises the peak yield sharply,
  and that difference is the whole multipaction question.
- The tabulated set is keyed by material and surface-condition together,
  covering aluminium, gold, silver, copper, nickel, titanium, magnesium
  and stainless-steel in as-received and sputter-cleaned states. Each
  entry carries two parameters: the peak yield and the impact energy at
  which that peak occurs. A material outside the table has no fallback
  at all, and the correct answer is a refusal that sends the project to
  a measurement, not a nearest-neighbour guess.
- The two parameters feed a universal yield-curve shape, normalized so
  the curve peaks at the tabulated peak yield at the tabulated peak
  energy and decays on both sides. Evaluating it at an impact energy
  gives the yield the analysis needs.
- Where the peak yield exceeds unity the curve crosses unity twice:
  a first crossover-energy below the peak and a second above it.
  Between them a surface emits more electrons than it receives, which
  is the energy window in which a multipaction discharge can sustain
  itself. Both crossovers are located numerically by bisection rather
  than by an algebraic inverse, which the curve does not admit.
- The disposition at a given impact energy follows from the yield: above
  unity the surface emits net electrons and drifts positive, below unity
  it absorbs them and drifts negative, and within a stated tolerance of
  unity it is balanced. That tolerance absorbs representation error, not
  physical uncertainty.

## Workflow

1. Normalize the material and surface-condition names through the alias
   map, so a supplier's "aluminum", "Al" or "oxidized" lands on the same
   table key as the canonical form.
2. Assess the measured record for representativeness against the flight
   material, surface-condition and required energy span, collecting a
   reason for each leg that fails. Reject a malformed record outright
   rather than treating it as non-representative.
3. If the record is representative, take its own peak yield and peak
   energy and mark the provenance measured. Otherwise look the surface
   up in the tabulated set.
4. If the material and surface-condition are not in the table, refuse:
   there is no fallback, and the assessment needs a measurement.
   Otherwise take the tabulated parameters and mark the provenance as a
   declared fallback carrying the reasons the measured record was set
   aside.
5. Evaluate the universal yield-curve at the impact energies of interest
   and, where the peak yield exceeds unity, bracket and bisect both
   crossover-energies.
6. Report the disposition at each impact energy of interest and emit the
   provenance declaration alongside the numbers, so a reader can see at a
   glance whether the curve came from this surface or from the table.

## Pitfalls

- Silently substituting a tabulated curve for a measurement. The number
  may be defensible; an undeclared substitution is not, because the
  downstream margin policy differs for measured and tabulated inputs.
- Reusing a sputter-cleaned entry for a flight surface that is
  as-received. Cleaning strips the oxide that drives the high peak
  yields, so the cleaned entry is the optimistic one and using it for a
  real, oxidized surface understates the multipaction risk.
- Accepting a measured record whose energy span stops short of the
  required range and extrapolating the curve past its data. The span
  shortfall is a representativeness failure, not something to be papered
  over by evaluating the fitted shape outside its support.
- Picking a nearest material when the table has no entry. An alloy is
  not its base metal for emission purposes; the absence of an entry is a
  result, and the honest output is a refusal.
- Solving for a crossover-energy by inverting the curve algebraically.
  The shape has no closed-form inverse; bracket the root on the correct
  side of the peak and bisect, and check that the peak actually exceeds
  unity before looking for a root at all.
- Reading a yield exactly at unity with a bare equality. Use the stated
  tolerance so a balanced surface is reported as balanced rather than
  flipping sign on the last bit of a floating-point evaluation.

## Behavior contract (gate 3)

The alias resolution, tabulated lookup, representativeness assessment,
source selection with refusal, yield-curve evaluation, crossover
bisection and disposition logic are exercised by the gate 3 contract
test: `scripts/test_e2001_standard_emission_yield_data.py` against
`scripts/e2001_standard_emission_yield_data_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_standard_emission_yield_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml. Tabulated parameters here are
  house reference values for the common metals, not reproduced text.
- compliance: STANDARDS-REF, gated: false.
