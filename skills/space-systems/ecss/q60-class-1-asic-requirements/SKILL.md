---
name: q60-class-1-asic-requirements
description: "Use when an ASIC is developed, reused or re-targeted. Determine which flow of the dedicated ASIC and FPGA development standard a class 1 application specific integrated circuit enters when ECSS-Q-ST-60C clause 4.6.2 hands it over: compare the candidate build against the qualified heritage on foundry, process node, mask set, design database, functional scope, package and die attach, group the moved axes into silicon, design and assembly, weigh the reuse evidence and the age of the qualification, then route the part to a full development, a delta qualification or a reuse flow and return the activities that route carries. Refuses a reuse claim with no evidence reference. Trigger: ecss, q-st-60c-clause-4-6-2, class-1-asic-development-routing, dedicated-asic-standard-referral, asic-heritage-delta-axes, foundry-process-node-change, asic-qualification-currency, asic-reuse-evidence-gap."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-1-asic-requirements, class-1-asic-development-routing, dedicated-asic-standard-referral, asic-heritage-delta-axes, foundry-process-node-change, asic-qualification-currency, asic-reuse-evidence-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 ASIC Requirements (space-systems/ecss/q60-class-1-asic-requirements)

Use when the task is the clause 4.6.2 hand-off of ECSS-Q-ST-60C: a class 1
application specific integrated circuit is on the parts list, and the
general component rules stop being the governing text because the part is
developed and reused under the dedicated ASIC and FPGA development
standard, ECSS-Q-ST-60-02. The work is not to restate that standard. It
is to decide which of its flows this particular part enters, and to say
why.

## Domain quick reference

- An ASIC is a component the project causes to exist. Everything the
  general rules lean on for a catalogue part — a manufacturer's
  qualification, a published detail specification, a production history
  across many customers — has no counterpart here, which is why the
  referral to the dedicated standard is not a cross-reference but a
  change of governing text.
- Heritage is the whole of a reuse argument, and it is not one fact. It
  is a set of axes: the foundry, the process node, the mask set, the
  design database version, the functional scope, the package and the die
  attach. Reuse is a claim that every one of them held.
- The axes are not interchangeable. A silicon axis moving voids the
  electrical evidence; a design axis moving voids the functional
  evidence; an assembly axis moving leaves the die alone and touches only
  the package evidence. Grouping the moved axes that way is what turns a
  list of differences into a route.
- Evidence comes before delta. A reuse claim that references no
  qualification report, no radiation evaluation and no lot acceptance
  data is not a small reuse or a large one — it is a claim with nothing
  behind it, and there is nothing yet to route.
- A qualification has an age. Evidence that stood five years ago covers
  a process that has since been tuned, and a break in production is the
  same statement in a different form: the line that made the qualified
  parts is not the line that will make these.
- Re-targeting a design to a new foundry is the case most often argued
  as reuse, because the design database did not change. The silicon did.
  The same netlist on a different process is a new part with a familiar
  function.

## Workflow

1. Validate the case: the part identifier, the declared route, and for
   anything other than a new development both the candidate and the
   qualified heritage records. A missing or blank axis is an input
   error; an axis that cannot be compared cannot be routed.
2. For a declared new development, route straight into the full flow of
   the dedicated standard and stop; there is no heritage to weigh.
3. Otherwise compare the two heritage records axis by axis and collect
   the ones that moved.
4. Group the moved axes into silicon, design and assembly, and take the
   share of the axis set that moved as a reported delta index.
5. Check the reuse evidence references are present. If any is absent,
   return that finding and route nothing.
6. Check the qualification age against its validity and whether
   production ran without a break.
7. Route in precedence order: evidence incomplete, then a silicon or
   design change to the full development flow, then an assembly change,
   a lapsed qualification or a production break to a delta
   qualification, otherwise the reuse flow. Return the route, the
   activity set it carries, the moved axes by group, and every finding.

## Pitfalls

- Reading the referral as a citation. Clause 4.6.2 moves the governing
  text; a parts list that names the dedicated standard but keeps
  applying the general component activities has not made the hand-off.
- Calling a foundry change reuse because the design database is
  untouched. The netlist is the part of the ASIC that did not change,
  and it is not the part the electrical evidence was taken from.
- Treating a package change as a full redevelopment. Over-routing costs
  as much credibility as under-routing: the die evidence stands, and the
  delta qualification exists precisely for this case.
- Routing before the evidence is in hand. A reuse route granted against
  a qualification report nobody can produce is a decision with no record
  behind it, and it surfaces at the review that needed the record.
- Letting a current-looking qualification cover a line that stopped. Age
  and continuity are separate questions; a part qualified last year on a
  line idle since is not covered by its date.
- Counting moved axes without grouping them. Two changes are not worse
  than one when the one is the foundry; the delta index describes the
  spread of the change and never decides the route on its own.

## Behavior contract (gate 3)

The case validation, heritage axis comparison, axis grouping, delta
index, reuse-evidence check, qualification currency test, route
precedence and activity-set lookup are exercised by the gate 3 contract
test: scripts/test_q60_class_1_asic_requirements.py against
scripts/q60_class_1_asic_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_asic_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
