---
name: q6005-hybrid-design-general-requirements
description: "Evaluate whether a hybrid microcircuit design is ready to leave the drawing office and enter manufacture under ECSS-Q-ST-60-05 clause 7.1. Use when a hybrid design package is offered for release and someone must say whether the general design expectations are met: confirm the mandated design evidence is present and complete, take every element's applied-to-rated stress ratio against its family derating limit, build the junction temperature from the dissipation and the stacked die-attach, substrate and package thermal resistances, grade conductor spacing, wire-bond and die-to-die clearance against the declared minima, and return a release-or-hold verdict naming each shortfall. Trigger: ecss, q-st-60-05, hybrid-microcircuit-design-release, hybrid-element-derating-ratio, hybrid-junction-temperature-margin, hybrid-substrate-layout-clearance, hybrid-design-evidence-completeness."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuit-scope, q6005-hybrid-design-general-requirements, hybrid-microcircuit-design-release, hybrid-element-derating-ratio, hybrid-junction-temperature-margin, hybrid-substrate-layout-clearance, hybrid-design-evidence-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — General Design Requirements (space-systems/ecss/q6005-hybrid-design-general-requirements)

Use when the task is the general design step of ECSS-Q-ST-60-05 clause 7.1 —
deciding whether the design of a hybrid microcircuit has met the expectations
placed on it before any of it is committed to manufacture, so the package is
either released to build or held with the shortfall named.

## Domain quick reference

- A hybrid is a design that cannot be reworked the way a board can. Once the
  die are attached, bonded and the package is sealed, a derating error or a
  clearance error is a scrap decision, not a modification. That is why the
  expectations sit before manufacture and not at first test.
- The design evidence is a set, not a score. Design rules, the parts and
  materials list, the derating analysis, the thermal analysis, the layout
  drawing, the worst-case analysis and the testability provisions each answer
  a different question, so a strong thermal analysis cannot stand in for an
  absent derating analysis. Any one of them missing holds the release.
- Derating is applied per element family, not per hybrid. A resistor, a
  capacitor, a semiconductor die, a magnetic element and an interconnect each
  carry their own applied-to-rated ceiling, and the screen is the worst
  element, never the average of the population.
- Junction temperature is built by stacking thermal resistances in series
  from the junction outward: die attach, substrate, package. A hybrid puts
  several dissipating elements on one substrate, so the base temperature the
  stack starts from is the local substrate temperature under that element,
  not the mounting-plate temperature of the whole unit.
- Layout clearances (conductor spacing, wire-bond to adjacent feature,
  die-to-die) are the design rules made numeric. They are graded against the
  declared minima of the applicable design rules, and every declared minimum
  needs a declared value to grade, or the layout has simply not been checked.
- The verdict is binary and the findings are additive: a package may be held
  for evidence, derating, thermal and layout at once, and all four are
  reported rather than the first one found.

## Workflow

1. Validate the design-evidence record: every item named is one of the
   mandated ones, every value is a plain yes or no, nothing is declared
   twice. An unknown item name is an input error, not an extra credit.
2. List the mandated evidence that is absent or not yet complete, in the
   mandated order, so the hold reads the same way every time.
3. Screen every declared element: resolve its family ceiling, form its
   applied-to-rated stress ratio, and mark it compliant only when the ratio
   is at or below the ceiling. A duplicate element reference is refused
   rather than silently overwritten.
4. Build the junction temperature from the local base temperature, the
   dissipation and the series thermal-resistance stack, then take the margin
   against the maximum junction temperature the design allows.
5. Grade every layout clearance against its minimum. A declared clearance
   with no minimum, or a minimum with no declared clearance, is refused.
6. Collect the findings and return one verdict: releasable only when the
   finding list is empty. Absorb an exact boundary equality with the named
   tolerance, never by relaxing the limit itself.

## Pitfalls

- Averaging the derating screen across the population. A hybrid with one
  element at 0.9 of rated and thirty at 0.1 has a derating finding; the
  population mean hides exactly the element that will fail.
- Starting the thermal stack from the unit mounting-plate temperature. On a
  shared substrate the neighbouring dissipators raise the local base
  temperature, and a stack started too cold under-reports the junction by
  the amount that matters.
- Treating a strong analysis as cover for an absent one. The evidence items
  are independent questions; completeness is a set membership test, not a
  weighted score.
- Relaxing a derating ceiling or a clearance minimum to clear a case that
  lands exactly on it. An equality at the limit is a representation
  question, handled by the tolerance inside the comparison, and the
  engineering limit stays where the design rules put it.
- Reporting only the first shortfall found. A held package is re-worked
  once, so all four finding families are gathered in the same pass.
- Grading a layout against minima that no design rule declared. A missing
  minimum means the clearance was never checked, which is itself the
  finding, not a pass by default.

## Behavior contract (gate 3)

The evidence-record validation, evidence-gap listing, per-family derating
screen, junction-temperature stack, clearance grading and the combined
release-or-hold verdict are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_design_general_requirements.py against
scripts/q6005_hybrid_design_general_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hybrid_design_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
