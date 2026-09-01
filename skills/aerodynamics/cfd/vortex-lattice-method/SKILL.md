---
name: vortex-lattice-method
description: "Use when you must compute the spanwise loading of a straight trapezoidal wing with the vortex lattice method: build the horseshoe vortex panel lattice at the quarter chord, assemble the influence coefficient matrix at the three-quarter chord control points, solve the linear system for the panel circulations, and derive the spanwise lift distribution, the downwash angles, and the induced drag. Produces the circulation solution, the per-panel lift, and the lift and induced drag coefficients that gate wing aerodynamic efficiency estimates. Trigger: vortex lattice method, horseshoe vortex, panel lattice, influence coefficients, spanwise lift distribution, downwash angle, induced drag, Trefftz plane."
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
  subdomain: cfd
  tags: [vortex-lattice-method, horseshoe-vortex, panel-lattice, influence-coefficient, spanwise-lift-distribution, downwash-angle, trefftz-plane]
  version: 0.1.0
  author: AeroSkills
---

# Vortex Lattice Method (aerodynamics/cfd/vortex-lattice-method)

Use when the task is computing wing spanwise loading with the
horseshoe vortex lattice method: panel geometry, influence
coefficients, circulation solution, and the derived lift and induced
drag.

## Domain quick reference

- The half wing is divided into spanwise panels; each panel carries a
  horseshoe vortex whose bound segment sits on the quarter chord and
  whose trailing legs run downstream.
- The root-side leg of the root panel is dropped, the mirror-image
  cancellation of the half-wing model.
- The no-penetration condition at the three-quarter chord control
  points gives a linear system in the panel circulations.
- The spanwise lift distribution follows from the Kutta-Joukowski law
  per panel; the downwash angles at the bound vortices give the
  induced drag by the near-field estimate.
- Near-square panels (spanwise width close to the local chord) give
  the cleanest solutions; the classic collocation converges to the
  Prandtl lifting-line result for straight wings.

## Workflow

1. Build the panel lattice with build_wing (span, root and tip chord,
   panel count).
2. Assemble the influence coefficient matrix with influence_matrix.
3. Solve for the panel circulations with solve_circulations.
4. Derive per-panel lift, downwash angles, and induced drag with
   lift_distribution, downwash_angles, and
   induced_drag_coefficient.
5. Report the lift coefficient, induced drag coefficient, and span
   efficiency from wing_coefficients.

## Pitfalls

- Using panels much narrower than the local chord; the elementary
  single-row horseshoe collocation develops an alternating
  checkerboard mode on narrow panels.
- Reporting the root panel downwash as positive; the dropped root leg
  leaves a small upwash artifact at the root.
- Applying the elementary single-row model to swept planforms; swept
  wings need a multi-row vortex ring lattice (see the
  swept-wing-aerodynamics leaf).
- Using the linear model beyond small angles of attack; the method is
  invalid for |alpha| at or above 45 degrees and never models stall.
- Confusing this method with the analytic lifting-line formula or the
  parabolic drag polar; those are the lift-curve-slope and drag-polar
  leaves.

## Behavior contract (gate 3)

The horseshoe Biot-Savart, influence matrix, circulation solve, lift
distribution, downwash, and induced drag logic is exercised by the
gate 3 contract test: scripts/test_vortex_lattice_method.py against
scripts/vortex_lattice_method_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_vortex_lattice_method.py

## Compliance

- NACA Report 824 anchors the section-data context (public domain);
  summary and physics values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
