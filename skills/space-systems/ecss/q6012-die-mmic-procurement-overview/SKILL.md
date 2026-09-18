---
name: q6012-die-mmic-procurement-overview
description: "Map the clause route a die-form MMIC procurement case pulls in under ECSS-Q-ST-60-12C clause 4.1: normalise the case, fire each clause area's own applicability rule and keep the reason it fired, close the routed set under the prerequisites those areas consume, order it so nothing is entered before what it depends on, and report the covered fraction with the findings an order clears first. Refuses a dependency cycle, an unknown clause key and a misspelt case flag, and reports a packaged part as outside the die-form map. Use when a bare microwave die order is being scoped. Trigger: ecss, q-st-60-12c-clause-4-1, die-form-mmic-procurement-scope, mmic-clause-route-map, die-procurement-applicability-rule, die-clause-prerequisite-closure, mmic-scope-coverage-ratio."
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
  tags: [ecss, q-st-60-12-die-mmic-scope, q6012-die-mmic-procurement-overview, die-form-mmic-procurement-scope, mmic-clause-route-map, die-procurement-applicability-rule, die-clause-prerequisite-closure, mmic-scope-coverage-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die-Form MMIC — Procurement Scope And Clause Map (space-systems/ecss/q6012-die-mmic-procurement-overview)

Use when the task is the entry clause of ECSS-Q-ST-60-12C: a bare
monolithic microwave die is about to be bought, and before any of the
downstream clauses can be worked the case has to be placed — is this
even a die-form purchase, which foundry standing is behind it, which
model are the dies for, and therefore which of the clauses that follow
this one the order actually pulls in.

## Domain quick reference

- A bare die is bought without the package that normally carries the
  part number, the screening history and the handling protection. Every
  downstream clause exists because one of those three disappeared with
  the package, so the scope clause is the place where the case is
  described well enough for the rest of the map to be derived from it.
- The map is not a fixed checklist. An engineering-model order, a
  qualification-model order and a flight order route different clause
  areas, and the same order routes different areas again depending on
  whether the dies are attached in house, whether they see a radiation
  environment, and whether the level offered meets the programme floor.
- Clause areas are not independent. Lot acceptance evidence is graded
  against the lot that procurement identified, and procurement is graded
  against the foundry selection behind it. A routed area therefore pulls
  its prerequisites into the map whether or not the case triggered them
  on their own, and a pulled-in area is marked so a reviewer can see it
  arrived by dependency rather than by rule.
- The order the areas are worked in matters as much as the set. An area
  entered before the area whose output it consumes produces a finding
  that cannot be closed, so the map is ordered by dependency and ties
  are broken on registry order to keep it reproducible run to run.
- A packaged part is not a small variation on a die order. The clause
  map does not cover it, and answering with a partial map would read as
  coverage; the correct response is to report the case out of scope.

## Workflow

1. Normalise the case, refusing an unknown token and — just as
   important — an unknown key, so a misspelt flag cannot silently take
   its default and drop a whole clause area out of the map.
2. If the item is a packaged part, report it out of scope with the scope
   area alone routed, and stop. Do not emit a partial map.
3. Fire each clause area's applicability rule against the case and keep
   the reason the rule returned alongside the key it routed.
4. Close the routed set under its prerequisites, recording which areas
   were pulled in by dependency rather than triggered by rule.
5. Order the closed set so no area precedes a prerequisite, breaking
   ties on registry order, and refuse a dependency cycle rather than
   emitting an arbitrary order that a reviewer would read as considered.
6. Compute the covered fraction of the registry, so a lean model order
   is visibly leaner than a flight order rather than looking equivalent.
7. Report the findings: a packaged part, a flight build pointed at an
   unassessed foundry, a flight build with no lot acceptance data, and
   an offered level under the programme floor.

## Pitfalls

- Treating the map as the same list for every order. The clause set is
  derived from the case; an engineering model that routes flight lot
  procurement has been mapped from a template, not from its own case.
- Ignoring an unknown key in the case. A misspelt radiation flag reads
  as absent, the radiation area never routes, and the map looks complete
  while the area that mattered most is the one missing from it.
- Routing an area without its prerequisites. Lot acceptance graded
  against a lot nobody identified is evidence about nothing, so the
  prerequisite closure runs before the ordering, not after it.
- Emitting an order for a cyclic graph. A cycle means the dependency
  declarations are wrong; producing some order anyway hides the defect
  behind a plausible-looking sequence.
- Answering a packaged-part case with a partial map. Out of scope is the
  answer; a partial map invites the reader to work the areas listed and
  conclude the purchase was covered.

## Behavior contract (gate 3)

The case normalisation, per-area applicability rules, prerequisite
closure, dependency ordering with cycle refusal, coverage ratio and
findings are exercised by the gate 3 contract test:
scripts/test_q6012_die_mmic_procurement_overview.py against
scripts/q6012_die_mmic_procurement_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_die_mmic_procurement_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
