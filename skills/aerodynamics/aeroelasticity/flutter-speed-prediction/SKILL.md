---
name: flutter-speed-prediction
description: "Use when the task is classical wing flutter of the two-DOF typical section, the V-g method, damping crossing, frequency coalescence, or flutter clearance. Compute the classical flutter speed of a two-degree-of-freedom bending-torsion wing section: build the typical section with plunge and pitch about the elastic axis, apply Theodorsen unsteady aerodynamics with the complex lift-deficiency function C(k), run the V-g method across the reduced frequency range, locate the flutter speed where the artificial structural damping g crosses zero, check frequency coalescence near the flutter boundary, and assess the flutter margin against the design dive speed in the FAR 25.629 clearance context. Produces the flutter speed, flutter frequency, reduced frequency, coalescence verdict, and a clearance margin assessment. Trigger: flutter speed, v-g method, bending-torsion flutter, frequency coalescence, typical section, flutter margin, far 25.629."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: aeroelasticity
  tags: [flutter-speed, v-g-method, bending-torsion, typical-section, frequency-coalescence, flutter-margin, theodorsen, reduced-frequency, far-25-629, aeroelasticity]
  version: 0.1.0
  author: Aero Agent Skills
---

# Flutter Speed Prediction (aerodynamics/aeroelasticity/flutter-speed-prediction)

Use when the task is the classical flutter condition of a
two-degree-of-freedom wing section: the flutter speed where the
bending-torsion modes lose stability, found with the V-g method, the
frequency coalescence check, and the flutter margin against the design
dive speed for flutter clearance in the FAR 25.629 context. This leaf
is the dynamic counterpart of
aerodynamics/aeroelasticity/divergence-speed (static divergence); it is
also distinct from structures/fem/modal-analysis (mode extraction) and
aerodynamics/high-speed/swept-wing-aerodynamics (sweep effects), which
feed and shape multi-mode flutter work.

## Domain quick reference

- Binary typical section: plunge h (positive down) and pitch theta
  (positive nose-up) about an elastic axis at a*b from the mid-chord
  (positive aft; a = -0.2 is the elastic axis at 40 percent chord), with
  semi-chord b. The structural parameters are the mass ratio mu = m /
  (pi * rho * b^2), the static unbalance x_theta (the distance from the
  elastic axis to the center of gravity divided by b, the inertia
  coupling), the radius of gyration squared r_theta^2 (inertia about the
  elastic axis I_theta = m * r_theta^2 * b^2), and the uncoupled bending
  and torsion frequencies omega_h and omega_theta (stiffnesses K_h = m *
  omega_h^2 and K_theta = I_theta * omega_theta^2).
- Unsteady aerodynamics: the Theodorsen loads with the complex
  lift-deficiency function C(k) = H1^(2)(k) / (H1^(2)(k) + i H0^(2)(k))
  built from Bessel J and Y series (Abramowitz and Stegun 9.1.10 to
  9.1.11), evaluated at harmonic motion with the reduced frequency k =
  omega * b / V. Limits: C = 1 in steady flow (k = 0) and C = 1/2 at
  high reduced frequency. Quasi-steady aerodynamics (C = 1) is known to
  give erroneous pitch damping and is not used here.
- V-g method: for each reduced frequency k the flutter determinant is
  solved with an artificial structural damping g added to the stiffness,
  det[K(1 + i g) - lambda E(k)] = 0, for real lambda = omega^2 and real
  g. g < 0 means the aerodynamic damping stabilizes the mode (negative
  artificial damping would be needed to sustain harmonic motion), g = 0
  is the neutral condition, and g > 0 means the mode is unstable. The
  flutter speed is the lowest airspeed where a mode's g rises through
  zero as V increases. This is a simple p-k style eigenvalue approach on
  the 2 x 2 aeroelastic system, a first-estimate typical section model,
  not a production flutter clearance tool.
- Flutter boundary: the flutter speed grows with the structural
  stiffness (a stiff section flutters at much higher speed, and the
  rigid limit is enormous), depends on the inertia coupling x_theta (no
  static unbalance leaves no classical flutter mechanism), on the
  frequency ratio omega_h / omega_theta, on the elastic axis location a,
  and on the aerodynamic stiffness (the circulatory V^2 terms that also
  drive static divergence).
- Frequency coalescence: in the classical mechanism the two modal
  frequencies converge strongly as the airspeed approaches the flutter
  boundary; the coalescence check reports the minimum frequency gap and
  the speed where it occurs, and the exact branch merge sits at or just
  above the flutter speed.
- Divergence versus flutter: flutter is the dynamic bending-torsion
  oscillation that loses stability at the damping crossing; divergence
  is the static torsional instability where the torsion stiffness
  vanishes at a higher dynamic pressure. For the typical section the
  torsion frequency collapses to zero at the divergence speed; static
  divergence analysis belongs to
  aerodynamics/aeroelasticity/divergence-speed.
- Flutter margin and clearance: margin = V_F / V_D against the design
  dive speed; clearance practice keeps the margin at or above 1.15 x
  V_D. FAR 25.629 (and the European counterpart CS 25.629) is the
  airworthiness context for transport category flutter clearance; the
  standards are referenced by name only, never reproduced
  (standards-map.yaml far-25 and cs-25, both reference-only).

## Workflow

1. Gather the section inputs: mass ratio mu, static unbalance x_theta,
   radius of gyration squared r_theta^2, uncoupled frequencies omega_h
   and omega_theta, elastic axis location a, semi-chord b, and the
   flight density rho (the ISA sea level default 1.225 kg/m^3).
2. Confirm the inertia coupling: x_theta must be non-negative (center
   of gravity aft of the elastic axis); without it there is no classical
   flutter mechanism.
