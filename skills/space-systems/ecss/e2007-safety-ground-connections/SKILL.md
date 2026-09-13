---
name: e2007-safety-ground-connections
description: "Use when verify that the protective-earth provision presented on an electromagnetic-compatibility bench mirrors the installation practice of the flight build under ECSS-E-ST-20-07C clause 5.2.6.4: categorize the safety-ground provision as protective-earth-terminal, protective-earth-pin, mounting-base-bond or unbonded, confirm the bench provision matches the flight one down to terminal count and earth-pin designation, size the protective-earth conductor adiabatically against prospective fault-current and clearing-time, sum the safety-ground path resistance across its segments, and flag a protective-earth conductor shared as a signal-return. Trigger: ecss, e-st-20-07c, protective-earth-terminal, protective-earth-pin, safety-ground-path, fault-current-sizing, earth-conductor-adiabatic, bonding-path-resistance, emc-bench-setup."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-safety-ground-connections, protective-earth-terminal, protective-earth-pin, safety-ground-path, fault-current-sizing, earth-conductor-adiabatic, bonding-path-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Safety Ground Connections (space-systems/ecss/e2007-safety-ground-connections)

Use when the task is the protective-earth provision of
ECSS-E-ST-20-07C clause 5.2.6.4 -- showing that the safety-ground
connection a unit is given on an electromagnetic-compatibility bench is
the one the real installation uses, sized for the fault it has to carry
and not doubling as a signal return.

## Domain quick reference

- A safety-ground connection is a fault path, and its job is to hold
  exposed conductive surfaces near the structure potential long enough
  for the upstream protection to clear. That makes it a two-property
  item: it must carry the prospective fault-current for the clearing
  time without melting, and it must present a low enough resistance
  that the touch potential stays bounded while it does so.
- Four provisions are distinguished. A protective-earth-terminal is a
  dedicated stud or lug on the unit housing. A protective-earth-pin is
  a designated contact inside a connector, carried on the harness. A
  mounting-base-bond takes the reference through the unit feet into the
  mounting panel. Unbonded means no provision was declared at all,
  which is a finding rather than a category the bench may choose.
- Mirroring is the whole point of the clause. A bench that improvises a
  crocodile clip onto a housing screw, where the flight build lands on
  a dedicated terminal, changes the fault-path impedance and the
  common-mode current division at the same time, so both the emission
  result and the injected-current distribution stop describing flight.
  Mirroring covers the provision family, the terminal count and the
  earth-pin designation set, not merely the presence of some green
  wire.
- Conductor sizing follows the adiabatic relation: the minimum
  cross-section grows with the fault-current and with the square root
  of the clearing-time, and falls with the material constant of the
  conductor and its insulation. A conductor sized for steady-state
  operating current is routinely too small for the fault it must
  survive.
- The path resistance is the sum over segments -- conductor runs,
  terminal interfaces, connector contact resistance, the strap into the
  bench structure. Segments given as geometry are resolved from
  resistivity, length and cross-section; segments given as a measured
  resistance are taken as measured.
- A protective-earth conductor that also carries a signal-return puts
  return current into the safety path, which both raises the reference
  potential of every circuit sharing it and defeats the fault-detection
  behaviour the path exists for.

## Workflow

1. Categorize the flight safety-ground provision and the bench
   provision from their declared hardware: terminal stud count, earth
   pin designations, or a mounting-base bond. Reject a record that
   declares hardware inconsistently.
2. Compare the two provisions. Flag a family mismatch, a differing
   terminal count and any earth-pin designation present on one side and
   absent on the other.
3. Flag an unbonded provision on either side; that is a missing
   connection, never an acceptable arrangement.
4. Compute the minimum protective-earth conductor cross-section from
   the prospective fault-current, the clearing-time and the material
   constant, then compare the installed cross-section against it.
5. Resolve every segment of the safety-ground path into a resistance
   and sum them, then compare the total against the declared interface
   limit.
6. Flag a protective-earth conductor declared as also carrying a
   signal-return.
7. Aggregate the findings. The provision mirrors the installation only
   when the finding list is empty.

## Pitfalls

- Sizing the protective-earth conductor from the operating current.
  The sizing case is the fault, and the adiabatic relation grows with
  the square root of the clearing-time, so a slow upstream protection
  device can double the required cross-section.
- Accepting any green wire as a mirror of the flight provision. A
  terminal and a connector pin place the fault path in different
  places relative to the unit housing, and swapping one for the other
  moves the common-mode current away from where it flows in flight.
- Summing only the conductor runs and ignoring the interfaces. The
  terminal and contact resistances frequently dominate the total on a
  short bench run, so a path that looks adequate on conductor
  resistance alone can still exceed the interface limit.
- Reading a measured path resistance under the limit as sufficient on
  its own. Resistance and cross-section are independent requirements;
  a thin conductor can measure low and still fail the fault-survival
  case.
- Letting the safety path double as a signal-return because it is
  convenient on the bench. The shared current makes the reference
  potential circuit-dependent and hides exactly the fault the path is
  there to reveal.

## Behavior contract (gate 3)

The provision categorization, installation-mirroring comparison,
adiabatic conductor sizing, path-resistance summation and aggregate
assessment logic is exercised by the gate 3 contract test:
scripts/test_e2007_safety_ground_connections.py against
scripts/e2007_safety_ground_connections_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_safety_ground_connections.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
