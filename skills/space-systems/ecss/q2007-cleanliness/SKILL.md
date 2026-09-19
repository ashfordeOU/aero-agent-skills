---
name: q2007-cleanliness
description: "Compute and police test-centre cleanliness per ECSS-Q-ST-20-07C clause 5.5.3. Use when each activity has to carry a stated cleanliness level and evidence it was held: derive the airborne particle limit from the class number and particle size rather than quoting a table, compare the worst count with a margin ratio, read the surface obscuration limit off the cleanliness level, reject a certificate coarser than the activity asks for, grade monitoring cadence separately from conformance, and roll the centre up to its tightest class. Trigger: ecss, q-st-20-07-test-centre, q2007-cleanliness, airborne-particulate-class-limit, test-centre-contamination-monitoring-cadence, surface-cleanliness-level-obscuration, cleanroom-particle-count-margin-ratio, test-activity-cleanliness-level-declaration."
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
  tags: [ecss, q-st-20-07-test-centre, q2007-cleanliness, airborne-particulate-class-limit, test-centre-contamination-monitoring-cadence, surface-cleanliness-level-obscuration, cleanroom-particle-count-margin-ratio, test-activity-cleanliness-level-declaration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Cleanliness and Contamination Control (space-systems/ecss/q2007-cleanliness)

Use when the task is the contamination step of ECSS-Q-ST-20-07C clause 5.5.3
-- stating the cleanliness level each activity in a test centre has to be
performed at, and showing from the monitoring record that the level was
actually held while the hardware was exposed.

## Domain quick reference

- Cleanliness is per activity, not per building. Integration of an optical
  bench and a cable-harness lay-up in the same hall are two activities with
  two levels, and the hall is only as clean as the monitoring of the
  tighter one proves.
- An activity that declares no level at all is the first finding to look
  for. "Kept clean" is not a level: it fixes no limit, so no count can be
  non-conforming and no monitoring plan can be written against it.
- The airborne limit is computed from the class number and the particle
  size, never quoted from memory. For class N at size D micrometres the
  admissible concentration is 10**N multiplied by (0.1 / D) raised to
  2.08, in particles per cubic metre. Computing it keeps the size visible:
  the same class admits two orders of magnitude fewer 5 um particles than
  0.1 um particles, and a count quoted without its size is meaningless.
- Report the margin ratio, not just the pass. A cell sitting at 98 percent
  of its limit and one at 10 percent are both conforming and are not the
  same cell; the first is the one that will fail during the campaign.
- Surface cleanliness is a level number with an obscuration limit in
  percentage area coverage, and the numbering runs the opposite way to
  intuition: a lower level number is a cleaner surface. A surface certified
  to level 500 does not satisfy an activity that asks for level 300.
- Monitoring cadence is graded on its own, separately from the counts. An
  activity sampled once a shift against a twice-a-shift requirement can
  hold a spotless record straight through an excursion. The record is then
  evidence about the sampling interval, not about the air.
- The airborne limit comes out of a power expression and is not exactly
  representable, so a count is compared against it with a small relative
  slack. A count landing exactly on the limit conforms on every platform;
  the slack is far below any counter's resolution and relaxes nothing.

## Workflow

1. List the activities. For each, state the airborne class and the particle
   size it is specified at, the surface cleanliness level where hardware is
   exposed, the counts recorded, the monitoring interval and the interval
   required.
2. Refuse the register when a class sits outside the 1-9 range, a particle
   size falls outside the range the formula covers, a surface level is not
   one of the defined levels, a count is negative, or an activity
   identifier repeats.
3. Compute the airborne limit per activity from its class and size, and
   compare the worst recorded count against it with the relative slack.
4. Divide the limit by the worst count to get the margin ratio and carry it
   into the report, so a narrow pass is visible as a narrow pass.
5. Read the surface obscuration limit off the required level. Flag a
   certified level coarser than the requirement and a measured obscuration
   above the limit as two distinct findings.
6. Compare the monitoring interval against the required interval and flag a
   slow cadence whether or not any count exceeded.
7. Roll the centre up: the non-conforming activities, the monitoring gaps
   and the tightest class in use.

## Pitfalls

- Quoting a class limit without the particle size it belongs to. The class
  alone does not fix a number.
- Reporting conformance as a boolean and dropping the margin ratio, so the
  cell running at 98 percent of its limit reads like the one at 10 percent.
- Reading the surface levels as if higher meant cleaner. Level 300 is
  cleaner than level 500, and a coarser certificate silently satisfying a
  tighter requirement is the defect this ordering causes.
- Accepting a clean count record from an activity nobody sampled often
  enough. The cadence check exists because that record looks identical to
  a genuinely clean one.
- Using a strict comparison against the computed airborne limit. It is a
  power expression, not an exact value, and a count on the boundary then
  conforms on one machine and fails on another.
- Applying the hall's level to every activity inside it, so the one
  exposed-optics operation inherits a limit two classes too loose.

## Behavior contract (gate 3)

The airborne class-limit computation, count comparison with relative slack,
margin ratio, surface-level ordering and obscuration limits, monitoring
cadence check and the centre roll-up are exercised by the gate 3 contract
test: scripts/test_q2007_cleanliness.py against
scripts/q2007_cleanliness_logic.py (stdlib unittest, offline). The limits
are graded against the independently published class table rather than a
second copy of the formula.
Run: python3 scripts/test_q2007_cleanliness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
