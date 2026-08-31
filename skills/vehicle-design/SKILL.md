---
name: vehicle-design
description: "Use when a task concerns aircraft or vehicle conceptual design and sizing: guide the router to the vehicle-design pack, whose weight-estimation sub-skill covers class-I weight estimation, weight fractions, center of gravity, and CG envelope checks for preflight weight and balance. This pack is the vehicle-level integration and sizing layer of the library. Trigger: vehicle design, aircraft design, sizing, weight estimation, weight and balance, center of gravity, CG envelope, weight fraction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; router/entry point for the vehicle-design domain pack"
metadata:
  domain: vehicle-design
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Vehicle design and integration domain pack (router)

Route here when the task is conceptual aircraft design, sizing, or
weight and balance.

## Domain

Vehicle design and integration: class-I weight estimation, weight
fractions, center of gravity and CG envelope discipline, and the
sizing loop that ties aerodynamic, structural, and performance
disciplines together.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| vehicle-design/sizing/weight-estimation | Weight estimation | class-I weights, CG, envelope, weight and balance sheets |

## Routing guidance

- Weight and CG questions route to the weight-estimation sub-skill.
- Airfoil and polar questions route to the aerodynamics pack.
- Structure and materials questions route to the structures pack.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
