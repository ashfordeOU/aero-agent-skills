---
name: q6013-class-3-asic-components
description: "Evaluate whether an application-specific device may ride on its supplier's own development assurance evidence at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.2: close the delegated route for a device kind the class never delegates, credit each assurance objective by the strength of the evidence behind it in exact integer basis points, refuse all credit for a non-delegable objective backed by nothing better than a supplier declaration, re-open one named activity per rated envelope axis the mission overruns, and compare credited assurance with the floor treating equality as met. Use when a catalogue ASIC is offered on supplier evidence alone. Trigger: ecss, q-st-60-13c-clause-6-6-2, class-three-asic-delegated-assurance, supplier-evidence-strength-credit, non-delegable-asic-objective, asic-rated-envelope-shortfall, reopened-asic-activity, asic-delegation-route-closed."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-3-asic-components, class-three-asic-delegated-assurance, supplier-evidence-strength-credit, non-delegable-asic-objective, asic-rated-envelope-shortfall, reopened-asic-activity, asic-delegation-route-closed]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 ASIC Components (space-systems/ecss/q6013-class-3-asic-components)

Use when the task is the clause 6.6.2 development assurance question of
ECSS-Q-ST-60-13C at the lowest assurance class: an application-specific
device is being offered into a commercial parts programme on the
strength of what its supplier did during its own development, and the
question is how much of that carries and what the programme still has to
do itself.

## Domain quick reference

- The delegated route is a property of the device kind, not of the
  paperwork. A catalogue standard product and a structured device were
  developed for a market and have a market's worth of evidence behind
  them; a full-custom or standard-cell device built for one application
  has whatever that application paid for. The kinds this class delegates
  are a declared list, and a kind outside it closes the route before any
  evidence is read.
- Evidence has a strength, and strength is what converts a development
  objective into credit. An independent audit, a third-party report and
  a supplier's own declaration are not the same claim, so each carries
  its own integer credit factor and an objective with nothing behind it
  carries none.
- A handful of objectives are not delegable whatever the class. Where
  one of those rests on nothing better than the supplier's own word, it
  earns no credit at all and re-opens as an activity the programme
  performs, rather than earning partial credit and quietly closing.
- Credit is summed in integer basis points: weight times credit factor,
  against the whole weight times a hundred. A device landing exactly on
  the declared floor is admitted, and it is admitted identically on
  every machine, which is not true of the same sum held as a fraction.
- The rated envelope is a separate question from the development
  evidence. Temperature and total dose the device was rated for either
  cover the mission or they do not, and each axis the mission overruns
  re-opens one named activity regardless of how strong the development
  evidence was.
- The output is a plan, not a grade. Refused objectives and re-opened
  activities are what the programme schedules; the credited figure is
  how it argues the rest.

## Workflow

1. Validate the device declaration: a reference, a device kind, the
   rated temperature bounds and the rated total dose. Validate the
   mission envelope the same way.
2. Close the delegated route where the declared kind is not one the
   class delegates, and return that as the verdict.
3. Validate the objective catalogue: each objective carries a positive
   integer weight and a non-delegable flag.
4. Read the evidence offered against each objective, refusing an
   evidence strength outside the recognised set and an objective the
   catalogue does not name.
5. Refuse all credit for a non-delegable objective whose evidence is
   weaker than the declared minimum strength, and re-open it as an
   activity.
6. Sum the credit in basis points across the objectives still standing.
7. Compare the rated temperature bounds and total dose with the mission
   envelope and re-open one named activity per axis that falls short.
8. Compare credited assurance with the floor by integer
   cross-multiplication, equality counting as met, and return one
   verdict in precedence order: route closed, a non-delegable objective
   unevidenced, an envelope shortfall, assurance below the floor,
   otherwise the delegated evidence is accepted.

## Pitfalls

- Reading a thick supplier dossier as a strong one. Volume is not
  strength; an unaudited declaration is an unaudited declaration however
  many pages it runs to, and the credit factor is what says so.
- Giving a non-delegable objective partial credit because some evidence
  exists. Partial credit closes the objective on the plan, which is the
  outcome the non-delegable flag was there to prevent.
- Treating a catalogue part number as proof of the catalogue route. The
  kind is what the device is, and a full-custom die offered under a
  catalogue reference is still a full-custom die.
- Summing credit as a fraction. A device landing exactly on the floor is
  the case two reviewers argue about, and it is the case a float decides
  differently in two places.
- Folding the envelope shortfall into the credited figure. Development
  evidence and rated envelope are independent: strong evidence about a
  device rated to a narrower range is strong evidence about a device
  that does not cover the mission.
- Reporting only the credited number. The refused objectives and the
  re-opened activities are the work; the number is the argument.

## Behavior contract (gate 3)

The device and envelope validation, delegated-route closure, evidence
strength crediting, non-delegable refusal, integer basis-point
summation, envelope shortfall activities and verdict precedence are
exercised by the gate 3 contract test:
scripts/test_q6013_class_3_asic_components.py against
scripts/q6013_class_3_asic_components_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_3_asic_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
