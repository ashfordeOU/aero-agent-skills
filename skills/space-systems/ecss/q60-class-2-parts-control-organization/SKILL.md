---
name: q60-class-2-parts-control-organization
description: "Determine which organizational unit is accountable for electronic part control activities on a reliability Class 2 programme under ECSS-Q-ST-60C clause 5.1.2.1: refuse a unit with no name or recorded appointment, take each mandated control activity in turn, read an activity named to two units as contested rather than covered twice, weight the covered activities by criticality, name every unassigned, contested and unappointed one, require an escalation route where the unit reports inside the design authority, and cap the activities one holder carries alone. Use when a declared parts control organization has to become an accountability verdict. Trigger: ecss, q-st-60c-clause-5-1-2-1, reliability-class-2-parts-control-unit, parts-control-unit-accountability-naming, parts-control-activity-ownership-map, parts-control-unit-contested-activity, parts-control-unit-appointment-record."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-2-parts-control-organization, reliability-class-2-parts-control-unit, parts-control-unit-accountability-naming, parts-control-activity-ownership-map, parts-control-unit-contested-activity, parts-control-unit-appointment-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 2 Parts Control Organization (space-systems/ecss/q60-class-2-parts-control-organization)

Use when the task is the clause 5.1.2.1 accountability question of
ECSS-Q-ST-60C at reliability Class 2: a programme has declared who
controls its electronic parts, and the question is whether that
declaration actually places every control activity with a named,
appointed unit that can be held to it.

## Domain quick reference

- Naming a unit is not the same as placing the work. The clause is
  satisfied by a unit that owns the activities, so the assessment runs
  over the activity list and asks who holds each one, rather than over
  the organization chart asking whether a parts office exists.
- An appointment has to be recorded in a form that survives the person
  who made it. A contract annex, a programme directive, a quality manual
  or an issued organization chart stands; a meeting remark, an email
  note or nothing at all does not, and a unit appointed that way owns no
  activity however busy it is.
- Two names on one activity is worse than none. An unassigned activity
  is visibly open; a contested one looks covered twice on the chart and
  is discovered only when both units assume the other acted, so it is
  reported as contested and credited to neither.
- The activities do not weigh the same. Selection approval and
  nonconformance disposition decide what flies; supply monitoring
  decides what is inconvenient later. Coverage is weighted by declared
  criticality so a high count of easy activities cannot hide the loss of
  a decisive one.
- Some duties cannot be lent. A unit may be supported on almost
  everything, but part-selection approval and nonconformance disposition
  handed to another unit are no longer the named unit's, and the
  delegation is a finding rather than a staffing arrangement.
- Independence is about who can be refused. A unit reporting through
  product assurance, programme management or corporate quality can say
  no to the design office; one sitting inside the design authority needs
  a declared escalation route before its refusal means anything.
- Concentration is a real risk at this class. A single competent
  engineer holding every activity passes a coverage count and fails the
  first week of leave, so the activities one holder carries alone are
  capped and reported.

## Workflow

1. Validate every declared unit: a non-blank identifier, a recognised
   appointment form, a recognised reporting line and a boolean
   escalation-route declaration. A unit declared twice is a data error
   and is refused rather than merged.
2. Validate and dispose of every assignment in turn. A record missing an
   identifier, activity, unit or holder cannot be disposed of at all and
   stops there; the remaining tests run in severity order so the
   strongest reason is the one reported.
3. Refuse an assignment that names an undeclared unit, an activity
   outside the mandated set, a unit with no recorded appointment, a
   delegation of a duty that cannot be lent, or an unqualified holder.
4. Read ownership from the accepted assignments only, and group the
   mandated activities into covered, contested and unassigned.
5. Take the criticality-weighted covered share, compare it with the
   required level, and absorb representation error at the boundary with
   a named tolerance rather than by lowering the level.
6. Test the escalation route for every unit that actually owns an
   activity, not for every unit declared, and count the activities each
   holder carries against the declared cap.
7. Report the ownership map, the weighted coverage, the unassigned and
   contested activities, the overloaded holders and the units without a
   route, ranked most severe first, and close on one verdict: unit
   accountable, or accountability not established.

## Pitfalls

- Reading the organization chart instead of the activity list. A chart
  with a parts control box on it says nothing about who signs the
  selection approval, which is the only thing this clause is asking.
- Counting a contested activity as covered. Two owners is not redundancy
  at this class; it is an activity nobody performed, and crediting it
  twice is how a coverage figure reaches one over an open gap.
- Accepting a verbal or minuted appointment. It is a real instruction to
  a real person and it still leaves nothing to hold the unit to once
  that person moves, so it stands as no appointment here.
- Treating a delegation of selection approval as staffing. Support is
  freely delegated; the decision is not, and the distinction is what
  keeps a named unit answerable for the part that flew.
- Reporting a bare verdict. The weighted coverage, the contested
  activities and the holder concentration are what the next programme
  review is compared against, and the verdict word carries none of them.

## Behavior contract (gate 3)

The unit validation, appointment and reporting-line reading, assignment
completeness and disposition, the ownership map, the contested and
unassigned grouping, the criticality-weighted coverage, the holder
concentration cap, the escalation-route test and the accountability
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_2_parts_control_organization.py against
scripts/q60_class_2_parts_control_organization_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_2_parts_control_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
