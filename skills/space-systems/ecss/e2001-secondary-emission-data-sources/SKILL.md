---
name: e2001-secondary-emission-data-sources
description: "Use when validate and select the secondary-emission dataset behind a multipactor analysis under ECSS-E-ST-20-01C clause 5.3.3.3: categorize each candidate by provenance -- flight-lot-sample-measurement, representative-coupon-measurement, standard-tabulated-dataset, supplier-datasheet, open-literature -- test it against the critical part's base-material, surface-treatment, surface-condition and the primary-energy span the analysis needs, reject a secondary-electron-yield curve that is malformed or contradicts its own crossover-energies, prefer the best-provenance representative curve with the more conservative one breaking a tie, and fall back to the conservative standard-tabulated curve when no candidate represents the emitting surface. Trigger: ecss, e-st-20-electrical-scope, secondary-electron-yield, secondary-emission-data, first-crossover-energy, surface-treatment-representativeness, standard-tabulated-yield-curve, multipactor-critical-material, coupon-measurement-provenance."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-secondary-emission-data-sources, secondary-electron-yield, secondary-emission-data, first-crossover-energy, surface-treatment-representativeness, standard-tabulated-yield-curve, multipactor-critical-material]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Secondary Emission Data Sources (space-systems/ecss/e2001-secondary-emission-data-sources)

Use when the task is the data-source selection of ECSS-E-ST-20-01C
clause 5.3.3.3 -- deciding which secondary-electron-yield curve a
multipactor analysis is entitled to use for a critical part, and
showing that the curve chosen represents the surface that actually
emits.

## Domain quick reference

- Multipactor builds only where the emitting surface multiplies: an
  impacting primary electron must, on average, release more than one
  secondary electron. The secondary-electron-yield curve gives that
  ratio against primary-electron energy, rising from a low value,
  crossing unity at the first-crossover-energy, peaking at the maximum
  yield, and falling back through unity at the second-crossover-energy.
  The band between the two crossings is the multiplying window; the
  whole multipactor threshold follows from where that window sits.
- Yield is a property of the outermost surface, not of the bulk part.
  A silver-plated aluminium-alloy waveguide emits like silver, and like
  contaminated silver if it has sat in air. So a dataset represents a
  part only when the base-material, the surface-treatment (plating,
  conversion coating, bare metal) and the surface-condition
  (as-received, vacuum-baked, air-exposed) all match, and when the
  tabulated energy span covers the primary-energy range the analysis
  drives the gap through.
- Provenance ranks the candidates. A measurement on a sample from the
  flight lot is the strongest evidence, a measurement on a
  representative coupon next, then the standard tabulated dataset,
  then a supplier datasheet or open-literature value whose sample
  preparation is unknown. Provenance orders the choice; it never
  overrides representativeness, because a first-rate measurement of
  the wrong surface is still the wrong surface.
- When nothing on offer represents the surface, the analysis does not
  proceed on the closest available curve: it proceeds on the
  conservative standard tabulated curve -- higher peak yield and lower
  first-crossover-energy, which widens the multiplying window and
  lowers the predicted threshold -- and records the fallback as a
  finding to be closed by a coupon measurement.
- A dataset that contradicts itself is unusable: a peak yield at or
  below unity cannot have two crossing energies, a second crossing
  cannot precede the first, and a curve whose energies do not increase
  cannot be interpolated. These are input defects, not conservative
  cases.

## Workflow

1. Describe the critical part as an emitting surface: base-material,
   surface-treatment, surface-condition, and the primary-energy span
   the analysis needs covered.
2. Validate every candidate dataset -- provenance recognised, peak
   yield above unity, crossing energies ordered, curve energies
   strictly increasing, at least two tabulated points. Reject a
   malformed candidate rather than repairing it.
3. Score each candidate for representativeness against the part's four
   attributes and collect the mismatches. A candidate with no
   mismatch may serve as the analysis dataset.
4. Among the representative candidates pick the best provenance tier,
   breaking a tie with the more conservative curve (higher peak yield
   first, then lower first-crossover-energy).
5. With no representative candidate, apply the standard tabulated
   fallback, refuse a fallback that is not itself a standard dataset,
   and record the fallback and its mismatches as open findings.
6. Interpolate the yield at any primary-energy inside the tabulated
   span and refuse an energy outside it; report the multiplying window
   the multipactor threshold work will use.
7. Aggregate over the part set: the set is accepted only when every
   part runs on representative data with no open finding.

## Pitfalls

- Selecting on provenance alone and using a flight-lot measurement of
  a differently-plated part -- the tier is a tie-break among
  representative candidates, not a licence to mismatch the surface.
- Treating a vacuum-baked coupon and an air-exposed one as the same
  surface; the adsorbed layer that bake-out removes is exactly what
  raises the yield of a contaminated surface.
- Extrapolating the curve past its last tabulated point to reach the
  impact energy the analysis needs, which invents yield data where the
  dataset has none.
- Reading the fallback to standard data as a pass because a threshold
  came out acceptable -- the fallback is itself the finding, closed by
  measuring the surface, not by the margin it happened to produce.
- Picking the lower-yield curve because two representative datasets
  disagree; the conservative curve is the one that multiplies harder
  and starts earlier.
- Carrying a declared peak yield that the tabulated points exceed,
  which leaves the window and the threshold computed from
  inconsistent numbers.

## Behavior contract (gate 3)

The provenance categorization, dataset validation, yield
interpolation, representativeness scoring, conservatism ordering,
selection and standard-fallback logic are exercised by the gate 3
contract test:
scripts/test_e2001_secondary_emission_data_sources.py against
scripts/e2001_secondary_emission_data_sources_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_secondary_emission_data_sources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
