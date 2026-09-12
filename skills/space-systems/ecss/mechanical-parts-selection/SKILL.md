---
name: mechanical-parts-selection
description: "Use when evaluate candidate mechanical parts — fasteners, inserts, and bearings — for inclusion in a spacecraft structural assembly per ECSS-E-ST-32C clause 4.5.7: categorize each part as fastener, insert, or bearing; verify it appears on a qualified-source parts list or approved equivalent; confirm the rated load capacity yields a non-negative margin of safety against applied structural loads; check the rated temperature range encompasses the full mission thermal environment; and flag any dissimilar-metal pairing with elevated galvanic corrosion risk. A part failing any single check is non-compliant and must be replaced or formally dispositioned before integration. Trigger: ecss, e-st-32-structures-scope, mechanical-parts, fastener, insert, bearing, qualified-parts-list, load-margin, galvanic-compatibility."
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
  tags: [ecss, e-st-32-structures-scope, mechanical-parts, fastener, insert, bearing, qualified-parts-list, load-margin, galvanic-compatibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mechanical Parts Selection (space-systems/ecss/mechanical-parts-selection)

Use when the task is evaluating and selecting mechanical parts (fasteners,
inserts, and bearings) for a spacecraft structural assembly per ECSS-E-ST-32C
clause 4.5.7 — verifying each part is drawn from a qualified source, carries
sufficient structural margin, and is thermally and galvanically compatible with
its installation environment.

## Domain quick reference

- ECSS-E-ST-32C clause 4.5.7 requires that mechanical parts — fasteners
  (bolts, screws, rivets, pins), inserts (helicoil, key-locking, threaded),
  and bearings (ball, roller, bush) — be selected only from qualified sources
  documented in a Qualified Parts List (QPL) or an equivalent approved-source
  register. A part not on the QPL must receive a formal approval or deviation
  before use.
- Each fastener or bearing installation must demonstrate a non-negative margin
  of safety (MS) against the applied structural load for the governing load
  case. MS = (rated load capacity / applied load) − 1; a part is structurally
  non-compliant if MS < 0.
- The part's rated temperature range must fully encompass the mission thermal
  envelope. A part whose rated minimum exceeds the mission cold-case minimum,
  or whose rated maximum falls below the mission hot-case maximum, is
  thermally non-compliant.
- Dissimilar-metal pairings between a fastener, insert, or bearing and its
  mating structure introduce galvanic corrosion risk in the presence of
  moisture or conductive fluid. High-risk pairs (such as aluminum against
  steel, CFRP against aluminum, or magnesium against steel) must be flagged
  and mitigated before the part is accepted into the assembly.

## Workflow

1. For each candidate part, determine its category (fastener, insert, or
   bearing) from the part type identifier. Reject any part whose type is not
   recognized before it enters the qualification or analysis steps.
2. Cross-reference the part number against the project QPL or approved-source
   register. Flag any part absent from the list; it requires a formal
   deviation or procurement from a qualified source before use.
3. Retrieve the rated load capacity from the part datasheet. Compute the
   margin of safety against the applied structural load for the governing load
   case: MS = (rated_load / applied_load) − 1. Flag the part if MS < 0.
4. Confirm the part's rated minimum temperature is at or below the mission
   cold-case minimum and the rated maximum temperature is at or above the
   mission hot-case maximum. Flag a part that violates either bound.
5. Identify the materials of the part and its direct mating surface. If the
   combination appears on the project's galvanic risk register or a recognized
   galvanic series, flag the pairing and require a documented mitigation before
   installation.
6. Aggregate all check results per part. A part is compliant only when
   qualification, load, temperature, and galvanic checks all return empty
   violation lists.

## Pitfalls

- Accepting a part as qualified because it was used on a previous project
  without verifying it appears on the current project's QPL — each project
  maintains its own approved-source register.
- Computing MS against a limit load that does not yet include the applicable
  design limit load factors; the applied load entering the MS calculation must
  already incorporate all load factors for the governing case.
- Declaring a part thermally compliant because its rated maximum exceeds room
  temperature — both the coldest cold case and the hottest hot case must be
  checked against the part's rated range.
- Overlooking galvanic risk for fasteners installed through CFRP fittings:
  carbon fibre composite forms a galvanic couple with most metallic fastener
  materials in the presence of moisture.

## Behavior contract (gate 3)

The part categorization, qualification-status, load-margin, temperature-range,
and galvanic-compatibility logic is exercised by the gate 3 contract test:
scripts/test_mechanical_parts_selection.py against
scripts/mechanical_parts_selection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_mechanical_parts_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
