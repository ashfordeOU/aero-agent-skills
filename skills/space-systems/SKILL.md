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
  author: Aero Agent Skills
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
| space-systems/subsystems/solar-array-sizing | Solar array sizing | array area from power demand, eclipse fraction, cell efficiency, packing factor, end-of-life degradation, photovoltaic panel sizing |
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
| space-systems/orbit-mechanics/hohmann-transfer | Hohmann transfer | coplanar circular-orbit transfer, transfer ellipse, delta-v budget, burn impulses, transfer time, rendezvous phase angle |
| space-systems/orbit-mechanics/orbital-perturbations | Secular orbital perturbations | J2 nodal regression, RAAN drift rate, argument-of-perigee drift, nodal period change, perturbation magnitude vs altitude |
| space-systems/orbit-mechanics/lambert-transfer | Lambert transfer | Lambert problem, two-position transfer, time of flight constraint, transfer orbit, transfer delta-v, short way, long way |
| space-systems/orbit-mechanics/satellite-coverage | Satellite coverage | access circle, swath width, off-nadir angle, minimum elevation, revisit time, coverage fraction |
| space-systems/orbit-mechanics/orbital-decay | Orbital decay | ballistic coefficient, atmospheric drag decay rate, deorbit lifetime, drag coefficient, LEO lifetime |
| space-systems/mission-design/mission-delta-v-budget | Mission delta-v budget | delta v budget, insertion, transfer, station keeping, deorbit, margin, Tsiolkovsky propellant mass, specific impulse |
| space-systems/mission-design/radiation-debris | Radiation and debris environment | radiation environment, trapped belts, total ionizing dose, single event effects, SEU rate, solar particle events, orbital debris, shielding attenuation, collision probability, mission design |
| space-systems/mission-design/entry-descent-landing | Entry descent and landing | entry descent landing, entry corridor, ballistic coefficient, entry heating, sutton-graves, deceleration, parachute, terminal velocity |
| space-systems/mission-design/launch-window-analysis | Launch Window Analysis | launch window, launch azimuth, inclination, sun-synchronous, ltan, raan, plane change, delta-v, orbital plane, direct injection, ksc. |
| space-systems/orbit-mechanics/low-thrust-spiral | Low-thrust spiral transfer | low-thrust transfer, Edelbaum, continuous thrust spiral, inclination change, spiral transfer time |
| space-systems/adcs/reaction-wheel-control | Reaction wheel control | reaction wheel control, wheel torque command, wheel momentum saturation, momentum desaturation, quaternion error feedback |
| space-systems/orbit-mechanics/clohessy-wiltshire | Clohessy-Wiltshire | Clohessy-Wiltshire, Hill equations, relative motion state transition matrix, deputy chief, two-impulse targeting, along-track drift |
| space-systems/orbit-mechanics/gravity-assist-swingby | Gravity assist swing-by | gravity assist, swing-by, hyperbolic excess velocity, turn angle, periapsis speed, delta-v gain, patched conic flyby, close approach altitude |
| space-systems/orbit-mechanics/conjunction-assessment | Conjunction assessment | conjunction assessment, time of closest approach, miss distance, probability of collision, hard body radius, combined covariance, close approach screening, actionable threshold |
| space-systems/adcs/control-moment-gyro | Control moment gyro (CMG) | control moment gyro, CMG, gimbal rate, gimbal axis, torque amplification, steering law, singularity, momentum envelope, pyramid cluster, gimbal lock |
| space-systems/subsystems/propellant-tank-sizing | Propellant tank sizing | propellant tank sizing, propellant volume, tank ullage fraction, pressurant mass, blowdown pressure range, sphere tank wall thickness |
| space-systems/subsystems/spacecraft-battery-sizing | Spacecraft battery sizing | spacecraft battery sizing, eclipse energy, depth of discharge, orbit battery capacity, series parallel cell layout, bus voltage cell count, LEO power storage |
| space-systems/orbit-mechanics/plane-change-maneuver | Plane change maneuver | plane change maneuver, inclination change delta-v, combined burn, orbital plane change, 2 v sin half inclination, plane change at apogee |

## Routing guidance

