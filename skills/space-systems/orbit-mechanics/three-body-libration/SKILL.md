---
name: three-body-libration
description: "Use when you must analyze the circular restricted three-body problem (CR3BP) for a spacecraft near two massive primaries: compute the mass ratio from the primary masses, locate the collinear points L1, L2, L3 by solving the rotating-frame force balance with a bracketed Newton iteration, place the triangular points L4 and L5 from the closed-form equilateral construction, convert dimensionless coordinates into physical distances from each primary, and evaluate the Jacobi constant for a planar state. Produces the five libration point locations, the physical distances, and the Jacobi constant that gate a three-body mission assessment. Trigger: three-body-libration, cr3bp, libration-points, lagrange-points-l1-l2, jacobi-constant, earth-moon-l1."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: orbit-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: orbit-mechanics
  tags: [three-body-libration, cr3bp, libration-points, jacobi-constant, collinear-points, earth-moon-l1]
  version: 0.1.0
  author: Aero Agent Skills
---

# Three-Body Libration (space-systems/orbit-mechanics/three-body-libration)

Use when the task is locating and assessing the equilibrium points of the
circular restricted three-body problem (CR3BP): a spacecraft moving under
the gravity of two massive primaries in circular orbits about their common
barycenter. This leaf computes the mass ratio, finds the collinear points
L1, L2, L3 as roots of the rotating-frame force balance with a bracketed
Newton iteration and a bisection fallback, places the triangular points L4
and L5 from the closed-form equilateral construction, converts the
dimensionless coordinates into physical distances from each primary, and
evaluates the Jacobi constant for a given planar state. It implements the
standard CR3BP equilibrium model in pure Python, stdlib only. It pairs
with space-systems/orbit-mechanics/gravity-assist-swingby for hyperbolic
flyby alternatives and with space-systems/orbit-mechanics/keplerian-
elements and space-systems/orbit-mechanics/hohmann-transfer for the
two-body motion context around the same mission.

## Domain quick reference

- Nondimensional rotating frame: the heavier primary 1 sits at x = -mu,
  the lighter primary 2 at x = 1 - mu, the barycenter at x = 0, and
  distances are normalized by the primary separation a. Distances are
  normalized by a, velocities by the circular orbit speed about the
  barycenter, so the equations carry no explicit gravitational constant.
- Mass ratio: mu = m2 / (m1 + m2), with m1 > m2 (mu < 0.5). For
  Earth-Moon, mu = 7.348e22 / (5.972e24 + 7.348e22) = 0.0121545, close to
  the representative constant 0.01215.
- Collinear force balance: f(x) = x - (1 - mu) * (x + mu) / |x + mu|^3 -
  mu * (x - (1 - mu)) / |x - (1 - mu)|^3. Its roots are L1 (between the
  primaries), L2 (beyond the lighter primary) and L3 (beyond the heavier
  primary). The derivative f'(x) = 1 + 2(1 - mu)/|x + mu|^3 + 2 mu/
  |x - (1 - mu)|^3 is strictly positive, so each branch has one root.
- Newton iteration from branch defaults (L1 from the midpoint 0.5 - mu,
  L2 from 1.2, L3 from -1.2); if Newton leaves the branch bracket or does
  not converge in 80 iterations, fall back to a 200-step bisection on the
  bracket (L1: (-mu + 1e-6, 1 - mu - 1e-6), L2: (1 - mu + 1e-6, 5.0),
  L3: (-5.0, -mu - 1e-6)). Convergence is measured by |f(x)| < 1e-12.
- Triangular points: L4 = (0.5 - mu, sqrt(3)/2) and L5 = (0.5 - mu,
  -sqrt(3)/2), the two equilateral configurations with the primaries; at
  these points r1 = r2 = 1 exactly.
- Physical distances: from primary 1 (heavier), d = (x + mu) * a; from
  primary 2 (lighter), d = |x - (1 - mu)| * a.
- Jacobi constant: C = x^2 + y^2 + 2(1 - mu)/r1 + 2 mu/r2 - (vx^2 + vy^2)
  with r1 = sqrt((x + mu)^2 + y^2) and r2 = sqrt((x - (1 - mu))^2 + y^2).
  C is an integral of the CR3BP motion in the rotating frame.
- The five points are the station-keeping sites that gate a three-body
  mission geometry assessment; this leaf does not propagate motion about
  them.
- ECSS frames the space systems engineering context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the system: masses of the two primaries and their separation a
   (mass_ratio gives mu from m1, m2 and rejects a secondary that is not
   lighter).
2. Solve the collinear points one branch at a time with collinear_point
   (mu, branch): Newton from the branch default guess, bisection fallback
   if Newton leaves the bracket. Confirm each root with
   collinear_force_balance: |f(x)| < 1e-10 is the correctness gate.
3. Get all five points in one call with lagrange_points (mu): L1, L2, L3
   as dimensionless x, L4 and L5 as (x, y) tuples from the closed-form
   equilateral construction.
4. Convert to physical distances with physical_distance_from_primary
   (x, mu, separation_m, primary): primary 1 is the heavier body (Earth
   in Earth-Moon), primary 2 the lighter (the Moon).
5. Evaluate the Jacobi constant with jacobi_constant (mu, x, y, vx, vy)
   for any planar rotating-frame state; the call rejects a state on top
   of a primary.
