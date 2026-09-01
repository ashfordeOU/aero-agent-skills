---
name: gnc-autonomy
description: "Use when a task concerns guidance, navigation, and control for aerospace vehicles: guide the router to the gnc-autonomy pack: orbit-dynamics Hohmann and J2 drift, rendezvous-phasing phasing maneuvers, attitude-dynamics quaternion kinematics, navigation-frames ECEF/NED/WGS-84, inertial-navigation INS drift and Schuler, dilution-of-precision GDOP/PDOP, python-control-design PID margins, root-locus-design closed-loop poles, state-space-analysis controllability, pid-control-design Ziegler-Nichols, lqr-design Riccati gains, dymos-trajectory pseudospectral optimization, proportional-navigation the PN law, command-to-line-of-sight CLOS guidance, pursuit-guidance capture conditions, kalman-filter-design state estimation. Trigger: GNC, navigation, control, orbit dynamics, Hohmann, rendezvous, attitude dynamics, quaternion, ECEF/NED/WGS-84, INS, Schuler, dilution of precision, GDOP, PID, root locus, controllability, proportional navigation, command to line of sight, pursuit guidance, kalman filter, state estimation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: ecss
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; router/entry point for the gnc-autonomy domain pack"
metadata:
  domain: gnc-autonomy
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# GNC and autonomy domain pack (router)

Route here when the task is guidance, navigation, and control:
orbital mechanics, control system design, trajectory optimization,
or guidance laws.

## Domain

GNC and autonomy: space orbit dynamics (propagation, maneuvers, J2),
rendezvous phasing, navigation frames (ECEF/NED/geodetic), inertial
navigation, classical control design (margins, tuning), state-space
control (root locus, LQR), pseudospectral trajectory optimization,
and guidance laws (proportional navigation, pursuit).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| gnc-autonomy/space/orbit-dynamics | Orbit dynamics | Hohmann delta-v, vis-viva, J2 drift, transfer time |
| gnc-autonomy/space/rendezvous-phasing | Rendezvous phasing | phasing orbit, catch-up maneuver, drift time, rendezvous planning |
| gnc-autonomy/space/attitude-dynamics | Attitude dynamics | quaternion kinematics, Euler equations, inertia tensor, nutation, gravity-gradient torque, momentum wheel |
| gnc-autonomy/navigation/navigation-frames | Navigation frames | ECEF, NED, geodetic conversion, Earth rotation, WGS-84 |
| gnc-autonomy/navigation/inertial-navigation | Inertial navigation | INS mechanization, strapdown, gyro drift, accelerometer bias, Schuler period, alignment, INS/GPS integration |
| gnc-autonomy/navigation/dilution-of-precision | Dilution of precision | GDOP, PDOP, HDOP, VDOP, TDOP, satellite geometry, elevation mask, UERE, subset selection |
| gnc-autonomy/control/python-control-design | Control design | PID tuning, gain/phase margins, stability checks |
| gnc-autonomy/control/root-locus-design | Root locus design | closed-loop poles vs gain, gain for damping ratio, stability from root locus |
| gnc-autonomy/control/state-space-analysis | State space analysis | controllability, observability, state transition matrix, eigenvalues, canonical forms |
| gnc-autonomy/control/pid-control-design | PID control design | Ziegler-Nichols gains, ultimate gain/period, anti-windup, pole placement |
| gnc-autonomy/optimal-control/lqr-design | LQR design | Riccati gain, quadratic cost weights, closed-loop stability |
| gnc-autonomy/optimal-control/dymos-trajectory | Trajectory optimization | dymos phases, convergence, launch/ascent delta-v bands |
| gnc-autonomy/guidance/proportional-navigation | Proportional navigation | closing velocity, line of sight rate, navigation constant, commanded acceleration |
| gnc-autonomy/guidance/pursuit-guidance | Pursuit guidance | pure pursuit aim heading, wrapped guidance error, lead pursuit lead angle, capture condition, intercept time |
| gnc-autonomy/navigation/kalman-filter-design | Kalman filter design | kalman gain, innovation variance, error covariance, process noise, measurement noise, state estimation |
| gnc-autonomy/guidance/command-to-line-of-sight | Command to line of sight | CLOS guidance, line of sight angle, steering command, LOS error |
| gnc-autonomy/guidance/impact-point-prediction | Impact point prediction | ballistic range equation, time of flight, impact coordinates, launch speed and angle sensitivity |
| gnc-autonomy/guidance/midcourse-guidance | Midcourse guidance | midcourse guidance, waypoint steering, trajectory shaping, velocity to be gained, zero effort miss, handover, turn rate limit |
| gnc-autonomy/control/lead-lag-compensation | Lead lag compensation | phase lead/lag compensator design, phase margin boost, gain crossover frequency, steady state error constant |
| gnc-autonomy/control/frequency-response-design | Frequency response design | bode magnitude and phase, gain/phase crossover frequencies, gain margin, phase margin, stability from the margins |
| gnc-autonomy/control/gain-scheduling | Gain scheduling | gain schedule breakpoints, scheduling variable, dynamic pressure and Mach scheduling, gain interpolation |
## Routing guidance

- Orbit and maneuver questions route to the orbit-dynamics sub-skill.
- Phasing and rendezvous planning questions route to the
  rendezvous-phasing sub-skill.
- Attitude dynamics, quaternion kinematics, and momentum questions
  route to the space attitude-dynamics sub-skill.
- Coordinate-frame and navigation-solution questions (ECEF/NED/geodetic,
  WGS-84) route to the navigation navigation-frames sub-skill.
- Inertial navigation, drift, and Schuler questions route to the
  navigation inertial-navigation sub-skill.
- DOP, satellite geometry, and subset-selection questions route to the
  navigation dilution-of-precision sub-skill.
- Controller design and margin questions route to the
  python-control-design sub-skill.
- Root-locus questions (pole trajectories, gain for target damping)
  route to the control root-locus-design sub-skill.
- State-space controllability, observability, transition-matrix, and
  canonical-form questions route to the control state-space-analysis
  sub-skill.
- PID gain tuning, Ziegler-Nichols, and anti-windup questions route to
  the control pid-control-design sub-skill.
- LQR and Riccati-gain questions route to the optimal-control
  lqr-design sub-skill.
- Optimal control and trajectory questions route to the
  dymos-trajectory sub-skill.
- Proportional navigation and intercept guidance questions route to
  the guidance proportional-navigation sub-skill.
- Pure pursuit, lead pursuit, and capture-condition questions route
  to the guidance pursuit-guidance sub-skill.
- Ballistic impact point, range equation, time of flight, and launch
  speed and angle sensitivity questions route to the guidance
  impact-point-prediction sub-skill.
- Midcourse waypoint steering, trajectory shaping, velocity-to-be-gained,
  zero-effort-miss, and terminal handover questions route to the guidance
  midcourse-guidance sub-skill.
- Certification and item-level assurance questions route to the
  avionics or systems-engineering-safety packs.

- Kalman filtering, state estimation, and sensor fusion questions route to the navigation kalman-filter-design sub-skill.
- Command-to-line-of-sight and LOS error steering questions route to the guidance command-to-line-of-sight sub-skill.
- Phase lead/lag compensator, phase margin boost, crossover placement, and steady state error constant questions route to the control lead-lag-compensation sub-skill.
- Bode frequency response, gain crossover, phase crossover, gain margin, and phase margin questions route to the control frequency-response-design sub-skill.
- Gain schedule breakpoint tables, scheduling variables (dynamic pressure, Mach), and gain interpolation questions route to the control gain-scheduling sub-skill.
## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
