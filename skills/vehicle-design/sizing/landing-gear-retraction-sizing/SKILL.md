---
name: landing-gear-retraction-sizing
description: "Use when you must size the landing gear retraction mechanism: the gear moment about the retract pivot from gear weight and CG arm, the retraction actuator force from that moment and actuator arm with a design factor, the actuator stroke from the four-bar linkage geometry between down-locked and up-locked positions via the law of cosines, the down-lock and up-lock hold loads at their lock arms, and the gear bay stowage fit of the wheel and folded strut envelope. Produces the retraction moment, required actuator force and stroke, lock hold loads, and a stowage PASS/FAIL verdict that gates the gear kinematic layout. Trigger: retraction actuator sizing, landing gear retraction mechanism, up lock down lock, gear bay stowage, lock hold load, retraction moment, landing gear kinematics, folding geometry."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [landing-gear-retraction-sizing, retraction-actuator-sizing, landing-gear-kinematics, up-lock-down-lock, gear-stowage-check]
  version: 0.1.0
  author: AeroSkills
---

# Landing Gear Retraction Sizing (vehicle-design/sizing/landing-gear-retraction-sizing)

Use when you must size the landing gear retraction mechanism at the
conceptual level: converting the gear weight acting ahead of the
retract pivot into a retraction moment, that moment through the
actuator arm into an actuator force with a design factor, the two
fixed links of the four-bar linkage into an actuator stroke by the law
of cosines between the down-locked and up-locked geometry, the same
moment into down-lock and up-lock hold loads at their lock arms, and
the wheel plus folded strut envelope against the bay dimensions into a
stowage verdict. This leaf implements that chain in pure Python,
stdlib only. It pairs with vehicle-design/sizing/landing-gear-sizing,
which sizes the static strut demand at touchdown and stops before the
mechanism, and with vehicle-design/sizing/hydraulic-system-sizing,
which takes the actuator force computed here as the demand on the
hydraulic power source.

## Domain quick reference

- Retraction moment about the pivot: M = W * d, with W the gear weight
  (N) and d the gear CG arm (m) ahead of the retract pivot.
- Actuator force: F = K * M / r_act, with r_act the actuator attach
  arm and K the design factor, K = 1.5 default, never below 1. The
  design factor covers friction in the joints and mechanism
  inefficiency at the conceptual level.
- Linkage law of cosines: the pivot, the gear attach point and the
  actuator attach point form a triangle with fixed links a and b; the
  effective link length between the two attach points is L =
  sqrt(a^2 + b^2 - 2 a b cos(theta)) with theta in degrees inside
  (0, 180). L always lies between |a - b| and a + b for realizable
  geometry.
- Actuator stroke: stroke = L(down) - L(up), the change in effective
  link length when the gear travels from the down-locked to the
  up-locked angle. A non-positive stroke means the up-lock geometry is
  longer than the down-lock geometry and the actuator cannot retract
  the gear.
- Lock hold load: R = factor * M / r_lock at the lock arm, factor 1.0
  default for the hold-load check; the gear moment is reacted by the
  over-center lock rather than by the actuator once locked.
- Stowage: the wheel diameter, wheel width and folded strut length
  must fit inside the bay length, bay width and bay depth; any
  violation fails the stowage check with a reason per dimension.
- Units are SI throughout: N, m, degrees. All angles enter the model
  through math.radians.
- FAR 25.729 frames the retraction system context (the gear must stay
  down in the event of a retraction system failure and up during
  flight); the relations above are standard engineering methodology,
  summary-only, not regulatory text.

## Workflow

1. Fix the gear demand: gear weight W and its CG arm d ahead of the
   retract pivot (retraction_moment).
2. Choose the actuator attach arm and the design factor, then size the
   actuator force with actuator_force (K * M / r_act).
3. Fix the linkage: the two fixed links a and b of the four-bar
   triangle and the down-locked and up-locked angles
   (link_length for each position, or actuator_stroke directly for the
   stroke).
4. Check the stroke sign: a down angle smaller than the up angle, or
   equal geometry at both positions, raises ValueError because the
   actuator cannot retract the gear.
5. Size the lock mechanism: lock_reaction at the down-lock and up-lock
   arms with the hold-load factor.
6. Check stowage: stowage_check on the wheel diameter and width and
   the folded strut length against the bay length, width and depth.
7. Roll everything up with retraction_summary for the complete dict:
   moment, force, stroke, linkage, lock reactions and the stowage
   verdict.
8. Confirm the deterministic checks with the contract test
   scripts/test_landing_gear_retraction_sizing.py.

## Worked example

Reference main gear: gear weight 14000 N with CG arm 1.10 m ahead of
the retract pivot, actuator attach arm 0.35 m, design factor 1.5;
four-bar links a = 0.55 m, b = 0.40 m; down-locked angle 85 deg,
up-locked angle 8 deg; down-lock arm 0.80 m, up-lock arm 0.60 m;
wheel 0.66 m diameter x 0.22 m wide; folded strut 2.80 m; bay 0.70 m
x 0.30 m x 3.00 m. Module outputs:

