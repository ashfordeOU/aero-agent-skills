---
name: rotorcraft-cyclic-pitch-trim
description: "Use when you must compute the cyclic-pitch trim of a helicopter main rotor blade in forward flight under uniform inflow: the steady first-harmonic (1/rev) flapping equilibrium of the idealized centrally hinged blade with the control channel added, longitudinal cyclic theta1s and lateral cyclic theta1c about the collective, in the standard rotor convention, and the trim inversion for the cyclic pitch and equivalent swashplate tilt that hold the tip-path plane at a target longitudinal and lateral attitude, level or prescribed. Produces the coning angle and the longitudinal and lateral flapping angles of the cyclic-forced equilibrium, the affine cyclic-flap-response gains, and the trim cyclic and swashplate tilt for the target attitude; the zero-cyclic limit reproduces the collective-only forward-flight flapping sibling exactly. Trigger: rotorcraft cyclic pitch trim, longitudinal cyclic pitch, lateral cyclic pitch, swashplate tilt, trim cyclic, cyclic flap response, disk attitude trim."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [rotorcraft-cyclic-pitch-trim, longitudinal-cyclic-pitch, lateral-cyclic-pitch, swashplate-tilt, cyclic-flap-response, trim-cyclic, control-plane-tilt, disk-attitude-trim]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Cyclic-Pitch Trim (flight-mechanics/performance/rotorcraft-cyclic-pitch-trim)

Use when the task is the cyclic-pitch trim of a helicopter main rotor blade
in forward flight: the longitudinal and lateral cyclic pitch, and the
equivalent swashplate tilt, that hold the tip-path plane at a target
longitudinal and lateral attitude under uniform inflow. This leaf extends
the wave-46 collective-only first-harmonic flap equilibrium (the
forward-flight flapping sibling) with the control channel
theta(psi) = theta0 + theta1c*cos(psi) + theta1s*sin(psi), where theta1c is
the lateral cyclic pitch (the cos(psi) harmonic) and theta1s the
longitudinal cyclic pitch (the sin(psi) harmonic) in the standard rotor
convention (Johnson, Helicopter Theory ch. 4 and Leishman, Principles of
Helicopter Aerodynamics ch. 4, paraphrased, never reproduced), and solves
the closed-form trim inversion for the cyclic command that holds a target
tip-path-plane attitude, level disk or prescribed tilt. Pure Python,
stdlib only, deterministic. It is the control-channel completion of
flight-mechanics/performance/rotorcraft-forward-flight-flapping, which
owns the collective-only equilibrium: at zero cyclic every closed form here
reduces exactly to that sibling's.

## Domain quick reference

- Blade element velocities in the hub plane frame: u_T = x + mu*sin(psi)
  (tangential, x = r/R) and u_P = lambda + x*beta' + mu*beta*cos(psi)
  (perpendicular), psi measured from the downwind blade position,
  advancing side at psi = pi/2, matching the wave-46 sibling convention.
- Blade pitch with the control channel:
  theta(psi) = theta0 + theta1c*cos(psi) + theta1s*sin(psi), theta1c the
  LATERAL cyclic pitch (peaks on the fore-aft line of the disk), theta1s
  the LONGITUDINAL cyclic pitch (peaks on the port-starboard line).
- First-harmonic flap ansatz: beta(psi) = a0 + a1s*cos(psi) +
  b1s*sin(psi); flap equation beta'' + beta = (gamma/2)*M(psi) with the
  dimensionless moment M(psi) = integral_0^1 x*[u_T^2*theta - u_T*u_P] dx.
  At 1/rev resonance the 1/rev content of beta'' + beta vanishes, so the
  equilibrium nulls the cos and sin projections of M and the steady
  projection fixes the coning.
- Closed forms (exact solution of the projection balances, all terms
  through mu^2):
  a0 = (gamma/2)*(theta0*(1 + mu^2)/4 - lambda/3 + mu*theta1s/3),
  a1s = -[4*mu*(2*theta0/3 - lambda/2) + theta1s*(1 + 3*mu^2/2)]/(1 - mu^2/2),
  b1s = theta1c - (4*mu/3)*a0/(1 + mu^2/2).
- a1s is gamma-free (the Lock number cancels in the 1/rev cos balance) and
  independent of theta1c; b1s carries theta1c with unity gain and gamma,
  mu and theta1s through the coning coupling. The coning gains the
  mean-lift term mu*theta1s/3 and stays free of theta1c, a1s and b1s.
