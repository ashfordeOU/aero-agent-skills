---
name: e2007-electromagnetic-radiation-hazards
description: "Use when evaluate a spacecraft radio-frequency emitter for electromagnetic-radiation-hazard effects on ordnance, ground-crew and propellant-vapour receptors under ECSS-E-ST-20-07C clause 4.2.7 and feed the result into the product-assurance hazard-analysis: categorize each receptor family, confirm the receptor stands beyond the reactive and radiating near-field boundary before any far-field formula is trusted, compute the incident field-strength and power-flux-density at the receptor stand-off distance, derate the receptor threshold by the family safety-margin, derive the safe-separation-distance a failing case needs, and verify every case carries a hazard-report identifier, a severity-category and enough independent inhibits for that severity. Trigger: ecss, e-st-20-electrical-scope, electromagnetic-radiation-hazard, electro-explosive-device, hazard-analysis-linkage, safe-separation-distance, field-strength-threshold, power-flux-density, severity-category."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-electromagnetic-radiation-hazards, electromagnetic-radiation-hazard, electro-explosive-device, hazard-analysis-linkage, safe-separation-distance, field-strength-threshold, power-flux-density, severity-category]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Electromagnetic Radiation Hazards (space-systems/ecss/e2007-electromagnetic-radiation-hazards)

Use when the task is the clause 4.2.7 obligation of ECSS-E-ST-20-07C: a
radio-frequency emitter on or around the spacecraft is assessed for the harm
its radiated field can do to ordnance, to the people working near it and to
propellant vapour, and the result is not a standalone number but an input to
the hazard-analysis process that product assurance already runs.

## Domain quick reference

- Three receptor families carry different physics and different thresholds.
  An electro-explosive-device is sensitive to induced firing current and is
  bounded by an incident field-strength threshold in volts per metre. A
  ground-crew receptor is bounded by a power-flux-density exposure threshold
  in watts per square metre. A propellant-vapour receptor is bounded by the
  field-strength at which an arc can ignite it. A receptor type outside these
  three families is not evaluated by this procedure and is rejected.
- The far-field formulas only hold beyond the radiating near-field boundary,
  taken as twice the squared aperture dimension over the wavelength, and
  never closer than the reactive near-field boundary. A receptor standing
  inside either boundary must be handled by measurement or a near-field
  model; reporting the far-field number there is a fabricated result, so the
  case is returned as near-field-invalid rather than compliant or exceeded.
- Beyond that boundary the incident field-strength is the square root of
  thirty times the radiated power times the linear antenna-gain, divided by
  the stand-off distance, and the power-flux-density is that same radiated
  power times gain spread over the sphere of that radius. Gain declared in
  decibels relative to an isotropic radiator converts to a linear factor
  before either formula is used.
- The receptor threshold is never used raw. Each family carries a
  safety-margin in decibels, largest for ordnance, and the allowable value is
  the threshold pulled down by that margin. Inverting the same relation gives
  the safe-separation-distance the layout owes, which is the number worth
  reporting when a case fails.
- Clause 4.2.7 is a linkage clause. Every evaluated case is expected to
  appear in the product-assurance hazard-analysis with an identifier and a
  severity-category, and the number of independent inhibits on record is
  expected to match what that severity demands -- two for a catastrophic
  case, two for a critical case, one for a major case, none mandated for a
  minor case. A numerically compliant case with no hazard-report on record
  still fails the clause, because the linkage is what the clause asks for.

## Workflow

1. Categorize the receptor into one of the three families; reject an
   unrecognised receptor type before any computation runs.
2. Convert the declared antenna-gain to a linear factor and compute the
   near-field boundary from the aperture dimension and the wavelength at the
   emitter frequency.
3. Compare the receptor stand-off distance against that boundary. Inside it,
   return near-field-invalid with the boundary distance and stop; the case
   needs measurement, not a formula.
4. Beyond it, compute the incident field-strength and the power-flux-density
   at the stand-off distance.
5. Derate the family threshold by the family safety-margin and compare the
   computed quantity against the derated allowable, absorbing floating-point
   round-off exactly at equality instead of relaxing the threshold.
6. Compute the safe-separation-distance from the derated allowable, and
   report the shortfall against the stand-off distance actually available.
7. Check the hazard-analysis linkage: a hazard-report identifier is present,
   the severity-category is one of the four recognised values, and the
   independent-inhibit count meets what that severity requires.
8. Aggregate: the emitter is hazard-compliant only when no case is
   near-field-invalid, no case exceeds its derated allowable, and no case
   carries a linkage finding.

## Pitfalls

- Applying the far-field field-strength relation at a stand-off distance
  inside the near-field boundary. The relation understates the real field
  there, so the case reads compliant precisely where the risk is highest.
- Comparing the computed field-strength straight against the raw receptor
  threshold. The family safety-margin exists because the threshold itself is
  a statistical quantity; a case that only just meets the raw threshold has
  no margin at all.
- Using the field-strength relation for a ground-crew receptor. Human
  exposure is bounded by power-flux-density, and converting between the two
  by eye drops the free-space-impedance factor.
- Treating a numerically compliant case as closed without the hazard-report
  linkage. Clause 4.2.7 exists to push the result into the product-assurance
  hazard-analysis, so an unreferenced case is an open finding regardless of
  how large its margin is.
- Counting a single inhibit as sufficient for a catastrophic or critical
  severity-category. Those severities need two independent inhibits, and a
  redundant path that shares a failure cause is one inhibit, not two.
- Taking antenna-gain in decibels into the field relation without converting
  it to a linear factor first, which inflates the safe-separation-distance by
  orders of magnitude and hides the real one.

## Behavior contract (gate 3)

The receptor categorization, near-field boundary, field-strength,
power-flux-density, margin derating, safe-separation-distance and
hazard-analysis-linkage logic is exercised by the gate 3 contract test:
scripts/test_e2007_electromagnetic_radiation_hazards.py against
scripts/e2007_electromagnetic_radiation_hazards_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2007_electromagnetic_radiation_hazards.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
