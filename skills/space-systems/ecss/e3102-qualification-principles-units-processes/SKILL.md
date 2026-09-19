---
name: e3102-qualification-principles-units-processes
description: "Determine the qualification process and the number of qualification units ECSS-E-ST-31-02 clause 4.4.1 obliges for a two-phase heat transport item: reduce the declared changes against the qualified reference to one category, map that category to a full, delta, source-requalification, similarity or heritage process, size the unit count from the build standards to be covered and the destructive tests that consume hardware, and escalate a heritage claim the declared change contradicts. Use when a heat pipe or loop heat pipe programme has to fix how many qualification models it builds and what each one proves. Trigger: ecss, e-st-31-02-two-phase, two-phase-qualification-unit-count, qualification-process-selection, delta-qualification-scope, qualification-by-similarity-envelope, destructive-life-test-unit, heritage-claim-escalation."
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
  tags: [ecss, e-st-31-02-two-phase, e3102-qualification-principles-units-processes, two-phase-qualification-unit-count, qualification-process-selection, delta-qualification-scope, qualification-by-similarity-envelope, destructive-life-test-unit, heritage-claim-escalation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase — Qualification Principles, Units and Processes (space-systems/ecss/e3102-qualification-principles-units-processes)

Use when the task is the qualification principle of ECSS-E-ST-31-02
clause 4.4.1 -- deciding which qualification process a heat pipe, loop
heat pipe or capillary pumped loop owes, and how many qualification units
have to exist before that process can actually be run.

## Domain quick reference

- The process is not chosen, it is obliged. What has changed against the
  qualified reference decides it, and the change declaration is
  therefore the input that has to be pinned down first.
- Change categories, most onerous first: new-technology (a working
  principle or fluid with no precedent), new-design (no qualified
  predecessor), performance-change (a qualified design changed where it
  performs), source-change (the same design from a new maker or
  process), scaled-within-range (the same design resized inside a
  qualified span), identical.
- The categories are ordered, not additive. A declaration that ticks
  several flags reduces to the most onerous one, because the most
  onerous process already covers the evidence the lesser ones would
  have produced.
- Unit count has two independent drivers. Coverage: how many build
  standards the qualification has to speak for, divided by how many one
  unit is allowed to bound. Consumption: a life test or a burst test
  destroys the unit it runs on, so it adds hardware rather than sharing
  a unit already counted.
- A similarity case is allowed to bound several build standards with one
  unit precisely because the span itself was qualified; a full
  qualification is not, and proves one build standard per unit.
- A heritage case builds nothing. That is what makes it cheap and also
  what makes it fragile: a destructive test planned on it, or a unit
  marked for retention, is evidence that the claim is not really a
  heritage claim.
- Retention is a duty on hardware the programme already built, not an
  extra unit. Counting it twice inflates the model philosophy and the
  budget behind it.

## Workflow

1. Take the change declaration and require every flag explicitly. An
   absent flag is not a False; refuse the declaration rather than assume
   nothing changed, because that assumption is the one that produces an
   unjustified heritage claim.
2. Reduce the declaration to one category by the onerousness order, and
   read off the process the category obliges.
3. Where a process was already claimed, compare it with the obliged one
   and escalate when the claim sits lower. Claiming more than obliged is
   allowed and is not a finding.
4. Size coverage: divide the build standards to be covered by the
   configurations one unit may bound for that process, round up in
   integers, and apply the unit floor the process carries.
5. Add one unit for every destructive test, and refuse a destructive
   test on a case that builds no unit at all.
6. Close with the category, the process, the coverage units, the total
   units and a verdict that is escalated while any finding stands.

## Pitfalls

- Letting a source change ride as an identical build. A new braze house,
  a new wick supplier or a new fill process changes the things two-phase
  performance is most sensitive to, and the qualified evidence was taken
  on the old one.
- Rounding a unit count in floating point. Coverage is a count, and
  dividing build standards by configurations-per-unit with float
  arithmetic can land a whole unit short on one platform and not on
  another; the division stays in integers for that reason.
- Absorbing a life test into a unit already counted for coverage. The
  test ends with the unit consumed, so the build standard it was meant
  to cover has no surviving article behind it.
- Reading a retained unit as an extra build. Retention is a duty on
  hardware already in the count, and adding it again quietly doubles the
  model philosophy.
- Accepting a qualification-by-similarity claim without checking the
  resize actually sits inside the qualified span. Outside it the case is
  a performance change, and the delta programme it owes is much larger
  than the similarity dossier that was offered.

## Behavior contract (gate 3)

Change declaration validation, category reduction, process selection,
coverage sizing, destructive-unit accounting, claim escalation and the
plan verdict are exercised by the gate 3 contract test:
scripts/test_e3102_qualification_principles_units_processes.py against
scripts/e3102_qualification_principles_units_processes_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_qualification_principles_units_processes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
