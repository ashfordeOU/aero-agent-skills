---
name: mmpsd-allowables
description: "Use when computing statistically based metallic material design allowables per MMPDS: determine A-basis and B-basis values from coupon test data, run the one-sided normal tolerance k-factor approximation, and validate that derived allowables sit below the sample mean. The skill applies minimum sample counts, confidence/content conventions, and sanity checks on design values, following the statistical approach of MMPDS and its MIL-HDBK-5 heritage. Trigger: allowables, a-basis, b-basis, k-factor, metallic materials, sample statistics, design values, mil-hdbk-5, test specimens."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [allowables, a-basis, b-basis, k-factor, metallic-materials, sample-statistics, design-values, mil-hdbk-5, test-specimens]
  version: 0.1.0
  author: Aero Agent Skills
---

# MMPDS Metallic Allowables (structures/materials/mmpsd-allowables)

Use when the task is statistically based metallic material design
allowables: A-basis and B-basis values from coupon test samples,
one-sided normal tolerance k-factors, and design-value sanity
checks.

## Domain quick reference

- A-basis: 95% confidence that 99% of the population exceeds the
  value; B-basis: 95% confidence that 90% exceeds the value.
- One-sided normal tolerance k-factor (Owen/Odeh approximation):
  z_c = 1.6448536269514722 (0.95 confidence); z_p = 2.3263478740408408
  for A-basis content or 1.2815515655446004 for B-basis;
  a = 1 - z_c^2/(2(n-1)); b = z_p^2 - z_c^2/n;
  k = (z_p + sqrt(z_p^2 - a*b))/a.
- Allowable = sample mean - k * sample standard deviation.
- Common minimum samples: 10 for A-basis, 6 for B-basis; verify
  against the current MMPDS edition.
- MMPDS is the successor to MIL-HDBK-5 for metallic allowables.

## Workflow

1. Gather the coupon test sample for the material, condition, and
   property of interest; check the sample count against
   min_samples.
2. Compute the k-factor with k_factor_one_sided for the basis.
3. Compute the allowable with allowable_from_sample.
4. Sanity-check the result with design_value_sanity: the allowable
   must be positive and below the sample mean.
5. Confirm the deterministic checks with the contract test
   scripts/test_mmpsd.py.

## Pitfalls

- Using a B-basis k-factor when A-basis is required (A is always
  lower/more conservative).
- Computing k-factors from samples below the minimum count.
- Applying the normal tolerance method to skewed or multimodal
  data without transformation.
- Copying design-value tables from MMPDS; derive values from the
  sample statistics instead.

## Behavior contract (gate 3)

The k-factor, sample, and sanity-check logic is exercised by the
gate 3 contract test: scripts/test_mmpsd.py against
scripts/mmpsd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_mmpsd.py

## Compliance

- Standards referenced, not reproduced: MMPDS is proprietary
  (SAE, successor to public-domain MIL-HDBK-5); name + paraphrase
  + link only per standards-map.yaml and brief 06; never
  reproduce design-value tables.
- compliance: STANDARDS-REF, gated: false.
