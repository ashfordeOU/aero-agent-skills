---
name: walker-delta-constellation
description: "Use when you must parameterize a Walker-Delta constellation: validate the t/p/f triple (total satellites divisible by the plane count, phasing parameter within range), enumerate the planes and the slots per plane, compute the right ascension of ascending node spacing 360/p, the in-plane mean anomaly spacing 360/s with s = t/p satellites per plane, and the inter-plane phasing offset f*360/t, and produce the unique (RAAN, mean anomaly) slot list. Produces the satellites per plane, the RAAN spacing, the mean anomaly spacing, the inter-plane phase, and the enumerated slot grid. Trigger: walker delta constellation, t/p/f phasing, constellation plane spacing, inter-plane phasing, constellation slot enumeration, raan mean anomaly grid."
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
  tags: [walker-delta-constellation, walker-delta-tpf, constellation-plane-spacing, inter-plane-phasing, constellation-slot-enumeration, raan-mean-anomaly-grid]
  version: 0.1.0
  author: AeroSkills
---

# Walker-Delta Constellation (space-systems/orbit-mechanics/walker-delta-constellation)

Use when the task is parameterizing a Walker-Delta constellation at the
conceptual level: validating the t/p/f triple, computing the plane and
slot geometry, and enumerating the full slot grid of a Walker-Delta
constellation such as the Galileo-class 24/3/1. This leaf implements the
standard Walker-Delta geometry model (t total satellites over p equally
spaced planes with phasing parameter f) in pure Python, stdlib only. It
pairs with space-systems/orbit-mechanics/satellite-coverage for the
single-satellite access side of a constellation and with
space-systems/orbit-mechanics/ground-track-repeat for repeat-cycle
context. It does NOT do single-sat access geometry, repeat-cycle
analysis, or empirical capacity studies of the deployed constellation;
those belong to sibling leaves.

## Domain quick reference

- Walker-Delta notation: t total satellites, p orbital planes, f the
  phasing parameter; s = t / p satellites per plane (t must be divisible
  by p, f must be an integer in [0, p - 1]).
- RAAN spacing: planes are equally spaced in right ascension of the
  ascending node, 360 / p degrees apart; plane j (0-based) sits at
  RAAN = j * 360 / p.
- Mean anomaly spacing: within a plane the s slots are equally spaced,
  360 / s degrees apart.
- Inter-plane phase: the phasing offset between adjacent planes is
  f * 360 / t degrees; each plane's first slot carries that offset.
- Slot mean anomaly: slot k in plane j sits at (k * 360 / s + j * f *
  360 / t) mod 360 degrees, so the constellation forms the characteristic
  Walker-Delta diagonal pattern across planes.
- Slot ids are (plane_index, slot_index); the grid has exactly t slots
  and t distinct (RAAN, mean anomaly) pairs.
- Identity checks: s * p == t; raan spacing * p == 360; mean anomaly
  spacing * s == 360; inter-plane phase == f * 360 / t.
- Angles in degrees throughout; no module constants are needed, the
  model is pure geometry.
- ECSS frames the space systems context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the constellation triple (t, p, f) and confirm it is physical
   with validate_walker: positive t and p, t divisible by p, f in
   [0, p - 1].
2. Get the derived geometry with walker_parameters: satellites per
   plane, RAAN spacing 360/p, mean anomaly spacing 360/s, and the
   inter-plane phase f*360/t.
3. Enumerate the constellation with walker_slots: t slot dicts, s per
   plane, each with plane, slot, raan_deg = j * 360 / p and
   mean_anomaly_deg = (k * 360 / s + j * f * 360 / t) mod 360.
4. Confirm the grid is complete and unique with unique_slot_count,
   which must return t.
5. Run the deterministic contract test
   scripts/test_walker_delta_constellation.py to confirm the model.

## Worked example

Reference constellation: Walker-Delta 24/3/1 (24 satellites, 3 planes,
phasing parameter 1, the Galileo-class geometry). Real module outputs:

- walker_parameters(24, 3, 1): satellites_per_plane 8,
  raan_spacing_deg 120.0, mean_anomaly_spacing_deg 45.0,
  inter_plane_phase_deg 15.0.
- walker_slots(24, 3, 1): 24 slots, 8 per plane. Plane 0 slot 0 sits at
  RAAN 0.0, MA 0.0; plane 1 slot 0 at RAAN 120.0, MA 15.0; plane 2 slot
  0 at RAAN 240.0, MA 30.0. Slot 3 of plane 1, for example, sits at MA
  (3 * 45.0 + 15.0) = 150.0 deg, giving the diagonal phasing pattern.
