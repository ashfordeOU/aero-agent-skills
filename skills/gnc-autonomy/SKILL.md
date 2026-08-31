---
name: gnc-autonomy
description: "Use when a task concerns guidance, navigation, and control for aerospace vehicles: guide the router to the gnc-autonomy pack, whose sub-skills cover orbit dynamics (Hohmann transfers, vis-viva, J2 perturbation), control law design (PID, gain and phase margins, stability), and trajectory optimization with pseudospectral methods. This pack is the GNC and autonomy layer of the library. Trigger: GNC, guidance navigation control, orbit dynamics, control law, PID, trajectory optimization, optimal control, Hohmann transfer, stability margins."
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
orbital mechanics, control system design, or trajectory optimization.

## Domain

GNC and autonomy: space orbit dynamics (propagation, maneuvers, J2),
classical control design (margins, tuning), and optimal control for
trajectory problems (pseudospectral collocation).

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| gnc-autonomy/space/orbit-dynamics | Orbit dynamics | Hohmann delta-v, vis-viva, J2 drift, transfer time |
| gnc-autonomy/control/python-control-design | Control design | PID tuning, gain/phase margins, stability checks |
| gnc-autonomy/optimal-control/dymos-trajectory | Trajectory optimization | dymos phases, convergence, launch/ascent delta-v bands |

## Routing guidance

- Orbit and maneuver questions route to the orbit-dynamics sub-skill.
- Controller design and margin questions route to the
  python-control-design sub-skill.
- Optimal control and trajectory questions route to the
  dymos-trajectory sub-skill.
- Certification and item-level assurance questions route to the
  avionics or systems-engineering-safety packs.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
