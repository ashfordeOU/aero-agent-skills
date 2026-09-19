---
name: e2021-actuator-firing-parameter-specification
description: "Define and grade the firing parameter set a current driven actuator has to state under ECSS-E-ST-20-21C clause 5.3.1. Use when the task is turning a datasheet into a specification that can be reviewed: name the parameters never stated rather than defaulting them, hold the no fire level below the all fire level and the firing current above it, build the all fire and no fire margins as ratios against declared policy minima, require a pulse at least as long as the duration the all fire level is specified over, and derive the pulse energy and the no fire bridge dissipation. Trigger: ecss, e-st-20-21-actuation-scope, actuator-firing-parameter-specification, no-fire-current-level, all-fire-current-level, actuator-firing-margin-ratio, firing-pulse-energy."
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
  tags: [ecss, e-st-20-21-actuation-scope, e2021-actuator-firing-parameter-specification, no-fire-current-level, all-fire-current-level, actuator-firing-margin-ratio, firing-pulse-energy, actuator-bridge-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuation Electronics — Actuator Firing Parameter Specification (space-systems/ecss/e2021-actuator-firing-parameter-specification)

Use when the task is the parameter set of ECSS-E-ST-20-21C clause
5.3.1 -- stating what a current driven actuator has to declare before
a firing circuit can be designed around it, and checking that the two
levels the whole safety argument rests on, no fire and all fire, are
present and consistent with everything else in the sheet.

## Domain quick reference

- Two levels carry the argument and they point in opposite
  directions. The no fire level is the current the device is
  guaranteed not to actuate on, so every stray, monitoring and leakage
  path has to stay below it. The all fire level is the current it is
  guaranteed to actuate on, so the firing circuit has to deliver above
  it.
- The band between the two is not a design region. Inside it the
  device may or may not actuate and the specification says nothing, so
  a firing current chosen there is a design that has been left to the
  hardware to decide.
- An all fire level without its duration is not a specification. The
  guarantee is a current held for a stated time, so a pulse shorter
  than that time is not an all fire condition however high the current
  is, and the two parameters are always quoted together.
- Both margins are ratios against declared policy, not physical
  constants. The all fire margin is the firing current over the all
  fire level; the no fire margin is the no fire level over the largest
  current anything else in the design can push through the bridge. A
  project may set its own minima and the report says which were used.
- A parameter that was not stated is not zero and is not a default. It
  is reported as absent, because a missing no fire level silently
  becomes an unbounded one in any calculation that defaults it, which
  is the error that puts a monitoring current into a bridge nobody
  bounded.
- The bridge resistance turns the currents into the quantities a
  reviewer asks for next: the energy a firing pulse delivers, and the
  power the bridge dissipates while sitting at its no fire level,
  which is the number the continuous monitoring case is argued from.

## Workflow

1. Take the declared parameters and validate them: each one positive
   and finite, an unknown key refused outright because a mistyped key
   drops the parameter it was meant to carry, and nothing defaulted.
2. Compare the declared set against the parameters the clause expects
   and name every absent one, reporting completeness as a fraction of
   the full set.
3. Check the ordering of the levels: the no fire level strictly below
   the all fire level, and the firing current strictly above it. An
   inverted or equal pair leaves no unspecified band at all and is
   reported before any margin is computed.
4. Build the two margins and compare each against its policy minimum,
   absorbing the representation error of a ratio that sits exactly on
   its bound rather than failing it.
5. Compare the firing pulse duration against the duration the all fire
   level is specified over, and raise a finding when the pulse is
   shorter.
6. Derive the firing pulse energy and the no fire bridge dissipation
   where the resistance is stated, and close with a verdict listing
   every absent parameter and every consistency finding.

## Pitfalls

- Quoting an all fire current with no duration. The guarantee is a
  current held for a time; without the time the number cannot be used
  to size a pulse, and a short pulse at that current is not an all
  fire condition.
- Choosing a firing current inside the band between the levels. Above
  no fire and below all fire the device is unspecified, so the design
  has handed the outcome to the hardware and kept the paperwork.
- Defaulting an absent parameter to zero. A missing no fire level
  treated as zero makes every stray current look compliant; a missing
  one has to stay missing and be reported.
- Comparing the no fire level against the firing circuit only. The
  current that has to stay below it is the largest any path can apply,
  including a bridge continuity monitor, which is usually the one
  nobody added to the list.
- Failing a margin that lands exactly on its minimum. A ratio of two
  declared floats can sit a few units in the last place either side of
  the bound, so the comparison absorbs that error while the policy
  minimum itself stays untouched.

## Behavior contract (gate 3)

Parameter validation, completeness against the expected set, policy
resolution, level ordering, the all fire and no fire margins, the
pulse duration check, the derived pulse energy and no fire
dissipation, and the compliance verdict are exercised by the gate 3
contract test:
scripts/test_e2021_actuator_firing_parameter_specification.py against
scripts/e2021_actuator_firing_parameter_specification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_actuator_firing_parameter_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
