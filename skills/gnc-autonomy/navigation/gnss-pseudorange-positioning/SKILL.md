---
name: gnss-pseudorange-positioning
description: "Use when you must compute a GNSS receiver position fix from pseudorange measurements: given satellite positions in ECEF and their pseudoranges (geometric range plus receiver clock bias), solve the four-unknown navigation equations for x, y, z and clock bias with an iterated least-squares adjustment and 4x4 normal equation solves. Produces the converged ECEF position, clock bias, post-fit residuals with RMS, and post-fit position error from the geometry matrix. Requires at least four satellites; treats the Earth as spherical for geodetic conversion only. Trigger: pseudorange positioning, GNSS position fix, receiver clock bias, iterated least squares fix, ECEF position solution, satellite pseudorange residual, snapshot navigation solution."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [gnss-pseudorange-positioning, pseudorange-positioning, gnss-position-fix, receiver-clock-bias, iterated-least-squares-fix, ecef-position-solution, satellite-pseudorange-residual, snapshot-navigation-solution]
  version: 0.1.0
  author: Aero Agent Skills
---

# GNSS Pseudorange Positioning (gnc-autonomy/navigation/gnss-pseudorange-positioning)

Use when the task is computing a single-epoch GNSS receiver position
fix from pseudorange measurements. Each measurement is the geometric
range to the satellite plus the receiver clock bias expressed in
metres, so the four unknowns (receiver ECEF position x, y, z and clock
bias) need at least four satellites and a nonlinear solve. This leaf
linearizes the range equations about the current state, builds the
geometry matrix H with rows [-(sx-rx)/range, -(sy-ry)/range,
-(sz-rz)/range, 1], solves the 4x4 normal equations (H^T H) dx = H^T dr
with a Gaussian elimination solver, and iterates until the correction
norm falls below tolerance. It pairs with dilution-of-precision for the
geometry quality read, kalman-filter-design for time-domain fusion of
successive fixes, and navigation-frames for the coordinate conventions.
The leaf is a snapshot solution: no smoothing, no dynamics model, and
the geodetic conversion uses a spherical Earth approximation only.

## Domain quick reference

- Measurement model: pseudorange_i = geometric range_i + clock bias,
  with geometric range |sat_i - recv| from the ECEF positions.
- Geometry row: the partial of the i-th range equation with respect to
  the receiver position is the negated line of sight, so row i of H is
  [-(sx-rx)/range, -(sy-ry)/range, -(sz-rz)/range, 1]; the 1 is the
  clock-bias partial.
- Linearized system: H dx = dr with dr_i = measured_i - predicted_i.
- Normal equations: dx = (H^T H)^-1 H^T dr, a 4x4 solve each iteration.
- Update: x, y, z, clock bias all shift by dx, then ranges and H are
  recomputed (iterated least squares, converges in a few iterations
  from the origin start).
- Convergence test: stop when the correction norm falls below tol.
- Post-fit residual RMS: sqrt(mean(residual_i^2)) after convergence.
- Post-fit position error: pos_1sigma = uere_equiv * pdop with
  uere_equiv = residual RMS and pdop from the trace of (H^T H)^-1,
  companion to the dilution-of-precision leaf.
- Spherical geodetic conversion: lat = atan2(z, sqrt(x^2 + y^2)),
  lon = atan2(y, x), alt = radius - R_EARTH with R_EARTH =
  6378137.0 m (WGS-84 ellipsoid out of scope, flagged approximate).
- Units are metres throughout: satellite positions, pseudoranges and
  clock bias all in m. Requires at least four satellites.
- ARP4754A frames the development context for the navigation function;
  the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Gather the satellite record list: each entry needs ECEF x, y, z and
   the measured pseudorange in metres; reject sets under four
   satellites and records with missing or non-finite values
   (ValueError).
2. Optionally seed the iteration with a prior x0, y0, z0, b0; the
   default start is the ECEF origin with zero clock bias.
3. Run solve_iterated(satellites, iters=8, tol=1e-6): the function
   rebuilds the geometry matrix each pass, solves the 4x4 normal
   equations, updates the state, and stops on a small correction.
4. Read the fix dict: x, y, z, clock_bias, the per-satellite
   residuals, residual_rms, iterations and the converged flag.
5. Gate navigation processing on the fix-quality flags: converged
   state, iteration count and the residual RMS level.
6. For the geometry quality read, call position_error_estimate on the
   fix to get the post-fit gdop, pdop, uere_equiv and pos_1sigma.
7. Convert to latitude, longitude and altitude with
   to_geodetic_approx when a geodetic output is needed, and flag the
   spherical-Earth approximation.
