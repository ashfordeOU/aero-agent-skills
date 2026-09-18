---
name: e2007-power-lead-susceptibility-purpose
description: "Scope a power-lead conducted susceptibility test against the aim of ECSS-E-ST-20-07C clause 5.4.7.1: proving the unit goes on working while disturbance signals are injected onto the leads that feed it. Use when such a test is planned or its purpose is challenged: separate supply leads from signal leads, name supply leads nothing is injected onto, expose sub-bands never disturbed on a lead, flag injections planned under the level the unit must tolerate, catch functions monitored only on undisturbed leads, and group each response as tolerant, degraded or malfunction. Trigger: ecss, e-st-20-07c, power-lead-susceptibility-purpose, supply-lead-disturbance-injection, power-lead-injection-band-coverage, power-lead-immunity-criterion, conducted-susceptibility-supply-lead-scope."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-power-lead-susceptibility-purpose, supply-lead-disturbance-injection, power-lead-injection-band-coverage, power-lead-immunity-criterion, conducted-susceptibility-supply-lead-scope, power-lead-response-grouping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Power Lead Susceptibility Purpose (space-systems/ecss/e2007-power-lead-susceptibility-purpose)

Use when the task is the purpose statement of ECSS-E-ST-20-07C clause
5.4.7.1 -- what the conducted susceptibility test on power leads is
for, and therefore what a proposed test has to reach before it can
claim the unit tolerates disturbance signals carried in on its supply.

## Domain quick reference

- The aim names the leads. This clause is about the conductors that
  feed the unit, so the primary supply, any secondary supply and their
  returns are in scope and a telemetry or data line is not. That is
  not a formality: a plan that spends its budget injecting onto signal
  lines has run a different test and demonstrated a different thing.
- The return lead is a supply lead. It is the one most often left out
  of an injection plan, because it looks passive, and it is the one
  that carries every disturbance current back. A plan covering the
  feed and not the return has not disturbed the loop.
- Reach is per lead and per frequency. A lead injected across part of
  the declared band has an undisturbed remainder, and the aim is not
  met there however thoroughly the rest was driven. Merge the
  injection spans within one lead before subtracting them from the
  band; a per-injection check passes a set that still leaves a hole.
- Level is what makes the claim mean something. An injection planned
  below the level the unit is required to tolerate proves the unit
  survives a smaller disturbance than the one it was asked about, and
  that is worth nothing at qualification.
- "Goes on working" is only decidable against an allowance. A
  monitored function with no stated allowed deviation cannot produce a
  verdict at all, which is why the allowance is required rather than
  optional, and why a function watched only on leads nothing is
  injected onto is a blind monitor.
- Responses group three ways. Inside its allowance is tolerant; past
  the allowance but self-recovering is degradation, which the aim can
  usually accept with a note; past the allowance without recovery is a
  malfunction and the unit has not met the aim.
- An injection onto a lead the clause does not cover is not a defect
  in the test. It is effort spent outside this aim, so it is recorded
  as a limitation and the reviewer decides whether it belonged to some
  other requirement.

## Workflow

1. Validate the declared leads: an identifier, a recognized kind, a
   non-negative nominal voltage and current.
2. Separate the supply leads the aim covers from the leads it does
   not, and keep both lists.
3. Validate the injection plan: a named lead, a recognized waveform, a
   real frequency span and a level.
4. Name supply leads that carry no injection, and injections that name
   a lead the declared set never listed.
5. Merge the injection spans within each supply lead and subtract them
   from the declared band to expose undisturbed sub-bands.
6. Flag injections planned below the level the unit must tolerate.
7. Validate the monitored functions, require an allowance on each, and
   name functions watched only on leads nothing is injected onto.
8. Group each observed response and aggregate: undisturbed leads and
   sub-bands, under-driven injections, blind monitors, undeclared
   targets and non-recovering malfunctions are findings; recovering
   degradation and out-of-scope injections are limitations.

## Pitfalls

- Reading the aim as "inject onto the power bus". The bus is a pair;
  the return is where the disturbance current comes home.
- Accepting a plan because every lead appears in it. Appearing once at
  one frequency is not reach across the declared band.
- Injecting at a convenient generator level. The level the unit must
  tolerate is the level that has to be reached, and anything less
  proves a weaker claim than the one being made.
- Monitoring a function on a lead nothing is injected onto. The
  monitor is green because nothing ever disturbed it, and that reads
  as immunity.
- Failing a unit for a deviation it recovered from. Self-recovering
  degradation is a graded outcome, not automatically a malfunction,
  and collapsing the two loses the distinction the reviewer needs.

## Behavior contract (gate 3)

The lead validation and scope separation, injection-plan validation,
undisturbed lead and sub-band detection, under-driven level check,
undeclared target detection, monitored-function allowance check, blind
monitor detection, response grouping and the aggregate verdict are
exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_susceptibility_purpose.py against
scripts/e2007_power_lead_susceptibility_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_power_lead_susceptibility_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
