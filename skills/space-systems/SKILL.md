---
name: space-systems
description: "Use when a task concerns space systems engineering for European space projects: guide the router to the space-systems pack. ECSS software-engineering criticality, software-verification verification depth, systems-engineering lifecycle gates, power-thermal-budget EPS and battery sizing, communication-link-budget link margin, thermal-design radiator sizing, command-data-handling telemetry, sun-pointing sun vector geometry, star-tracker star identification, attitude-control-sizing reaction wheels, attitude-determination-triad TRIAD, magnetorquer-control B-dot detumbling, sun-synchronous-inclination J2 nodal regression, keplerian-elements orbital elements, ground-track-repeat repeat ground track, eclipse-time duration and shadow fraction. Trigger: space systems, ECSS, power budget, battery, link budget, thermal, telemetry, sun pointing, star tracker, attitude control, TRIAD, attitude determination, magnetorquer, sun synchronous, inclination, orbital elements, ground track, eclipse time, beta angle."
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
series, spacecraft subsystem budgeting, or orbit selection and
elements.

## Domain

Space systems and astrodynamics: spacecraft subsystem engineering,
European space software assurance (ECSS-E-ST-40C software engineering,
Q-ST-80C product assurance), systems-engineering lifecycle management
(ECSS-E-ST-10C), electrical power and thermal subsystem sizing,
communication link budgets, attitude control, sun-synchronous orbit
selection, and classical orbital element determination.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| space-systems/ecss/software-engineering | ECSS space software | criticality A-D, lifecycle gates, heritage reuse |
| space-systems/ecss/software-verification | ECSS software verification | verification methods, depth by criticality, verification records |
| space-systems/ecss/systems-engineering | ECSS systems engineering | lifecycle phases 0-F, MDR/PRR/SRR/PDR/CDR/QR/AR/FRR gates |
| space-systems/subsystems/power-thermal-budget | Power and thermal budget | EPS sizing, eclipse, battery and solar array budgets |
| space-systems/subsystems/communication-link-budget | Communication link budget | EIRP, free-space path loss, C/N0, Eb/N0 margin, data rate |
| space-systems/subsystems/thermal-design | Thermal design | thermal balance, radiator sizing, component temperatures |
| space-systems/subsystems/command-data-handling | Command and data handling | telemetry framing, CCSDS packets, onboard storage, downlink budget, CRC, data bus |
| space-systems/adcs/sun-pointing | Sun pointing | sun vector geometry, pointing constraints, solar beta angle |
| space-systems/adcs/star-tracker | Star tracker | star identification, star catalog, centroid matching, boresight error, lost in space vs tracking |
| space-systems/adcs/attitude-control-sizing | Attitude control sizing | reaction wheels, momentum management, control torque sizing |
| space-systems/adcs/magnetorquer-control | Magnetorquer control | B-dot detumbling, dipole moment, torque from magnetic field, coil sizing |
| space-systems/orbit-mechanics/sun-synchronous-inclination | Sun-synchronous inclination | J2 nodal regression, retrograde inclination, local time of ascending node |
| space-systems/orbit-mechanics/keplerian-elements | Keplerian orbital elements | rv2coe state-vector conversion, semimajor axis, eccentricity, inclination, RAAN, argument of periapsis, true anomaly, orbital period, periapsis/apoapsis |
| space-systems/orbit-mechanics/eclipse-time | Eclipse time | earth shadow, beta angle, shadow fraction, eclipse duration, daylight fraction |
| space-systems/adcs/attitude-determination-triad | TRIAD attitude determination | TRIAD algorithm, attitude matrix, vector observations, body and reference vectors |
| space-systems/orbit-mechanics/ground-track-repeat | Ground track repeat | repeat ground track, nodal precession, orbital period, integer revolutions per day |

## Routing guidance

- Space software questions (criticality classification, assurance rigor,
  lifecycle reviews, heritage reuse) route to the ECSS software
  sub-skill.
- ECSS software-verification questions (methods, depth, records) route
  to the ecss software-verification sub-skill.
- Lifecycle and phase-gate questions (reviews, readiness) route to the
  ecss systems-engineering sub-skill.
- Power and thermal budgeting questions (EPS sizing, eclipse, battery,
  solar array) route to the power-thermal-budget sub-skill.
- Communication link budget questions (EIRP, path loss, link margin)
  route to the communication-link-budget sub-skill.
- Thermal design questions (radiator sizing, component temperatures)
  route to the thermal-design sub-skill.
- Telemetry, CCSDS framing, storage, and downlink questions route to
  the subsystems command-data-handling sub-skill.
- Sun vector and pointing questions route to the sun-pointing
  sub-skill; reaction wheel and momentum questions route to the
  attitude-control-sizing sub-skill; star identification and boresight
  questions route to the adcs star-tracker sub-skill; detumble and
  dipole questions route to the adcs magnetorquer-control sub-skill.
- Sun-synchronous orbit and J2 nodal regression questions route to the
  sun-synchronous-inclination sub-skill.
- Classical orbital element questions (state vector to elements,
  RAAN, argument of periapsis, true anomaly, period) route to the
  keplerian-elements sub-skill.
- GNC, propulsion, and structural questions route to their domain
  packs (gnc-autonomy, propulsion, structures).

- Eclipse duration, earth shadow, beta angle, and shadow fraction questions route to the orbit-mechanics eclipse-time sub-skill.
- TRIAD, attitude-matrix, and vector-observation questions route to the adcs attitude-determination-triad sub-skill.
- Repeat ground track and integer-revolutions-per-day questions route to the orbit-mechanics ground-track-repeat sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
