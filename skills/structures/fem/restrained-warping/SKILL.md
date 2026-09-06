---
name: restrained-warping
description: "Use when you must compute the restrained (non-uniform) torsion response of a thin-walled open I-beam section: the warping constant Cw = I_y*h^2/4 of the doubly symmetric I-section, the sectorial coordinate at the flange tip, the decay parameter k = sqrt(G*J/(E*Cw)) of the non-uniform torsion equation E*Cw*theta'''' - G*J*theta'' = 0, the hyperbolic closed-form twist and twist rate, the bimoment B = -E*Cw*theta'' and the warping normal stress sigma_w = B*omega/Cw at the flange tip for a built-in cantilever under a tip torque and a fork-supported beam under a midspan torque, and the shear-torque versus warping-torque split. Produces the section constants, the twist and twist-rate profiles, the bimoment with its root or midspan peak, the flange-tip warping stress and the torque-partition table that gate restrained-torsion checks of open-section spars and stiffeners. Trigger: restrained warping, non-uniform torsion, warping constant, bimoment, torsional flexure, warping normal stress."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [restrained-warping, non-uniform-torsion, bimoment, warping-constant, warping-normal-stress, torsional-flexure]
  version: 0.1.0
  author: AeroSkills
---

# Restrained Warping (structures/fem/restrained-warping)

Use when the load case is restrained (non-uniform) torsion of a
thin-walled open doubly symmetric I-section: the built-in or fork-held
ends block the free warping of the flanges, so the torque is carried by
differential flange bending (a bimoment) as well as by Saint-Venant
shear, and the twist follows the fourth-order equation
E*Cw*theta'''' - G*J*theta'' = 0 rather than the free uniform twist
rate. This leaf implements the classical warping-torsion model (Vlasov
sectorial theory for an I-section with its shear center at the centroid
and the web on the sectorial zero line) in pure Python, stdlib only. It
pairs with structures/fem/torsion-shear-flow, the free-warping
complement that reports the uniform Saint-Venant twist rate and the
closed-section shear flow, and with structures/fem/shear-center-analysis,
the transverse-shear complement that walks a contour under a transverse
force. Deterministic, offline, SI units (metres, newtons, pascals).

## Domain quick reference

- Open-section Saint-Venant constant: J = (2*b*t_f**3 + h_w*t_w**3)/3,
  the sum b_i*t_i**3/3 over the two flanges and the web, with h_w = d -
  2*t_f the web depth.
- Warping constant: h = d - t_f (flange mid-line spacing), I_y =
  2*b**3*t_f/12 (flange pair about the web plane), Cw = I_y*h**2/4. The
  direct sectorial integral t_f*h**2*b**3/24 reproduces Cw to roundoff
  (the web sits on the sectorial zero line, so its own minor term
  contributes nothing).
- Sectorial coordinate: omega(s) = integral of rho ds from the web
  mid-line with rho = h/2 the flange lever arm; omega is linear along
  each flange, zero on the web, and omega_tip = h*b/4 at the flange
  tip. Sectorial modulus W_w = Cw/omega_tip.
- Non-uniform torsion ODE: E*Cw*theta'''' - G*J*theta'' = 0 on the
  torque-free span, with decay parameter k = sqrt(G*J/(E*Cw)) (1/m),
  the characteristic 1/k over which the restraint decays, and
  dimensionless u = k*L (cantilever) and v = k*L/2 (fork half-beam).
- Bimoment: B(z) = -E*Cw*theta''(z) in N m^2, the flange counter-bending
  couple B = M_f*h. Warping normal stress at the flange tip:
  sigma_w = B*omega_tip/Cw.
- Torque partition: T_sv(z) = G*J*theta'(z), T_w(z) = -E*Cw*theta'''(z)
  (the z-derivative of the bimoment), with T_sv + T_w equal to the
  torque carried at every station.
