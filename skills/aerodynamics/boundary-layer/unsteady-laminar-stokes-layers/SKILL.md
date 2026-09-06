---
name: unsteady-laminar-stokes-layers
description: "Use when you must compute the exact unsteady laminar Stokes layer of an infinite plate in a quiescent fluid, either impulsively started or oscillating in its own plane: for the stokes-first-problem Rayleigh layer of a plate started at speed U, evaluate the similarity profile u/U = erfc(y/(2*sqrt(nu*t))), the layer edge at 3.64*sqrt(nu*t) where u/U = 0.01, the wall shear decaying as 1/sqrt(t) from rho*U*sqrt(nu/(pi*t)), and the displacement thickness; for the stokes-second-problem oscillating-plate-layer at omega, evaluate the exponential-cosine velocity field, the penetration depth sqrt(2*nu/omega) with exp(-1) amplitude and 1-rad lag, and the wall shear amplitude rho*U*sqrt(nu*omega) leading the plate velocity by 45 degrees. Produces the closed-form velocity profiles, thicknesses and wall-shear histories in SI units for unsteady shear-layer and viscous time-scale checks. Trigger: unsteady-laminar-stokes-layers, stokes-first-problem, oscillating-plate-layer, rayleigh-layer."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: boundary-layer
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: boundary-layer
  tags: [unsteady-laminar-stokes-layers, stokes-first-problem, oscillating-plate-layer, rayleigh-layer, stokes-second-problem, penetration-depth]
  version: 0.1.0
  author: AeroSkills
---

# Unsteady Laminar Stokes Layers (aerodynamics/boundary-layer/unsteady-laminar-stokes-layers)

Use when you must compute the exact unsteady laminar Stokes layer of
an infinite flat plate in a quiescent half-space: the closed-form
solutions of the one-dimensional vorticity diffusion equation
u_t = nu * u_yy for a plate impulsively started at t = 0 (Stokes first
problem, the Rayleigh layer) and for a plate oscillating in its own
plane (Stokes second problem). The time-dependent layer is the
unsteady member of the exact-viscous family whose steady members are
already in the tree: the Blasius flat-plate boundary layer
(boundary-layer-theory) and the shear-driven Couette gap
(compressible-couette-flow). The aeroelasticity leaves cover only
inviscid indicial airfoil response, so no existing leaf owns
time-dependent laminar shear layers over a plate. Fully closed form,
pure stdlib, no iteration. It does not do steady boundary layers,
regime classification, Couette gap flow or inviscid oscillating-airfoil
aerodynamics; incompressible constant-property laminar flow only, with
uniform nu.

## Domain quick reference

- Diffusion balance: u_t = nu * u_yy over the half-space y >= 0 above
  a plate at y = 0 in fluid at rest. Module constants: NU_AIR =
  1.46e-5 m2/s, RHO_AIR = 1.225 kg/m3, DELTA99_COEF = 3.6428
  (2 * 1.8214, where erfc(1.8214) = 0.01). Dynamic viscosity is always
  derived mu = rho * nu, never an input.
- Stokes first problem (impulsive start, Rayleigh layer): the plate
  starts at speed U at t = 0 and the layer diffuses outward
  self-similarly with u/U = erfc(eta), similarity variable
  eta = y / (2 * sqrt(nu * t)); u(0, t) = U exactly for all t > 0
  (no slip) and the profile shape is identical at every time.
- Layer edge: delta = 3.6428 * sqrt(nu * t), where u/U = erfc(1.8214)
  = 0.0099994, the 99-percent-deficit point; delta grows as sqrt(t),
  delta(t2)/delta(t1) = sqrt(t2/t1), without bound.
- First-problem wall shear: du/dy|0 = -U / sqrt(pi * nu * t), so
  tau_w = mu * |du/dy|0 = rho * U * sqrt(nu / (pi * t)), decaying as
  1/sqrt(t); tau_w * sqrt(t) = rho * U * sqrt(nu / pi) exactly
  constant.
- Displacement thickness: delta* = integral_0^inf (1 - u/U) dy =
  2 * sqrt(nu * t / pi) (the half-space erfc integral is 1/sqrt(pi));
  the momentum balance rho * U * d(delta*)/dt = tau_w holds
  identically.
- Stokes second problem (oscillating plate): the plate moves as
  U * cos(omega * t) and the steady-periodic solution is u = U *
  exp(-y/delta) * cos(omega * t - y/delta) with wavenumber k =
  sqrt(omega / (2 * nu)) = 1/delta, penetration depth
  delta = sqrt(2 * nu / omega), the real part of U * exp(i * omega * t
  - (1 + i) * k * y). At depth y the amplitude is U * exp(-y/delta)
  and the signal lags the wall by y/delta radians; at y = delta the
  amplitude is exp(-1) * U = 0.3679 * U and the lag is exactly 1 rad
  (57.30 deg).
