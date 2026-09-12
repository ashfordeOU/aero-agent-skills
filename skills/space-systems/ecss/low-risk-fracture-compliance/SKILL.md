---
name: low-risk-fracture-compliance
description: "Use when determine low-risk fracture compliance for a metal structural item under ECSS E-ST-32C clause 6.3.5: check whether the item satisfies the load-limited criterion (maximum gross-section stress at limit load ≤ 60 % of material yield strength) or the non-fracture-critical criterion (item failure results only in contained or non-critical consequences), establish the qualifying compliance path, and confirm no full fracture mechanics analysis is needed. Items whose failure consequence is fracture-critical, or whose gross-section stress exceeds the load-limited threshold, are excluded from the low-risk path and must follow the full fracture control procedure. Trigger: ecss, e-st-32-structures-scope, fracture-control, low-risk-fracture, load-limited, non-fracture-critical, structural-metals, compliance-path, damage-tolerance."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, low-risk-fracture, load-limited, non-fracture-critical, structural-metals, compliance-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Low-Risk Fracture Item Compliance (space-systems/ecss/low-risk-fracture-compliance)

Use when the task is to determine whether a metal structural item qualifies for the
low-risk fracture compliance path under ECSS E-ST-32C clause 6.3.5 — verifying either
the load-limited stress criterion or the non-fracture-critical consequence criterion,
and establishing which path forms the compliance basis.

## Domain quick reference

- Clause 6.3.5 defines two routes by which an item avoids full fracture control
  analysis: the load-limited criterion (maximum gross-section stress at limit load
  is at most 60 % of material yield strength, making crack growth a non-credible
  driver) and the non-fracture-critical criterion (even total fracture would carry
  only contained or non-critical consequences).
- An item is categorized as load-limited when its stress ratio
  (max stress / yield strength) is ≤ 0.60. This threshold excludes items where
  fatigue or stress corrosion cracking could drive life-limiting crack growth.
- An item is categorized as non-fracture-critical when its failure consequence
  falls into an accepted group: contained failure, redundant load path,
  non-structural function, cosmetic role, or mission-non-critical function.
- A fracture-critical consequence (loss of crew safety, loss of mission, primary
  structure in a single-load-path, pressure vessel failure, life support failure)
  is an absolute disqualifier: the item must follow the full fracture control
  procedure regardless of stress level.
- Once low-risk qualification is established on either path, no damage-tolerance
  analysis, no crack growth calculation, and no NDE fracture screening are required.
  The compliance record documents the qualifying path and the supporting data.

## Workflow

1. Collect the item data: name, material yield strength, maximum gross-section stress
   at limit load (for load-limited assessment) and/or the identified failure consequence
   category (for the non-fracture-critical assessment).
2. If a failure consequence is provided, evaluate it first. If the consequence is
   fracture-critical, stop — the item is disqualified from the low-risk path and
   the full fracture control procedure applies.
3. If stress data are available, compute the stress ratio (max stress / yield strength)
   and compare against the threshold (default 0.60). A ratio ≤ threshold means the
   load-limited criterion is met.
4. Determine the compliance path: load-limited if the stress criterion passes;
   non-fracture-critical if the consequence criterion passes and the stress criterion
   does not (or stress data are absent). If neither criterion passes, the item does
   not qualify as low-risk.
5. Document the qualifying path, supporting values (stress ratio and yield strength
   for load-limited; consequence category for non-fracture-critical), and any
   findings (threshold exceedance, missing data).
6. For a set of items, aggregate the results and flag the assessment as fully compliant
   only when every item qualifies on a documented path with no errors.

## Pitfalls

- Applying a gross-section stress limit without verifying it is the maximum stress at
  limit load — local stress concentrations are not the check here, but the limit-load
  gross-section value must be the worst-case envelope, not a nominal service value.
- Treating an unrecognized failure consequence as acceptable by default — the procedure
  raises an error on unrecognized categories rather than defaulting to non-fracture-critical,
  because an undocumented consequence is a missing analysis, not a pass.
- Allowing a partial data set (stress data only, no consequence) to mask a fracture-critical
  item — the workflow evaluates consequence first and short-circuits to disqualification;
  if consequence data are missing and stress data alone are provided, the only available
  path is load-limited.
- Confusing low-risk qualification with full fracture control programme compliance —
  this procedure establishes that a specific item is exempt from fracture mechanics
  analysis, not that the overall fracture control programme is complete.

## Behavior contract (gate 3)

The load-limited criterion, non-fracture-critical consequence check, item qualification,
and multi-item compliance assessment are exercised by the gate 3 contract test:
scripts/test_low_risk_fracture_compliance.py against
scripts/low_risk_fracture_compliance_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_low_risk_fracture_compliance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