- Fixed-end cantilever (root z = 0 built in, point torque T at the free
  tip): theta(z) = (T/(G*J*k))*(k*z - sinh(k*z) + tanh(u)*(cosh(k*z) -
  1)), identically satisfying theta(0) = 0, theta'(0) = 0, theta''(L) =
  0 and G*J*theta'(L) - E*Cw*theta'''(L) = T. Closed-form consequences:
  theta(L) = (T*L/(G*J))*(1 - tanh(u)/u), |B(0)| = T*tanh(u)/k,
  T_sv(L) = T*(1 - 1/cosh(u)), T_w(L) = T/cosh(u), T_sv(0) = 0 and
  T_w(0) = T.
- Fork-supported beam (fork ends hold theta = theta'' = 0, torque T at
  midspan through a rigid collar): half-beam x in [0, L/2],
  theta(x) = (T/(2*G*J))*(x - sinh(k*x)/(k*cosh(v))), mirrored across
  the symmetry plane theta'(L/2) = 0. Closed-form consequences:
  theta(L/2) = (T*L/(4*G*J))*(1 - tanh(v)/v),
  B(L/2) = (T/(2*k))*tanh(v), B(0) = 0, and per half at the fork face
  T_sv = (T/2)*(1 - 1/cosh(v)) with T_w = (T/2)/cosh(v), while at the
  collar T_sv = 0 and T_w = T/2.
- Free Saint-Venant baselines appear only inside the twist ratios
  (never as a deliverable): cantilever free twist T*L/(G*J) and fork
  free midspan twist T*L/(4*G*J); the ratios 1 - tanh(u)/u and
  1 - tanh(v)/v quantify the stiffening of the restraint.

## Workflow

1. Fix the section and the material: the I-section dims (d, b, t_f,
   t_w) in that order and the isotropic moduli E, G, with the
   thin-walled open geometry d > 2*t_f. Evaluate the open-section
   Saint-Venant constant J with i_section_saint_venant_j.
2. Compute the warping section constants: i_section_warping_constant
   for Cw = I_y*h**2/4, i_section_sectorial_max for the sectorial
   coordinate omega_tip = h*b/4 at the flange tip, and the sectorial
   modulus Cw/omega_tip. Verify the identity Cw = t_f*h**2*b**3/24.
3. Get the decay parameter of the non-uniform torsion equation:
   torsion_decay_parameter for k = sqrt(G*J/(E*Cw)), the decay length
   1/k and the dimensionless products u = k*L and v = k*L/2.
4. Solve the built-in cantilever response: fixed_end_response for the
   restrained tip twist, tip twist rate, root bimoment and tip torque
   split, then fixed_end_twist, fixed_end_twist_rate and
   fixed_end_bimoment for the span profile, with torque_components
   showing the Saint-Venant share climbing from 0% at the built-in root
   to T*(1 - 1/cosh(u)) at the free tip.
5. Solve the fork-supported beam response: fork_response for the
   restrained midspan twist, the midspan bimoment peak and the per-half
   torque components at the fork face and the collar, then fork_twist
   and fork_bimoment for the symmetric span profile.
6. Evaluate the warping normal stress at the flange tip:
   warping_stress on the peak bimoment (the root for the cantilever,
   the midspan collar for the fork beam), sigma_w = B*omega_tip/Cw.
7. Quantify the restraint and confirm determinism: compare the
   restrained twist against the free Saint-Venant baseline through the
   twist_ratio keys of the response dicts, then confirm the
   deterministic checks with the contract test
   scripts/test_restrained_warping.py.

## Worked example

I-beam d = 0.3 m, b = 0.15 m, t_f = 0.01 m, t_w = 0.006 m (a
spar-like open section), aluminium E = 70 GPa, G = 27 GPa, span L =
3 m. All values below are real outputs of
scripts/restrained_warping_logic.py (stdlib math, exit 0).

- Section constants: h = 0.29 m, h_w = 0.28 m; J = 1.2016e-07 m^4 with
  G*J = 3244.32 N m^2; I_y = 5.625e-06 m^4, Cw = 1.18265625e-07 m^6
  with E*Cw = 8278.59375 N m^4 (the sectorial integral t_f*h**2*b**3/24
  matches to a 1.32348898008e-23 m^6 residual); omega_tip = 0.010875
  m^2 with sectorial modulus W_w = 1.0875e-05 m^4; k =
  0.626013294436 1/m, decay length 1/k = 1.59741016507 m (more than
  half the span, so u = k*L = 1.87803988331 is a strongly restrained
  regime, not a local end effect).