3. Sweep the reduced frequency with vg_damping_crossing over a range
   such as k in [0.05, 4] and inspect the per-mode rows (airspeed,
   frequency, g): both modes must be damped (g < 0) at the low-speed
   end, and the flutter branch must rise through g = 0 as the airspeed
   grows.
4. Locate the flutter speed with flutter_speed_binary, which bisects on
   the g = 0 crossing and returns the flutter speed, the flutter
   frequency, the reduced frequency, and the other mode's frequency at
   the flutter point. A None result means no crossing inside the scanned
   reduced frequency range.
5. Check the mechanism with frequency_coalescence_check: the modal
   frequency gap should shrink well below its low-speed value near the
   flutter boundary (coalescing True), confirming the classical
   frequency-coalescence flutter mechanism.
6. Assess the clearance with flutter_margin(v_f, v_design): a margin at
   or above the 1.15 clearance practice (FAR 25.629 context) is
   acceptable; below it the section needs stiffness or damping changes,
   and the analysis is re-run from step 3.
7. Confirm the deterministic behavior with the contract test
   scripts/test_flutter_speed_prediction.py.

## Worked example

Classic typical section benchmark: b = 1 m semi-chord, elastic axis at
a = -0.2 (40 percent chord), center of gravity 0.2 m aft of the elastic
axis (x_theta = 0.2), r_theta^2 = 0.24, mu = 20, omega_h = 30 rad/s,
omega_theta = 50 rad/s, sea level air (rho = 1.225 kg/m^3).

- V-g sweep: at k = 4 (about 14 m/s) both modes are damped, g = -0.011
  for the torsion branch and g = -0.017 for the bending branch; the
  torsion branch rises through g = 0 between k = 0.5 (g = -0.025, about
  85.6 m/s) and k = 0.46 (g = +0.002, about 89.1 m/s).
- flutter_speed_binary gives the flutter point where the damping crosses
  zero: V_F = 88.85 m/s at reduced frequency k_F = 0.462, flutter
  frequency omega_F = 41.07 rad/s, with the bending branch at 30.10
  rad/s. Normalized: V_F / (b * omega_theta) = 1.78 and omega_F /
  omega_theta = 0.82, the classic typical section result.
- frequency_coalescence_check: the modal frequency gap shrinks from 27.7
  rad/s at low speed to 8.0 rad/s at the coalescence station (about 94
  m/s, 30.7 rad/s), a 71 percent convergence: coalescing True, the
  classical mechanism.
- flutter_margin: with a design dive speed V_D = 80 m/s the margin is
  88.85 / 80 = 1.111, below the 1.15 clearance practice, so the section
  is flagged at flutter risk; with V_D = 70 m/s the margin is 1.269 and
  the clearance closes.
- Divergence context: the torsion frequency collapses to zero at the
  static divergence speed of about 141 m/s, above the flutter speed, so
  flutter is the critical instability for this section.

## Related leaves

- aerodynamics/aeroelasticity/divergence-speed: the static counterpart
  (divergence dynamic pressure, divergence speed, and divergence margin
  for the same typical section geometry).
- aerodynamics/high-speed/swept-wing-aerodynamics: spanwise sweep
  couples bending and torsion through the flow and shifts the flutter
  boundary of the wing.
- structures/fem/modal-analysis: structural mode shapes and frequencies
  that feed multi-mode flutter analyses beyond the two-DOF typical
  section.

## Pitfalls

- Using quasi-steady aerodynamics (C = 1) for the damping search: it is
  documented to give erroneous pitch damping, so the flutter crossing is
  computed with the full Theodorsen C(k) - do not shortcut the
  deficiency function.
- Reading a mode as stable because g is negative at one speed: the V-g
  sweep must show both modes damped at the low-speed end and the
  torsion branch rising through g = 0 as airspeed grows; a single point
  is not a stability verdict.
- Treating a None flutter speed as "no flutter": flutter_speed_binary
  returns None when no g = 0 crossing exists inside the scanned reduced
  frequency range - widen the k sweep before concluding the section is
  flutter-free.
- Neglecting the static-unbalance requirement: with x_theta = 0 there is
  no inertia coupling and no classical flutter mechanism, so a
  zero-unbalance section must not be pushed through the binary search
  as if it could flutter; a negative x_theta (elastic axis aft of the
  center of gravity) is rejected because the mechanism assumption
  breaks.
- Clearing against the margin without checking the mechanism: the
  frequency_coalescence_check verdict (gap shrinking from 27.7 to 8.0
  rad/s in the benchmark) confirms the coalescence mechanism - a
  clearance margin alone does not prove the flutter boundary was found.
- Forgetting that flutter and divergence are different instabilities:
  the torsion frequency collapsing to zero at about 141 m/s is static
  divergence (divergence-speed leaf), not the 88.85 m/s flutter
  crossing this leaf locates.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_flutter_speed_prediction.py

The test covers the Bessel reference values, the published C(k) values
and limits, low-speed stability (negative g), the torsion damping
crossing, the benchmark flutter speed and its normalized classic values,
the no-crossing-within-range and rigid edge cases, the coalescence
verdict, the flutter margin verdicts, and invalid-input edge cases.

## Compliance

- The typical section flutter analysis is public-domain textbook
  methodology (Theodorsen 1935, NACA Report 496; Bisplinghoff, Ashley
  and Halfman, Aeroelasticity; Hodges and Pierce, Introduction to
  Structural Dynamics and Aeroelasticity); the airworthiness context is
  FAR 25.629 and CS 25.629, referenced by name only, summary-only per
  standards-map.yaml (both reference-only).
- compliance: STANDARDS-REF, gated: false.
