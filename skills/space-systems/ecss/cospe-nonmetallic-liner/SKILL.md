---
name: cospe-nonmetallic-liner
description: "Use when assess the structural integrity of a composite overwrapped pressure vessel with a homogeneous non-metallic liner per ECSS-E-ST-32C clause 4.6.3: categorize the liner material family, verify the proof pressure and burst pressure factors against the maximum allowable working pressure, check liner strain at proof pressure against the liner allowable strain, validate the overwrap fiber volume fraction, and apply environmental degradation to the effective burst margin. A vessel assessment is not compliant until all margin checks pass. Trigger: ecss, e-st-32-structures-scope, cospe, composite-overwrapped-pressure-vessel, nonmetallic-liner, burst-factor, proof-factor, strain-compatibility."
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
  tags: [ecss, e-st-32-structures-scope, cospe, composite-overwrapped-pressure-vessel, nonmetallic-liner, burst-factor, proof-factor, strain-compatibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COSPE with Homogeneous Non-Metallic Liner (space-systems/ecss/cospe-nonmetallic-liner)

Use when the task is the structural assessment of a composite
overwrapped pressure vessel with a homogeneous non-metallic liner
under ECSS-E-ST-32C clause 4.6.3 — checking that liner material
family, proof and burst margins, liner strain at proof, overwrap
fiber volume fraction, and environmental degradation factors are
all within acceptable bounds before the vessel is considered
structurally compliant.

## Domain quick reference

- ECSS-E-ST-32C clause 4.6.3 covers COSPE vessels whose liner is a
  homogeneous non-metallic material (polymer, elastomer, thermoplastic,
  thermoset, or fluoropolymer). The liner carries the leak-tight
  pressure boundary; the composite overwrap provides the primary
  structural load path. The two must be strain-compatible at proof
  pressure: the liner strain at proof must not exceed its own allowable
  strain.

- Proof and burst pressure factors are the ratio of proof or burst
  pressure to the maximum allowable working pressure (MAWP). The
  minimum proof factor is 1.1 and the minimum burst factor is 1.5.
  Environmental degradation (moisture absorption, thermal cycling,
  UV, chemical exposure) reduces effective burst strength; a
  degradation factor (0 < f ≤ 1.0) is multiplied against the burst
  pressure before the effective burst factor is computed.

- The overwrap fiber volume fraction (FVF) must lie within defined
  bounds (0.50 to 0.70 inclusive). A value below the lower bound
  indicates insufficient fiber density; a value above the upper bound
  indicates resin starvation and elevated void content. Both
  conditions are structural risks and are flagged independently.

- A vessel is not structurally compliant until every margin check
  passes: proof factor, effective burst factor, liner strain
  compatibility, and FVF.

## Workflow

1. Confirm the liner material family is a recognized non-metallic
   category. Reject any unrecognized liner material before the rest of
   the assessment proceeds.
2. Check the proof pressure factor: divide proof pressure by MAWP and
   verify the result is at least 1.1. Flag a shortfall.
3. Apply the environmental degradation factor to the burst pressure to
   obtain the effective burst strength. Divide by MAWP and verify the
   effective factor is at least 1.5. Flag a shortfall.
4. Check liner strain compatibility: verify the liner strain at proof
   pressure does not exceed the liner allowable strain. Flag an
   exceedance.
5. Check the overwrap fiber volume fraction: verify it lies between
   0.50 and 0.70 inclusive. Flag values below the lower bound and
   above the upper bound separately.
6. Aggregate all findings. The vessel is compliant only when every
   finding list is empty.

## Pitfalls

- Omitting the degradation factor and using raw burst pressure to
  compute the burst factor — environmental exposure reduces effective
  burst strength; using the undegraded value overstates margin and
  may allow a non-compliant vessel to appear compliant.
- Treating a missing or unrecognized liner material entry as a pass —
  an unrecognized liner type is outside the validated range and must
  be rejected before any margin check runs.
- Using MAWP as zero or negative — all factor calculations divide by
  MAWP; a zero or negative MAWP is a data error and must be caught
  before computation proceeds.
- Checking FVF against only one bound — both a low FVF (fiber
  starvation) and a high FVF (resin starvation with elevated void
  content) are structural risks and both bounds must be verified.
- Applying the degradation factor greater than 1.0 — a degradation
  factor above 1.0 would imply the vessel gains strength from
  environmental exposure, which is physically inadmissible; a value
  outside (0, 1.0] must be rejected.

## Behavior contract (gate 3)

The liner categorization, proof factor, burst factor, liner strain
compatibility, and FVF checks are exercised by the gate 3 contract
test: scripts/test_cospe_nonmetallic_liner.py against
scripts/cospe_nonmetallic_liner_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_cospe_nonmetallic_liner.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
