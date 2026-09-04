---
name: orbit-determination
description: "Use when you must determine an initial orbit from three inertial position vectors: run the Gibbs method to recover the velocity at the central observation, apply the Herrick-Gibbs finite-difference method when the vectors are closely spaced, and convert the state to classical orbital elements with the vis-viva energy consistency check. Produces the central velocity, the classical elements (a, e, i, RAAN, argp, nu), the chosen method verdict and the orbit-fit verdict. Trigger: orbit-determination, gibbs-method, herrick-gibbs, three position vectors, initial orbit determination, rv-to-elements, orbital elements, angular separation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: gnc-autonomy
pack: space
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: space
  tags: [orbit-determination, gibbs-method, herrick-gibbs, three-position-vectors, initial-orbit-determination, rv-to-elements, orbital-elements, vis-viva-consistency]
  version: 0.1.0
  author: Aero Agent Skills
---

# Initial Orbit Determination (gnc-autonomy/space/orbit-determination)

Use when the task is the deterministic three-vector initial orbit
determination classic: three inertial position observations of a
spacecraft or debris object with time tags, and the need for the
velocity at the central observation plus the classical orbital
elements, before any propagation or refinement work starts. This leaf
implements the Gibbs method (three position vectors to the middle
velocity) and the Herrick-Gibbs finite-difference method for closely
spaced vectors, with an automatic method chooser based on the triangle
area spanned by the observations, in pure Python, stdlib only. States
are geocentric ECI (J2000 frame assumed) with Earth gravitational
parameter mu = 3.986004418e14 m^3/s^2. It pairs with
gnc-autonomy/space/orbit-dynamics for propagation once the state is
known and with the gnc-autonomy estimation-filtering leaves for
sequential refinement of the state from many later measurements. This
leaf does NOT propagate, does NOT run stochastic estimators, and does
NOT solve Lambert targeting: it is the deterministic geometric
preliminary orbit determination only.

## Domain quick reference

- Cross products: C12 = r1 x r2, C23 = r2 x r3, C31 = r3 x r1.
- Gibbs method (Vallado classical form), with magnitudes n1 = |r1|,
  n2 = |r2|, n3 = |r3|:
  - N = n1*C23 + n2*C31 + n3*C12 (vector sum)
  - D = C12 + C23 + C31 (vector sum)
  - S = r1*(n2 - n3) + r2*(n3 - n1) + r3*(n1 - n2) (vector sum)
  - v2 = sqrt(mu / (|N|*|D|)) * ( (D x r2)/n2 + S )
  - If |N| or |D| vanishes the three vectors are collinear and the
    method raises ValueError("near-collinear observation geometry").
- Herrick-Gibbs (closely spaced vectors), dt12 = t2 - t1,
  dt23 = t3 - t2, dt13 = t3 - t1:
  - v2 = -dt23*(1/(dt12*dt13) + mu/(12*n1^3))*r1
      + (dt23 - dt12)*(1/(dt12*dt23) + mu/(12*n2^3))*r2
      + dt12*(1/(dt13*dt23) + mu/(12*n3^3))*r3
  - The middle coefficient (dt23 - dt12) is the standard Vallado and
    Curtis form; it vanishes for equally spaced tags, reducing the
    formula to the central-difference limit. Time tags must be
    strictly increasing (repeated tags raise ValueError).
- Method chooser: triangle area = 0.5*|(r2 - r1) x (r3 - r1)|. Below
  the area threshold (default 1.0e12 m^2) the vectors are treated as
  closely spaced and 'hg' is chosen, else 'gibbs'.
- Classical elements from (r2, v2): h = r2 x v2, node vector
  n = K x h with K = [0,0,1], eccentricity vector
  e_vec = ((v^2 - mu/|r|)*r - (r.v)*v)/mu, semi-major axis from
  energy a = -mu/(2*E). Inclination, RAAN, argument of perigee and
  true anomaly follow with the standard quadrant checks; equatorial
  orbits take RAAN = 0 by convention and circular orbits take
  argp = 0 with nu measured from the node.
- Vis-viva consistency: 0.5*|v2|^2 - mu/|r2| must equal -mu/(2a) to
  within 1e-6 relative for the fit to be rated 'consistent'.
- ECSS space engineering standards frame the flight-dynamics context
  by name; the relations above are standard astrodynamics methodology,
  summary-only.

## Workflow

1. Collect the three inertial position vectors r1, r2, r3 (m, ECI
   frame) and their time tags t1 < t2 < t3 (s, same clock).
2. Validate geometry: radii positive, components finite, tags strictly
   increasing; reject otherwise with ValueError.
3. Choose the method with choose_method(r1, r2, r3, t1, t2, t3,
   area_threshold): 'hg' for closely spaced vectors, 'gibbs' for a
   wide arc.
4. Recover the middle velocity: gibbs_velocity(r1, r2, r3) or
   herrick_gibbs_velocity(r1, r2, r3, t1, t2, t3) returns v2 at r2.
5. Convert the state with rv_to_elements(r2, v2, mu) to get a, e,
   i_deg, raan_deg, argp_deg, nu_deg and period_s.
6. Run the full summary orbit_determination(r1, r2, r3, t1, t2, t3)
   which reports method, v2, elements, the vis-viva energy check and
   the 'consistent' or 'inconsistent' verdict.
7. Hand the recovered state to orbit-dynamics for propagation after
   the initial orbit is fixed, or to an estimation-filtering leaf for
   later refinement.

## Worked example

