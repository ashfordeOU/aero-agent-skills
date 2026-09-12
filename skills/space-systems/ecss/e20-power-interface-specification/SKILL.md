---
name: e20-power-interface-specification
description: "Use when define and check the internal and external power interfaces of a spacecraft electrical power subsystem under ECSS-E-ST-20C clause 5.4: categorize each interface as internal to the subsystem or external to a user, confirm the specification carries every mandatory field including source and load impedance, compute the harness drop so the delivered voltage stays inside the load's operating window across the current range, derive the constant-power load's negative-incremental input impedance, and evaluate the source-to-load impedance separation in decibels against the stability margin the interface must hold. Trigger: ecss, e-st-20c-clause-5-4, power-interface-specification, source-impedance, load-impedance, impedance-stability-margin, harness-voltage-drop, constant-power-load, bus-interface-control-document."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-interface-specification, power-interface-specification, source-impedance, load-impedance, impedance-stability-margin, harness-voltage-drop, constant-power-load]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Power Interface Specification (space-systems/ecss/e20-power-interface-specification)

Use when the task is the clause 5.4 power-interface definition of
ECSS-E-ST-20C -- writing down what crosses each internal and external
power boundary of the electrical power subsystem, including the source
impedance the supplying side presents and the load impedance the
receiving side presents, and checking that the pair is both statically
and dynamically compatible.

## Domain quick reference

- Every power boundary is categorized once as internal (array to
  regulator, battery to bus, regulator to bus, internal distribution)
  or external (subsystem to user equipment, payload power feed,
  umbilical, ground support equipment, launcher interface). The
  category sets the mandatory field list: both carry nominal voltage,
  voltage range, current limit, source impedance, load impedance and
  the return and bonding definition; an internal interface adds the
  regulation mode, and an external interface adds connector and pin
  allocation plus the isolation and protection provision. A field left
  off the interface sheet is a finding in itself, not a detail to
  settle later.
- The static check is the delivered voltage. The receiving end sees
  the source voltage less the harness drop, current times the
  round-trip harness resistance, and that must stay inside the load's
  operating window at both the minimum and the maximum interface
  current -- the worst case is usually maximum current at minimum
  source voltage, not the nominal point.
- The dynamic check is impedance separation. A regulated user
  equipment behaves as a constant-power load, whose input impedance
  magnitude is the square of the interface voltage divided by the
  drawn power and whose incremental slope is negative: drawing more
  current at a lower voltage is the mechanism that destabilises an
  otherwise stable source. The supplying side presents an output
  impedance that rises with frequency, approximated from its series
  resistance and inductance at the frequency of interest.
- The separation is reported in decibels as twenty times the base-ten
  logarithm of load impedance over source impedance. A positive margin
  above the required minimum means the source looks stiff compared to
  the load and the cascade is stable; a margin at or below the
  requirement is a finding against the interface, not against either
  box on its own.

## Workflow

1. Categorize the interface as internal or external; reject an
   interface kind that is neither before it reaches the field check.
2. Build the mandatory field list for that category and list every
   field the interface sheet does not carry.
3. Compute the harness drop at the maximum interface current from the
   round-trip harness resistance, subtract it from the minimum source
   voltage, and flag a delivered voltage below the load's minimum.
4. Repeat at the minimum interface current against the maximum source
   voltage and flag a delivered voltage above the load's maximum.
5. Derive the load impedance magnitude for the constant-power draw at
   the interface voltage, and the source output impedance magnitude
   from its series resistance and inductance at the analysis
   frequency.
6. Compute the separation in decibels and flag a margin below the
   minimum the interface requires.
7. Aggregate the specification, static and stability findings; the
   interface is specified and compatible only when all three lists are
   empty.

## Pitfalls

- Recording a single nominal voltage and calling the interface
  specified -- without the source and load impedance the receiving
  side cannot check stability, and clause 5.4 asks for the impedance
  pair explicitly.
- Checking the harness drop only at nominal current and nominal source
  voltage, which hides the real corner: maximum current drawn while
  the source sits at its lower regulation limit.
- Treating a constant-power load as a resistor because its impedance
  magnitude has the units of ohms; the negative incremental slope is
  the whole reason the separation margin exists, and a resistive model
  reports a stable cascade that is not.
- Comparing source and load impedance as a bare ratio and reading any
  value above one as a pass; the requirement is a margin in decibels,
  so a ratio of 1.1 is roughly 0.8 dB and fails almost every practical
  requirement.
- Evaluating the source impedance at direct current only; it rises
  with frequency through the series inductance, and the crossover
  region where the margin is thinnest sits well above zero hertz.

## Behavior contract (gate 3)

The interface categorization, mandatory-field, harness-drop,
constant-power-impedance and separation-margin logic is exercised by
the gate 3 contract test:
scripts/test_e20_power_interface_specification.py against
scripts/e20_power_interface_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_power_interface_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
