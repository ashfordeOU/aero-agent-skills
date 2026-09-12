---
name: fci-classification
description: "Use when determine whether a structural item qualifies as a fracture-critical item (FCI) under ECSS-E-ST-32-01C clause 6.2.2: evaluate each candidate item against the pressurized-system criterion, the fracture-limited life item (FLLI) criterion, the NDT-limited criterion, and the composite primary-structure criterion; assign the applicable FCI category or none; and produce a determination with rationale traceable to the failure-consequence level (catastrophic, critical, or non-critical). Trigger: ecss, e-st-32-structures-scope, fracture-critical-item, fci, flli, pressure-vessel, composites, ndt-limited, fracture-control."
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
  tags: [ecss, e-st-32-structures-scope, fracture-critical-item, fci, flli, pressure-vessel, composites, ndt-limited, fracture-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture-Critical Item (FCI) Determination (space-systems/ecss/fci-classification)

Use when the task is to determine whether individual structural items on a
space hardware assembly are fracture-critical items (FCIs) under
ECSS-E-ST-32-01C §6.2.2, and to assign each item to its applicable FCI
category so that the correct fracture-control obligations follow.

## Domain quick reference

- ECSS-E-ST-32-01C §6.2.2 defines an FCI as any structural item whose
  fracture or separation could directly cause a catastrophic or critical
  failure consequence. Four distinct criteria trigger FCI status;
  an item satisfying any one of them is an FCI.
- **Pressurized system criterion**: a pressure vessel, pressurized line, or
  pressurized fitting whose burst or leak leads to a catastrophic or
  critical consequence. The pressure boundary itself is the item under
  evaluation, not the surrounding structure.
- **Fracture-limited life item (FLLI) criterion**: an item whose service life
  is bounded by the crack-growth life rather than conventional fatigue life,
  and whose fracture leads to a catastrophic or critical consequence. FLLI
  items require an explicit fracture-mechanics life calculation; a
  stress-life or strain-life analysis alone does not satisfy the FLLI
  obligation.
- **NDT-limited criterion**: an item that cannot be effectively inspected by
  conventional non-destructive testing methods (geometry, material, or
  access prevents reliable flaw detection), and whose fracture leads to a
  catastrophic or critical consequence. Because flaws cannot be bounded by
  inspection, an assumed initial flaw per §6.3.2 is mandatory.
- **Composite primary-structure criterion**: a load-carrying composite item
  in the primary structural load path whose fracture leads to a catastrophic
  or critical consequence. Secondary composite structures (fairings, covers,
  non-load-path panels) do not meet this criterion unless they independently
  satisfy another criterion.
- Failure consequence categories:
  - *catastrophic* — loss of crew, vehicle, or range-safety impact.
  - *critical* — loss of mission or major mission system.
  - *non-critical* — tolerable degradation; no FCI criteria are triggered
    for non-critical items even when other properties apply.
- An item may satisfy multiple criteria simultaneously; all applicable
  categories are recorded and each imposes its own fracture-control
  obligations.

## Workflow

1. Inventory every structural item at the assembly level and record:
   item identifier, item type (pressure vessel, pressurized line,
   pressurized fitting, composite primary, composite secondary, metallic
   primary, metallic secondary, weld, fastener, other), failure consequence
   (catastrophic / critical / non-critical), NDT accessibility (can
   conventional NDT bound flaw size?), and whether the design life is
   controlled by crack growth (FLLI flag).
2. Apply the pressurized-system criterion: for each item typed as a
   pressure vessel, pressurized line, or pressurized fitting, check whether
   the failure consequence is catastrophic or critical. If yes, assign
   category PRESSURE_VESSEL_OR_LINE.
3. Apply the FLLI criterion: for each item with the life-limited-by-fracture
   flag set, check whether the consequence is catastrophic or critical. If
   yes, assign category FLLI and require a crack-growth life analysis per
   §6.4.
4. Apply the NDT-limited criterion: for each item where conventional NDT
   cannot reliably bound the flaw size, check whether the consequence is
   catastrophic or critical. If yes, assign category NDT_LIMITED and require
   an assumed initial flaw per §6.3.2.
5. Apply the composite primary-structure criterion: for each item typed as
   composite_primary, check whether the consequence is catastrophic or
   critical. If yes, assign category COMPOSITE_PRIMARY.
6. Collect all assigned categories per item. An item with at least one
   category is an FCI; an item with no categories is not fracture-critical
   at this consequence level.
7. For each FCI, record the determination rationale referencing which
   criterion was met and the consequence level so that the fracture-control
   plan can be traced to the input data.

## Pitfalls

- Applying fracture-control obligations to non-critical items because they
  are pressurized or NDT-limited — consequence level is a gate condition;
  a non-critical item does not become an FCI regardless of its other
  properties.
- Treating composite secondary structures (non-load-path panels, covers) as
  meeting the composite primary-structure criterion — only items in the
  primary structural load path satisfy that criterion; secondary composite
  items must independently meet another criterion to be FCIs.
- Omitting the FLLI flag because a fatigue analysis already exists — a
  fatigue analysis does not bound crack growth; an item is an FLLI whenever
  fracture mechanics controls its life, even if a fatigue analysis is also
  present.
- Assuming NDT accessibility without verification — if inspection access or
  material properties have not been confirmed to allow reliable flaw-size
  bounding, the item must be treated as NDT-limited.
- Recording only the first triggered criterion and stopping — all applicable
  criteria must be checked because each may impose distinct fracture-control
  obligations.

## Behavior contract (gate 3)

The pressurized-system, FLLI, NDT-limited, and composite primary-structure
criterion logic is exercised by the gate 3 contract test:
scripts/test_fci_classification.py against
scripts/fci_classification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fci_classification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