8. Confirm the deterministic checks with the contract test
   scripts/test_gnss_pseudorange_positioning.py.

## Worked example

Four satellites around a receiver at the ECEF origin (0, 0, 0) with a
true clock bias of 100 m (documented test constellation):

- sat1 (0, 0, 20000 km), pseudorange 20000000 + 100 m.
- sat2 (20000 km, 0, 0), pseudorange 20000000 + 100 m.
- sat3 (0, 20000 km, 0), pseudorange 20000000 + 100 m.
- sat4 on the diagonal at 10^7*sqrt(2) m per axis (about 14142 km per
  axis, the spec's rounded 14142 km label), true range
  sqrt(6)*10^7 = 24494897.42 m, pseudorange 24494897.42 + 100 m.

Run solve_iterated on the four records: the iterated least squares
fix converges to x = -1.44e-13, y = -1.28e-13, z = -1.28e-13 m (the
origin within 0.5 m on every axis), clock bias 100.0 m within 0.5 m,
residual RMS 0.0 m (the exact +100 m bias model solves exactly),
iterations 2 and converged True.

Add a fifth satellite at (-10000 km, -10000 km, 0) with true range
sqrt(2)*10^7 m plus the same 100 m bias, then perturb the z-axis
pseudorange by +3 m: the fix shifts by about 2.53 m in 3D and the
residual RMS becomes 0.596 m, showing how redundant measurements turn
a single measurement error into observable post-fit residuals.

## Verification

- Confirm solve_iterated on the worked constellation returns the
  origin within 0.5 m per axis and a clock bias within 0.5 m of
  100.0 m, with residual RMS below 0.5 m, iterations at most 8 and
  converged True.
- Confirm the +3 m perturbation of the redundant set shifts the fix by
  about 2.53 m and gives residual_rms above zero.
- Confirm position_error_estimate satisfies pos_1sigma = uere_equiv *
  pdop and gives gdop 1.7216197603949122, pdop 1.6202812472328787 on
  the clean redundant constellation.
- Confirm every invalid input raises ValueError: fewer than four
  satellites, missing satellite keys, non-finite pseudoranges,
  iters below 1, a satellite coincident with the receiver and a
  singular normal matrix.
- Run the contract test offline: python3
  scripts/test_gnss_pseudorange_positioning.py (41 tests,
  deterministic).

## Pitfalls

- Solving with fewer than four satellites: four unknowns (x, y, z, clock
  bias) need at least four measurements and fewer raise ValueError; a
  4-satellite exact set solves with zero residual RMS while redundancy is
  what exposes measurement errors as post-fit residuals.
- Reading residual RMS as position error on a minimal set: with exactly four
  satellites the residual RMS is 0.0 even with a common bias (the worked
  +100 m bias solves exactly); position error needs the redundant
  constellation or the position_error_estimate read.
- Ignoring the converged flag and iteration count: solve_iterated stops when
  the correction norm falls below tol and reports converged and iterations;
  gate navigation processing on those flags before quoting the fix.
- Forgetting the spherical approximation: to_geodetic_approx uses a
  spherical Earth (R_EARTH = 6378137.0 m) with WGS-84 out of scope, so
  geodetic outputs carry that approximation.
- A satellite coincident with the receiver (zero range), singular normal
  matrix, missing keys, non-finite pseudoranges and iters below 1 raise
  ValueError; pos_1sigma = uere_equiv*pdop ties into the
  dilution-of-precision leaf.

## Related leaves

- gnc-autonomy/navigation/dilution-of-precision: the geometry quality
  read (DOP values and elevation mask) for subset selection around
  this snapshot fix.
- gnc-autonomy/navigation/kalman-filter-design: time-domain fusion of
  successive snapshot fixes with a dynamics model and process noise.
- gnc-autonomy/navigation/navigation-frames: ECEF and frame rotation
  conventions for the satellite and receiver coordinates.
- gnc-autonomy/space/orbit-determination: satellite orbit state used
  to form the satellite positions in ECEF.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gnss_pseudorange_positioning.py

The test covers the geometric range and predicted pseudorange model,
measured minus predicted residuals, the geometry matrix rows (unit
lines of sight, clock column of ones, coincident satellite rejection),
the 4x4 Gaussian elimination solver (identity, diagonal, coupled and
singular systems), the worked example convergence to the origin with
the 100 m bias recovered, the exact module output anchors, the
perturbation shift of the redundant constellation, the post-fit
position error estimate identity, the spherical geodetic conversion
at the origin, equator and pole, and ValueError rejection of every
non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the airborne
  system development context (arp4754a, reference-only per
  standards-map.yaml); the GNSS pseudorange positioning relations above
  are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