- Retraction moment: M = 14000 * 1.10 = 15400.0 N m.
- Actuator force: F = 1.5 * 15400 / 0.35 = 66000.0 N (66.0 kN).
- Effective link lengths: L(down) = 0.6513 m at 85 deg, L(up) =
  0.1637 m at 8 deg.
- Actuator stroke: 0.6513 - 0.1637 = 0.4876 m (about 488 mm).
- Down-lock hold load: 15400 / 0.80 = 19250.0 N.
- Up-lock hold load: 15400 / 0.60 = 25666.7 N.
- Stowage: 0.66 <= 0.70, 0.22 <= 0.30 and 2.80 <= 3.00, verdict PASS
  with an empty reason list.


## Pitfalls

- Ignoring the stroke sign: the actuator stroke is L(down) - L(up),
  and a down angle below the up angle (or equal geometry at both
  positions) raises ValueError because the actuator cannot retract
  the gear - a non-positive stroke is a kinematic failure, not a
  sizing nuance.
- Skipping the design factor on the actuator: the force is K * M /
  r_act with K = 1.5 default and never below 1, covering joint
  friction and mechanism inefficiency; an undiscounted actuator
  force under-sizes the actuator and the hydraulic demand.
- Reading the lock loads off the actuator force: once locked, the
  over-center lock reacts the gear moment (R = factor * M / r_lock),
  not the actuator; the down-lock and up-lock hold loads use their
  own lock arms (19250 and 25666.7 N in the worked example).
- Sizing the mechanism without the stowage check: the wheel and
  folded strut envelope must fit the bay in every dimension, and the
  check reports a reason per failing dimension - a mechanism that
  retracts into a bay that cannot hold the gear is not sized.
- Misreading the linkage triangle: the effective length L =
  sqrt(a^2 + b^2 - 2 a b cos(theta)) always lies between |a - b|
  and a + b, and the angle must sit inside (0, 180) degrees; a link
  pair outside that geometry raises ValueError.
- Doing the static gear sizing here: the touchdown strut demand,
  nose and main CG split and shock absorber stroke belong to
  landing-gear-sizing; this leaf sizes the retraction mechanism for
  a gear that leaf already sized.
## Verification

- Confirm retraction_moment(14000, 1.10) returns 15400.0 N m and that
  doubling the gear weight doubles the moment.
- Confirm actuator_force(15400, 0.35) returns 66000.0 N; doubling the
  design factor doubles the force and doubling the actuator arm halves
  it.
- Confirm link_length(1.0, 1.0, 60.0) returns 1.0 m (equilateral law
  of cosines) and link_length(1.0, 1.0, 90.0) returns sqrt(2); the
  even cosine identity makes the length at theta equal the closed form
  at -theta.
- Confirm actuator_stroke(0.55, 0.40, 85.0, 8.0) returns a 0.4876 m
  stroke and that a down angle below the up angle raises ValueError
  (up-lock not reachable).
- Confirm lock_reaction(15400, 0.80) returns 19250.0 N and the
  reaction is inversely proportional to the lock arm.
- Confirm stowage_check passes the nominal wheel and strut and fails
  with one reason for an oversize wheel and two reasons when the strut
  is oversize too.
- Confirm every non-positive weight, arm, link, angle or dimension,
  every angle outside (0, 180) degrees, and every design factor below
  1 raises ValueError.
- Run the contract test offline: python3
  scripts/test_landing_gear_retraction_sizing.py (35 tests,
  deterministic).

## Related leaves

- vehicle-design/sizing/landing-gear-sizing: the static strut demand
  at touchdown, the nose and main gear CG split and the shock absorber
  stroke; it sizes the gear before the mechanism, this leaf sizes how
  the gear retracts.
- vehicle-design/sizing/tire-sizing: the wheel and tire dimensions
  used here as the stowage envelope inputs.
- vehicle-design/sizing/hydraulic-system-sizing: the hydraulic power
  source; it takes the actuator force computed by this leaf as its
  actuation demand.
- structures/loads/landing-ground-loads: the ground load cases that
  bound the gear structure the retraction mechanism carries.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_landing_gear_retraction_sizing.py

The test covers the reference gear sizing contract (moment 15400 N m,
actuator force 66000 N, link lengths 0.6513 and 0.1637 m, stroke
0.4876 m, lock reactions 19250 and 25666.7 N, stowage PASS), the
scaling identities (weight, design factor, actuator arm, lock arm),
the equilateral and sqrt(2) law-of-cosines closed forms with the
cosine-even identity, the stroke sign guard, dict key contracts,
determinism, and ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25.729 is a regulatory
  requirement (retraction system context); the relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
