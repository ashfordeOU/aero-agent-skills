# Wave-36 leaf spec: walker-delta-constellation (space-systems, orbit-mechanics pack)

- Path: skills/space-systems/orbit-mechanics/walker-delta-constellation/
- Pack: orbit-mechanics. Closest siblings: satellite-coverage (single-
  sat access/revisit geometry), ground-track-repeat (single-sat repeat
  cycle), sun-synchronous-inclination, conjunction-assessment, launch-
  window-analysis (mission-design), mission-delta-v-budget. Whole-tree
  grep: "walker|constellation" hits only incidental text in ground-track-
  repeat, satellite-coverage, mission-delta-v-budget and gnss tests; no
  leaf routes constellation phasing or design. ZERO owners for the
  constellation geometry class.
- Standards id: ecss (pack convention; reference-only). Ledger
  Standard: ecss.
- Family: space-systems

## Claim

Parameterize a Walker-Delta constellation at the conceptual level:
check the t/p/f parameter validity (total satellites t divisible by the
plane count p, phasing parameter f in [0, p-1]), enumerate the planes
and the slots per plane, compute the right ascension of ascending node
spacing (360/p), the in-plane mean anomaly spacing (360/s with s = t/p
satellites per plane), and the inter-plane phasing offset (f*360/t),
and produce the unique (RAAN, mean anomaly) slot list for the
constellation. Produces the satellites per plane, the RAAN spacing, the
mean anomaly spacing, the inter-plane phase, and the enumerated slot
grid.

Does NOT do: single-satellite access geometry, revisit time and coverage
fraction (satellite-coverage); ground-track repeat cycle (ground-track-
repeat); coverage-fraction or capacity analysis of the constellation
(empirical; explicitly out of scope).

## Model (implement exactly)

Module constants: none (pure geometry).

Conventions: t total satellites; p planes; f phasing parameter; s = t/p
satellites per plane; RAAN of plane j (0-based) = j*360/p; mean anomaly
of slot k in plane j = (k*360/s + j*f*360/t) mod 360 (each plane's
first slot carries the inter-plane phase offset). Slot ids are
(plane_index, slot_index).

Functions (pure stdlib):
- validate_walker(t, p, f) -> None. ValueErrors: t <= 0 or p <= 0;
  t % p != 0 (must be divisible); f < 0 or f >= p.
- walker_parameters(t, p, f) -> dict {satellites_per_plane,
  raan_spacing_deg, mean_anomaly_spacing_deg, inter_plane_phase_deg}.
  ValueErrors as validate_walker.
- walker_slots(t, p, f) -> list of dict {plane, slot, raan_deg,
  mean_anomaly_deg} with s = t/p entries per plane and t total entries;
  RAAN = j*360/p; MA = (k*360/s + j*f*360/t) mod 360. ValueErrors as
  validate_walker.
- unique_slot_count(t, p, f) -> int == t (verify the slot grid has t
  distinct (raan, ma) pairs). ValueErrors as validate_walker.

Identity to test: satellites_per_plane * p == t; the slot list length
== t; raan_spacing * p == 360; mean_anomaly_spacing * s == 360;
inter-plane phase == f*360/t.

## Worked example

Reference constellation: Walker-Delta 24/3/1 (24 satellites, 3 planes,
phasing parameter 1; the Galileo-class geometry).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- satellites per plane = 24/3 = 8.
- RAAN spacing = 360/3 = 120.0 deg; MA spacing = 360/8 = 45.0 deg.
- inter-plane phase = 1*360/24 = 15.0 deg.
- slot count = 24 unique (RAAN, MA) pairs; plane 0 slot 0 MA = 0.0,
  plane 1 slot 0 MA = 15.0 deg, plane 2 slot 0 MA = 30.0 deg.
- f = 2 -> phase 30.0 deg; Galileo analog 27/3/1 -> phase 360/27 =
  13.333 deg.
- ValueError: (24, 5, 1) -> t not divisible by p; (24, 3, 3) -> f not
  in [0, p-1].

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: t % p != 0; f out of range; non-positive t or p.
- Parameters: 24/3/1 -> {8, 120.0, 45.0, 15.0} within 1e-9.
- Slots: length 24; distinct pairs == 24; plane1 slot0 MA == 15.0;
  plane2 slot0 MA == 30.0.
- f=2 -> phase 30.0; 27/3/1 -> 13.333 within 1e-3.
- Identities: per-plane count * p == t; raan*p == 360; ma*s == 360.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-walker-delta-constellation.yaml)

Query 1 (copy verbatim):
  "compute the raan spacing and in plane phasing of a walker delta 24 by 3 by 1 constellation"
  intent: "space-systems; Walker-Delta t/p/f plane and slot parameterization"
  expected_skill: "space-systems/orbit-mechanics/walker-delta-constellation"
Query 2 (copy verbatim):
  "enumerate the unique raan and mean anomaly slots for a walker delta constellation with 8 satellites per plane"
  intent: "space-systems; Walker-Delta constellation slot enumeration"
  expected_skill: "space-systems/orbit-mechanics/walker-delta-constellation"
Task ids: w36-walker-delta-constellation-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must parameterize a Walker-Delta
constellation:" and include the outputs in the Claim. First tag:
walker-delta-constellation. Additional tags ONLY: walker-delta-tpf,
constellation-plane-spacing, inter-plane-phasing, constellation-slot-
enumeration, raan-mean-anomaly-grid. NEVER single generic words
(walker, delta, constellation, plane, phasing, slot, raan, satellite,
orbit). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): access time, revisit, coverage
fraction, swath (satellite-coverage); repeat cycle, ground track
(ground-track-repeat); collision probability, conjunction
(conjunction-assessment); launch window (launch-window-analysis).
