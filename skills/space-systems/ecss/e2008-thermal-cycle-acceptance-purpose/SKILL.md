---
name: e2008-thermal-cycle-acceptance-purpose
description: "Evaluate whether an acceptance thermal cycling run on a photovoltaic assembly serves the two purposes ECSS-E-ST-20-08C clause 5.5.3.7.1 gives it, revealing infant mortality and confirming supplier workmanship: hold the cycle count, the range and the dwell soak above the depth a screen needs, convert the run into qualification-equivalent damage and cap the demonstrated fatigue life it may spend, group every failure by onset so an early escape is charged to workmanship while a late one is escalated, and report the lot escape rate. Use when an acceptance campaign is about to be signed off as a screen it may be too shallow or too long to be. Trigger: ecss, e-st-20-08c-clause-5-5-3-7-1, solar-array-acceptance-thermal-cycling, infant-mortality-screen-adequacy, supplier-workmanship-confirmation, coffin-manson-life-consumption, cycle-dwell-soak-adequacy, failure-onset-grouping."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-thermal-cycle-acceptance-purpose, solar-array-acceptance-thermal-cycling, infant-mortality-screen-adequacy, supplier-workmanship-confirmation, coffin-manson-life-consumption, cycle-dwell-soak-adequacy, failure-onset-grouping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Acceptance Thermal Cycling Purpose (space-systems/ecss/e2008-thermal-cycle-acceptance-purpose)

Use when the task is clause 5.5.3.7.1 of ECSS-E-ST-20-08C -- why a
flight photovoltaic assembly is thermally cycled at acceptance at all.
The design is already qualified, so this run is not a second
qualification. It exists to stress the article hard enough that an
early-life escape declares itself on the ground, and to give evidence
that the supplier's process produced this particular assembly the way
it produced the qualified one.

## Domain quick reference

- The two purposes are separate and can be served or missed
  independently. A campaign that finds an escape has revealed infant
  mortality and done its job; the same campaign has not confirmed
  workmanship, because a confirmation is what a clean run produces.
- The campaign sits between two walls. Too few cycles, too shallow a
  range or dwells too short to soak and nothing is precipitated, so
  the run is a schedule item rather than a screen. Too much and the
  acceptance run spends the fatigue life the qualification demonstrated
  -- which is the life the mission was sold.
- Dwell length is a thermal question, not a procedural one. An
  assembly needs roughly three thermal time constants at an extreme
  before its joints are actually at chamber temperature, so a short
  dwell delivers a smaller range than the profile sheet claims while
  every recorded number still looks nominal.
- Damage is not linear in cycle count. A Coffin-Manson exponent
  scales it with the temperature range, so acceptance cycles at one
  range have to be converted into qualification-equivalent cycles
  before a consumed-life fraction means anything. Twenty deep cycles
  can cost more than two hundred shallow ones.
- Where a failure appears is the evidence that separates the two
  purposes. An opening-cycle failure is an early-life escape and
  speaks about the process that built this unit; a failure that only
  appears once most of the campaign has run is a different mechanism
  and belongs to design or wear-out.
- The escape rate across the delivered lot is the workmanship number
  that survives the campaign. A single unit says little; the share of
  the lot that failed at acceptance is what a supplier audit acts on.

## Workflow

1. Validate the acceptance profile and the qualification profile it is
   measured against. An inverted extreme pair or a missing dwell stops
   the judgement rather than defaulting to something plausible.
2. Check the campaign can precipitate anything: cycle count above the
   screen floor, range deep enough to strain the joints, and both
   dwells above the soak floor in thermal time constants.
3. Convert the acceptance cycles into qualification-equivalent cycles
   with the fatigue exponent, and hold the consumed fraction of the
   demonstrated life under its ceiling.
4. Group every recorded failure by the cycle it appeared in. Early
   onsets are charged against supplier workmanship; later onsets are
   escalated to the design authority instead of being written into a
   supplier report where they will be answered with a process change
   that fixes nothing.
5. Compute the escape rate over the units cycled, not over the units
   that failed, so a lot with one bad article is separable from a lot
   with a bad process.
6. Close with the verdict the evidence supports: workmanship
   confirmed, infant mortality revealed, or the purpose not served at
   all because the campaign could never have shown either.

## Pitfalls

- Reading a clean acceptance run as proof the assembly is sound. It is
  proof the screen found nothing, and a screen too shallow to
  precipitate a defect finds nothing by construction.
- Treating a late failure as a workmanship escape. The onset is the
  evidence: a mechanism that needs most of the campaign to appear is
  not the one an acceptance screen was built to catch, and charging it
  to the supplier buys a corrective action against the wrong cause.
- Counting acceptance cycles against a qualification cycle count
  directly. Without the range conversion a deep acceptance run looks
  cheap while it is quietly spending the demonstrated life.
- Setting the dwell from the chamber controller rather than from the
  assembly. The controller reaches temperature long before the joints
  do, and a dwell measured against the controller overstates the
  applied range.
- Comparing a soak ratio or a consumed-life fraction against its limit
  by bare arithmetic. Both are float quotients that can land a few
  units in the last place either side of a limit written in another
  unit, so the comparison absorbs that error while the limit itself is
  never relaxed.
- Quoting an escape count without the lot size. Two failures mean
  different things in a lot of four and a lot of two hundred, and the
  supplier action that follows is different in each case.

## Behavior contract (gate 3)

The two-purpose separation, screen-capability floors on cycle count,
range and dwell soak, the Coffin-Manson conversion into
qualification-equivalent cycles, the consumed-life ceiling, the
failure-onset grouping and the lot escape rate are exercised by the
gate 3 contract test:
scripts/test_e2008_thermal_cycle_acceptance_purpose.py against
scripts/e2008_thermal_cycle_acceptance_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_thermal_cycle_acceptance_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