- unique_slot_count(24, 3, 1): 24 distinct (RAAN, MA) pairs.
- Variation: f = 2 gives inter_plane_phase_deg 30.0; the Galileo analog
  27/3/1 gives inter_plane_phase_deg 13.333 and 9 satellites per plane
  with RAAN spacing 120.0 and MA spacing 40.0.
- Identity spot check: 8 * 3 = 24 satellites, 120.0 * 3 = 360 deg of
  RAAN sweep, 45.0 * 8 = 360 deg of in-plane MA sweep, and the phase
  1 * 360 / 24 = 15.0 deg.

## Verification

- Confirm validate_walker(24, 5, 1) raises ValueError (t not divisible
  by p) and validate_walker(24, 3, 3) raises ValueError (f outside
  [0, p - 1]); non-positive t or p also raise ValueError.
- Confirm walker_parameters(24, 3, 1) returns exactly
  {satellites_per_plane: 8, raan_spacing_deg: 120.0,
  mean_anomaly_spacing_deg: 45.0, inter_plane_phase_deg: 15.0} with the
  documented dict keys.
- Confirm walker_slots(24, 3, 1) has 24 entries, that plane 1 slot 0
  carries MA 15.0 and plane 2 slot 0 carries MA 30.0, and that all MAs
  stay within [0, 360).
- Confirm the identities: satellites per plane times p equals t, RAAN
  spacing times p equals 360, mean anomaly spacing times s equals 360,
  and the phase equals f * 360 / t.
- Confirm walker_slots is deterministic (two calls return identical
  lists) and unique_slot_count returns t for every valid triple.
- Run the contract test offline: python3
  scripts/test_walker_delta_constellation.py (35 tests, deterministic).

## Related leaves

- space-systems/orbit-mechanics/satellite-coverage: the single-satellite
  access geometry side of a constellation, out of scope here.
- space-systems/orbit-mechanics/ground-track-repeat: repeat-cycle and
  ground-track context for constellation design.
- space-systems/orbit-mechanics/sun-synchronous-inclination: the
  inclination choice that fixes the plane geometry a Walker-Delta
  pattern is laid over.
- space-systems/mission-design/launch-window-analysis and
  space-systems/mission-design/mission-delta-v-budget: the deployment
  and station-keeping loop that a Walker-Delta constellation feeds.

## Pitfalls

- Reading t/p/f as three independent knobs: t must be divisible by p and
  f is bounded to [0, p - 1], so triples like 24/5/1 or 24/3/3 are
  rejected by validate_walker before any geometry is computed.
- Confusing the in-plane spacing with the phasing offset: the mean
  anomaly spacing 360/s spaces the s slots within a plane, while the
  inter-plane phase f*360/t shifts whole planes relative to each other;
  quoting 45.0 deg as the phase of 24/3/1 when the true phase is 15.0
  deg collapses the constellation into an un-phased stack.
- Forgetting the first-slot phase offset: each plane's first slot is not
  at MA 0 but carries j * f * 360 / t (15.0 deg for plane 1 of 24/3/1),
  which is what creates the diagonal Walker-Delta pattern.
- Summing angles without the modulo: slot mean anomalies are wrapped mod
  360, so a slot whose raw offset exceeds 360 deg folds back into the
  [0, 360) band.
- Dropping the RAAN dimension in uniqueness checks: slots are unique
  (RAAN, MA) pairs; with f = 0 the MA repeats across planes and only the
  distinct RAAN values keep the t slots unique.
- Treating the conceptual grid as a capacity model: this leaf produces
  the t/p/f geometry and slot grid only; empirical capacity and access
  studies of the deployed constellation belong to sibling leaves.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_walker_delta_constellation.py

The test covers the 24/3/1 worked example within 1e-9 (8 satellites per
plane, RAAN spacing 120.0 deg, MA spacing 45.0 deg, phase 15.0 deg),
the f = 2 phase of 30.0 and the 27/3/1 phase of 13.333 within 1e-3, the
slot grid enumeration (length t, s entries per plane, plane 1 slot 0 at
MA 15.0, plane 2 slot 0 at MA 30.0, MA wrapped into [0, 360)), the
uniqueness of the (RAAN, MA) pairs, the documented identities (s * p ==
t, RAAN spacing * p == 360, MA spacing * s == 360, phase == f * 360 /
t), dict key exactness, determinism, and ValueError rejection of
non-divisible t, out-of-range f and non-positive t or p.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA standards
  family (ecss.nl/standards); the Walker-Delta relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
