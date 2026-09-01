---
name: centrifugal-compressor
description: "Use when you must design or assess a centrifugal compressor stage: compute the impeller tip speed from the rotational speed and the impeller diameter, the slip factor from the Wiesner correlation with the blade count and back-sweep angle, the work input coefficient from the Euler work relation, the total temperature rise, and the isentropic stage pressure ratio from the rotor work input, the isentropic efficiency, and the inlet total temperature. Also compute the impeller diffusion ratio and the de Haller number to check the inducer-to-exit relative velocity decay. Produces SI velocity triangle and stage performance parameters that gate the compressor stage design review in the FAR-33 engine certification context. Trigger: centrifugal compressor, impeller tip speed, slip factor, Wiesner correlation, work input coefficient, back-sweep angle, diffusion ratio, de Haller number."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: turbomachinery
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: turbomachinery
  tags: [centrifugal-compressor, impeller, slip-factor, wiesner-correlation, work-input-coefficient, back-sweep-angle, diffusion-ratio, de-haller-number, tip-speed, velocity-triangle]
  version: 0.1.0
  author: AeroSkills
---

# Centrifugal Compressor Stage (propulsion/turbomachinery/centrifugal-compressor)

Use when the task is centrifugal compressor stage design and
off-design assessment: impeller tip speed, slip factor, work input
coefficient, isentropic stage pressure ratio, and the impeller
diffusion check.

## Domain quick reference

- Wiesner slip factor sigma = 1 - sqrt(cos(beta2b))/z**0.7, with z
  the blade count and beta2b the back-sweep angle from the radial
  direction in radians (0 for radial vanes). Back sweep slightly
  raises sigma (sqrt(cos(beta2b)) < 1 shrinks the subtracted term)
  while the tan(beta2b) term in the Euler work relation reduces the
  work input and flattens the work curve.
- Stanitz slip factor sigma = 1 - 1.98/z for radial vanes
  (beta2b = 0).
- Impeller tip speed U = pi*d*n/60 in m/s from diameter d in m and
  rotational speed n in rpm; U2 at the impeller exit, U1 at the
  inducer tip.
- Specific rotor work w = u2*(sigma*u2 - cm2*tan(beta2b)) - u1*ctheta1
  in J/kg; ctheta1 is the prewhirl tangential velocity at the inducer
  inlet (0 for an axial inlet). w = u2**2 when sigma = 1 and
  beta2b = ctheta1 = 0 (the slip-free Euler work relation).
- Work input coefficient psi = w/u2**2, dimensionless; psi = sigma
  for a radial-vaned rotor with no prewhirl.
- Total temperature rise delta_t0 = w/cp in K.
- Isentropic stage pressure ratio
  pi = (1 + eta*w/(cp*t01))**(gamma/(gamma-1)) from the stage
  isentropic efficiency eta and the inlet total temperature t01 in K.
- Impeller diffusion: inducer relative velocity
  w1 = sqrt(ca1**2 + (u1 - ctheta1)**2), impeller exit relative
  velocity w2 = cm2/cos(beta2b), diffusion ratio dr = w1/w2, de
  Haller number dh = w2/w1. Keep dr below about 1.6 (dh above about
  0.6) to limit relative velocity decay losses.
- Air-standard defaults: eta = 0.85, cp = 1005 J/(kg K), gamma = 1.4.

## Workflow

1. Fix the geometry: rotational speed n, impeller diameter d2,
   inducer tip diameter d1, blade count z, back-sweep angle beta2b.
2. Compute the tip speeds with tip_speed.
3. Compute the slip factor with wiesner_slip (or stanitz_slip for
   radial vanes).
4. Set the exit meridional velocity cm2 and the inducer axial
   velocity ca1; compute the specific work with euler_work and the
   loading with work_input_coefficient.
5. Compute the total temperature rise with total_temperature_rise and
   the isentropic stage pressure ratio with stage_pressure_ratio.
6. Check the impeller diffusion with diffusion_ratio.
7. Assemble the full assessment with design_point and gate the stage
   design review on it.

## Pitfalls

- Rotational speed in rad/s or Hz instead of rpm: U = pi*d*n/60
  assumes rpm; convert first.
- Degrees instead of radians for beta2b: cos and tan change
  drastically; pass radians.
- Using the tip speed in place of the slip-affected tangential
  velocity: the Euler work is u2*(sigma*u2 - cm2*tan(beta2b)), not
  u2**2, unless sigma = 1 and the vanes are radial.
- Backward-swept blades reduce the work input and the pressure
  ratio: psi falls below sigma; do not report the radial-vane value.
- Non-physical inputs: n <= 0, d <= 0, z <= 0, t01 <= 0, eta outside
  (0, 1], or |beta2b| >= pi/2 raise ValueError; do not catch and
  continue, the numbers are meaningless.
- Diffusion ratio above the limit: dr > 1.6 flags an over-loaded
  inducer-to-exit diffusion; redesign before accepting the stage.

## Behavior contract (gate 3)

The centrifugal compressor logic is exercised by the gate 3 contract
test: scripts/test_centrifugal_compressor.py against
scripts/centrifugal_compressor_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_centrifugal_compressor.py

## Compliance

- Standards referenced, not reproduced: FAR-33 is US government work
  (public domain) and covers engine type certification, not stage
  analysis methods; the slip factor and Euler work relations are
  common turbomachinery methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
