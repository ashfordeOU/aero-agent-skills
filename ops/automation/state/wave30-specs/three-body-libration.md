# Wave-30 leaf spec: three-body-libration (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/three-body-libration/
- Pack: orbit-mechanics (dense pack; the CR3BP collinear and triangular
  libration points are NOT covered by any sibling: gravity-assist-swingby is
  the patched-conic hyperbolic flyby, orbit-dynamics is two-body + J2,
  hohmann/low-thrust/plane-change/lambert are transfer maneuvers).
- Standards ids: ecss (reference-only; space-systems orbit pack convention).
  Ledger Standard: ecss.
- Family: space-systems

## Claim

Analyze the circular restricted three-body problem (CR3BP) for a spacecraft
near two massive primaries: compute the mass ratio from the primary masses,
locate the collinear libration points L1, L2, and L3 by solving the rotating-
frame force-balance equation with a bracketed Newton iteration, place the
triangular points L4 and L5 from the closed-form equilateral construction,
convert the dimensionless coordinates into physical distances from each
primary, and evaluate the Jacobi constant for a given planar state. Produces
the five libration point locations, the physical distances, and the Jacobi
constant that gate a three-body mission geometry assessment.

Does NOT do: compute hyperbolic gravity-assist swingby trajectories
(gravity-assist-swingby owns periapsis speed and turn angle from v_infinity);
propagate two-body or J2-perturbed orbits (orbit-dynamics owns vis-viva and
Hohmann sizing); compute transfer maneuvers (hohmann-transfer, low-thrust-
spiral, plane-change-maneuver, lambert-transfer own those); model unstable
manifolds, halo/Lissajous orbits, or station-keeping (the linearized motion
about the points is out of scope). This leaf finds the equilibrium points and
the Jacobi constant only; no orbit propagation.

## Model (implement exactly)

Module constants:
- GRAV = 6.67430e-11 (m3/kg/s2) - not strictly needed because the
  nondimensional formulation uses the mass ratio directly; kept for a mass
  ratio sanity check.
- MU_EARTH_MOON_DEFAULT = 0.01215 (representative Earth-Moon mass ratio,
  used when mass inputs are not given).
- ND_TOL = 1e-12, ND_MAX_ITER = 80 (Newton iteration control).

Functions (pure stdlib; positions in the rotating frame: primary 1 at x =
-mu, primary 2 at x = 1 - mu, barycenter at 0, distances normalized by the
primary separation a):
- mass_ratio(mass_primary, mass_secondary) -> float: mu = m2 / (m1 + m2).
  ValueError if either mass <= 0 or mu >= 0.5 (secondary heavier than
  primary breaks the convention).
- collinear_force_balance(x, mu) -> float:
  f = x - (1 - mu) * (x + mu) / abs(x + mu)**3 - mu * (x - (1 - mu)) /
  abs(x - (1 - mu))**3 (rotating-frame equilibrium; sign convention gives
  f(x) = x - gravitational pull terms; roots are L1 (between the primaries),
  L2 (beyond the secondary), L3 (beyond the primary)).
- collinear_point(mu, branch, x_guess=None) -> float: solve f(x) = 0 with
  Newton from the guess (defaults: L1 guess midpoint between primaries
  (1 - 2*mu)/2? use 0.5 - mu? use x = (1 - mu)/2; L2 guess 1 - mu + mu**0.4?
  use 1.2; L3 guess -1.2), guarded: if Newton leaves the branch bracket or
  does not converge in ND_MAX_ITER, fall back to 200-step bisection on the
  branch bracket (L1: (-mu + 1e-6, 1 - mu - 1e-6); L2: (1 - mu + 1e-6, 5.0);
  L3: (-5.0, -mu - 1e-6)). ValueError if branch not in ("L1","L2","L3") or
  mu outside (0, 0.5). Return the converged x.
- lagrange_points(mu) -> dict: {L1: x, L2: x, L3: x, L4: (0.5 - mu,
  sqrt(3)/2), L5: (0.5 - mu, -sqrt(3)/2)} (L4/L5 x coordinates in the same
  barycentric frame: x = 0.5 - mu, y = +/- 0.8660254037844386).
- physical_distance_from_primary(x, mu, separation_m, primary=1) -> float:
  primary 1 (heavier, at -mu): distance = (x + mu) * separation_m;
  primary 2 (lighter, at 1 - mu): distance = abs(x - (1 - mu)) *
  separation_m. ValueError if separation_m <= 0 or primary not in (1, 2).