- Fixed-end cantilever, torque T = 500 N m at the free tip: restrained
  tip twist theta(L) = 0.227407224589 rad against the free baseline
  T*L/(G*J) = 0.462346500962 rad, twist ratio 1 - tanh(u)/u =
  0.49185453792: the built-in root cuts the twist to 49.2% of the free
  value. Twist rate peaks at the tip at 0.108066620404 rad/m (zero at
  the root, where warping is blocked); the Saint-Venant surface shear
  there is tau = G*t*theta' = 29177987.509 Pa on the flange (t = t_f)
  and 17506792.5054 Pa on the web (t = t_w).
- Bimoment at the root B(0) = -762.21819312 N m^2 (magnitude
  T*tanh(u)/k) and the tip bimoment B(L) = 3.54696309006e-13 N m^2,
  zero to roundoff: the tip warps freely. Warping normal stress at the
  flange tip at the root sigma_w = B(0)*omega_tip/Cw = -70089029.2524
  Pa (-70.09 MPa, compression at the positive-omega tip; the two tips
  of each flange pair carry equal and opposite stress), which equals
  E*omega_tip*|theta''(0)|, the flange-bending picture of the bimoment.
- Torque split (T = 500 N m carried everywhere): at the root T_sv = 0
  and T_w = 500 N m (all warping torque: the root blocks warping, so
  the torque arrives as differential flange bending); at the tip
  T_sv(L) = T*(1 - 1/cosh(u)) = 350.602697909 N m (70.1%) and
  T_w(L) = T/cosh(u) = 149.397302091 N m (29.9%).
  Span table (real module rows; theta rad, theta' rad/m, B N m^2,
  sigma_w Pa, T_sv N m, T_w N m):
  z = 0.000:  theta = 0.000000e+00,  rate = 0.000000e+00,
    B = -7.622182e+02, sigma_w = -7.008903e+07, T_sv = 0.000000e+00,
    T_w = 5.000000e+02
  z = 0.750:  theta = 2.208046e-02,  rate = 5.431743e-02,
    B = -4.588543e+02, sigma_w = -4.219350e+07, T_sv = 1.762231e+02,
    T_w = 3.237769e+02
  z = 1.500:  theta = 7.591534e-02,  rate = 8.622829e-02,
    B = -2.585118e+02, sigma_w = -2.377120e+07, T_sv = 2.797522e+02,
    T_w = 2.202478e+02
  z = 2.250:  theta = 1.476402e-01,  rate = 1.028972e-01,
    B = -1.162102e+02, sigma_w = -1.068600e+07, T_sv = 3.338314e+02,
    T_w = 1.661686e+02
  z = 3.000:  theta = 2.274072e-01,  rate = 1.080666e-01,
    B = 3.546963e-13, sigma_w = 3.261575e-08, T_sv = 3.506027e+02,
    T_w = 1.493973e+02
  The Saint-Venant share climbs monotonically from 0% at the root to
  70.1% at the tip while the bimoment magnitude decays hyperbolically
  from the root peak.
- Fork-supported beam, torque T = 1000 N m at midspan through a rigid
  collar (both forks hold theta = 0 and let the section warp):
  restrained midspan twist theta(L/2) = 0.0502830037738 rad against the
  free baseline T*L/(4*G*J) = 0.231173250481 rad, twist ratio
  1 - tanh(v)/v = 0.217512206405: the collar restraint cuts the midspan
  twist to 21.8% of the free value, far stronger than the cantilever
  case because the collar blocks warping at the very section of maximum
  twist.
- Bimoment: it vanishes at the forks (B(0) = 0 N m^2, warping free) and
  peaks at the collar at B(L/2) = (T/(2*k))*tanh(v) = 586.865845196
  N m^2, with sigma_w = 53964675.4204 Pa (53.96 MPa) at the flange tip
  there.
