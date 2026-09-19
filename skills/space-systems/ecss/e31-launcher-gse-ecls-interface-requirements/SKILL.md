---
name: e31-launcher-gse-ecls-interface-requirements
description: "Define the thermal-control interfaces to the launch vehicle, ground support equipment and crew life support under ECSS-E-ST-31C clauses 4.3.7 to 4.3.9. Use when fairing conditioned air, a test cooling loop or a crew-reachable surface has to be specified: take the air temperature rise the pre-launch dissipation adds and grade the item against its non-operating limit, hold the supply dew point clear of the coldest surface, subtract thermal growth and deflection from the dynamic envelope clearance, size the ground coolant flow and its capacity margin, and grade touch temperature by material group and contact duration. Trigger: ecss, e-st-31c, fairing-conditioned-air-interface, launcher-thermal-envelope-clearance, fairing-condensation-dew-point, gse-test-cooling-interface, gse-capacity-margin, crew-touch-temperature-limit, ecls-thermal-interface."
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
  tags: [ecss, e-st-31-thermal-scope, e31-launcher-gse-ecls-interface-requirements, fairing-conditioned-air-interface, launcher-thermal-envelope-clearance, fairing-condensation-dew-point, gse-test-cooling-interface, gse-capacity-margin, crew-touch-temperature-limit, ecls-thermal-interface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Launcher, GSE and Life Support Interface Requirements (space-systems/ecss/e31-launcher-gse-ecls-interface-requirements)

Use when the task is the thermal control subsystem interfaces that point
outside the spacecraft under ECSS-E-ST-31C clauses 4.3.7 to 4.3.9 — the
conditioned air and thermal envelope the launch vehicle provides, the
cooling or heating the ground support equipment provides during test, and
the touch temperatures a crew-tended item owes the life support subsystem.

## Domain quick reference

- Fairing conditioned air is a flow interface, not a temperature. The air
  picks up whatever the spacecraft dissipates on the pad, so the item sees
  the inlet temperature plus Q / (m_dot * cp). Specifying only the inlet
  band leaves the rise unbounded, and a starved flow rate turns a
  comfortable 18 C supply into a non-operating overtemperature.
- The same interface carries a humidity requirement. If the supply dew
  point is not held clear of the coldest exposed surface, water condenses
  inside the fairing onto optics, connectors and blankets. The clearance
  is a temperature difference, and the requirement is stated as a margin
  in kelvin, not as a relative humidity alone.
- The thermal envelope is the static envelope minus what temperature does
  to it. Growth over the ground-to-flight swing plus the declared
  deflection eat into the gap to the fairing dynamic envelope, and what
  remains has to clear the minimum. A long aluminium item over a sixty
  kelvin swing moves millimetres, which is the same order as the margin.
- Ground support cooling is sized twice: the coolant mass flow the test
  load demands at the allowed coolant rise, Q / (cp * dT), and the
  capacity margin of the equipment against that load. Equipment sized at
  the load with no margin cannot absorb a hotter-than-predicted article.
- Crew touch limits depend on the material, not only the temperature.
  Metal pulls heat out of skin far faster than composite or an insulator,
  so the allowable band narrows for metal and narrows again as contact
  duration goes from momentary to short to prolonged. Surfaces are
  categorized by material group and duration band before being graded.

## Workflow

1. Validate the launcher record: inlet temperature, air mass flow, pad
   dissipation, the non-operating limit, dew point and coldest surface,
   the static gap, expansion coefficient, swing, length, deflection and
   minimum clearance.
2. Compute the air temperature rise and the temperature the item reaches;
   grade it against the non-operating limit with a boundary tolerance.
3. Compute the clearance between the coldest exposed surface and the
   supply dew point and grade it against the condensation margin.
4. Compute the thermal growth over the ground-to-flight swing, subtract it
   and the deflection from the static gap, and grade the remaining
   clearance against the minimum.
5. Size the ground support coolant flow from the test load, the coolant
   heat capacity and the allowed coolant rise; compute the capacity margin
   and grade it against the required margin.
6. Put every crew-reachable surface into its material group and duration
   band, look up the allowable band and return a within-limits, hot-hazard
   or cold-hazard verdict; an unknown material group is refused.
7. Report the three interface records and the aggregated findings.

## Pitfalls

- Writing the fairing air requirement as an inlet temperature band only.
  Without a flow rate the rise across the spacecraft is undefined, and the
  launch vehicle can meet the stated requirement while the item overheats.
- Treating condensation as a launch-site weather problem. The interface
  requirement is a dew-point margin against the coldest surface the
  spacecraft presents, and the coldest surface is a thermal design output.
- Checking the envelope against the cold static dimension. The clearance
  that matters is the one left after thermal growth and deflection, and
  those are taken at the worst combination, not at ambient.
- Sizing ground support equipment at exactly the predicted test load. The
  article under test is hotter than predicted often enough that a capacity
  margin is part of the interface, not a nicety.
- Applying one touch temperature limit to every surface. A metal bracket
  and an insulating blanket at the same temperature sit on opposite sides
  of the crew limit, and prolonged contact narrows the band further.

## Behavior contract (gate 3)

Air temperature rise and reached item temperature, dew-point clearance,
thermal growth and envelope clearance, ground coolant flow and capacity
margin, touch duration banding and material-group touch verdicts, and the
three-part aggregate assessment are exercised by the gate 3 contract test:
scripts/test_e31_launcher_gse_ecls_interface_requirements.py against
scripts/e31_launcher_gse_ecls_interface_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_launcher_gse_ecls_interface_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
