---
name: damage-tolerance-functionality
description: "Use when assess damage-tolerance design intent for a structural element under ECSS-E-ST-32C clause 4.3.8: categorize the structure into the safe-life or fail-safe approach, bound crack growth against the critical flaw size across the design service life, verify that a damaged structure retains sufficient residual strength, and determine whether the applied stress-intensity ratio triggers mandatory fracture control per ECSS-E-ST-32-01C. Apply after the load environment is established and before the fracture-control plan is drafted. Trigger: ecss, e-st-32-structures-scope, damage-tolerance, crack-growth, residual-strength, safe-life, fail-safe, fracture-control."
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
  tags: [ecss, e-st-32-structures-scope, damage-tolerance, crack-growth, residual-strength, safe-life, fail-safe, fracture-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Damage Tolerance Functionality (space-systems/ecss/damage-tolerance-functionality)

Use when the task is to assess the damage-tolerance design intent for a structural element per ECSS-E-ST-32C clause 4.3.8 — categorizing the approach, bounding crack growth, checking residual strength, and flagging the fracture-control interface to ECSS-E-ST-32-01C.

## Domain quick reference

- Clause 4.3.8 recognizes two damage-tolerance approaches for each structural element. In the safe-life approach the element is designed to carry all loads for the entire service life without a detectable crack growing to failure; this requires bounding the crack size at end of life against the critical flaw size. In the fail-safe approach the element relies on load-path redundancy so that after a partial failure (loss of one load path) the surviving paths can still carry a specified minimum load without general collapse.
- Crack growth in the safe-life path is assessed by propagating a postulated initial flaw under the design load spectrum over the full service life and comparing the resulting crack size to the fracture-critical size for the material and geometry. The initial flaw size is normally taken as the maximum undetectable flaw for the inspection method used.
- Residual strength applies to both approaches: a damaged structure must retain at least the required fraction (typically 70 % of design-ultimate load as a minimum) of its strength after sustaining the design damage state. An element that passes the crack-growth check but fails the residual-strength check is not compliant.
- The fracture-control interface is triggered when the applied stress-intensity factor K approaches the material fracture toughness K_Ic above a defined ratio threshold. Elements above that threshold require a formal fracture-control plan per ECSS-E-ST-32-01C; the damage-tolerance assessment flags the need but does not itself produce the fracture-control plan.
- Safe-life and fail-safe are not interchangeable: a single load path with no redundancy cannot satisfy fail-safe requirements regardless of its residual-strength margin.

## Workflow

1. Identify every structural element subject to damage-tolerance requirements and categorize each one as safe-life or fail-safe. Reject any element whose approach cannot be unambiguously placed in one category before proceeding.
2. For each safe-life element, obtain the postulated initial flaw size (from the non-destructive inspection capability baseline), the crack growth rate under the design spectrum, and the number of load cycles over the service life. Propagate the crack forward to end-of-life and compare the result to the critical flaw size. Flag any element whose end-of-life crack meets or exceeds the critical size.
3. For each fail-safe element, verify that at least two independent load paths exist. Then confirm that after the loss of the worst-case single path, the surviving paths collectively carry the design-ultimate load without exceedance. Flag any element where the surviving capacity falls short.
4. For every element (both approaches), check that the residual strength after the design damage state meets the required fraction of the design-ultimate load. Flag an exceedance or a missing residual-strength budget.
5. For every element, compute the ratio of the applied stress-intensity factor K to the material fracture toughness K_Ic. Flag any element whose ratio meets or exceeds the fracture-control trigger threshold and record that a fracture-control plan per ECSS-E-ST-32-01C is required.
6. Aggregate findings per element. An element is compliant only when all four checks (approach validity, crack-growth or redundancy, residual strength, and fracture-control flag) return no finding.

## Pitfalls

- Treating the initial flaw size as zero or negligible — ECSS-E-ST-32C requires that a specific postulated flaw tied to the inspection method's detectability limit be used; a zero-flaw assumption is only valid if the method can detect cracks of any size, which is never achievable in practice.
- Accepting a fail-safe designation for a monolithic structure with no physical load-path redundancy — fail-safe requires that at least two independent load paths exist; a structure that redistributes stress internally within one continuous member is not fail-safe by that redistribution alone.
- Conflating the crack-growth check with the residual-strength check — an element can have a bounded end-of-life crack that is still large enough to reduce the net-section capacity below the residual-strength requirement; both checks must be run independently.
- Omitting the fracture-control flag when K / K_Ic is near the threshold — a small margin in K ratio can flip the fracture-control requirement; use the actual computed ratio rather than an estimate, and when the ratio is close to the threshold apply engineering judgment with explicit documentation.
- Skipping the fail-safe check for an element categorized as fail-safe — the redundancy check and the residual-strength check are separate steps; passing one does not imply passing the other.

## Behavior contract (gate 3)

The approach-categorization, crack-growth, residual-strength, fail-safe redundancy, and fracture-control interface logic is exercised by the gate 3 contract test: scripts/test_damage_tolerance_functionality.py against scripts/damage_tolerance_functionality_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_damage_tolerance_functionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
