# Wave-31 leaf spec: bi-elliptic-transfer (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/bi-elliptic-transfer/
- Pack: orbit-mechanics (15 siblings). Direct sibling: hohmann-transfer owns
  the two-impulse Hohmann transfer between coplanar circular orbits. The
  bi-elliptic three-impulse transfer (the standard alternative that beats
  Hohmann at large radius ratios) is absent: no leaf computes the three burns
  or the crossover comparison. This leaf is the comparison sibling.
- Standards ids: ecss (reference-only, same convention as the space leaves).
  Ledger Standard: ecss.
- Family: space-systems

## Claim

Analyze the bi-elliptic three-impulse transfer between two coplanar circular
orbits and compare it against the Hohmann two-impulse transfer: compute the
three burn delta-v values (perigee raise to the intermediate apogee radius,
the intermediate-apogee burn that raises perigee to the target radius, and the
target circularization), the total bi-elliptic delta-v, the Hohmann delta-v
for the same pair, the delta-v saving of the better strategy, and the chosen
transfer verdict. Produces the three impulse magnitudes, the two totals, the
saving, and the strategy verdict that gate an orbit-transfer design choice at
large radius ratios.

Does NOT do: the Hohmann two-impulse transfer itself as the primary result
(hohmann-transfer owns the two-burn calculation and its timing); plane-change
or combined maneuvers (plane-change-maneuver owns inclination changes);
low-thrust spirals (low-thrust-spiral owns the Edelbaum continuous-thrust
case); Lambert or three-body transfers; phasing (rendezvous-phasing). The
leaf re-derives the Hohmann delta-v ONLY as the comparison baseline inside its
own functions (self-contained stdlib leaf, standard practice in the library);
the description and outputs stay framed on the bi-elliptic three-burn case and
the crossover verdict.

## Model (implement exactly)

Module constants:
- MU_EARTH = 3.986004418e14 (m3/s2, default gravitational parameter).

Functions (pure stdlib):
- circular_speed(mu, radius) -> float: v = sqrt(mu / radius). ValueError if
  radius <= 0 or mu <= 0.
- hohmann_delta_v(mu, r1, r2) -> dict: {dv1, dv2, total} with
  dv1 = sqrt(mu*(2/r1 - 2/(r1+r2))) - sqrt(mu/r1) and
  dv2 = sqrt(mu/r2) - sqrt(mu*(2/r2 - 2/(r1+r2))). ValueErrors: r1 <= 0,
  r2 <= 0, r1 == r2 (a transfer between identical orbits is not a transfer).
- bi_elliptic_delta_v(mu, r1, r_b, r2) -> dict: {dv1, dv2, dv3, total} where
  dv1 = sqrt(mu*(2/r1 - 2/(r1+r_b))) - sqrt(mu/r1) (raise apogee to r_b),
  dv2 = sqrt(mu*(2/r_b - 2/(r_b+r2))) - sqrt(mu*(2/r_b - 2/(r1+r_b)))
  (at r_b raise the perigee from r1 to r2: the speed on the second transfer
  ellipse at r_b minus the speed on the first transfer ellipse at r_b),
  dv3 = sqrt(mu/r2) - sqrt(mu*(2/r2 - 2/(r_b+r2))) (circularize at r2).
  ValueErrors: r1 <= 0, r_b <= r2 (the intermediate apogee must exceed the
  target radius), r2 <= r1 (outward transfer only), r1 == r2.
- transfer_comparison(mu, r1, r2, r_b) -> dict: {hohmann_dv1, hohmann_dv2,
  hohmann_total, bi_dv1, bi_dv2, bi_dv3, bi_total, saving, verdict} where
  saving = hohmann_total - bi_total (positive when the bi-elliptic transfer
  is cheaper) and verdict = "bi-elliptic" when saving > 0 else "hohmann"
  (ties go to hohmann, the simpler two-burn strategy).
- transfer_time_bi_elliptic(mu, r1, r_b, r2) -> float: the sum of the two
  half-period coast times: pi * sqrt((r1+r_b)^3 / (8*mu)) + pi * sqrt((r_b+r2)^3
  / (8*mu)). ValueError as in bi_elliptic_delta_v.

## Worked example

Earth mu = 3.986004418e14 m3/s2. Start radius r1 = 6578 km (300 km circular
orbit), target radius r2 = 30 * r1 = 197 340 km, intermediate apogee
r_b = 2 * r2 = 394 680 km.

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- Hohmann total in 3900-4300 m/s (about 4106; dv1 about 3045, dv2 about 1060).
- Bi-elliptic total in 3850-4150 m/s (about 3992; dv1 about 3134, dv2 about
  639, dv3 about 220).
- saving in 50-180 m/s (about 113): the bi-elliptic transfer is cheaper at
  this radius ratio with r_b = 2*r2.
- verdict "bi-elliptic".
- transfer time is long: in 10-40 days (compute in seconds and convert for
  the SKILL body).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: r1 <= 0, r2 <= 0, r1 == r2, r_b <= r2, mu <= 0.
- Sanity: at a small radius ratio (r2 = 2*r1) with a moderate r_b the Hohmann
  total is below the bi-elliptic total (verdict "hohmann").
- Degenerate check: with r_b -> r2 the bi-elliptic total approaches the
  Hohmann total plus a small excess (assert bi_total > hohmann_total - 1.0
  when r_b is very close to r2, e.g. r_b = r2 * 1.01 at r2 = 2*r1).
- Round-trip: each dv equals the difference of the speeds it is defined from
  (vis-viva consistency); total equals dv1+dv2+dv3 within 1e-6.
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dicts contain exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-bi-elliptic-transfer.yaml)

Query 1 (copy verbatim):
  "compute the bi-elliptic three impulse transfer delta-v between two coplanar circular orbits with an intermediate apogee radius and compare it with the hohmann transfer total"
  intent: "space-systems; bi-elliptic three-burn orbit transfer delta-v"
  expected_skill: "space-systems/orbit-mechanics/bi-elliptic-transfer"
Query 2 (copy verbatim):
  "determine whether a bi-elliptic transfer saves delta-v over the hohmann transfer for a large radius ratio orbit raise and return the strategy verdict"
  intent: "space-systems; bi-elliptic versus hohmann crossover verdict"
  expected_skill: "space-systems/orbit-mechanics/bi-elliptic-transfer"
Task ids: w31-bi-elliptic-transfer-1 and -2.

Forbidden tokens that belong to siblings: do NOT use plane change, inclination,
low-thrust, spiral, Edelbaum, Lambert, rendezvous, phasing, phase angle, or
claim the Hohmann leaf's timing/position results as the primary output. The
word hohmann appears only as the comparison baseline.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze the bi-elliptic three-impulse
transfer between two coplanar circular orbits and compare it against the
Hohmann transfer:" and include the outputs listed in the Claim. First tag:
bi-elliptic-transfer. Additional tags only: three-impulse-transfer,
intermediate-apogee, delta-v-saving, orbit-transfer-comparison,
bi-elliptic-crossover. NEVER single generic words (transfer, orbit, delta-v,
maneuver, impulse). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.