- jacobi_constant(mu, x, y, vx, vy) -> float:
  C = x**2 + y**2 + 2 * (1 - mu) / r1 + 2 * mu / r2 - (vx**2 + vy**2)
  with r1 = sqrt((x + mu)**2 + y**2), r2 = sqrt((x - (1 - mu))**2 + y**2).
  ValueError if r1 or r2 < 1e-12 (on top of a primary).
- three_body_assessment(mass_primary, mass_secondary, separation_m,
  state=None) -> dict: {mu, lagrange_points, L1_distance_from_primary_km,
  L2_distance_from_primary_km (from the lighter primary for L2, from the
  heavier for L1 - document clearly), jacobi_constant (if state given)}.
  state is a dict {x, y, vx, vy} in dimensionless rotating-frame units.

## Worked example

Earth-Moon: m1 = 5.972e24 kg, m2 = 7.348e22 kg, a = 384 400 km.

Deterministic anchors (module outputs as assert targets; bounds):
- mu = 7.348e22 / (5.972e24 + 7.348e22) = 0.0121557 (bound 0.0120-0.0123).
- L4 = (0.4878443, 0.8660254038): assert x within 1e-9 of 0.5 - mu and y
  within 1e-12 of sqrt(3)/2 (closed form exact).
- L5 mirrors L4 with negative y.
- L1 dimensionless x: the Earth-to-L1 physical distance fraction is in
  0.80-0.88 of a -> with x_L1 = -mu + fraction: x_L1 in 0.79-0.87 (hand
  expectation ~0.837; assert the builder's converged value and check the
  force balance |f(x)| < 1e-10 as the REAL correctness check).
- L2: Earth-to-L2 fraction in 1.12-1.20 -> x_L2 in 1.11-1.19; |f| < 1e-10.
- L3: x_L3 < -0.9 and |f| < 1e-10.
- Physical L1 distance from Earth center = (x_L1 + mu) * 384400 km in
  310 000-345 000 km (published ~326 000 km).
- Physical L2 distance from Earth center = (x_L2 + mu) * 384400 km in
  425 000-465 000 km (published ~448 000 km).
- Jacobi check at L4 with zero velocity: C = x^2 + y^2 + 2(1-mu)/1 + 2mu/1
  (r1 = r2 = 1 at L4): x^2 + y^2 = 0.4878443^2 + 0.75 = 0.237992 + 0.75 =
  0.987992; C = 0.987992 + 2 = 2.987992 (bound 2.98-3.00; assert builder value
  within 1e-6 of this closed form).
If a value is outside its bound, debug before writing tests. The |f| < 1e-10
residual check is the primary correctness gate for the collinear points. Show
real module outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: masses <= 0, mu >= 0.5, separation <= 0, branch not in
  ("L1","L2","L3"), primary not in (1,2), state on top of a primary (r <
  1e-12).
- L4/L5 closed-form exactness.
- Residual |f(collinear x)| < 1e-10 for L1, L2, L3 at mu = 0.01215 and at a
  second mu (e.g. 0.1) (the iteration must converge for a different mu too).
- Jacobi closed-form at L4.
- Determinism.

## Corpus fragment (eval/hit1-wave30-three-body-libration.yaml)

Forbidden tokens (siblings): swingby, periapsis, turn-angle, v-infinity,
hyperbolic excess (gravity-assist-swingby); hohmann, vis-viva, j2, transfer
delta-v (orbit-dynamics); low-thrust, lambert, phasing (transfer leaves);
halo-orbit propagation (explicitly out of scope). Distinctive tokens ONLY:
three-body-libration, cr3bp, libration-points, lagrange-points-l1-l2,
jacobi-constant, earth-moon-l1.

Query 1: "Locate the libration-points of the earth-moon cr3bp: L1, L2, L3 by
force balance and L4, L5 by the equilateral construction" (id
w30-three-body-libration-1).
Query 2: "Compute the jacobi-constant for a spacecraft state in the
three-body-libration problem and the physical L1 distance from Earth"
(id w30-three-body-libration-2).
intent: "space-systems; CR3BP libration point and Jacobi analysis".

## Description/tag guidance

Description opens "Use when you must analyze the circular restricted
three-body problem (CR3BP) for a spacecraft near two massive primaries:" and
lists the outputs in the Claim. First tag: three-body-libration. Additional
tags: cr3bp, libration-points, jacobi-constant, collinear-points,
earth-moon-l1. No generic single words. 50-150 words, <=1000 chars, no em
dash, no "classified".
