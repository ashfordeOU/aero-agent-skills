---
name: material-class-design-rules
description: "Use when determine and enforce material-class design rules for a spacecraft structural element under ECSS-E-ST-32C sections 4.5.9–4.5.12: categorize the element material as metal, non-metallic, composite, or adhesive-bonded; apply the corresponding rule set — ductility floor, stress-corrosion cracking mitigation, and galvanic-pair screening for metals; outgassing budget (TML, CVCM) and radiation tolerance for non-metallics; symmetric/balanced layup, hygrothermal knockdown factor, and micro-crack susceptibility for composites; bond-line thickness, surface preparation, thermal-cycling load, and peel-stress margin for adhesive joints — and report all violations before the material is accepted into the structural design baseline. Trigger: ecss, e-st-32-structures-scope, material-design-rules, metals, non-metallic, composites, adhesive-bonded, galvanic-compatibility, outgassing, hygrothermal."
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
  tags: [ecss, e-st-32-structures-scope, material-design-rules, metals, non-metallic, composites, adhesive-bonded, galvanic-compatibility, outgassing, hygrothermal]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Material Class Design Rules (space-systems/ecss/material-class-design-rules)

Use when the task is applying the material-class-specific structural design
rules of ECSS-E-ST-32C sections 4.5.9–4.5.12 — covering metallic materials,
non-metallic materials, composite laminates, and adhesive-bonded joints —
to confirm a candidate material or joint configuration is acceptable for
the structural design baseline before drawings are released or analysis
evidence is closed.

## Domain quick reference

- ECSS-E-ST-32C §4.5.9–§4.5.12 groups structural materials into four
  classes: metal, non-metallic, composite laminate, and adhesive-bonded
  joint. Each class carries its own rule set that must be satisfied in
  addition to the general strength and stiffness requirements of the
  standard.
- For **metals (§4.5.9)**: the rule set covers minimum ductility (elongation
  floor), stress-corrosion cracking (SCC) susceptibility screening, and
  galvanic-pair compatibility between dissimilar alloys in structural
  contact. A ductile failure mode is a prerequisite for the factors-of-safety
  regime in E-ST-32C; an SCC-susceptible alloy without a documented
  mitigation is a design non-conformance; a galvanic-incompatible pair without
  insulating or coating protection risks accelerated corrosion in ground
  handling and on-orbit environments.
- For **non-metallic materials (§4.5.10)**: outgassing characterisation per
  ECSS-Q-ST-70-02 (TML ≤ 1.0 %, CVCM ≤ 0.1 %) is required to protect
  adjacent optical, thermal, and electrical surfaces. Radiation tolerance
  must be confirmed for the mission dose level. The operating temperature
  envelope must be bounded and on record.
- For **composite laminates (§4.5.11)**: the layup must be symmetric about
  its mid-plane and balanced (equal populations of +θ and −θ plies) to
  prevent out-of-plane warping and in-plane shear distortion under curing
  and thermal loads. Allowable properties must carry a hygrothermal
  knockdown factor (wet/hot condition) before comparison with analysis
  results. Laminates with a high fraction of 0° plies (above ~80 %) require
  a micro-cracking susceptibility assessment under thermal cycling.
- For **adhesive-bonded joints (§4.5.12)**: the bond-line thickness must
  fall within the adhesive manufacturer's qualified window (nominally
  0.05–0.50 mm); the bond surfaces must be cleaned and primed before
  adhesive application; thermal-cycling-induced peel and shear loads must
  be included in the joint analysis; and the calculated peel stress must
  remain below the system allowable.

## Workflow

1. Receive the candidate material or joint data sheet and identify its
   material class. Reject any material class label that does not map to
   one of the four recognized classes before proceeding.
2. **Metal path (§4.5.9):** confirm yield strength, ultimate strength, and
   elongation are documented. Flag an elongation below 2 % as a ductility
   violation. If the alloy is SCC-susceptible, verify a mitigation measure
   (heat treatment, stress relief, protective coating, or alloy substitution)
   is on record; absent one, flag a rule violation. List all alloys in
   structural contact and check every pair against the galvanic-incompatibility
   table; flag any incompatible pair that lacks insulation or protective
   coating.
3. **Non-metallic path (§4.5.10):** retrieve TML and CVCM values from the
   outgassing test data sheet. Flag an exceedance of either limit. Confirm
   radiation qualification evidence covers the design dose level. Confirm
   the operational temperature range is documented and bounded.
4. **Composite path (§4.5.11):** retrieve the layup card. Flag an
   unsymmetric layup or an unbalanced layup. Confirm the allowables table
   carries a hygrothermal knockdown entry; flag its absence. If the fraction
   of 0° plies exceeds 0.80, confirm a micro-cracking assessment is on
   record; absent one, flag a susceptibility risk.
5. **Adhesive-bonded path (§4.5.12):** confirm the bond-line thickness
   specification falls within 0.05–0.50 mm; flag values outside this range.
   Confirm cleaning and primer steps are documented in the process card;
   flag absent steps. Confirm the joint analysis includes thermal-cycling
   loads; flag their absence. Compare calculated peel stress with the
   adhesive-system allowable; flag an exceedance.
6. Aggregate the findings across all applicable rule checks. The material
   or joint is not cleared for the structural baseline until the violation
   list is empty.

## Pitfalls

- Applying the strength rules from §4.5.3–§4.5.8 but skipping the
  material-class rules in §4.5.9–§4.5.12 entirely — both sets are
  mandatory; the strength analysis alone does not satisfy the material
  design rules.
- Treating an elongation value below 2 % as acceptable because the
  ultimate margin is positive — the ductility floor is a separate,
  unconditional gate; a brittle failure mode invalidates the
  factors-of-safety basis of the strength analysis.
- Omitting the hygrothermal knockdown factor from composite allowables
  because the mission environment is "mostly cold" — the knockdown is
  applied to the allowable, not derived from a predicted environment; its
  absence means the allowables table is non-compliant with §4.5.11
  regardless of the thermal prediction.
- Accepting an outgassing test data sheet with TML or CVCM values above
  the ECSS-Q-ST-70-02 limits on the grounds that the test article was a
  "representative coupon" — only a test article from the same lot and
  process can substitute; a coupon from a different batch requires its
  own test entry.
- Using the bond-line thickness specification as the process target without
  checking that it falls inside the adhesive manufacturer's qualified
  window — specifying a thickness the adhesive manufacturer has not
  qualified creates a latent design non-conformance even if the measured
  thickness satisfies the drawing.

## Behavior contract (gate 3)

The material-categorization, metal-rule, non-metallic-rule, composite-rule,
and adhesive-bonded-rule logic is exercised by the gate 3 contract test:
scripts/test_material_class_design_rules.py against
scripts/material_class_design_rules_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_material_class_design_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
