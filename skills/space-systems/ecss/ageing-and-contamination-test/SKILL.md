---
name: ageing-and-contamination-test
description: "Use when verify structural materials and passive film coatings for degradation under ageing and contamination exposures per ECSS-E-ST-32C clauses 4.6.3.16–4.6.3.17: categorize each test specimen by type, validate the ageing conditioning regime against the approved test specification, compute mechanical property retention ratios from pre- and post-exposure measurements, assess contamination exposure level against the allowable limit, and determine whether each specimen and the overall test campaign satisfy acceptance requirements. Trigger: ecss, e-st-32-structures-scope, ageing-test, contamination-test, passive-film-coating, property-retention, thermal-cycling, structural-verification."
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
  tags: [ecss, e-st-32-structures-scope, ageing-test, contamination-test, passive-film-coating, property-retention, thermal-cycling, structural-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Ageing and Contamination Test (space-systems/ecss/ageing-and-contamination-test)

Use when the task is to verify that structural materials and passive film coatings
(PFCs) retain adequate mechanical and functional properties after exposure to ageing
environments and contamination conditions per ECSS-E-ST-32C clauses 4.6.3.16–4.6.3.17.

## Domain quick reference

- ECSS-E-ST-32C clauses 4.6.3.16–4.6.3.17 require verification that the mechanical
  and thermal properties of structural materials and passive film coatings do not
  degrade beyond allowable limits when subjected to combined ageing and contamination
  environments representative of the service life.
- Specimens are categorized into two types: passive film coating (PFC) coupons and
  structural material coupons. Each type carries specific property measurements
  (e.g. adhesion strength, modulus, thermal emittance) that must be recorded before
  and after exposure conditioning to enable a retention ratio calculation.
- Ageing conditioning encompasses three main environment types: thermal cycling
  (repeated excursion between low and high temperature extremes), hygrothermal soak
  (elevated temperature and relative humidity for a prescribed duration), and UV
  irradiation (accumulated equivalent sun hours). A test campaign may apply one or
  more of these in sequence or combination.
- Contamination exposure is quantified as deposited mass per unit area (mg/m²).
  Each specimen carries an allowable contamination level derived from the
  contamination control plan; absence of a recorded allowable when exposure is
  non-zero is itself a finding.
- Property retention is the ratio of the post-conditioning measured value to the
  pre-conditioning baseline. Each property has a minimum retention threshold set
  by the design requirement; falling below it flags a non-conformance.

## Workflow

1. Categorize each test specimen as "passive_film_coating" or "structural_material".
   Reject any specimen with an unrecognized type before it enters the conditioning
   sequence.
2. Validate the ageing conditioning regime defined in the test specification: confirm
   that thermal cycling provides valid temperature bounds (low < high) and a positive
   cycle count; that hygrothermal soak specifies a positive duration and relative
   humidity in the valid range (0, 100]%; and that UV irradiation specifies a
   positive dose in equivalent sun hours. Reject a regime containing an unrecognized
   condition type.
3. For each specimen, record pre-conditioning property baselines (strength, modulus,
   adhesion, emittance, or other applicable properties) before applying the ageing
   and contamination conditioning.
4. Apply the approved conditioning sequence. Record post-conditioning property
   measurements and the actual contamination exposure level on each specimen.
5. Compute the property retention ratio (post / pre) for each measured property.
   Compare it against the minimum retention threshold from the design requirement;
   flag any property that falls below its threshold.
6. Compare the actual contamination exposure level on each specimen against the
   allowable; flag an exceedance. Flag a specimen with non-zero exposure but no
   recorded allowable as a missing-allowable finding.
7. Aggregate all retention and contamination findings per specimen. A specimen is
   accepted only when both violation lists are empty. Report the overall test
   campaign as accepted when every specimen is accepted.

## Pitfalls

- Measuring properties only after conditioning without establishing a pre-conditioning
  baseline makes it impossible to compute a retention ratio; the pre-value must be
  captured from the same batch of specimens before the conditioning sequence begins.
- Applying a minimum retention threshold of 1.0 (no degradation permitted) without
  verifying it is the stated requirement; many design allowables accept up to 10–15%
  degradation under the specified service environment.
- Treating an unset contamination allowable as zero (most restrictive) rather than
  flagging it as a missing-requirement finding; an unset allowable means the
  contamination control plan linkage was never captured.
- Comparing post-conditioning property values from differently scaled specimens
  without normalizing them to the same reference area or cross-section.

## Behavior contract (gate 3)

The specimen categorization, ageing-condition validation, property-retention
computation, contamination-exposure assessment, and campaign-acceptance logic is
exercised by the gate 3 contract test:
scripts/test_ageing_and_contamination_test.py against
scripts/ageing_and_contamination_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ageing_and_contamination_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
