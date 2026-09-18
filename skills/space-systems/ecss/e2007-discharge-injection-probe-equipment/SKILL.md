---
name: e2007-discharge-injection-probe-equipment
description: "Determine whether the dedicated pulse generator and coaxial cabling listed for an ECSS-E-ST-20-07C clause 5.4.13.2 injection-probe discharge test can actually deliver the pulse: derive the chain bandwidth from the required rise time, convert the cable mismatch and the skin-effect attenuation into delivered amplitude, size the generator open-circuit voltage and the connector rating from the current the probe must push through its insertion impedance, then categorize every declared item as adequate, marginal or inadequate and name the one that governs. Use when assembling or reviewing an injection-probe discharge bench. Trigger: ecss, e-st-20-07c, discharge-injection-probe-equipment, discharge-pulse-generator-sizing, injection-probe-coaxial-cabling, probe-insertion-impedance-drive, injection-chain-bandwidth, coaxial-mismatch-loss-budget."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-discharge-injection-probe-equipment, discharge-pulse-generator-sizing, injection-probe-coaxial-cabling, probe-insertion-impedance-drive, injection-chain-bandwidth, coaxial-mismatch-loss-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Discharge Injection-Probe Equipment (space-systems/ecss/e2007-discharge-injection-probe-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause
5.4.13.2 -- the dedicated pulse generator and the coaxial cabling that
the injection-probe method of applying a discharge pulse to a harness
needs, and whether a particular bench of them can carry the pulse the
test plan asks for.

## Domain quick reference

- The generator is dedicated for a reason. A discharge pulse is defined
  by its edge as much as by its amplitude, and a bench supply or a
  general-purpose function generator is specified for settled output,
  not for a nanosecond-class edge into a reactive load. The bench is
  sized from the edge first and the amplitude second.
- The edge sets the bandwidth of everything downstream. A rise time
  implies a bandwidth of roughly 0.35 divided by that rise time, and
  every item between the generator and the harness -- cable, connector,
  probe -- has to pass it. The slowest item in the chain is the edge
  that reaches the harness, whatever the generator is capable of on its
  own.
- The cabling is coaxial because the pulse has to arrive undistorted,
  not merely at amplitude. A cable of the wrong characteristic
  impedance reflects part of the edge back up the run and returns it
  late, so the probe sees a stepped waveform. That defect is measured
  as a mismatch rather than as a loss: the power lost is small while the
  waveform damage is not, so the mismatch carries its own tight budget.
- Above a few megahertz coaxial loss is skin-effect dominated, so it
  rises with the square root of frequency. A loss figure quoted at a
  reference frequency has to be scaled to the chain bandwidth and
  multiplied by the run length before it means anything for this test.
- What the generator has to produce is set by the probe, not by the
  harness. The probe presents an insertion impedance; the drive needed
  is the required injected current through that impedance, raised again
  by everything the cable run took out. The connectors on that run are
  rated against the same drive voltage, because they see it first.
- Items are categorized, not merely counted. An item that exactly meets
  its requirement is usable today with nothing left for cable ageing or
  a colder lab, and it is reported as marginal so the bench owner can
  see where the next failure will come from.

## Workflow

1. Derive the chain bandwidth from the pulse rise time the test plan
   requires.
2. Compute the cable mismatch against the system impedance the probe
   and generator are built for, as a reflection coefficient, a VSWR and
   a mismatch loss in dB.
3. Scale the quoted cable attenuation from its reference frequency to
   the chain bandwidth and multiply by the run length.
4. Sum the mismatch and attenuation into a total loss and convert it to
   the fraction of drive amplitude that survives to the probe.
5. Compute the generator open-circuit voltage needed: the required
   injected current through the probe insertion impedance, divided by
   that surviving fraction.
6. Compare each declared item -- generator voltage, generator rise time,
   optional generator bandwidth, cable match, cable attenuation,
   connector rating -- with its requirement, inverting the ratio for the
   quantities that must not be exceeded so one categorization covers the
   whole bench.
7. Categorize each as adequate, marginal or inadequate, absorbing an
   exact equality with a named tolerance, and report the item with the
   least headroom as the governing one.

## Pitfalls

- Sizing the generator on amplitude alone. An adequate-looking voltage
  behind a slow edge injects a pulse the harness never sees as a
  discharge.
- Quoting a cable loss figure without a frequency. The same run costs
  several times more at the chain bandwidth than at the reference point
  the datasheet used.
- Budgeting the impedance mismatch as a power loss. A tenth of a
  decibel of reflected power is a visible step on the injected edge, so
  the match carries a far tighter budget than the attenuation does.
- Rating the connectors against the harness current instead of the
  generator drive. The connectors sit at the top of the run and see the
  full drive voltage before the cable takes any of it out.
- Treating an item that exactly meets its requirement as a pass with no
  comment. It is the item that will govern the bench the first time
  anything ages.

## Behavior contract (gate 3)

The rise-time bandwidth derivation, reflection coefficient, VSWR and
mismatch loss, frequency-scaled cable attenuation, delivered-amplitude
fraction, required drive voltage, per-item ratio and categorization, and
the governing-item selection are exercised by the gate 3 contract test:
scripts/test_e2007_discharge_injection_probe_equipment.py against
scripts/e2007_discharge_injection_probe_equipment_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_discharge_injection_probe_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
