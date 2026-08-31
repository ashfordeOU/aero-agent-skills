---
name: gnc-autonomy
description: "Use when a task concerns guidance, navigation, and control for aerospace vehicles: guide the router to the gnc-autonomy pack, whose orbit-dynamics covers Hohmann transfers, vis-viva, and J2 drift, rendezvous-phasing covers phasing maneuvers, navigation-frames covers ECEF/NED/WGS-84 conversion, inertial-navigation covers INS mechanization, drift, and Schuler tuning, python-control-design covers PID tuning and margins, root-locus-design covers closed-loop poles versus gain, lqr-design covers Riccati gain and cost weights, dymos-trajectory covers pseudospectral optimization, proportional-navigation covers the PN law, and pursuit-guidance covers pure and lead pursuit with capture conditions. Trigger: GNC, guidance navigation control, orbit dynamics, Hohmann, rendezvous, phasing, navigation frames, ECEF, NED, WGS-84, inertial navigation, INS, gyro drift, Schuler, PID, gain margin, root locus, LQR, Riccati, dymos, proportional navigation, closing velocity, pursuit guidance."
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
| gnc-autonomy/navigation/navigation-frames | Navigation frames | ECEF, NED, geodetic conversion, Earth rotation, WGS-84 |
| gnc-autonomy/navigation/inertial-navigation | Inertial navigation | INS mechanization, strapdown, gyro drift, accelerometer bias, Schuler period, alignment, INS/GPS integration |
| gnc-autonomy/control/python-control-design | Control design | PID tuning, gain/phase margins, stability checks |
| gnc-autonomy/control/root-locus-design | Root locus design | closed-loop poles vs gain, gain for damping ratio, stability from root locus |
| gnc-autonomy/optimal-control/lqr-design | LQR design | Riccati gain, quadratic cost weights, closed-loop stability |
| gnc-autonomy/optimal-control/dymos-trajectory | Trajectory optimization | dymos phases, convergence, launch/ascent delta-v bands |
| gnc-autonomy/guidance/proportional-navigation | Proportional navigation | closing velocity, line of sight rate, navigation constant, commanded acceleration |
| gnc-autonomy/guidance/pursuit-guidance | Pursuit guidance | pure pursuit aim heading, wrapped guidance error, lead pursuit lead angle, capture condition, intercept time |

## Routing guidance

- Orbit and maneuver questions route to the orbit-dynamics sub-skill.
- Phasing and rendezvous planning questions route to the
  rendezvous-phasing sub-skill.
- Coordinate-frame and navigation-solution questions (ECEF/NED/geodetic,
  WGS-84) route to the navigation navigation-frames sub-skill.
- Inertial navigation, drift, and Schuler questions route to the
  navigation inertial-navigation sub-skill.
- Controller design and margin questions route to the
  python-control-design sub-skill.
- Root-locus questions (pole trajectories, gain for target damping)
  route to the control root-locus-design sub-skill.
- LQR and Riccati-gain questions route to the optimal-control
  lqr-design sub-skill.
- Optimal control and trajectory questions route to the
  dymos-trajectory sub-skill.
- Proportional navigation and intercept guidance questions route to
  the guidance proportional-navigation sub-skill.
- Pure pursuit, lead pursuit, and capture-condition questions route
  to the guidance pursuit-guidance sub-skill.
- Certification and item-level assurance questions route to the
  avionics or systems-engineering-safety packs.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
