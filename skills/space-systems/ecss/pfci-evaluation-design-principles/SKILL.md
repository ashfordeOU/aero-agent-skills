---
name: pfci-evaluation-design-principles
description: "Use when evaluate the damage-tolerance design principle (safe life, fail-safe, or low-risk fracture) for each Potentially Fracture Critical Item under ECSS-E-ST-32C clause 6.2.1: check each PFCI against low-risk fracture criteria (net section stress and cross-section thickness thresholds), assign fail-safe where redundant load paths or in-service inspectability apply, and assign safe life to single-path non-inspectable items that require fracture life demonstration. Trigger: ecss, e-st-32-structures-scope, fracture-control, pfci, safe-life, fail-safe, low-risk-fracture, damage-tolerance, design-principle."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, pfci, safe-life, fail-safe, low-risk-fracture, damage-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — PFCI Evaluation: Damage-Tolerance Design Principles (space-systems/ecss/pfci-evaluation-design-principles)

Use when the task is selecting and documenting the damage-tolerance design
principle for each Potentially Fracture Critical Item (PFCI) per
ECSS-E-ST-32C clause 6.2.1 — choosing between safe life, fail-safe, and
low-risk fracture, and recording the rationale for each assignment.

## Domain quick reference

- Clause 6.2.1 defines three permitted damage-tolerance design principles
  for PFCIs. Each PFCI must be assigned exactly one principle before
  fracture control analysis begins.
- **Low-risk fracture**: the item is excluded from detailed fracture
  analysis when its net section stress under limit load falls at or below
  the low-risk stress threshold AND its governing cross-section thickness
  falls at or below the low-risk thickness threshold. Both criteria must be
  satisfied simultaneously. An item that meets only one criterion is not
  eligible for this designation.
- **Fail-safe**: the item must maintain structural integrity after partial
  failure. Eligibility requires either redundant load paths (so that loss
  of one load path leaves a surviving path able to carry limit load) or
  in-service inspectability (so that damage is detectable and correctable
  before it becomes critical). Either condition alone is sufficient;
  together they strengthen the argument. An inspection plan with defined
  intervals must accompany any fail-safe assignment.
- **Safe life**: the item must be shown by analysis and/or test to sustain
  the required service life — from an assumed initial flaw size — without
  the crack growing to a critical size under worst-case loading. This
  principle applies to any PFCI that does not meet the low-risk fracture
  criteria and is neither redundant nor inspectable; it carries the most
  stringent demonstration burden.

## Workflow

1. Identify the PFCI and retrieve its limit-load net section stress
   (MPa) and its governing cross-section thickness (mm). Reject any item
   with a zero or negative thickness before it enters the selection logic.
2. Test for low-risk fracture eligibility: check net section stress against
   the low-risk stress threshold and cross-section thickness against the
   low-risk thickness threshold. If both are at or below their respective
   thresholds, assign low-risk fracture and record both numeric values as
   the rationale. Stop here for this item.
3. If the item does not meet both low-risk criteria, record a finding for
   each threshold that is exceeded. Then determine whether the item has
   redundant load paths (multiple parallel structural members each capable
   of carrying limit load independently) or is accessible for inspection
   during the service life.
4. If either condition in step 3 holds, assign fail-safe. Document which
   condition applies (redundant paths, inspectable, or both) and attach
   the required inspection interval plan.
5. If neither condition holds, assign safe life. Document that the item is
   a single-load-path structure that is not inspectable, and flag that a
   fracture life demonstration (analysis or test) is required.
6. After assigning a principle to every PFCI, aggregate the set: count
   items per principle, list any items that generated threshold-exceeded
   findings, and confirm that every item has a principle and a rationale
   on record.

## Pitfalls

- Assigning low-risk fracture when only one threshold is satisfied. The
  ECSS clause requires both the stress criterion and the thickness
  criterion to be met simultaneously; passing one alone does not
  reduce fracture risk sufficiently for the exemption.
- Assigning fail-safe without an inspection plan. Fail-safe relies on
  the assumption that damage is detected and removed; if no inspection
  interval is defined, the structural argument is incomplete regardless
  of how many load paths exist.
- Leaving the principle field blank and treating the omission as safe life
  by default. An unassigned PFCI has no documented rationale, which is
  itself a compliance gap distinct from a wrong assignment.
- Applying the low-risk thresholds to gross section stress rather than net
  section stress. The net section value (accounting for holes, cutouts,
  and stress concentrations) is the governing quantity; using the lower
  gross value underestimates the fracture driving force.

## Behavior contract (gate 3)

The low-risk eligibility check, fail-safe condition evaluation, safe-life
default assignment, threshold-finding generation, and set-aggregation logic
are exercised by the gate 3 contract test:
scripts/test_pfci_evaluation_design_principles.py against
scripts/pfci_evaluation_design_principles_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_pfci_evaluation_design_principles.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