6. For a one-shot summary run three_body_assessment (mass_primary,
   mass_secondary, separation_m, state = None): mu, all five points, the
   L1 distance from the heavier primary, the L2 distance from the lighter
   primary (L2 lies beyond it), and the Jacobi constant when a state is
   given.
7. Confirm the deterministic checks with the contract test
   scripts/test_three_body_libration.py.

## Worked example

Earth-Moon: m1 = 5.972e24 kg, m2 = 7.348e22 kg, a = 384400 km. Real
module outputs:

- Mass ratio: mu = 0.0121545 (bound 0.0120-0.0123), consistent with the
  representative Earth-Moon constant 0.01215.
- L1: x = 0.8368957, force balance residual f = 4.4e-16. The Earth-to-L1
  fraction x + mu = 0.84905 lies in the 0.80-0.88 band.
- L2: x = 1.1556974, residual f = 1.7e-16; Earth-to-L2 fraction
  x + mu = 1.16785 in the 1.12-1.20 band.
- L3: x = -1.0050643, residual f = 4.3e-16, below the -0.9 ceiling.
- L4: (0.4878455, 0.8660254) and L5: (0.4878455, -0.8660254): x equals
  0.5 - mu to machine precision, y equals +/- sqrt(3)/2 exactly.
- Physical L1 distance from Earth center: (x_L1 + mu) * 384400 km =
  326375 km (bound 310000-345000 km; published about 326000 km).
- Physical L2 distance from Earth center: (x_L2 + mu) * 384400 km =
  448922 km (bound 425000-465000 km; published about 448000 km). The
  same point sits 64522 km beyond the Moon center (the
  L2_distance_from_primary_km assessment key, quoted from the lighter
  primary).
- Jacobi constant at L4 with zero velocity: C = 2.987993. Closed form:
  x^2 + y^2 + 2 = 0.237993 + 0.75 + 2 = 2.987993, matching to 1e-12 and
  inside the 2.98-3.00 bound.
- three_body_assessment(m_earth, m_moon, 3.844e8, state = L4 rest state)
  returns mu 0.0121545, all five points, L1 distance 326375 km from
  Earth, L2 distance 64522 km from the Moon, and C = 2.987993.


## Pitfalls

- Reversing the primary roles: the heavier body is primary 1 (mu
  comes from m2 / (m1 + m2) and the code rejects a secondary that is
  not lighter), so swapping the masses changes mu, every point
  location, and the physical distance mapping.
- Confusing the physical-distance anchor: L1 is quoted from the
  heavier primary while the assessment's L2 key is the distance from
  the LIGHTER primary (64522 km beyond the Moon), not from Earth;
  the same point is 448922 km from Earth center.
- Forgetting the frame is dimensionless: distances come back
  normalized by the separation a, and only the conversion call
  multiplies by the physical separation; a dimensionless x read as
  kilometers is off by orders of magnitude.
- Trusting Newton without the residual gate: each collinear root
  must satisfy |f(x)| < 1e-10 and the iteration falls back to
  bisection when Newton leaves the branch bracket, so check the
  force-balance residual rather than accepting the raw iterate.
- Assigning the wrong branch to the wrong point: L1 sits between the
  primaries, L2 beyond the lighter one, and L3 beyond the heavier;
  using the 1.2 default guess on the wrong branch returns the wrong
  equilibrium.
- Treating the points as motion endpoints: this leaf locates and
  gates the five equilibrium sites but does not propagate or
  stabilize motion about them, so station-keeping analysis must come
  from elsewhere.
## Verification

- Confirm every collinear root satisfies |f(x)| < 1e-10: at mu =
  0.01215 the residuals are below 5e-16 and at mu = 0.1 below 1e-10 for
  all three branches (the iteration converges for a different mass ratio
  too).
- Confirm L4/L5 closed-form exactness: x = 0.5 - mu to 1e-9 and
  y = +/- sqrt(3)/2 to 1e-12.
- Confirm physical distances: L1 from Earth in 310000-345000 km and L2
  from Earth in 425000-465000 km for the Earth-Moon system.
- Confirm the Jacobi closed form at L4: C equals x^2 + y^2 + 2 within
  1e-6 and lies in the 2.98-3.00 bound.
- Confirm ValueError rejection of non-positive masses, mu >= 0.5,
  non-positive separation, a branch outside L1/L2/L3, a primary outside
  1/2, and a state on top of a primary (r < 1e-12).
- Confirm determinism: repeated calls return identical results.
- Run the contract test offline: python3
  scripts/test_three_body_libration.py (35 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/gravity-assist-swingby: the hyperbolic
  flyby alternative to libration point placement.
- space-systems/orbit-mechanics/keplerian-elements: two-body orbital
  elements that frame the primaries' own motion.
- space-systems/orbit-mechanics/hohmann-transfer: two-body transfer
  sizing for reaching a libration region.
- space-systems/orbit-mechanics/orbital-perturbations: perturbing
  accelerations that matter once a point is occupied.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_three_body_libration.py

The test covers the Earth-Moon worked example (mass ratio in 0.0120-
0.0123, collinear roots with the |f| < 1e-10 residual gate and their
dimensionless bounds, L4/L5 closed-form exactness, physical L1 and L2
distances from Earth in 310000-345000 km and 425000-465000 km, the L2
distance from the Moon, the Jacobi constant closed form at L4), the same
residual gate at mu = 0.1 and at the default constant mu, the bisection
fallback when Newton leaves the branch bracket, determinism, and
ValueError rejection of every non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA download
  (ecss.nl/standards); the CR3BP relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