- Zero-cyclic identity: at theta1c = theta1s = 0 the forms reduce EXACTLY
  to the wave-46 sibling closed forms, and a1s_free and b1s_free report
  that collective-only equilibrium.
- Hover limit mu = 0: a1s = -theta1s exactly and b1s = theta1c exactly
  (the 90-degree flap lag of the centrally hinged blade), so lateral
  cyclic controls the lateral disk orientation and longitudinal cyclic the
  longitudinal orientation.
- Sign convention: a1s < 0 is the tip-path-plane aft tilt; b1s < 0 means
  the advancing blade tip sits below the coning plane; theta1c and theta1s
  may be negative (trim routinely needs them so).
- Scope: 0 <= mu < 1 (singular at mu = 1, reverse flow out of scope),
  lambda > 0 (downward-positive convention), theta0 > 0, gamma > 0,
  centrally hinged, first harmonic only, small angles.
- Units are radians for the angle inputs and the _rad outputs; the _deg
  outputs are the _rad values times 180/pi.
- FAR-29 frames the transport-category rotorcraft certification context
  for rotor control loads; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the operating point: advance ratio mu, uniform inflow ratio lambda,
   collective theta0, blade Lock number gamma and the cyclic command
   (theta1c, theta1s) where one is applied.
2. Compute the cyclic-forced coning angle with coning_angle and confirm
   the cross-leaf identities: at zero cyclic it equals the wave-46
   collective-only coning closed form, and at mu = 0 it equals the hover
   coning closed form 0.5*gamma*(theta0/4 - lambda/3), cyclic-free.
3. Compute the longitudinal flapping angle with
   longitudinal_flapping_angle (no gamma, no theta1c: neither enters the
   1/rev cos balance) and read the tip-path-plane response to the
   longitudinal cyclic pitch, exactly -theta1s at mu = 0.
4. Compute the lateral flapping angle with lateral_flapping_angle and
   confirm the coning-coupling identity against coning_angle, exactly
   theta1c at mu = 0.
5. Run flap_response_summary for the one-call cyclic-forced equilibrium
   dict with all six documented keys in radians and degrees.
6. Run cyclic_response_gains for the affine control-to-flap gains:
   a1s_free and b1s_free (the wave-46 zero-cyclic flapping angles),
   d_a1s_d_theta1s, the exact zero and unity entries d_a1s_d_theta1c = 0.0
   and d_b1s_d_theta1c = 1.0, and the coning-mediated coupling
   d_b1s_d_theta1s, quadratic in mu.
7. Solve the trim inversion with trim_cyclic for the cyclic command that
   holds the tip-path plane at the target attitude, level disk
   (a1s_target = b1s_target = 0.0) or prescribed tilt, and round-trip the
   command through flap_response_summary to confirm the disk lands on the
   target.
8. Report the equivalent ideal zero-phase swashplate plane tilt with
   trim_swashplate_tilt: the tilt components equal the trim cyclic
   harmonics and the magnitude is their hypot.
9. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_cyclic_pitch_trim.py.

## Worked example

Cruise case in the corpus band: advance ratio mu = 0.3, uniform inflow
ratio lambda = 0.06, collective theta0 = 0.14 rad, Lock number gamma = 6.0
(the exact worked point of the wave-46 leaf, so the cross-leaf identities
are direct). Real module outputs:

- Zero-cyclic limit: flap_response_summary(0.3, 0.06, 0.14, 6.0, 0.0, 0.0)
  returns coning_angle_rad 0.05445 (3.11976 deg),
  longitudinal_flapping_rad -0.07958 (-4.55966 deg) and
  lateral_flapping_rad -0.02084 (-1.19416 deg), bit-identical to the
  wave-46 sibling worked values.
- Forward map under a cyclic command: at theta1c = 0.02 rad and
  theta1s = -0.04 rad the coning relaxes to 0.04245 rad (2.43221 deg, the
  negative longitudinal cyclic unloading the advancing-side mean lift),
  the aft tilt eases to -0.03204 rad (-1.83586 deg) and the lateral
  flapping becomes +0.00375 rad (0.21493 deg, the lateral cyclic
  overcoming the coning coupling).
