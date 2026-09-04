# Wave-34 leaf spec: kepler-orbit-propagation (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/kepler-orbit-propagation/
- Pack: orbit-mechanics. Closest siblings: keplerian-elements (strictly
  rv2coe EXTRACTION, one direction: position/velocity state to classical
  elements; its body says conversion only; it ends where propagation
  begins), gnc-autonomy/space/orbit-dynamics (vis-viva, Hohmann dv/time,
  J2 nodal-regression flag only; its "propagation" tag is transfer-time
  context, no Kepler solver), lambert-transfer (two-position time of
  flight, not element propagation), bi-elliptic-transfer / hohmann-
  transfer (impulsive maneuver delta-v). Repo-wide grep (12 families):
  zero hits for mean-anomaly / eccentric-anomaly / Kepler equation.
- Standards id: ecss (reference-only; orbit-mechanics convention,
  matches keplerian-elements). Ledger Standard: ecss.
- Family: space-systems

## Claim

Propagate a Keplerian orbit in time: mean motion from semimajor axis,
the Kepler equation M = E - e sin E solved by Newton iteration, the
eccentric-to-true anomaly conversion, the radius at a given true
anomaly, the full 3D inertial position and velocity vectors after an
elapsed time from a classical-element state (a, e, i, RAAN, argp, nu0),
and the time since periapsis for a given true anomaly. Produces the
propagated true/eccentric/mean anomaly, radius, r-vector and v-vector
and the time since periapsis, enabling ground-track and event timing on
a two-body orbit.

Does NOT do: state vector to element EXTRACTION (keplerian-elements
owns the inverse map); J2 perturbation drift (orbital-perturbations);
Hohmann/bi-elliptic/plane-change transfer delta-v (their own leaves);
Lambert two-position targeting (lambert-transfer); SGP4/TLE (declined
as not a compact deterministic contract).

## Model (implement exactly)

Module constants:
- MU_EARTH_DEFAULT = 398600.4418 (km3/s2), matching keplerian-elements.
- KEPLER_NEWTON_TOL = 1e-12, KEPLER_MAX_ITER = 100.

Conventions: length in km, time in s, angles in rad. The classical
element state is (a km, e, i rad, RAAN rad, argp rad, nu0 rad).
Propagation: M0 = E0 - e sin E0 via kepler_solve on nu0; M = M0 +
n dt; E = kepler_solve(M); nu = true_anomaly_from_eccentric(E, e);
r = a(1 - e cos E). The inertial r,v use the standard perifocal
rotation through argp, i, RAAN (active rotation, same convention as
keplerian-elements).

Functions (pure stdlib):
- mean_motion(semimajor_axis_km, mu = MU_EARTH_DEFAULT) ->
  n = sqrt(mu / a^3) rad/s. ValueError on a <= 0 or mu <= 0.
- orbital_period(semimajor_axis_km, mu = MU_EARTH_DEFAULT) ->
  T = 2 pi / n s.
- kepler_solve(mean_anomaly_rad, eccentricity) -> E (rad) by Newton:
  E = M + e sin M initial guess; iterate E -= (E - e sin E - M)/(1 -
  e cos E) to KEPLER_NEWTON_TOL. ValueError on e < 0 or e >= 1
  (parabolic/hyperbolic excluded; e in [0, 1)).
- true_anomaly_from_eccentric(E, e) -> nu = 2 atan2(sqrt(1+e)
  sin(E/2), sqrt(1-e) cos(E/2)) (rad, branch-safe, in (-pi, pi]).
- eccentric_anomaly_from_true(nu, e) -> E = 2 atan2(sqrt(1-e)
  sin(nu/2), sqrt(1+e) cos(nu/2)) (inverse, used by propagation from a
  nu0 state). ValueError on e in [1, inf).
- radius_at_anomaly(semimajor_axis_km, eccentricity,
  true_anomaly_rad) -> r = a(1 - e^2)/(1 + e cos nu). ValueError on
  e >= 1.
- time_since_periapsis(true_anomaly_rad, semimajor_axis_km,
  eccentricity, mu = MU_EARTH_DEFAULT) -> t = (E - e sin E)/n with E
  from the inverse map. ValueErrors as above.
- propagate_kepler(semimajor_axis_km, eccentricity, inclination_rad,
  raan_rad, argp_rad, true_anomaly0_rad, dt_s, mu =
  MU_EARTH_DEFAULT) -> dict {mean_anomaly_rad, eccentric_anomaly_rad,
  true_anomaly_rad, radius_km, position_km (3-vector),
  velocity_kms (3-vector), period_s}. Implements: E0 from nu0, M0,
  M = M0 + n dt, E, nu, r, and the r/v reconstruction. ValueError on
  e in [0,1) violations, a <= 0, dt < 0.
- perifocal_to_inertial(r_pf, v_pf, raan_rad, inclination_rad,
  argp_rad) -> (r, v) inertial via the standard 3-rotation
  (R3(-RAAN) R1(-i) R3(-argp) on the perifocal frame, ACTIVE
  convention matching keplerian-elements - verify by round-trip).
  Used internally by propagate_kepler; exposed for testing.

