---
name: q40-02-step1-implementation
description: "Define the implementation requirements for a space-project hazard analysis under ECSS-Q-ST-40-02C clause 5.2.1, step 1. Use when the task is fixing what the analysis must cover before a single hazard is written down: reading the project type - crewed or uncrewed, ground, launch, orbital or re-entry segment, hardware recovered, third party exposed - into the analysis depth it forces, deriving the scope elements, the technique set and the specialist disciplines the safety team has to hold, then comparing each derived set against the declared plan and reporting every missing item as a planning finding rather than a later surprise. Trigger: ecss, q-st-40-02c, hazard-analysis-implementation-step, crewed-mission-analysis-depth, hazard-analysis-technique-selection, safety-team-discipline-coverage, hazard-analysis-scope-definition, third-party-exposure-depth-driver."
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
  tags: [ecss, q-st-40-02-hazard-analysis-scope, q40-02-step1-implementation, hazard-analysis-implementation-step, crewed-mission-analysis-depth, hazard-analysis-technique-selection, safety-team-discipline-coverage, hazard-analysis-scope-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — Step 1, Implementation Requirements (space-systems/ecss/q40-02-step1-implementation)

Use when the task is step 1 of the ECSS-Q-ST-40-02C clause 5.2 process —
turning the project type into the depth, the scope, the techniques and
the team the hazard analysis is required to have before any hazard is
identified.

## Domain quick reference

- Step 1 is where the analysis is sized, and it is sized by the project
  rather than by the effort available. Four attributes do the work:
  whether crew is carried, which segments are flown, whether hardware
  is recovered, and whether a third party is exposed. Everything else
  in step 1 follows from them.
- Depth has three settings and crew is the switch. A project with no
  launch segment and no third-party exposure runs at the baseline; a
  launch segment or an exposed third party raises it; crew takes it to
  the safety-critical level, where failure tolerance has to be shown
  rather than argued.
- Scope is a list of things the analysis walks, not a boundary drawn
  around the spacecraft. Flight hardware, ground support equipment,
  handling and transport, and software-driven functions are owed by
  every project; each segment adds its own, crew adds interfaces and
  escape provisions, and recovery adds the post-flight safing that is
  routinely forgotten because the mission is over by then.
- A deeper project does not run the same techniques harder. It owes
  techniques a shallower one does not: crew task and error analysis
  and a failure-tolerance demonstration for a crewed vehicle, a
  casualty-footprint assessment for anything that re-enters, a
  third-party risk assessment where the public is exposed.
- The team is checked by discipline, not by headcount. A crewed
  analysis without human factors and life support on the team is
  short a discipline no amount of system engineering covers, and the
  gap is invisible in a staffing plan that only counts people.
- A declaration outside the derived set is not a finding. Running an
  extra technique is the project's business; the finding is the
  derived item that nobody planned.

## Workflow

1. Validate the project type. Reject an unknown segment, a crewed
   project with neither an orbital nor a re-entry segment, and a
   recovered project with no re-entry segment — each is a contradiction
   the derived sets cannot resolve.
2. Derive the required depth from crew presence, launch segment and
   third-party exposure.
3. Derive the scope elements: the baseline set, plus the elements each
   flown segment adds, plus crew and recovery additions.
4. Derive the technique set and the team disciplines the same way, so
   all three derived sets come from one project reading.
5. Validate the declared plan, then compare it against each derived
   set. Record the missing items and, separately, the items declared
   outside the derived set.
6. Compare declared depth against derived depth on the ordinal, so a
   plan deeper than required passes and only a shallower one is a
   finding.
7. Aggregate. Step 1 is complete only when no derived item is missing
   and the declared depth is not under the required one.

## Pitfalls

- Sizing the analysis from the schedule. The depth is a property of
  what the project flies and who it can hurt; a plan that declares the
  baseline for a crewed vehicle is not a lean plan, it is short two
  techniques and two disciplines.
- Taking recovery for granted. A recovered vehicle owes post-flight
  safing operations, and those get dropped because the mission is
  considered finished at touchdown.
- Counting the safety team instead of reading it. Six engineers with no
  human-factors specialist cannot perform a crewed task-and-error
  analysis, and the staffing plan will not show it.
- Treating an extra technique as over-scoping and trimming it back to
  the derived set. The derived set is a floor, and cutting to it loses
  work that was already planned for a reason.
- Deriving depth, scope, techniques and disciplines from four separate
  readings of the project. They must come from one validated project
  record or they will disagree with each other in review.

## Behavior contract (gate 3)

The project-type validation, depth derivation, scope, technique and
discipline derivation, plan comparison and depth-ordinal logic is
exercised by the gate 3 contract test:
scripts/test_q40_02_step1_implementation.py against
scripts/q40_02_step1_implementation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_step1_implementation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
