---
name: q6013-class-3-hybrid-components
description: "Evaluate whether a hybrid microcircuit may be procured at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.3: refuse an element carrying no procurement reference of its own, rank every constituent element -- die, substrate, interconnect, chip capacitor, chip resistor, package seal -- by the basis it was bought against, take the weakest as the basis the assembled hybrid can claim, then weight lot traceability and source-change exposure by element criticality and compare both against the class floor, an exact landing counted as met. Use when a lowest-class parts list carries a hybrid and only a vendor datasheet stands behind it. Trigger: ecss, q-st-60-13c-clause-6-6-3, class-three-hybrid-procurement, hybrid-weakest-element-basis, hybrid-element-lot-traceability, hybrid-source-change-exposure, hybrid-unreferenced-element-refusal."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-hybrid-components, class-three-hybrid-procurement, hybrid-weakest-element-basis, hybrid-element-lot-traceability, hybrid-source-change-exposure, hybrid-unreferenced-element-refusal]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Hybrid Components (space-systems/ecss/q6013-class-3-hybrid-components)

Use when the task is clause 6.6.3 of ECSS-Q-ST-60-13C at the lowest assurance
class: a commercial parts list carries a hybrid microcircuit, the procurement
rests on whatever the vendor publishes rather than on a dedicated generic
specification, and the question is what that buys and what it leaves open.

## Domain quick reference

- The lowest class widens the document a hybrid may be bought against; it does
  not narrow what is inside the package. A hybrid is still an assembly sold
  under one part number, and the die, substrate, interconnect, chip resistors,
  chip capacitors and package seal behind that number were each procured on
  their own terms.
- The bases form a ladder, and the rungs differ in what the buyer can hold the
  supplier to afterwards. A generic plus a detail specification fixes what the
  family survives and what this type is; a vendor detail specification fixes
  the type alone; a catalogue datasheet fixes what the vendor happens to build
  today and nothing about tomorrow.
- An element with no reference at all is not at the bottom of that ladder. Its
  basis is unknown, so it closes the assessment before any ranking, because
  ranking it would invent the answer the missing reference was meant to give.
- Assurance does not average across an assembly. The weakest element sets the
  basis the hybrid can claim, since the hybrid fails where that element fails,
  and a count of well-bought elements does not offset one poorly bought one.
- Lot traceability and source-change exposure are the two things the lowest
  class actually gives away, so they are weighted rather than waived. Weighting
  by element criticality keeps an untraceable die from reading like an
  untraceable chip resistor.
- Exposure is a recorded condition, not a refusal. A supplier free to change a
  source without notice is a build the programme can accept knowingly and
  cannot accept silently, which is why it carries its own verdict.

## Workflow

1. Validate the hybrid record: a reference and a non-empty element list, each
   element carrying an identifier, a recognised kind, its own procurement
   basis, a lot-identity flag and a change-notification flag.
2. Reject a duplicated element identifier and an element list holding no die;
   an assembly with no die is not the component this clause is about.
3. List the elements carrying no procurement reference of their own.
4. Rank each element basis and take the weakest present as the effective basis
   of the assembled hybrid, then list every element below the declared floor.
5. Share each kind's criticality equally between the elements of that kind and
   normalise over the kinds present, so a build with two dies is not weighted
   as though it had one.
6. Compute the traceability coverage and the source-change exposure as shares
   of assembly criticality, and compare each against its floor or cap through
   a named tolerance rather than by moving the bound.
7. Return one verdict in precedence order: an unreferenced element, a basis or
   traceability shortfall, a recorded exposure, otherwise a clean procurement.
   Report the effective basis, both shares and every finding.

## Pitfalls

- Reading the lowest class as permission to buy on a part number alone. The
  class widens the acceptable basis; it never removes the need for one, and an
  element with no reference leaves the assembly unassessable rather than cheap.
- Averaging the element bases into a score. An assembly is as good as its
  poorest part, so a hybrid with one catalogue-bought interconnect sits at the
  catalogue rung whatever the rest of the build cost.
- Weighting every element alike. An untraceable die and an untraceable chip
  resistor are not the same loss, and treating them as equal lets the cheap
  fix carry the expensive one.
- Counting elements instead of criticality when a kind repeats. Two dies in
  one package do not double the die's share of the argument; they split it.
- Moving the traceability floor to absorb a share that landed on it. An exact
  landing is met by tolerance, and shifting the floor instead quietly changes
  the rule for every later build graded against it.
- Treating source-change exposure as a pass or a refusal. It is neither: it is
  a condition the programme carries knowingly, and a build accepted without it
  written down is a build nobody can reconstruct after the source changes.

## Behavior contract (gate 3)

The element validation, basis ranking, unreferenced-element refusal, weakest
element rollup, criticality sharing across repeated kinds, traceability and
exposure shares, tolerance handling on an exact landing and the verdict
precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_hybrid_components.py against
scripts/q6013_class_3_hybrid_components_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_hybrid_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