Kepler identities to test: (1) one-period propagation returns the
initial true anomaly and radius exactly (M advances by 2 pi); (2) the
radius from r = a(1 - e cos E) equals a(1-e^2)/(1 + e cos nu) to float
tolerance; (3) inverse time-of-flight: time_since_periapsis(nu) after
dt equals dt for the propagated state.

## Worked example

Reference orbit: a = 12000 km, e = 0.35, i = 30 deg, RAAN = 45 deg,
argp = 20 deg, starting at periapsis (nu0 = 0), dt = 3600 s, Earth mu.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- mean_motion = sqrt(398600.4418 / 12000^3) = 4.80283e-4 rad/s.
- orbital_period = 2 pi / n = 13082.262 s (3.634 h).
- After 3600 s from periapsis: M = n dt = 1.729018 rad; E =
  kepler_solve = 2.041030 rad; nu = 2.336674 rad (133.8815 deg);
  r = a(1 - e cos E) = 13902.9969 km; v magnitude = 4.911570 km/s
  (check via vis-viva at that radius).
- One-period return: r = a(1-e) = 7800.000000 km with nu -> 0 mod 2 pi
  (E -> 2 pi, M -> 2 pi).
- time_since_periapsis of the propagated nu recovers 3600.000000 s
  exactly (inverse TOF).
- rv round-trip: converting the propagated r,v back with the
  keplerian-elements-style extraction recovers a to 1e-9 relative
  (3.64e-12 achieved) and e to 1e-12 (2.22e-16 achieved).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: a <= 0; mu <= 0; e < 0 or e >= 1; dt < 0; eccentricity
  out of [0,1).
- Kepler solver: for e = 0, E == M exactly; for the worked e = 0.35
  and M = 1.729018 rad, E = 2.041030 rad to 1e-9; residual
  |E - e sin E - M| < 1e-12.
- True-anomaly map: for E = 2.041030, e = 0.35, nu = 2.336674 to 1e-9;
  nu at periapsis (E = 0) is 0; nu at apoapsis (E = pi) is pi.
- Radius identity: a(1 - e cos E) == a(1-e^2)/(1 + e cos nu) to 1e-9
  for the worked state.
- Propagation round trip: after one period, nu == nu0 (mod 2 pi) and
  the radius returns to a(1-e) to 1e-9; after dt = 0 the state is
  unchanged.
- TOF inverse: time_since_periapsis(propagated nu) == dt to 1e-6.
- Perifocal-to-inertial consistency: the reconstructed r,v at
  periapsis lie in the orbital plane (the angular momentum vector
  matches h = sqrt(mu a (1-e^2)) direction to 1e-9); the r-vector
  magnitude equals a(1-e) at periapsis.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-kepler-orbit-propagation.yaml)

Query 1 (copy verbatim):
  "propagate a keplerian orbit in time by solving the Kepler equation for the eccentric anomaly from the mean anomaly and return the true anomaly and radius"
  intent: "space-systems; Kepler equation time propagation, eccentric and mean anomaly, radius"
  expected_skill: "space-systems/orbit-mechanics/kepler-orbit-propagation"
Query 2 (copy verbatim):
  "compute the inertial position and velocity vectors of a spacecraft after an elapsed time from the classical orbital elements and the time since periapsis"
  intent: "space-systems; inertial r and v from classical elements after elapsed time"
  expected_skill: "space-systems/orbit-mechanics/kepler-orbit-propagation"
Task ids: w34-kepler-orbit-propagation-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must propagate a spacecraft orbit
in time from its classical orbital elements:" and include the outputs
in the Claim. First tag: kepler-orbit-propagation. Additional tags
ONLY: keplerian-propagation, kepler-equation, mean-anomaly,
eccentric-anomaly, time-since-periapsis. NEVER single generic words
(orbit, propagation, anomaly, kepler, spacecraft, time). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): state vector to elements,
rv2coe, eccentricity vector, node vector (keplerian-elements owns the
extraction direction); vis-viva, Hohmann, delta-v, J2 drift
(gnc-autonomy/space/orbit-dynamics + orbital-perturbations); Lambert,
transfer time between two positions (lambert-transfer); SGP4, TLE.
The words "Kepler equation", "mean anomaly", "eccentric anomaly",
"propagation in time", "time since periapsis" are this leaf's own.

Tags: [kepler-orbit-propagation, keplerian-propagation, kepler-equation,
mean-anomaly, eccentric-anomaly, time-since-periapsis]

Sibling-citation lines for Related leaves:
space-systems/orbit-mechanics/keplerian-elements (the inverse map: rv
to elements; this leaf is elements to rv in time),
gnc-autonomy/space/orbit-dynamics (two-body/Hohmann/J2 context),
space-systems/orbit-mechanics/lambert-transfer (two-position targeting
boundary).

Ledger Standard: ecss.
