---
name: q7046-fastener-application-control
description: "Verify that a threaded fastener installation is controlled: the preload window, the locking feature and the right to reuse the part. Use when a joint is about to be tightened or re-tightened and someone must show the numbers close: take the stress area from diameter and pitch, set the target as a fraction of proof load, spread it into the band the tightening method actually delivers, check the low end still holds the joint closed and the high end stays under proof, demand an obstruction rather than a friction torque where losing the fastener loses the function, and retire a part whose prevailing torque has decayed or that was taken past yield. Trigger: ecss, q-st-70-46-fasteners, fastener-preload-window-check, fastener-torque-nut-factor, fastener-positive-locking-requirement, fastener-reuse-prevailing-torque."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-70-46-fasteners, q7046-fastener-application-control, fastener-preload-window-check, fastener-torque-nut-factor, fastener-positive-locking-requirement, fastener-reuse-prevailing-torque]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Application Control (space-systems/ecss/q7046-fastener-application-control)

Use when the task is the application clause of ECSS-Q-ST-70-46, read
together with the companion design-and-application standard it points at
for the joint analysis: settling the preload the joint is actually going
to see, whether the locking feature matches what losing the fastener
costs, and whether a part that has been in once may go back in.

## Domain quick reference

- The joint sees a band, not a target. The tightening method spreads the
  target preload by its own scatter, so the number written on the
  procedure is the least interesting value in the calculation.
- Both ends of that band are limits. The low end has to still hold the
  joint closed against the separating load; the high end has to stay
  under the proof load. A wide-scatter method can breach both at once
  from a target that looked comfortable in the middle.
- Tightening a fastener further does not always make the joint safer.
  Past the proof load the part takes a permanent set, loses preload on
  the next thermal cycle, and the joint that was over-tightened is the
  one that comes loose.
- Torque is a proxy, not the quantity of interest. It reaches the
  preload through a nut factor that lumps thread and bearing friction
  together, and that factor moves with lubrication, plating and reuse
  far more than the preload target ever does.
- A friction locking feature resists rotation; a positive one obstructs
  it. Friction decays under exactly the vibration that made someone ask
  for locking, so where losing the fastener loses the function the
  locking has to be an obstruction.
- A prevailing-torque feature is consumed by use. Reuse is defensible
  only while the measured prevailing torque still reaches the minimum,
  and that is a measurement, not a count of installations.
- A part tightened by a method that takes it past yield has no elastic
  range left. It is single-use whatever the threads look like, and the
  threads will look fine.
- Thread-locking adhesive does not survive removal. The thread is
  cleaned and fresh adhesive applied, so the old feature contributes
  nothing to the next installation.

## Workflow

1. Take the diameter and pitch and compute the stress area, then the
   proof load from the material's proof stress.
2. Set the target preload as a fraction of the proof load, refusing a
   utilisation that targets past proof outright.
3. Apply the tightening method's scatter to get the band the joint will
   actually see, and report both ends.
4. Check the low end against the separating load and the high end
   against the proof load, carrying a small relative slack so a value
   landing on its own limit reads the same everywhere.
5. Convert the target to a torque through the nut factor only when a
   nut factor is given; leave the torque unstated rather than defaulting
   it to a number the procedure will then quote.
6. Match the locking feature against what losing the fastener costs, and
   call out a friction feature standing in for a positive one.
7. For a reinstallation, judge reuse: measured prevailing torque against
   its minimum, adhesive that has to be renewed, and the single-use rule
   for a part taken past yield.

## Pitfalls

- Designing to the target preload and never computing the band. The
  target is met by no real installation; every one lands somewhere in
  the scatter, and both ends of it are what the joint is qualified for.
- Quoting a torque without saying which nut factor produced it. The same
  torque delivers very different preloads dry, lubricated and on a
  re-plated thread, and the torque alone hides which one was assumed.
- Treating a prevailing-torque nut as positive locking because it takes
  a spanner to move. Friction is what it has, and friction is what the
  vibration removes.
- Counting installations instead of measuring prevailing torque. The
  count is a proxy for a decay that depends on the mating thread and the
  removal, and the measurement is available on the bench.
- Reusing a yield-tightened fastener because it looks undamaged. The
  permanent set is in the shank, not the thread, and nothing visible
  reports it.
- Tightening harder to be safe. Preload past proof is lost on the first
  thermal cycle, and the joint ends with less clamp than the one
  tightened to plan.

## Behavior contract (gate 3)

The stress area, the proof and target loads, the per-method scatter
band, the torque conversion through the nut factor, the two-sided
preload window check, the locking adequacy rule and the reuse verdict
are exercised by the gate 3 contract test:
scripts/test_q7046_fastener_application_control.py against
scripts/q7046_fastener_application_control_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q7046_fastener_application_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