- Cyclic response gains: cyclic_response_gains(0.3, 0.06, 0.14, 6.0)
  returns a1s_free -0.07958, b1s_free -0.02084, d_a1s_d_theta1s -1.18848,
  d_a1s_d_theta1c 0.0, d_b1s_d_theta1c 1.0 and d_b1s_d_theta1s -0.11483:
  one degree of longitudinal cyclic moves the longitudinal tilt 1.19 deg,
  one degree of lateral cyclic moves the lateral tilt 1.00 deg, and the
  coning-mediated cross coupling moves the lateral tilt only 0.115 deg per
  degree of longitudinal cyclic.
- Level-disk trim: trim_cyclic(0.3, 0.06, 0.14, 6.0, 0.0, 0.0) returns
  longitudinal_cyclic_pitch_rad -0.06696 (-3.83655 deg) and
  lateral_cyclic_pitch_rad 0.01315 (0.75360 deg): holding the tip-path
  plane level at mu = 0.3 needs -3.84 deg of longitudinal cyclic and +0.75
  deg of lateral cyclic. Round trip: the forward map at that command
  returns a1s = 0.0 and b1s = 0.0 exactly.
- Prescribed attitude trim: trim_cyclic(0.3, 0.06, 0.14, 6.0, -0.02, 0.0),
  holding the disk at a relaxed aft tilt of -0.02 rad (-1.14592 deg),
  returns longitudinal_cyclic_pitch_rad -0.05013 (-2.87236 deg) and
  lateral_cyclic_pitch_rad 0.01509 (0.86432 deg). Round trip returns
  a1s = -0.02 and b1s = 0.0 within 1e-9.
- Free-equilibrium identity: trim_cyclic at the a1s_free and b1s_free
  attitude returns theta1s = -0.0 and theta1c = 0.0 exactly: the wave-46
  collective-only equilibrium is held with zero cyclic, as it must be.
- Level-disk swashplate report: trim_swashplate_tilt under the ideal
  zero-phase idealization returns swashplate_longitudinal_tilt_rad 0.01315
  (0.75360 deg), swashplate_lateral_tilt_rad -0.06696 (-3.83655 deg) and
  swashplate_tilt_magnitude_rad 0.06824 (3.90986 deg): the swashplate
  plane stands tilted 3.91 deg from level at the level-disk cruise trim.
- Hover anchors at mu = 0.0 with theta1c = 0.02, theta1s = -0.04: a1s =
  0.04000 (exactly -theta1s), b1s = 0.02 (exactly theta1c) and a0 =
  0.04500 (the hover coning closed form, cyclic-free); a level disk at
  hover needs zero cyclic.
- Ordering anchor: the level longitudinal cyclic magnitude 0.06696 rad
  sits below the free aft tilt 0.07958 rad, because the leveling
  denominator (1 + 3*mu^2/2) exceeds the free-flap denominator
  (1 - mu^2/2).

## Verification

- Confirm flap_response_summary(0.3, 0.06, 0.14, 6.0, 0.0, 0.0) matches
  the worked values and that each component equals the wave-46 sibling
  closed form computed from the printed formulas within 1e-12.
- Confirm the hover cyclic identities: longitudinal_flapping_angle(0.0,
  0.06, 0.14, -0.04) = 0.04000 (equals -theta1s), lateral_flapping_angle
  (0.0, 0.06, 0.14, 6.0, 0.02, -0.04) = 0.02 (equals theta1c) and
  coning_angle(0.0, 0.06, 0.14, 6.0, -0.04) = 0.04500 (the hover coning
  closed form), all within 1e-9.
- Confirm both trim round trips: the level-disk and prescribed-attitude
  trims return the target attitude through flap_response_summary within
  1e-9, and the free-equilibrium trim returns both cyclic pitches exactly
  0.0 (math.isclose at 1e-15).
- Confirm the gain structure: cyclic_response_gains(0.3, 0.06, 0.14, 6.0)
  gives d_a1s_d_theta1s -1.18848, d_a1s_d_theta1c exactly 0.0,
  d_b1s_d_theta1c exactly 1.0 and d_b1s_d_theta1s -0.11483, each gain
  matching its closed form within 1e-12.
- Confirm the ordering identity |theta1s_level| = 0.06696 rad is below
  |a1s_free| = 0.07958 rad (strict comparison).
- Confirm the two-point inflow linearity of the level trim: over lam =
  0.06 versus 0.05 the theta1s difference 0.0052863 rad and the theta1c
  difference -0.0032207 rad equal the exact closed-form slopes within
  1e-12.