- Second-problem wall shear: du/dy|0 = k * U * (sin(omega * t) -
  cos(omega * t)), so with the resistance-on-plate convention
  tau_w = -mu * du/dy|0 (positive resisting +x plate motion)
  tau_w(t) = tau_amp * cos(omega * t + pi / 4) with
  tau_amp = rho * U * sqrt(nu * omega) = mu * U * sqrt(omega / nu);
  the shear leads the plate velocity by 45 degrees (one-eighth period,
  T/8 = pi / (2 * omega)) and passes through zero at omega * t = pi/4.
- SI units throughout: m/s, m, Pa, rad/s, s.

## Workflow

1. Fix the flow state: uniform kinematic viscosity nu, density rho
   and plate speed U; decide between the stokes-first-problem
   impulsive start (Rayleigh layer) and the stokes-second-problem
   plate oscillation at frequency omega. Dynamic viscosity is always
   mu = rho * nu.
2. First problem, similarity profile traverse: evaluate the erfc
   Rayleigh-layer profile with stokes_first_velocity(U, nu, y, t) =
   U * erfc(y / (2 * sqrt(nu * t))) at the stations y and times t of
   interest; u(0, t) = U at the wall and u/U collapses onto one erfc
   curve in eta at every time.
3. First problem, layer-edge traverse: locate the edge of the
   Rayleigh layer with rayleigh_layer_thickness(nu, t) =
   3.6428 * sqrt(nu * t), the 99-percent-deficit point where
   u/U = 0.01, and scale it across times with the sqrt(t) growth law.
4. First problem, shear-decay traverse: evaluate the wall shear
   history with stokes_first_wall_shear(rho, U, nu, t) =
   rho * U * sqrt(nu / (pi * t)); check the 1/sqrt(t) decay with the
   tau_w * sqrt(t) invariant.
5. First problem, displacement-thickness traverse: compute the
   displacement thickness with stokes_first_displacement_thickness(nu,
   t) = 2 * sqrt(nu * t / pi) and confirm the momentum balance of the
   growing layer, rho * U * d(delta*)/dt = tau_w, by finite
   difference.
6. Second problem, penetration-depth traverse: evaluate the Stokes
   layer thickness with stokes_penetration_depth(nu, omega) =
   sqrt(2 * nu / omega), the depth of the exp(-1) amplitude point.
7. Second problem, oscillating-field traverse: evaluate the
   exponential-cosine velocity field with stokes_second_velocity(U,
   nu, omega, y, t) at the depths and phases of interest; the local
   amplitude is U * exp(-y/delta) and the phase lag is y/delta
   radians, so the field peaks at each depth one radian of omega * t
   after the wall does.
8. Second problem, shear-phase traverse: compute the wall shear
   amplitude with stokes_second_shear_amplitude(rho, U, nu, omega) =
   rho * U * sqrt(nu * omega) and its time history with
   stokes_second_wall_shear(rho, U, nu, omega, t) =
   tau_amp * cos(omega * t + pi / 4); the shear leads the plate
   velocity by 45 degrees and crosses zero at omega * t = pi/4,
   exactly T/8 after the wall velocity peak.
9. Input-rejection and determinism traverse: confirm every
   non-physical input (nu <= 0, t <= 0, y < 0, rho <= 0, omega <= 0)
   raises ValueError, then run the contract test
   scripts/test_unsteady_laminar_stokes_layers.py.

## Worked example

Air at standard conditions, nu = 1.46e-5 m2/s, rho = 1.225 kg/m3,
plate speed U = 30 m/s (real outputs of the module functions).

Stokes first problem, plate started at t = 0:

- Similarity profile u/U = erfc(eta) at t = 0.001 s (eta = 1 at y =
  0.2417 mm): u/U = 0.723674 at eta = 0.25, 0.479500 at eta = 0.5,
  0.157299 at eta = 1.0, 0.033895 at eta = 1.5, 0.0099994 at
  eta = 1.8214, 0.004678 at eta = 2.0; monotone from 1.000000 at the
  wall toward 0 in the far field.
- Layer edge delta = 3.6428 * sqrt(nu * t): 0.4402 mm at t = 0.001 s,
  1.392 mm at 0.01 s, 4.402 mm at 0.1 s, 13.92 mm at 1 s, 44.02 mm at
  10 s, one hundred times thicker after four decades of time, with
  u/U = 0.0099994 at the edge at every time (self-similar collapse).
- Wall shear decay tau_w = rho * U * sqrt(nu / (pi * t)): 2.505295 Pa
  at 0.001 s, 0.792244 Pa at 0.01 s, 0.250529 Pa at 0.1 s,
  0.079224 Pa at 1 s, 0.025053 Pa at 10 s; tau_w(10 s) / tau_w(0.001 s)
  = 0.01 and tau_w * sqrt(t) = 0.0792244 Pa sqrt(s) constant.
