---
name: space-systems
description: "Use when a task concerns space systems engineering for European space projects: guide the router to the space-systems pack, whose ECSS software-engineering sub-skill covers space software criticality and assurance, software-verification covers verification methods by criticality, systems-engineering covers lifecycle phases and review gates, power-thermal-budget covers EPS sizing, eclipse, and battery and solar array budgeting, communication-link-budget covers EIRP, free-space path loss, and link margin, thermal-design covers radiator sizing, sun-pointing covers sun vector geometry, attitude-control-sizing covers reaction wheel sizing, and sun-synchronous-inclination covers the sun-synchronous inclination from J2 nodal regression. This pack is the space counterpart of the avionics spine under the ECSS series. Trigger: space systems, spacecraft, space software, ECSS, power budget, battery sizing, EPS, link budget, path loss, thermal design, sun pointing, attitude control, sun synchronous orbit, inclination."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; router/entry point for the space-systems domain pack"
metadata:
  domain: space-systems
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Space systems domain pack (router)

Route here when the task is space systems engineering under the ECSS
series, spacecraft subsystem budgeting, or orbit selection.

## Domain

Space systems and astrodynamics: spacecraft subsystem engineering,
European space software assurance (ECSS-E-ST-40C software engineering,
Q-ST-80C product assurance), systems-engineering lifecycle management
(ECSS-E-ST-10C), electrical power and thermal subsystem sizing,
communication link budgets, attitude control, and sun-synchronous
orbit selection.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| space-systems/ecss/software-engineering | ECSS space software | criticality A-D, lifecycle gates, heritage reuse |
| space-systems/ecss/software-verification | ECSS software verification | verification methods, depth by criticality, verification records |
| space-systems/ecss/systems-engineering | ECSS systems engineering | lifecycle phases 0-F, MDR/PRR/SRR/PDR/CDR/QR/AR/FRR gates |
| space-systems/subsystems/power-thermal-budget | Power and thermal budget | EPS sizing, eclipse, battery and solar array budgets |
| space-systems/subsystems/communication-link-budget | Communication link budget | EIRP, free-space path loss, C/N0, Eb/N0 margin, data rate |
| space-systems/subsystems/thermal-design | Thermal design | thermal balance, radiator sizing, component temperatures |
| space-systems/adcs/sun-pointing | Sun pointing | sun vector geometry, pointing constraints, solar beta angle |
| space-systems/adcs/attitude-control-sizing | Attitude control sizing | reaction wheels, momentum management, control torque sizing |
| space-systems/orbit-mechanics/sun-synchronous-inclination | Sun-synchronous inclination | J2 nodal regression, retrograde inclination, local time of ascending node |

## Routing guidance

- Space software questions (criticality classification, assurance rigor,
  lifecycle reviews, heritage reuse) route to the ECSS software
  sub-skill.
- ECSS software-verification questions (methods, depth, records) route
  to the ecss software-verification sub-skill.
- Lifecycle and phase-gate questions (reviews, readiness) route to the
  ECSS systems-engineering sub-skill.
- Power, battery, and thermal budgeting questions route to the
  subsystems power-thermal-budget sub-skill.
- Communications questions (link budget, path loss, margins, data
  rate) route to the subsystems communication-link-budget sub-skill.
- Radiator and thermal balance questions route to the subsystems
  thermal-design sub-skill.
- Sun-pointing geometry and attitude constraint questions route to
  the adcs sun-pointing sub-skill.
- Reaction wheel and control torque sizing questions route to the
  adcs attitude-control-sizing sub-skill.
- Sun-synchronous orbit inclination and nodal regression questions
  route to the orbit-mechanics sun-synchronous-inclination sub-skill.
- Aircraft software and hardware questions route to the avionics pack.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
