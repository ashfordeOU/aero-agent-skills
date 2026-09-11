---
name: e1006-char-tolerance
description: "Use when verify that each quantitative performance characteristic in
  a system requirement set carries an explicit tolerance alongside its nominal value,
  per ECSS-E-ST-10C §8.2.10: for each quantitative requirement, confirm a nominal
  value is present, a plus-tolerance and minus-tolerance are both stated (symmetric
  or asymmetric), and tolerance magnitudes are non-negative. Qualitative requirements
  are out of scope. Trigger: ecss, e-st-10c, e-st-10-system-scope, characteristic-tolerance,
  quantitative-requirements, tolerance-verification, requirements-completeness."
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
  tags: [ecss, e-st-10-system-scope, characteristic-tolerance, quantitative-requirements, tolerance-verification, requirements-completeness, performance-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Characteristic Tolerance Check — Quantitative Requirements (space-systems/ecss/e1006-char-tolerance)

Use when the task is to verify that every quantitative performance
characteristic in a system requirements document carries an explicit
tolerance per ECSS-E-ST-10C §8.2.10. A quantitative requirement states
a numeric performance target; that target is only verifiable when the
allowable deviation — the tolerance — is also on record. This leaf
checks that every such requirement records a nominal value, a
plus-tolerance, and a minus-tolerance, and that both tolerance
magnitudes are non-negative.

## Domain quick reference

- §8.2.10 distinguishes two kinds of requirements: quantitative
  (a numeric value is stated, e.g. mass ≤ 120 kg, frequency
  28.5 ± 0.1 MHz) and qualitative (no numeric value, e.g. the
  interface shall be compatible with the ground support equipment).
  Only quantitative requirements are in scope for the tolerance check;
  qualitative requirements need no tolerance.
- A complete tolerance record has three parts: the nominal value, the
  plus-tolerance (maximum permitted excess above nominal), and the
  minus-tolerance (maximum permitted shortfall below nominal). The two
  magnitudes may be equal (symmetric, written ± T) or unequal
  (asymmetric, written +T₁/−T₂). Both forms are acceptable provided
  the magnitudes are non-negative.
- A bound-only statement ("value shall not exceed 120 kg") is not a
  complete tolerance record unless the implicit nominal and the
  opposite bound are also on record or derivable from adjacent
  requirements. Flag such requirements for clarification rather than
  treating them as compliant.
- Tolerance magnitudes of exactly zero are permitted when a
  requirement is point-exact (e.g. a discrete frequency channel),
  provided the design can realistically achieve it; the tolerance-
  completeness check does not evaluate engineering achievability.

## Workflow

1. Inventory every requirement in the set. For each requirement,
   determine whether it is quantitative (a numeric performance target
   is stated) or qualitative (no numeric target). Skip qualitative
   requirements — they do not need a tolerance.
2. For each quantitative requirement, confirm a nominal value is
   recorded. A requirement with no nominal is incomplete regardless
   of tolerances; record it as a finding before proceeding.
3. Check that both a plus-tolerance and a minus-tolerance are on
   record for the requirement. A requirement missing either or both
   tolerance halves is a finding; report which half (or halves) are
   absent.
4. Confirm that each tolerance magnitude is non-negative. A negative
   value is a data-entry error; flag it with the stored value.
5. If a requirement uses a bound-only form (upper bound only, or lower
   bound only), investigate whether the complementary bound is
   available to derive the symmetric form. If not, flag it as
   incomplete.
6. Aggregate per-requirement results. The requirements set is
   tolerance-complete only when every quantitative requirement passes
   steps 2–5 with no findings.

## Pitfalls

- Treating a one-sided bound statement as tolerance-complete — an
  upper-bound-only requirement lacks a stated lower bound and nominal,
  which means the allowable working range cannot be determined.
  Flag it; do not infer a zero lower bound without explicit authority.
- Accepting a symmetric ± T entry without verifying sign — if the
  stored T is negative, the record is corrupt even though both halves
  are present. The non-negativity check (step 4) must run on every
  record, including symmetric ones.
- Skipping the qualitative-vs-quantitative split and running the
  tolerance check on all requirements — qualitative requirements have
  no numeric target and cannot carry a tolerance; treating their
  absence of tolerance as a finding inflates the finding count and
  masks real gaps.
- Treating zero tolerance as invalid — a point-exact requirement has
  plus-tolerance = 0 and minus-tolerance = 0, and both fields are
  legitimately present. Zero tolerance is a design constraint, not an
  incomplete record.
- Merging the plus and minus fields into a single ± value in the data
  model — asymmetric tolerances are common in space-systems
  requirements and must be stored separately to preserve the
  engineering intent.

## Behavior contract (gate 3)

The quantitative-check, tolerance-completeness, non-negativity, and
bounds-derivation logic is exercised by the gate 3 contract test:
scripts/test_e1006_char_tolerance.py against
scripts/e1006_char_tolerance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_char_tolerance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