- Front arrival at y = 1 mm: 0.000000 m/s after 1 ms, 1.926887 m/s
  after 10 ms, 16.752282 m/s after 100 ms, 25.595499 m/s after 1 s.
- Displacement thickness delta* = 2 * sqrt(nu * t / pi): 0.136343 mm
  at 1 ms, 13.6343 mm at 10 s; delta*/delta = 0.3098 always.
- Momentum balance: rho * U * d(delta*)/dt over t = 1.0 to 1.02 s
  reproduces tau_w(1.01 s) with relative error 1.2e-5.

Stokes second problem, plate oscillating at omega = 50 rad/s (period
T = 0.12566 s):

- Penetration depth delta = sqrt(2 * nu / omega) = 7.6419893e-4 m
  (0.7642 mm).
- Amplitude profile U * exp(-y/delta) with phase lag y/delta:
  y/delta = 0: 30.0000 m/s, 0.00 deg; 0.5: 18.1959 m/s, 28.65 deg;
  1.0: 11.0364 m/s, 57.30 deg (exp(-1) * U, lag exactly 1 rad);
  2.0: 4.0601 m/s, 114.59 deg; 3.0: 1.4936 m/s, 171.89 deg.
- Velocity at y = delta over a cycle: 5.9630 m/s at t = 0, 9.6853 m/s
  at t = 0.01 s, 11.0364 m/s at t = 0.02 s (the peak, one radian after
  the wall peak), 9.6853 m/s at t = 0.03 s, 0.7807 m/s at t = 0.05 s.
- Wall shear amplitude tau_amp = rho * U * sqrt(nu * omega) =
  0.992930 Pa, identical to mu * U * sqrt(omega / nu) (relative
  difference below 1e-12). Time history tau_w = tau_amp *
  cos(omega * t + pi / 4): 0.702108 Pa (0.707107 of the amplitude,
  cos 45 deg) at t = 0, 0.000000 Pa at t = 0.015708 s (omega * t = 45
  deg), -0.992930 Pa at t = 0.047124 s (135 deg), -0.702108 Pa at
  t = 0.062832 s (180 deg).
- Phase read-off: T/8 = 0.015708 s = pi / (4 * omega), and the shear
  zero crossing sits exactly one-eighth period after the wall velocity
  peak at t = 0: the shear waveform leads the plate velocity by 45
  degrees.

Read-off: a plate start in air at 30 m/s carries 2.5 Pa of wall shear
for the first millisecond but only 0.025 Pa after 10 s while the
affected layer grows from 0.44 mm to 44 mm; a 50 rad/s (about 8 Hz)
oscillation at the same speed confines the motion to a 0.76 mm Stokes
layer with shear swinging between plus and minus 0.99 Pa, peaking
one-eighth period before the plate reaches peak speed.

## Verification

- Confirm stokes_first_velocity(30.0, 1.46e-5, 0.0, 0.001) returns
  30.0 exactly (erfc(0) = 1) and u/U at eta = 1 (y = 2 * sqrt(nu * t))
  is 0.1572992071 within 1e-6.
- Confirm rayleigh_layer_thickness(1.46e-5, 0.001) returns
  4.40161e-4 m within 1e-6, u/U = 0.01 within 1e-3 at the edge, and
  delta(10 s) / delta(0.001 s) = 100 = sqrt(10 / 0.001).
- Confirm stokes_first_wall_shear(1.225, 30.0, 1.46e-5, 0.001)
  returns 2.505295 Pa within 1e-3 (between 2.0 and 3.0 Pa), the decay
  ratio tau_w(10 s) / tau_w(0.001 s) is 0.01, and
  tau_w * sqrt(t) = 0.0792244 Pa sqrt(s) is constant.
- Confirm the momentum balance: rho * U * (delta*(1.02) -
  delta*(1.0)) / 0.02 reproduces tau_w(1.01 s) within 1e-3 relative
  (anchor error 1.2e-5), and delta*/delta = 0.3098 within 1e-3.
- Confirm stokes_penetration_depth(1.46e-5, 50.0) returns
  7.64199e-4 m within 1e-8, u(0, t) = U * cos(omega * t), the signal
  at y = delta peaks at t = 1/omega at exp(-1) * U = 11.0364 m/s, and
  the amplitude at y = 3 * delta is 1.4936 m/s.
- Confirm stokes_second_shear_amplitude(1.225, 30.0, 1.46e-5, 50.0)
  returns 0.992930 Pa within 1e-4 (between 0.9 and 1.1 Pa) and equals
  mu * U * sqrt(omega / nu) within 1e-12 relative; tau_w(0) / tau_amp
  = cos(pi / 4) = 0.707107, tau_w vanishes at t = pi / (4 * omega)
  (residual 6.08e-17 Pa), and tau_w = -tau_amp at t = 3 * pi / (4 *
  omega).