Generating orbit: low-Earth orbit with a = 7000 km, e = 0.01,
i = 98 deg, RAAN = 45 deg, argp = 30 deg, mu =
3.986004418e14 m^3/s^2. Mean motion n = sqrt(mu/a^3) = 1.07798e-3
rad/s. Three position vectors are synthesized on the two-body arc at
60 s intervals (mean anomaly step n*60 = 0.06468 rad), with the
central observation at mean anomaly 10 deg; the central radius is
|r2| = 6932.03 km.

- Gibbs: v2 = [-3191.361, -4273.000, 5442.079] m/s with
  |v2| = 7619.681 m/s. Recovered elements from rv_to_elements(r2, v2):
  a = 7000000 m, e = 0.01, i = 98.0 deg, RAAN = 45.0 deg,
  argp = 30.0 deg, nu = 13.98 deg, period = 5828.52 s, all within 1% of the generating values (the
  Gibbs recovery is exact on clean two-body geometry).
- Herrick-Gibbs on the same tags: |v2| = 7619.678 m/s, agreeing with
  the Gibbs result to 3.9e-7 relative on |v2| (band well inside the
  1e-2 acceptance).
- Triangle area check: 0.5*|(r2 - r1) x (r3 - r1)| = 6.82e9 m^2,
  below the default 1.0e12 m^2 threshold, so choose_method returns
  'hg' for these closely spaced vectors.
- Energy check: 0.5*|v2|^2 - mu/|r2| = -2.8471460e7 m^2/s^2 equals
  -mu/(2a) = -2.8471460e7 m^2/s^2, relative error below 1e-9, verdict
  'consistent'.
- Circular equatorial special case: three points on a 7000 km circle
  in the xy plane give i = 0 deg, RAAN = 0 deg (node undefined by
  convention), e = 0 and a = 7000 km exactly.

## Verification

- Confirm gibbs_velocity recovers elements within 1% of the
  generating a, e, i, RAAN, argp on the worked example, and |v2|
  within 2% of the circular speed sqrt(mu/|r2|).
- Confirm herrick_gibbs_velocity agrees with gibbs_velocity to within
  1e-2 on |v2| for the 60 s-spaced LEO vectors (observed band
  ~4e-7).
- Confirm the vis-viva identity holds to 1e-6 relative and the
  summary verdict is 'consistent'.
- Confirm circular equatorial geometry yields i ~ 0 and RAAN = 0.
- Confirm ValueError rejection: collinear position vectors, zero
  radius, non-finite components, repeated or decreasing time tags,
  non-finite times, negative area threshold, degenerate (radial)
  state in rv_to_elements.
- Run the contract test offline: python3
  scripts/test_orbit_determination.py (29 tests, deterministic,
  under 1 s).

## Pitfalls

- Feeding near-collinear vectors: Gibbs needs the triangle spanned by the
  three radii - if N or D vanishes the vectors are collinear and
  gibbs_velocity raises ValueError('near-collinear observation geometry').
- Trusting Gibbs on closely spaced vectors: choose_method selects
  herrick-gibbs below the triangle-area threshold (1.0e12 m2; the 60
  s-spaced LEO example spans 6.82e9 m2) because the classical Gibbs form
  degrades as the arc shrinks.
- Time tags must be strictly increasing: repeated or decreasing tags raise
  ValueError, and the Herrick-Gibbs middle coefficient (dt23 - dt12) is the
  standard Vallado/Curtis form that vanishes for equally spaced tags.
- Quoting elements without the vis-viva check: the summary rates the fit
  'consistent' only when 0.5*|v2|^2 - mu/|r2| equals -mu/(2a) to within 1e-6
  relative; an inconsistent verdict means the recovered state does not close
  an orbit.
- Reading the equatorial/circular conventions as geometry: equatorial orbits
  take RAAN = 0 by convention and circular orbits take argp = 0 with nu
  measured from the node (i = 0, RAAN = 0, e = 0, a = 7000 km in the worked
  special case).
- Scope guard: this leaf does not propagate (orbit-dynamics), refine with
  estimators (estimation-filtering) or solve Lambert targeting; zero radius,
  non-finite components and degenerate radial states raise ValueError.

## Related leaves

- gnc-autonomy/space/orbit-dynamics: two-body and J2 motion,
  vis-viva and Hohmann transfers; the propagation step after the
  state is determined here.
- gnc-autonomy/space/rendezvous-phasing: phasing maneuvers for a
  chaser once both orbits are known.
- gnc-autonomy/estimation-filtering: sequential refinement of the
  initial state from many noisy measurements over time (stochastic
  estimators, owned by that pack, not this leaf).
- gnc-autonomy/space/attitude-dynamics: the attitude side of the same
  spacecraft, distinct from the translational orbit work here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_orbit_determination.py

The test covers the worked-example contract (Gibbs recovery of a, e,
i, RAAN, argp within tolerance, Herrick-Gibbs agreement band, vis-viva
consistency to 1e-6 relative, circular equatorial i ~ 0 with RAAN 0,
Kepler period match), the cross and norm vector primitives, method
chooser behavior on close and wide arcs and threshold switching, the
full summary fields and verdict, and ValueError rejection of
collinear geometry, zero and non-finite radii, repeated and
decreasing time tags, non-finite times, negative thresholds and
degenerate states.

## Compliance

- Standards referenced, not reproduced: ECSS space engineering
  standards (ecss.nl/standards) frame the flight-dynamics and GNC
  context by name only; the Gibbs and Herrick-Gibbs relations above
  are standard astrodynamics methodology (Vallado, Curtis),
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