- Torque split (each half carries T/2 = 500 N m): at the fork face
  T_sv = (T/2)*(1 - 1/cosh(v)) = 160.842723176 N m (32.2%) and
  T_w = (T/2)/cosh(v) = 339.157276824 N m (67.8%); at the collar
  T_sv = 0 and T_w = 500 N m per half: the applied torque enters the
  beam entirely as warping torque at the midspan collar.
  Span table (real module rows):
  z = 0.000:  theta = 0.000000e+00,  B = 0.000000e+00,
    sigma_w = 0.000000e+00,  T_sv = 1.608427e+02, T_w = 3.391573e+02
  z = 0.750:  theta = 3.427006e-02,  B = 2.638170e+02,
    sigma_w = 2.425903e+07,  T_sv = 1.227691e+02, T_w = 3.772309e+02
  z = 1.500:  theta = 5.028300e-02,  B = 5.868658e+02,
    sigma_w = 5.396468e+07,  T_sv = 0.000000e+00, T_w = 5.000000e+02
  z = 2.250:  theta = 3.427006e-02,  B = 2.638170e+02,
    sigma_w = 2.425903e+07,  T_sv = 1.227691e+02, T_w = 3.772309e+02
  z = 3.000:  theta = 0.000000e+00,  B = 0.000000e+00,
    sigma_w = 0.000000e+00,  T_sv = 1.608427e+02, T_w = 3.391573e+02
  The profile is symmetric about midspan: theta and the bimoment
  mirror, and each half twists toward its own fork.
- Residual and identity checks (real module runs): the cantilever ODE
  residual max |E*Cw*theta'''' - G*J*theta''| over 501 stations is
  zero to machine roundoff (spec anchor 1.137e-13, bound 1e-9), as is
  the torque partition residual max |T_sv + T_w - T|; the cantilever
  boundary residuals are |theta(0)| = 0.0, |theta'(0)| = 0.0,
  |theta''(L)| = 4.284e-17 1/m^2 and |G*J*theta'(L) - E*Cw*theta'''(L)
  - T| = 0.0; the fork torque at the fork section and at the midspan
  face of the half-beam both equal 5.000000e+02 N m against T/2 = 500;
  the mirror remainder |theta(L/2) - theta(L/2 + 0.006)| = 1.274e-06
  rad equals theta''(L/2)*dz**2/2, the second-order remainder of the
  symmetry.

## Verification

- Confirm the section constants of the anchor I-beam: J = 1.2016e-07
  m^4, Cw = 1.18265625e-07 m^6, omega_tip = 0.010875 m^2, W_w =
  1.0875e-05 m^4 and k = 0.626013294436 1/m, with the identity
  |Cw - t_f*h**2*b**3/24| below 1e-20 m^6.
- Confirm the restraint twist ratios: fixed_end_response twist_ratio =
  0.49185453792 equals 1 - tanh(u)/u, fork_response twist_ratio =
  0.217512206405 equals 1 - tanh(v)/v, each below the free baseline.
- Confirm the torque partition: torque_components sums T_sv + T_w to
  the carried torque at every sampled station, T_sv equals G*J*theta'(z)
  from the twist-rate profile, the root split is 0/500 N m and the tip
  split is 350.602697909/149.397302091 N m for the cantilever.
- Confirm the boundary conditions: |theta(0)| and |theta'(0)| below
  1e-9 for the cantilever root and |B(L)| below 1e-9 N m^2 at its free
  tip; |fork_twist(0)|, |fork_bimoment(0)| and the fork midspan twist
  rate below 1e-9, with fork_twist(z) equal to fork_twist(L - z).
- Confirm the flange-bending identity of the warping stress:
  |sigma_w| = B*omega_tip/Cw equals E*omega_tip*|theta''| at the root
  and midspan peaks (anchor -70089029.2524 Pa and 53964675.4204 Pa).
- Confirm every non-physical input raises ValueError: non-positive
  section dims, d <= 2*t_f, non-positive E, G, Cw, J, zero span,
  zero torque in the response functions, and non-positive omega_tip or
  Cw in warping_stress; wrong function arity raises TypeError.
