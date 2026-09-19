---
name: e3301-structural-dimensioning-basis-loads-allowables
description: "Define the load and allowable basis a spacecraft mechanism is structurally dimensioned on under ECSS-E-ST-33-01 clauses 4.7.5.2.1 to 4.7.5.2.4. Use when limit loads have to be gathered from every mission event, raised by the model factor their knowledge basis carries and by the project factor, enveloped into the one case that actually sizes the part, and paired with a material allowable whose statistical basis matches the redundancy of the load path and the temperature the part really sees. Trigger: ecss, e-st-33-01-mechanisms, mechanism-design-limit-load, mechanism-load-case-envelope, mechanism-material-allowable-basis, single-load-path-a-basis, mechanism-load-model-factor, mechanism-allowable-temperature-retention."
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
  tags: [ecss, e-st-33-01-mechanisms, e3301-structural-dimensioning-basis-loads-allowables, mechanism-design-limit-load, mechanism-load-case-envelope, mechanism-material-allowable-basis, single-load-path-a-basis, mechanism-load-model-factor, mechanism-allowable-temperature-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Structural Dimensioning Basis, Loads and Allowables (space-systems/ecss/e3301-structural-dimensioning-basis-loads-allowables)

Use when the task is the dimensioning basis of ECSS-E-ST-33-01 clauses
4.7.5.2.1 to 4.7.5.2.4 -- fixing, before any margin is computed, which
loads a mechanism part is sized to and which material numbers it is
allowed to be sized against.

## Domain quick reference

- A mechanism sees loads from events that have nothing to do with each
  other: ground handling, the launch quasi-static ride, the random
  environment reduced to an equivalent static load, shock, thermoelastic
  distortion of the mounting, the reaction of its own actuation, the
  deployment latch-up transient, and on-orbit operation. The schedule is
  built per event, not per direction.
- A limit load is the largest load expected in service. It is raised
  into a design limit load by two separate multipliers: a model factor
  that prices how the load was obtained, and a project factor the
  programme declares. Both sit on the load side. Folding either one into
  the allowable instead makes it invisible to the next reviewer and
  invites a second application.
- The model factor follows the knowledge basis. A measured load needs no
  uplift, a coupled-loads analysis a small one, a specification envelope
  more, an engineering estimate the most. The basis is a stated
  attribute of the case, so an uncategorized basis is rejected rather
  than quietly defaulted to the cheapest value.
- The part is dimensioned on the enveloping case, and that case is
  named. A weak basis can promote a physically smaller load into the
  driving one, which is exactly the outcome the factors exist to force.
- The allowable basis has to match the redundancy of the load path. A
  single load path has no alternative route when the weakest specimen in
  the population is the one that flew, so it carries a basis that bounds
  the population. A redundant path admits a less severe basis. A typical
  or average value describes a population rather than bounding it and is
  never a dimensioning allowable.
- An allowable is a function of temperature. The room value is reduced
  by the retention the material keeps at the design temperature, and the
  allowable must have been stated at a temperature that actually covers
  the part -- hotter for a hot part, colder for a cold one.

## Workflow

1. Declare the part: its identifier, whether its load path is single or
   redundant, and the design temperature it is dimensioned at.
2. Enter each load case with its mission event, its knowledge basis, its
   limit load and the project factor. Reject an unknown event or basis
   instead of defaulting it.
3. Raise each limit load to a design limit load by the model factor and
   the project factor, then envelope the schedule and record the driving
   case identifier and its event.
4. Check event coverage. A mechanism that flies owes at least a launch
   quasi-static case and an on-orbit operational case; a missing one is
   a gap in the basis, not a zero.
5. Enter the yield and ultimate allowables with their material,
   statistical basis, room value, temperature retention and the
   temperature they were stated at. Grade each basis against the load
   path and each stated temperature against the design point.
6. Report the design limit load, the driving case, the resolved design
   allowables and every finding, so the margin computation downstream
   starts from a basis that is already agreed.

## Pitfalls

- Applying the project factor to the allowable rather than the load. The
  arithmetic looks the same in one case and stops being the same the
  moment a second factor appears, and the factored allowable then
  propagates into every other part that quotes the same material.
- Enveloping the raw limit loads and then factoring once. The factors
  differ per case, so the largest limit load is not always the largest
  design load, and an estimated actuation reaction can outrank a
  measured launch load once both are factored.
- Dimensioning a single-load-path fitting on a B-basis or typical
  number. The number is right for the population and wrong for the one
  specimen that has no back-up path, which is the only specimen the
  clause is about.
- Carrying a room-temperature allowable into a hot or cryogenic design
  point because a retention factor was applied to it. The retention is
  necessary but not sufficient; the source value still has to have been
  established over a temperature that covers the part.
- Treating an absent mission event as a zero load. An event with no case
  has not been shown to be benign, and the schedule is incomplete until
  it is either entered or argued away in writing.
- Comparing two design loads for the envelope by bare arithmetic. They
  are products of floats, so two cases that are physically identical can
  differ in the last place; the comparison absorbs that representation
  error rather than reporting a spurious driver.

## Behavior contract (gate 3)

Load-case validation, the model-factor table, the design-limit-load
build-up, the envelope and its driving case, mandatory-event coverage,
allowable-basis admissibility against load-path redundancy, temperature
retention and coverage, and the part-level verdict are exercised by the
gate 3 contract test:
scripts/test_e3301_structural_dimensioning_basis_loads_allowables.py
against
scripts/e3301_structural_dimensioning_basis_loads_allowables_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_structural_dimensioning_basis_loads_allowables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