- Confirm the degree outputs each equal the _rad value times 180.0/pi
  within 1e-12 and that each summary, trim and swashplate dict returns
  exactly its documented keys.
- Confirm the coning decoupling: coning_angle depends on theta1s only
  through the mu*theta1s/3 mean-lift term and is unchanged by any finite
  theta1c.
- Confirm the independent Fourier self-consistency: the closed-form
  equilibrium nulls the steady, cos and sin projections of
  (gamma/2)*M - (beta'' + beta) by direct quadrature (at least 1024 by 128
  points) with absolute residuals below 1e-5.
- Confirm ValueError rejection of mu < 0, mu >= 1, lambda <= 0,
  theta0 <= 0, gamma <= 0 and any non-finite argument (mu = 0.0, negative
  cyclic pitches and negative a1s_target are valid inputs).
- Run the contract test offline: python3
  scripts/test_rotorcraft_cyclic_pitch_trim.py (41 tests, deterministic,
  no network).

## Pitfalls

- Passing gamma or theta1c to longitudinal_flapping_angle: the function
  takes no Lock number and no lateral cyclic argument by design, because
  gamma cancels in the 1/rev cos balance and the cos-harmonic pitch never
  projects onto the longitudinal balance.
- Reading a1s as the cyclic command: a1s is the flapping RESPONSE, not the
  input. The longitudinal cyclic theta1s that holds a level disk comes out
  NEGATIVE at cruise (it cancels the free aft tilt), and negative cyclic
  values are valid, expected inputs.
- Confusing the cyclic harmonics: theta1c (the cos(psi) harmonic) is the
  LATERAL cyclic pitch and theta1s (the sin(psi) harmonic) the
  LONGITUDINAL cyclic pitch in the pinned standard rotor convention; at
  hover the response is a1s = -theta1s and b1s = theta1c, the 90-degree
  flap lag.
- Using this leaf for the collective-only equilibrium: the zero-cyclic
  flapping angles themselves, the collective-only forward-flight
  equilibrium and the tip-path-plane-tilt surface belong to
  rotorcraft-forward-flight-flapping; this leaf reports them only as the
  zero-cyclic limit and as a1s_free and b1s_free.
- Treating the swashplate tilt as rigging geometry: the report uses the
  ideal zero-control-phase swashplate idealization with unit pitch
  gearing; real rotors phase their control horns, and that rigging
  geometry is out of scope.
- Extrapolating past mu = 1: the uniform-inflow model is singular at
  mu = 1 and reverse flow is out of scope; ValueError rejects mu >= 1.0.
- Expecting the trim to be gamma-free: theta1s is gamma-free by
  cancellation, but theta1c carries gamma through the coning coupling
  (the d_b1s_d_theta1s gain is quadratic in mu and linear in gamma).

## Related leaves

- flight-mechanics/performance/rotorcraft-forward-flight-flapping: the
  collective-only sibling whose equilibrium this leaf reproduces exactly
  at zero cyclic; its first-harmonic flap response is the free-flapping
  state the trim cyclic here commands against.
- flight-mechanics/performance/rotorcraft-blade-flapping-dynamics: the
  hover-state sibling that owns the Lock number, the hover coning angle
  and the flap frequency ratio.
- flight-mechanics/performance/rotorcraft-forward-flight-performance: the
  power and best-speeds leaf of forward flight; it never touches blade
  motion or rotor control.
- flight-mechanics/performance/rotorcraft-lead-lag-dynamics: the in-plane
  blade motion sibling, distinct from the out-of-plane flap control
  channel here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_cyclic_pitch_trim.py

The test covers the zero-cyclic cross-leaf identity against the wave-46
closed forms, the hover cyclic response identities (a1s = -theta1s,
b1s = theta1c, cyclic-free hover coning), the hover no-cyclic zero, the
level-disk and prescribed-attitude trim inversions with their round trips
through flap_response_summary, the free-equilibrium inversion identity,
the exact gain structure, the ordering identity, the two-point inflow
linearity of the trim, the degree-output and dict-key discipline of every
function, the coning decoupling, the independent Fourier self-consistency
of the closed forms, ValueError rejection of every non-physical or
non-finite input, and run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: FAR-29 is the FAA
  transport-category rotorcraft airworthiness standard (ecfr.gov); the
  cyclic-trim relations above are standard engineering methodology
  (Johnson, Leishman), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