- Run the contract test offline: python3
  scripts/test_restrained_warping.py (35 tests, deterministic, no RNG,
  math only).

## Related leaves

- structures/fem/torsion-shear-flow: the free-warping complement of
  this pack. It returns the uniform Saint-Venant twist rate T/(G*J),
  the closed-section shear flow of the Bredt-Batho circulation and the
  torsional stress margin; this leaf returns the restrained response
  that torsion-shear-flow never touches (no warping constant, no
  bimoment, no theta'' warping-stress term in its claim).
- structures/fem/shear-center-analysis: the transverse-shear complement
  that walks the contour under a transverse force V and builds the
  V*Q/I shear-flow distribution to locate the shear-center offset; it
  applies no torque, while this leaf applies torque with the shear
  center at the centroid.
- structures/fem/beam-column-analysis: elastic compression and bending
  of columns, the axial companion; torsional-flexure instability under
  axial load is outside both leaves.
- structures/fem/buckling-analysis: elastic buckling eigenvalues, a
  stability check, not a torque response.
- structures/fem/beam-frame-analysis: member-end bending and frame
  response under applied loads, adjacent stiffness checks in the same
  airframe.

## Pitfalls

- Reading the free twist rate as the restrained response: the free
  Saint-Venant baselines T*L/(G*J) and T*L/(4*G*J) exist in this leaf
  only as denominators of the twist ratios; the deliverable is the
  restrained twist, 49.2% of free for the cantilever and 21.8% for the
  fork beam in the worked example.
- Flipping the root torque split: at the built-in root the full torque
  arrives as warping torque (T_sv = 0, T_w = T) because the root blocks
  warping and the torque becomes differential flange bending; quoting
  the Saint-Venant share there as anything but zero misstates the load
  path. At the free tip the shares are T*(1 - 1/cosh(u)) and
  T/cosh(u).
- Using the full-section minor inertia for Cw: the thin-walled
  sectorial model keeps only the flange pair in I_y = 2*b**3*t_f/12
  because the web lies on the sectorial zero line; the AISC-style
  addition of the web's own t_w**3*h_w/12 term stays below 0.1% here
  and belongs to a different model.
- Applying the doubly symmetric closed form to a channel, Z, angle or
  hat section: their shear center sits off the web line and the
  sectorial coordinates need the shear-center-offset integration, a
  stated extension outside this contract.
- Forgetting the mirror in the fork case: the half-beam closed form
  only covers x in [0, L/2]; the full span is theta(min(z, L - z)),
  which is why the fork table rows repeat symmetrically about midspan.
- Sign of the warping stress: sigma_w = B*omega_tip/Cw is signed, and
  the two flange tips of each flange pair carry equal and opposite
  stress; quote the sign relative to the positive-omega tip.
- Mixing unit systems: kN m torque against Pa moduli and metre
  dimensions silently shifts k, the twist and the bimoment by decades;
  keep N m, m and Pa together before quoting a result.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_restrained_warping.py

The test covers the worked-example contract (section constants within
1e-9 relative, k = 0.626013294436, restrained tip twist 0.227407224589
rad with twist ratio 0.49185453792 for the cantilever and 0.0502830037738
rad with ratio 0.217512206405 for the fork beam), the open-section
rectangle-sum identity for J and the sectorial integral identity for Cw,
the closed-form bimoment and torque-split expressions at the root, tip,
fork face and collar, the five anchor span rows of both cases, the
torque partition and ODE residual over 501 stations, the boundary
conditions, the flange-bending stress identity, fork symmetry and the
second-order mirror remainder, run-to-run determinism and ValueError
rejection of every non-physical input in the validation list. All
numeric asserts are order-safe tolerances, so the file passes under both
/usr/bin/python3 and the pre-push hook interpreter.

## Compliance

- FAR-25 (25.301 applied loads, 25.303 1.5 ultimate factor) and CS-25
  (25.301/25.303) set the load context of the torque cases, summarized
  only; standards-map.yaml marks both reference-only and gated: false.
  No standard text is reproduced.
- compliance: STANDARDS-REF, gated: false.