- Confirm every non-positive nu, rho, omega and t and every negative y
  raises ValueError, and that repeated calls are bit-identical
  (deterministic, stdlib math only).
- Run the contract test offline: python3
  scripts/test_unsteady_laminar_stokes_layers.py (32 tests,
  deterministic).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: the steady
  Blasius flat-plate member of the exact-viscous family; the Rayleigh
  layer is its unsteady counterpart driven by the plate momentum
  rather than the free stream.
- aerodynamics/boundary-layer/boundary-layer-transition,
  aerodynamics/boundary-layer/boundary-layer-separation,
  aerodynamics/boundary-layer/stagnation-flow-boundary-layer,
  aerodynamics/boundary-layer/rough-wall-skin-friction: the rest of
  the boundary-layer pack, all steady-state content.
- aerodynamics/high-speed/compressible-couette-flow: the steady
  shear-driven gap between two plates with a linear velocity profile,
  the other exact solution of the viscous diffusion balance; this leaf
  covers the unsteady half-space layer driven by one moving surface.
- aerodynamics/aeroelasticity/aeroelastic-gust-response and
  aerodynamics/aeroelasticity/flutter-speed-prediction: the inviscid
  unsteady-airfoil leaves (indicial response and oscillating-airfoil
  loads), which share time-dependence but no viscous-layer physics.
- aerodynamics/high-speed/shock-tube: the compressible unsteady
  expansion wave, a wave process rather than a viscous Stokes layer.

## Pitfalls

- Expecting the layer to reach a steady state: the Rayleigh layer of
  the impulsively started plate keeps growing as sqrt(nu * t) forever
  (0.44 mm after 1 ms, 44 mm after 10 s), and its wall shear keeps
  decaying as 1/sqrt(t); there is no equilibrium thickness in the
  first problem.
- Confusing the two layer edges: the first-problem 99-percent edge is
  3.6428 * sqrt(nu * t) and grows in time, while the second-problem
  penetration depth sqrt(2 * nu / omega) is fixed by the frequency; at
  the second-problem depth the amplitude is exp(-1) * U = 0.3679 * U,
  not 0.01 * U.
- Reading the shear phase sign backwards: with the resistance
  convention tau_w = -mu * du/dy|0 (positive resisting +x plate
  motion) the oscillating-plate wall shear tau_amp *
  cos(omega * t + pi / 4) LEADS the plate velocity by 45 degrees and
  passes through zero at omega * t = pi/4, one-eighth period AFTER the
  plate reaches peak speed; a shear that lagged the wall motion would
  put the zero crossing elsewhere in the cycle.
- Using a steady skin-friction correlation for an impulsive start: the
  first-problem wall shear rho * U * sqrt(nu / (pi * t)) is singular
  at t = 0 and decays as 1/sqrt(t); a steady correlation has no time
  argument and cannot represent the transient.
- Treating the second problem as a start-up: stokes_second_velocity
  and stokes_second_wall_shear describe the steady-periodic state and
  accept any real t, including negative t; the initial transient after
  the oscillation is switched on is not part of this closed form.
- Passing rho where nu belongs: dynamic viscosity is always derived
  mu = rho * nu; the shear functions take (rho, U, nu, ...) and the
  velocity functions take (U, nu, ...), so swapping rho into a
  velocity call silently mis-scales the profile.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_unsteady_laminar_stokes_layers.py

The 32-test contract covers the worked example of the impulsively
started plate (erfc similarity profile against math.erfc, eta = 1
anchor, far-field decay, front arrival at a fixed station), the
Rayleigh layer edge (anchor thickness, u/U = 0.01 at the edge, sqrt(t)
growth ratio), the wall shear decay (anchor value and magnitude bound,
decade ratio 0.01, tau_w * sqrt(t) invariant), the displacement
thickness and its 0.3098 ratio with the momentum balance identity, the
oscillating-plate layer (penetration depth anchor, no-slip cosine,
phase-zero local amplitude, cycle samples at y = delta, amplitude
profile decay), the wall shear amplitude and phase (anchor value and
magnitude bound, mu identity, 45 degree phase lead, zero crossing at
omega * t = pi/4, negative peak, one-eighth-period read-off), and
ValueError rejection of every non-physical input class with the
determinism and stdlib-only checks. It passes under both
/usr/bin/python3 and the pyenv 3.13.12 hook interpreter.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 is the sibling
  precedent for the viscous-layer family (standards-map.yaml); the
  classical treatment of unsteady laminar boundary layers follows
  Schlichting, whose material is cited through the report. The
  relations above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
