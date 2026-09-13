---
name: e20-antenna-design-baseline-definition
description: "Use when define the antenna design-baseline that has to be fixed early in the design cycle under ECSS-E-ST-20C clause 7.2.2.1: categorize the declared build into its antenna family (reflector, lens, array, horn, wire), confirm every mandatory element role of that family is present and that no element belongs to another family, check each selected technology is an admissible implementation of its element role and carries enough technology-readiness at the baseline-freeze review, verify the fixed performance-parameter set (frequency-band, peak-gain, half-power-beamwidth, axial-ratio, input-return-loss, polarization) is complete and inside its declared bounds, and flag anything still open at or after the freeze. Trigger: ecss, e-st-20-electrical-scope, e20-antenna-design-baseline-definition, antenna-design-baseline, antenna-family, radiating-element-set, technology-readiness-level, performance-parameter-set, baseline-freeze."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-design-baseline-definition, antenna-design-baseline, antenna-family, radiating-element-set, technology-readiness-level, performance-parameter-set, baseline-freeze]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical & Optical — Antenna Design-Baseline Definition (space-systems/ecss/e20-antenna-design-baseline-definition)

Use when the task is fixing the antenna design-baseline of ECSS-E-ST-20C
clause 7.2.2.1 -- choosing the antenna family, the elements that make it
up, the technology behind each element and the performance-parameter set,
early enough that the rest of the design cycle refines a frozen baseline
instead of re-opening it.

## Domain quick reference

- The baseline has four layers and they are fixed in order: family, then
  element set, then per-element technology, then the
  performance-parameter set. A later layer cannot be settled while an
  earlier one is open -- a technology choice means nothing until the
  element role it implements exists in the baseline.
- Families carry mandatory element roles. A reflector baseline needs a
  reflector-surface, a feed-chain and a support-structure; a lens
  baseline substitutes a lens-body; an array baseline needs a
  radiating-element, a beam-forming-network and a support-structure; a
  horn baseline needs the horn-aperture and its guided-wave-interface; a
  wire baseline needs the radiating-element and its ground-plane. An
  element that belongs to a different family is a categorization error,
  not an extra.
- Each element role admits a bounded set of implementation technologies
  (for example a reflector-surface as carbon-fibre-shell, metallic-shell
  or deployable-mesh). A technology outside that set signals the family
  or the role was categorized wrongly upstream.
- Technology-readiness is judged against the review at which the
  baseline freezes. Below that review, immature technology is a normal
  trade; at or after it, immature technology is a finding because the
  baseline it belongs to is meant to be fixed.
- The performance-parameter set fixed at the baseline is the numeric
  contract the later design work is verified against: frequency-band,
  peak-gain, half-power-beamwidth, axial-ratio, input-return-loss and
  the polarization scheme. Each numeric parameter carries declared
  bounds; the polarization is categorical and must name a recognized
  scheme.

## Workflow

1. Categorize the declared build into its antenna family. Reject an
   unrecognized build before any downstream check runs -- a wrong family
   invalidates every element and technology judgement after it.
2. Validate the element set against the family's mandatory roles: report
   each missing role, and each declared role that belongs to a different
   family. Reject an unknown or duplicated role as malformed input.
3. For every element, check the technology against the admissible set
   for its role, and check its technology-readiness against the
   baseline-freeze review.
4. Check the performance-parameter set: every required parameter
   present, every numeric value inside its declared bounds, the
   polarization a recognized scheme, and nothing carried in the set that
   does not belong to it.
5. List anything still open. At or after the freeze review, every open
   item is a finding; before it, open items are expected.
6. Roll the findings up. The baseline is defined when the list is empty
   at the freeze review -- not when a review chart declares it frozen.

## Pitfalls

- Freezing the performance-parameter set while the element set is still
  in trade. The numbers are only meaningful against a fixed family and
  element breakdown; frozen numbers over an open architecture get
  re-opened at the next review.
- Recording a technology choice against a role the family does not have
  -- it reads as progress in a review chart and disappears from the
  baseline when the element list is finally reconciled.
- Judging technology-readiness against today rather than against the
  freeze review. Maturity that is acceptable at a system requirements
  review is a finding at the freeze, and the check needs the milestone,
  not just the number.
- Accepting a parameter that only sits marginally outside its bounds
  because the excess "is rounding". A value assembled from stage
  contributions can land a few ULPs beyond a limit; the comparison
  absorbs that representation error, but a genuine excursion stays a
  finding and the limit itself never moves.
- Treating extra parameters carried in the baseline as harmless. A
  parameter outside the fixed set is not verified by anyone and quietly
  competes with the set that is.

## Behavior contract (gate 3)

The family-categorization, element-set, technology-admissibility,
technology-readiness, performance-parameter and baseline-freeze logic is
exercised by the gate 3 contract test:
scripts/test_e20_antenna_design_baseline_definition.py against
scripts/e20_antenna_design_baseline_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_antenna_design_baseline_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
