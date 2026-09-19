---
name: e2021-actuator-voltage-withstand
description: "Verify that an actuator tolerates the full input voltage arriving through its nominal side and through its redundant side alike, under ECSS-E-ST-20-21C clause 5.6.2: raise the bus to its upper envelope, resolve the terminal voltage each side imposes from the smallest credible line drop, size current and dissipation against the declared ratings, add the cross-strapped case where both sides are energised and the drop halves, and report the margin each side actually holds. Use when a datasheet quotes one withstand figure and the drive is dual-redundant. Trigger: ecss, e-st-20-electrical-scope, actuator-voltage-withstand, nominal-side-drive, redundant-side-drive, dual-side-energisation, actuator-terminal-voltage, drive-side-asymmetry, withstand-margin-ratio."
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
  tags: [ecss, e-st-20-electrical-scope, e2021-actuator-voltage-withstand, actuator-voltage-withstand, nominal-side-drive, redundant-side-drive, dual-side-energisation, actuator-terminal-voltage, drive-side-asymmetry, withstand-margin-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuators — Actuator Voltage Withstand (space-systems/ecss/e2021-actuator-voltage-withstand)

Use when the task is the input-voltage withstand duty of ECSS-E-ST-20-21C
clause 5.6.2 -- showing that the actuator survives the full input voltage
however it is delivered, through the nominal drive side, through the
redundant drive side, or through both at once.

## Domain quick reference

- Withstand is a maximum-stress case, so the source is the bus upper
  envelope -- nominal plus the upper tolerance band plus any transient
  the power interface permits -- never the bus nominal value. A figure
  quoted at nominal understates every case the clause is about.
- The voltage that actually reaches the terminals is what the divider
  formed by the drive-path resistance and the actuator resistance
  leaves. Line resistance is therefore protective here: the worst case
  takes the SMALLEST credible drop, which is the opposite of the
  worst case used for actuation, where the largest drop starves the
  device.
- The two sides are almost never symmetric. Harness routing, connector
  count, slip rings and series switching differ between the nominal and
  redundant paths, so one side imposes more than the other and a
  single-side qualification does not cover the pair. The governing side
  is the one with the lower drop, not the one named first.
- Cross-strapping is the case a per-side view misses. With both sides
  energised the two path resistances appear in parallel, the drop falls
  again, and the terminal voltage rises above either single-side value.
  A part sized on one side can fail only in this configuration, which
  is reachable by a commanding error or a stuck-on switch.
- Voltage is not the only rating. The same terminal voltage fixes the
  current through the winding and the dissipation in it, and an
  actuator that holds off the voltage can still fail thermally when the
  command is held. Duration is graded against the declared withstand
  time whenever a commanded time is stated at all.

## Workflow

1. Raise the bus to its upper envelope: nominal, the upper tolerance as
   a fraction, and any declared transient added on top. Reject a
   tolerance quoted as a whole number rather than a fraction, because
   the error silently multiplies the envelope.
2. Declare both drive sides with the smallest credible resistance of
   each path. Reject a specification that names only one side or that
   invents a third, since the clause is about the pair.
3. Resolve the terminal voltage, current and dissipation each side
   imposes, and compare each against its declared rating. Absorb
   representation error in the comparison and never widen the rating.
4. Name the governing side and report the asymmetry between the two. An
   asymmetry beyond a few percent is itself a finding: it means the
   qualification evidence has to name which side it was taken on.
5. Run the both-sides-energised case through the parallel path
   resistance and grade it separately. Report it even when each side
   passes alone, because that is exactly the case the clause protects.
6. Where a commanded duration is stated, compare it against the rated
   withstand time and refuse to grade it when no rated time exists.

## Pitfalls

- Grading the withstand against the bus nominal. The tolerance band and
  the transient are part of the input voltage the actuator has to
  tolerate, and dropping them removes the whole stress case.
- Carrying the nominal line resistance into the withstand case. A
  larger drop lowers the terminal voltage, so using a typical or a
  worst-case-high drop makes the result optimistic; the withstand case
  wants the low end of the resistance band.
- Qualifying on one side and declaring the pair covered. The redundant
  path usually has a different length and switch count, so its terminal
  voltage differs, and the evidence has to say which path it came from.
- Ignoring simultaneous energisation because it is not a nominal
  command. It is reachable, the parallel drop is genuinely lower, and
  it produces the highest terminal voltage the actuator will ever see.
- Closing on voltage alone. Current and dissipation follow from the
  same terminal voltage, and a held command can take the winding past
  its thermal rating while the voltage rating is still satisfied.

## Behavior contract (gate 3)

The source envelope, per-side divider, current and dissipation grading,
asymmetry detection, dual-energisation case and duration check are
exercised by the gate 3 contract test:
scripts/test_e2021_actuator_voltage_withstand.py against
scripts/e2021_actuator_voltage_withstand_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2021_actuator_voltage_withstand.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
