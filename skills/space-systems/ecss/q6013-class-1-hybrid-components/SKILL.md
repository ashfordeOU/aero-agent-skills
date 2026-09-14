---
name: q6013-class-1-hybrid-components
description: "Evaluate the specification chain a class 1 hybrid microcircuit is procured against under ECSS-Q-ST-60-13C clause 4.6.3: confirm a dedicated generic specification governs the type, confirm the detail specification cites that generic as its parent, then rank every constituent element -- die, chip resistor, chip capacitor, substrate, interconnect, package -- by the procurement class it was itself bought at, and take the weakest element as the effective class the assembled hybrid can claim. Refuses an element carrying no specification reference of its own and names each element short of the declared class. Use when a hybrid is offered without a complete generic-plus-detail chain. Trigger: ecss, q-st-60-13c-clause-4-6-3, class-1-hybrid-procurement, hybrid-generic-specification, hybrid-detail-specification-parent, hybrid-element-procurement-class, weakest-element-effective-class, hybrid-element-class-shortfall."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-hybrid-components, class-1-hybrid-procurement, hybrid-generic-specification, hybrid-detail-specification-parent, hybrid-element-procurement-class, weakest-element-effective-class, hybrid-element-class-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 1 Hybrid Components (space-systems/ecss/q6013-class-1-hybrid-components)

Use when the task is the clause 4.6.3 procurement question of
ECSS-Q-ST-60-13C: a class 1 parts list carries a hybrid microcircuit,
and the hybrid is admissible only against its own dedicated generic
specification with a detail specification for the type -- not against
a purchase order that names a vendor part number and nothing else.

## Domain quick reference

- A hybrid is an assembly sold as a component. It has a part number and
  a package like a monolithic device, but inside it are separately
  procured die, chip resistors, chip capacitors, a substrate and the
  interconnect between them. The specification chain exists because the
  outer part number hides all of that.
- The chain has two levels and they do different work. The generic
  specification fixes what this family of hybrids has to survive; the
  detail specification fixes what this type is. A detail specification
  that does not cite a generic as its parent is a loose document, and
  the requirements it inherits are whatever the reader assumes.
- A catalogue type and a custom build are not the same procurement. A
  custom hybrid has no established type, so its detail specification is
  the only place the type is written down and it cannot be optional. A
  catalogue type already sits under the generic with an established
  detail behind it.
- Assurance does not average across an assembly. One element bought at
  a weaker class sets the class of the whole hybrid, because the hybrid
  will fail where that element fails. The weakest element, not the
  count of good ones, is the effective class.
- An element with no specification reference is not an element at a low
  class. It is an element whose class is unknown, so it closes the
  assessment ahead of any ranking; ranking it would be inventing the
  answer the reference was supposed to supply.
- The share of elements reaching the declared class is worth reporting
  and worth never using as the verdict. It describes how far the build
  is from the claim; it does not soften a single weak element.

## Workflow

1. Validate the declared hybrid class and the element list: each
   element carries an identifier, a kind from the recognised set, its
   own procurement class and a specification reference. An unknown kind
   or a duplicate identifier is an input error.
2. Read the generic specification. An absent or unidentified generic
   closes the assessment: there is nothing for a detail specification
   or a purchase order to sit under.
3. Decide whether the type is custom or catalogue. A custom type with
   no detail specification is a finding; a catalogue type may rest on
   the generic alone.
4. Where a detail specification is present, confirm it cites this
   generic as its parent, by identifier, not by resemblance of the
   numbering.
5. List the elements carrying no specification reference of their own.
6. Rank each element and list those weaker than the declared hybrid
   class; take the weakest present as the effective class of the
   assembled hybrid and compute the share that reach the declaration.
7. Return one verdict in precedence order: generic missing, an element
   with no specification, a detail specification absent or not derived,
   an element class shortfall, otherwise a complete chain. Report the
   effective class, the shortfall list and every finding.

## Pitfalls

- Procuring the hybrid on a vendor part number and a datasheet. The
  datasheet describes what the vendor currently builds; the generic
  specification describes what the vendor is obliged to keep building,
  and only one of those survives a process change.
- Accepting a detail specification because its number looks like a
  child of the generic. Numbering conventions are a convenience; the
  parent is the identifier the detail actually cites, and a detail
  inherited from a different generic inherits different limits.
- Treating the detail specification as optional for a custom build.
  A custom hybrid has no established type behind it, so dropping the
  detail leaves the type undefined at exactly the point it is unique.
- Averaging the element classes into a score. An assembly is as good as
  its poorest part; a hybrid with one weak capacitor is not mostly at
  the declared class, it is at the capacitor's class.
- Ranking an element that carries no specification reference as if the
  declared class were evidence. The declaration without a reference is
  a claim about an unknown part, and it belongs in the findings rather
  than in the ranking.
- Reporting the compliant share as the verdict. The share is useful to
  see how far a build sits from its claim and useless as a pass, since
  one uncovered element decides the outcome on its own.

## Behavior contract (gate 3)

The class ranking, specification validation, parent derivation check,
element validation, shortfall listing, effective-class rollup and
verdict precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_hybrid_components.py against
scripts/q6013_class_1_hybrid_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_hybrid_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
