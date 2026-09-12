---
name: material-selection
description: "Use when determine which structural materials are suitable for a spacecraft application under ECSS-E-ST-32 section 4.5.6: categorize each candidate by family (metallic, composite, ceramic, polymer), evaluate stress-corrosion susceptibility from the ECSS-Q-ST-70-32C rating matrix (1=immune to 4=high—reject or apply protective design above rating 2), assess space environment compatibility against orbital hazards (atomic oxygen, radiation dose, thermal cycling, outgassing), and derive an ACCEPTABLE, CONDITIONAL, or NOT_ACCEPTABLE verdict per candidate. Trigger: ecss, e-st-32-structures-scope, material-selection, stress-corrosion, q-st-70-32, space-environment, structural-material."
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
  tags: [ecss, e-st-32-structures-scope, material-selection, stress-corrosion, q-st-70-32, space-environment, structural-material]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Material Selection (space-systems/ecss/material-selection)

Use when the task is material selection for spacecraft structural components under
ECSS-E-ST-32 §4.5.6: categorizing each candidate by material family, evaluating
stress-corrosion susceptibility for the ground and in-service environments (linked to
ECSS-Q-ST-70-32C), checking compatibility with active space environment hazards, and
reaching an ACCEPTABLE, CONDITIONAL, or NOT_ACCEPTABLE verdict before the structural
analysis is locked.

## Domain quick reference

- Section 4.5.6 of ECSS-E-ST-32 requires material selection to clear three layers:
  mechanical properties vs applied loads, environmental compatibility in the service
  environment, and stress-corrosion susceptibility referenced against ECSS-Q-ST-70-32C.
  Each layer is a gate — failing any one rejects or conditions the candidate.
- Materials are categorized into four families: metallic, composite, ceramic, and
  polymer. Each family carries a distinct set of space-environment concerns. Metallic
  materials carry a mandatory stress-corrosion check for every ground environment where
  moisture or electrolyte may be present. Composite materials require outgassing and
  CTE-mismatch verification. Polymers require outgassing and radiation-dose limits.
  Ceramics require low-temperature fracture toughness verification.
- Stress-corrosion susceptibility is rated 1 to 4 (1=immune, 2=low, 3=medium,
  4=high) per the ECSS-Q-ST-70-32C material/environment lookup. A rating above 2
  is not passable without design action: rating 3 requires a protective coating or
  design modification; rating 4 requires material substitution.
- Space environment hazard checks cover four factors: atomic oxygen (LEO below
  ~700 km), radiation dose (missions beyond the magnetosphere and high-inclination
  LEO), thermal cycling (structures bonding dissimilar-CTE materials), and outgassing
  (all materials adjacent to optics, thermal control surfaces, or solar cells). Each
  factor flags the affected material family for verification or direct rejection.

## Workflow

1. List every candidate material with its identifier and stated family. Reject any
   candidate whose family is not in {metallic, composite, ceramic, polymer} before
   proceeding — an unknown or ambiguous family is a data gap, not a default pass.
2. For each metallic candidate, look up the stress-corrosion susceptibility rating
   (ECSS-Q-ST-70-32C) for the applicable ground and in-service environments. Record
   the rating and required action: rating 1–2 → no action; rating 3 → apply
   protective coating or redesign; rating 4 → substitute material.
3. For each candidate in any family, check the active space environment hazards for
   the mission profile. Map each hazard to the affected family and record the severity:
   "flag" (requires resolution before the selection is accepted) or "verify" (requires
   confirmation data but does not block alone).
4. Aggregate the stress-corrosion and space-environment findings per candidate and
   assign a verdict:
   - ACCEPTABLE: stress-corrosion rating ≤ 2 and no "flag" or open "verify" findings.
   - CONDITIONAL: stress-corrosion rating = 3, or at least one "verify" finding is
     present, or at least one "flag" finding exists but the candidate is not rating 4.
   - NOT_ACCEPTABLE: stress-corrosion rating = 4 (substitution required regardless
     of other findings).
5. Rank candidates: ACCEPTABLE first, then CONDITIONAL, then NOT_ACCEPTABLE. When
   multiple ACCEPTABLE candidates exist, the selection narrows on mass and secondary
   criteria outside this procedure's scope.
6. Document the verdict and all findings in the material selection justification
   record that feeds the structural analysis (ECSS-E-ST-32 §4.5.6 traceability
   requirement).

## Pitfalls

- Checking stress-corrosion only against the in-service (vacuum) environment and
  skipping the humid or salt-laden ground-handling environment — many structural
  failures trace to ground-handling corrosion that propagated undetected into flight.
- Accepting a rating 3 candidate without a recorded protective measure — the
  ECSS-Q-ST-70-32C linkage is not satisfied until the specific coating or design
  modification is captured in the material selection record.
- Treating outgassing as relevant only to polymer materials — composite matrix resins
  also outgas and must be verified when adjacent to contamination-sensitive surfaces.
- Conflating "no space-environment hazard flag" with "space-compatible" — if no
  hazards are listed for a mission, the hazard list is incomplete, not the environment
  benign. Always derive the active hazard set from the mission orbit first.

## Behavior contract (gate 3)

The categorization, stress-corrosion lookup, space-environment compatibility check,
evaluation, and selection logic is exercised by the gate 3 contract test:
scripts/test_material_selection.py against scripts/material_selection_logic.py
(stdlib unittest, offline). Run:
  python3 scripts/test_material_selection.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the standard and clause as
  anchor and paraphrase into procedure — no verbatim text.
- compliance: STANDARDS-REF, gated: false.
- ECSS-E-ST-32C §4.5.6 — material selection vs loads and environment.
- ECSS-Q-ST-70-32C — stress corrosion test methods for metallic materials (rating
  matrix source).
