# Wave-24R leaf spec: orbit-determination (gnc-autonomy)

- Path: skills/gnc-autonomy/space/orbit-determination/
- Pack: space (existing: attitude-dynamics, orbit-dynamics,
  rendezvous-phasing)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: gnc-autonomy

## Claim

Preliminary orbit determination from observations: Gibbs method (three
inertial position vectors -> velocity at the middle vector -> classical
orbital elements) and Herrick-Gibbs improvement for closely spaced
vectors, with a sanity check against Keplerian consistency. Produces the
velocity vector at the central observation, the classical orbital
elements (a, e, i, RAAN, argp, nu), and an orbit-fit verdict.

Does NOT do: orbit PROPAGATION or dynamics (orbit-dynamics,
space-systems orbit-mechanics leaves), Kalman/least-squares sequential
estimation of an orbit from many noisy measurements over time
(estimation-filtering leaves own stochastic filters), Lambert targeting.
This leaf is the deterministic three-vector initial orbit determination
classic.

## Method (implement exactly)

Gibbs (Vallado/classical, geocentric, mu = 3.986004418e14 m^3/s^2):
Given three inertial position vectors r1, r2, r3 (m, ECI J2000 assumed;
document assumption):
- C12 = r1 x r2, C23 = r2 x r3, C31 = r3 x r1 (cross products).
- N = r1*|C23|? classical form: N = r1 (r2 x r3)?? Use the standard
  Vallado Gibbs: N = r1_norm? Define:
    N = |r1| * (r2 x r3) + |r2| * (r3 x r1) + |r3| * (r1 x r2)   (vector)
    D = (r1 x r2) + (r2 x r3) + (r3 x r1)                        (vector)
    S = r1*(|r2|-|r3|) + r2*(|r3|-|r1|) + r3*(|r1|-|r2|)         (vector)
  Check coplanarity: if |N| ~ 0 or |D| ~ 0 the vectors are nearly
  collinear -> raise ValueError("near-collinear observation geometry").
- v2 = sqrt(mu / (|N|*|D|)) * ( (D x r2)/|r2| + S )   (velocity at r2)
- Then orbital elements from r2, v2 via the classical
  rv_to_elements(r, v) routine (implement the standard algorithm:
  h = r x v; n = K x h (K = [0,0,1]); e_vec = ((v^2-mu/|r|) r -
  (r.v) v)/mu; a from energy; i = acos(h_z/|h|); RAAN = acos(n_x/|n|)
  with quadrant checks; argp from n and e_vec; nu from e_vec and r).
Herrick-Gibbs (for closely spaced vectors, dt small): use the
Herrick-Gibbs three-vector finite-difference velocity:
- v2 = -dt23*(1/(dt12*dt13) + mu/(12*|r1|^3)) * r1
      + (dt13 - dt12)*(1/(dt12*dt23) + mu/(12*|r2|^3)) * r2
      + dt12*(1/(dt13*dt23) + mu/(12*|r3|^3)) * r3
  where dt12 = t2 - t1, dt23 = t3 - t2, dt13 = t3 - t1 (s). Choose
  Herrick-Gibbs automatically when the angular separation between the
  position vectors is small (e.g. the triangle area |C12|/2 is below a
  threshold input), else Gibbs; expose both functions and a chooser.

Functions:
- cross3(u, v), norm3(v)
- gibbs_velocity(r1, r2, r3) -> v2 (raises on near-collinear)
- herrick_gibbs_velocity(r1, r2, r3, t1, t2, t3) -> v2
- rv_to_elements(r, v, mu) -> dict (a, e, i_deg, raan_deg, argp_deg,
  nu_deg, period_s)
- choose_method(r1, r2, r3, t1, t2, t3, area_threshold) -> 'gibbs'|'hg'
- orbit_determination(r1, r2, r3, t1, t2, t3, ...) -> summary dict with
  method, v2, elements, energy_check (vis-viva consistency), verdict
ValueError on: zero/near-collinear geometry, repeated time tags,
non-positive radii, non-finite inputs.

## Worked example

Use a known low-Earth orbit (e.g. a = 7000 km, e = 0.01, i = 98 deg)
as a test case: pick three true-anomaly separated positions 60 s apart
propagated by the two-body solution (your module can synthesize the r
vectors with a small helper: r = R * [cos(nu), sin(nu), 0] rotated by
the elements, or hard-code three position vectors you generate with a
script and paste into the test). Anchors:
- Gibbs recovers v2 such that rv_to_elements returns a, e, i within 1%
  of the generating elements (assert with your real numbers).
- Herrick-Gibbs on the same 60 s-spaced vectors agrees with Gibbs to
  within ~1e-2 of |v2| for a LEO example (assert the band your run
  produces; report the value).
- Circular equatorial special case: r vectors in the equatorial plane
  give i = 0 and RAAN undefined/0 (documented; assert i ~ 0).
- Vis-viva energy check: |v2|^2/2 - mu/|r2| equals -mu/(2a) within
  1e-6 relative.
- ValueError rejections (collinear r vectors, same-time tags).

## Corpus tasks (2 tasks, ids w24r-orbit-determination-1/2)

Distinctive tokens: orbit-determination, gibbs-method,
herrick-gibbs, three position vectors, initial orbit determination,
rv-to-elements. Avoid: "propagate", "kalman", "lambert", "hohmann",
"perturbation", "rendezvous phasing" (siblings).

1. "determine the initial orbit of the debris object from three
   inertial position vectors: run the Gibbs method to recover the
   velocity at the central observation and convert the state to
   classical orbital elements with the vis-viva consistency check"
2. "the tracking pass gave three closely spaced position vectors with
   time tags, decide between the Gibbs and Herrick-Gibbs initial orbit
   determination methods, compute the middle-vector velocity, and report
   the orbital elements with the method verdict"

## SKILL body notes

Pair with orbit-dynamics (propagation after the state is known),
estimation-filtering leaves (sequential refinement), space-systems
orbit-mechanics siblings. Compliance: ECSS space engineering standards
referenced by name only.
