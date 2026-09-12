---
name: fracture-material-data
description: "Use when derive fracture material properties for a space structure component: establish valid plane-strain fracture toughness KIC from test specimens, fit Paris-law da/dN crack growth curves from coupon data, determine the fatigue crack growth threshold ΔKth for each applicable load ratio, and apply conservative knockdown factors when data originate from a handbook or a limited-data campaign. Covers KIC specimen validity checks per the plane-strain size criterion, R-ratio adjustment of thresholds, three-region crack growth characterisation (threshold, Paris, near-KIC), minimum data requirements for Paris-curve fitting, and assembling a fully adjusted material data record. Trigger: ecss, e-st-32-structures-scope, fracture-toughness, crack-growth, paris-law, kic-validity, delta-kth, limited-data, material-data, da-dn."
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
  tags: [ecss, e-st-32-structures-scope, fracture-toughness, crack-growth, paris-law, kic-validity, delta-kth, limited-data, material-data, da-dn]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Material Data Derivation (space-systems/ecss/fracture-material-data)

Use when the task is deriving fracture material properties for a fracture
control analysis under ECSS-E-ST-32C clause 7.2.5: verifying KIC specimen
validity, fitting crack growth curves, establishing thresholds, and applying
the appropriate data-source treatment (test-derived, handbook, or limited).

## Domain quick reference

- **KIC (plane-strain fracture toughness)**: The result of a fracture-toughness
  test is only accepted as a valid KIC when both the specimen thickness B and
  the crack length a satisfy the plane-strain size criterion
  (2.5 × (KIC/σys)²). A result that does not meet this criterion is a
  conditional value KQ and must be treated with additional conservatism.

- **Paris-law crack growth curve**: In the Paris regime, the crack growth rate
  per fatigue cycle follows da/dN = C × ΔK^n, where C and n are material
  constants derived by linear regression on log–log coupon data. A minimum of
  three (da/dN, ΔK) data pairs are required before a fitted curve is
  acceptable for fracture analysis. Three crack growth regions exist:
  threshold (ΔK ≤ ΔKth, negligible growth), Paris (stable power-law growth),
  and near-KIC (rapid growth as Kmax approaches KIC).

- **Threshold ΔKth**: The stress-intensity-factor range below which fatigue
  crack propagation is negligible. ΔKth decreases as the load ratio
  R = Kmin/Kmax increases. A Walker-type scaling (ΔKth(R) = ΔKth(0) × (1−R)^γ)
  adjusts the R = 0 reference value to any positive R. For compressive cycles
  (R < 0), treat R as zero — the compressive portion of the cycle does not
  contribute to crack opening.

- **Data source categories and knockdowns**: Material data are categorized as
  test-derived (from a dedicated coupon campaign for the flight material lot),
  handbook (a qualified reference source such as MMPDS or equivalent), or
  limited (insufficient data points for a statistically representative fit).
  Handbook and limited data require a conservative knockdown applied to both
  KIC and ΔKth before use in analysis; test-derived data carry no knockdown.

## Workflow

1. Confirm the source category for all available material data (test-derived,
   handbook, or limited). Reject any source that does not belong to one of
   these three categories before proceeding.

2. Assess KIC specimen validity: for each reported toughness value, compute
   the plane-strain size criterion 2.5 × (KIC/σys)² and confirm that both B
   and a meet or exceed it. A value that fails the criterion is treated as KQ
   (conditional), not as a valid plane-strain KIC. Carry a note in the material
   record flagging that the validity criterion was not met.

3. Fit the Paris-law parameters: collect all (ΔK, da/dN) coupon data pairs in
   the stable Paris regime, perform linear regression in log–log space to
   obtain C and n, and record the coefficient of determination R². Reject a
   fit derived from fewer than three data pairs; mark the data source as
   limited and apply the limited-data knockdown.

4. Determine ΔKth: use the measured or handbook threshold at R = 0 and adjust
   it to each load ratio present in the fatigue spectrum using the Walker
   scaling. Use the most conservative (lowest) adjusted threshold across all
   relevant load ratios as the single design value unless the analysis
   explicitly tracks R-ratio bins.

5. Apply source knockdowns: reduce KIC and ΔKth by the appropriate knockdown
   factor (test-derived: 1.0; handbook: 0.90; limited: 0.85) to arrive at
   design-allowable values.

6. Characterize the crack growth regime for each crack size and load event in
   the fracture analysis: threshold (ignore), Paris (apply da/dN = C·ΔK^n),
   or near-KIC (flag for imminent fracture assessment). A crack that enters the
   near-KIC regime during its growth life requires an immediate residual-
   strength check against KIC before any further growth integration.

7. Document the adjusted material record — name, adjusted KIC, adjusted ΔKth,
   Paris C and n, source category, and any warnings — and carry it forward into
   the crack growth life calculation.

## Pitfalls

- Accepting a KQ result as KIC without applying the plane-strain validity
  check: a conditional toughness value can be substantially higher than the
  true plane-strain KIC, leading to non-conservative crack-critical size
  predictions.

- Fitting a Paris curve from only two data points: the minimum is three pairs;
  a two-point fit has zero degrees of freedom and its scatter band is
  meaningless.

- Ignoring the R-ratio dependence of the threshold: using the R = 0 threshold
  for a high-R mission load history overcounts crack arrest events and
  underestimates crack growth.

- Treating a handbook value without knockdown as if it were test-derived: a
  handbook value is a statistical result from a population of heats and product
  forms that may not match the flight material lot; the 0.90 knockdown accounts
  for this uncertainty.

- Applying threshold-region treatment to a crack that has already entered the
  Paris regime in a previous load event: the regime assignment is per-event per
  current crack size, not a global property of the crack.

## Behavior contract (gate 3)

The KIC validity, Paris-law, threshold-adjustment, data-source categorization,
crack-growth-region, Paris-parameter derivation, knockdown, and material-record
logic is exercised by the gate 3 contract test:
scripts/test_fracture_material_data.py against
scripts/fracture_material_data_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_fracture_material_data.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS-E-ST-32C §7.2.5 (Material data derivation).