- Space software questions (criticality classification, assurance rigor,
  lifecycle reviews, heritage reuse) route to the ECSS software
  sub-skill.
- ECSS software-verification questions (methods, depth, records) route
  to the ecss software- Launch window questions route to the mission-design launch-window-analysis sub-skill.
-verification sub-skill.
- Lifecycle and phase-gate questions (reviews, readiness) route to the
  ecss systems-engineering sub-skill.
- Power and thermal budgeting questions (EPS sizing, eclipse, battery,
  solar array) route to the power-thermal-budget sub-skill.
- Solar array sizing questions (array area from power demand, cell
  efficiency, packing factor, degradation over mission life, end-of-life
  power) route to the subsystems solar-array-sizing sub-skill; overall
  EPS budgets and battery sizing stay with power-thermal-budget.
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
- Eclipse duration, earth shadow, beta angle, and shadow fraction
  questions route to the orbit-mechanics eclipse-time sub-skill.
- Repeat ground track and integer-revolutions-per-day questions route
  to the orbit-mechanics ground-track-repeat sub-skill.
- Hohmann transfer, transfer-ellipse, burn-impulse, and transfer-time
  questions route to the orbit-mechanics hohmann-transfer sub-skill.
- J2 secular perturbation questions (RAAN drift rate, argument-of-
  perigee drift, nodal period change, perturbation magnitude versus
  altitude) route to the orbit-mechanics orbital-perturbations
  sub-skill.
- Two-position orbit transfers with a fixed transfer time, Lambert
  problem solutions, and short-way/long-way branches route to the
  orbit-mechanics lambert-transfer sub-skill.
- Classical orbital element questions (state vector to elements,
  RAAN, argument of periapsis, true anomaly, period) route to the
  keplerian-elements sub-skill.
- TRIAD, attitude-matrix, and vector-observation questions route to
  the adcs attitude-determination-triad sub-skill.
- GNC, propulsion, and structural questions route to their domain
  packs (gnc-autonomy, propulsion, structures).
- Access circle, swath width, off-nadir angle, minimum elevation constraint, and coverage fraction questions route to the orbit-mechanics satellite-coverage sub-skill.
- Orbital decay and deorbit lifetime estimation, ballistic coefficient, and atmospheric drag effects on LEO spacecraft route to the orbit-mechanics orbital-decay sub-skill.
- Mission delta-v budget summation, insertion and transfer contributions, margin allocation, and Tsiolkovsky propellant mass questions route to the mission-design mission-delta-v-budget sub-skill.
- Space radiation and orbital debris environment assessment, trapped belt dose, single event effects, and collision probability over mission life route to the mission-design radiation-debris sub-skill.
- Atmospheric entry corridor, ballistic coefficient, deceleration g-loads, Sutton-Graves convective heating, and parachute terminal velocity questions route to the mission-design entry-descent-landing sub-skill.
- Control moment gyro gimbal rates, steering law, torque amplification, singularity measure, and cluster momentum envelope questions route to the adcs control-moment-gyro sub-skill.
- Propellant tank sizing questions (propellant tank sizing, propellant volume, tank ullage fraction, pressurant mass, blowdown pressure range, sphere tank wall thickness) route to the propellant-tank-sizing sub-skill.
- Spacecraft battery eclipse-energy sizing, depth of discharge, and cell layout questions route to the subsystems spacecraft-battery-sizing sub-skill.
- Orbital plane change and combined-burn delta-v questions route to the orbit-mechanics plane-change-maneuver sub-skill.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
- Low-thrust spiral and Edelbaum transfer questions route to the orbit-mechanics low-thrust-spiral sub-skill.
- Reaction-wheel attitude control laws and momentum desaturation questions route to the adcs reaction-wheel-control sub-skill.
- Clohessy-Wiltshire relative motion and two-impulse targeting questions route to the orbit-mechanics clohessy-wiltshire sub-skill.
- Gravity-assist swing-by, hyperbolic excess velocity turn angle, and flyby delta-v questions route to the orbit-mechanics gravity-assist-swingby sub-skill.
- Close-approach miss distance, probability of collision, and hard-body-radius screening questions route to the orbit-mechanics conjunction-assessment sub-skill.
