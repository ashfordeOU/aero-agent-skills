---
name: swept-wing-aerodynamics
description: "Use when you must apply wing sweep effects for high-speed aerodynamics: compute the simple sweep theory cosine corrections for the lift curve slope and the section Mach number, find the effective Mach number and the velocity components normal and tangential to the leading edge, and estimate the critical Mach number increase that sweep provides over the unswept wing. Produces the swept wing lift slope, the effective Mach number, and the critical Mach estimate that feed transonic cruise and high-speed wing design. Trigger: swept wing, sweep angle, leading edge sweep, simple sweep theory, critical Mach, effective Mach."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [swept-wing, sweep-angle, critical-mach, simple-sweep-theory, leading-edge-sweep]
  version: 0.1.0
  author: AeroSkills
---

# Swept Wing Aerodynamics (aerodynamics/high-speed/swept-wing-aerodynamics)

Use when the task is wing sweep effects for high-speed flight: simple
sweep theory, the cosine corrections on lift curve slope and section
Mach, and the critical Mach number increase that sweep provides.

## Domain quick reference

- Simple sweep theory: a yawed infinite wing behaves like an unswept
  wing at the velocity component normal to the leading edge. The sweep
  angle Lambda is the angle between the leading edge and the plane
  perpendicular to the freestream; all corrections below use
  cos(Lambda).
- Effective (section) Mach: M_eff = M * cos(Lambda). The section sees
  a reduced Mach number, which is the mechanism behind the critical
  Mach increase.
- Velocity components about the leading edge: normal
  M_n = M * cos(Lambda), tangential M_t = M * sin(Lambda).
- Lift curve slope (simple sweep theory): a_swept = a0 * cos(Lambda),
  a0 the unswept section slope (2 * pi for thin sections). The
  lift-curve-slope leaf applies this as one step of its correction
  chain; this leaf owns the sweep-specific analysis and design forms.
- Critical Mach: M_crit,swept = M_crit,0 / cos(Lambda), from the
  condition that the section reaches its critical Mach at the reduced
  effective Mach. A 35 degree sweep (cos = 0.819) raises a 0.7
  section critical Mach to about 0.85.
- Design form: Lambda = acos(M_crit,0 / M_crit,target) gives the sweep
  angle needed to reach a target critical Mach.
- Range: the cosine corrections are subsonic small-disturbance
  results, valid for 0 <= Lambda < 90 degrees with the effective Mach
  kept subsonic; a swept critical Mach at or above 1 is out of domain.
- Validation anchor: NACA Report 824 (public domain) supplies the
  unswept section data that the cosine corrections act on.

## Workflow

1. Confirm the leading-edge sweep angle Lambda in degrees and the
   flight Mach number M.
2. Compute cos(Lambda) with cos_sweep.
3. Reduce the section Mach with effective_mach, or take both
   components with mach_components.
4. Correct the section lift slope with swept_lift_slope.
5. Estimate the critical Mach with critical_mach, or size the sweep
   for a target critical Mach with sweep_for_critical_mach.
6. Report the swept values next to the unswept baseline so the change
   that sweep buys is visible.

## Pitfalls

- Applying the cosine correction to dynamic pressure: simple sweep
  theory acts on Mach number and on slope, not on q.
- Using a sweep angle measured from the freestream instead of the
  leading edge: the corrections need the leading-edge sweep.
- Accepting sweep at or beyond 90 degrees, where cos(Lambda) <= 0.
- Using the swept critical Mach formula when the result would reach or
  exceed 1: the wing is transonic or supersonic there and simple sweep
  theory no longer applies.
- Reading a section polar at the free-stream Mach: the section behaves
  at M * cos(Lambda), not at M.
- Treating cos(Lambda) as exact for a finite wing: real wings need
  planform and leading-edge suction corrections; the cosine is the
  first-order estimate.
- Reusing the unswept critical Mach as the wing value: the
  / cos(Lambda) step is what quantifies the margin sweep buys.
- Assuming sweep cures all transonic problems: the root and tip
  regions still see three-dimensional flow and local supercritical
  conditions.

## Behavior contract (gate 3)

The sweep logic is exercised by the gate 3 contract test:
scripts/test_swept_wing_aerodynamics.py against
scripts/swept_wing_aerodynamics_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_swept_wing_aerodynamics.py

## Compliance

- Simple sweep theory and the cosine corrections are standard subsonic
  wing methodology (public-domain textbook content, e.g. Anderson,
  Fundamentals of Aerodynamics); NACA TR 824 is referenced as the
  pack's public-domain anchor for the section data, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
