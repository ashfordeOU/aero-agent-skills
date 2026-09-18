---
name: e2020-telemetry-accuracy-verification-points
description: "Evaluate the load points a current telemetry accuracy verification actually exercises against the ones ECSS-E-ST-20-20C clause 5.2.8.7.1 expects, and name what the test programme would leave unproven. Use when a proposed current telemetry test matrix has to be accepted or sent back: match every proposed point against the required fractions of full scale inside a stated tolerance, carry each declared mission load current as a required point of its own, refuse a point outside the channel range, group proposals that add no coverage, insist on a no-load point and a loaded low-end point where the fixed error governs, and close with the gaps named. Trigger: ecss, e-st-20-20c-clause-5-2-8-7-1, telemetry-accuracy-verification-points, current-telemetry-test-matrix, full-scale-fraction-coverage, low-end-verification-point, mission-load-point-coverage, verification-point-match-tolerance."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-telemetry-accuracy-verification-points, current-telemetry-test-matrix, full-scale-fraction-coverage, low-end-verification-point, mission-load-point-coverage, verification-point-match-tolerance, no-load-verification-point]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Telemetry Accuracy Verification Points (space-systems/ecss/e2020-telemetry-accuracy-verification-points)

Use when the task is the clause 5.2.8.7.1 question of ECSS-E-ST-20-20C:
a current telemetry channel claims a reporting accuracy, and the
verification has to demonstrate it at load points spread across the
range rather than wherever the bench happened to sit.

## Domain quick reference

- Accuracy is only verified where it was measured. A matrix that
  clusters around one load says nothing about the rest of the range,
  and the accuracy figure carried into the budget is then an
  extrapolation dressed as a measurement.
- Required points come from two independent places. The range
  contributes declared fractions of full scale, no-load and full load
  among them; the mission contributes the load currents the equipment
  is actually declared to operate at. A mission point that happens to
  coincide with a range fraction is one point, not two, but a mission
  point on its own is required in its own right.
- A proposed point covers a required point when it sits inside a
  tolerance stated as a fraction of full scale. The tolerance scales
  with the range, so the same percentage is a different current on a
  2 A channel and a 20 A one, and the matrix cannot be carried across
  channels unchanged.
- The low end has a rule of its own. Offset, quantisation and noise do
  not shrink with the load, so they dominate the error near no-load and
  a matrix with nothing under about a tenth of full scale has skipped
  the region where the accuracy claim is hardest to meet.
- The no-load point does a different job from the low-end point. No-load
  separates the fixed part of the error from the part that scales with
  the reading; a small loaded point shows what that fixed part does to
  the percentage figure once there is a reading to be wrong about.
- Two proposals inside the match tolerance of each other are one point
  of coverage. Counting them separately inflates the matrix and can
  carry it over a minimum-points rule it never really met.

## Workflow

1. Take the plan: full scale, the proposed load points, the declared
   mission operating currents, and the policy that fixes the required
   fractions, the match tolerance, the low-end fraction and the minimum
   distinct count. Refuse a proposed or mission current outside the
   channel range rather than clamping it silently.
2. Build the required set: every policy fraction scaled to full scale,
   plus each mission current that no fraction already covers, tagged
   with where it came from.
3. Match each required point to its nearest proposal and record the
   distance. Inside the tolerance it is covered; outside it is a gap
   carrying the nearest proposal for context.
4. Group proposals that fall inside the tolerance of an earlier one and
   count only the distinct points against the minimum.
5. Apply the two low-load rules separately: a no-load point, and a
   loaded point at or below the low-end fraction.
6. Close with the verdict, the coverage fraction, each missing point,
   and a duty naming the current to add.

## Pitfalls

- Verifying at full load only because that is where the equipment is
  interesting. The percentage error is at its most forgiving there, and
  the reported current can be well out of budget at the loads the
  channel spends most of the mission reporting.
- Treating a no-load reading as the low-end point. They answer
  different questions, and a matrix carrying only no-load has measured
  the offset without ever checking what it does to a reading.
- Reusing a matrix from another channel because the percentages match.
  The match tolerance and the required points are currents, not
  percentages, so they move with full scale.
- Counting a repeated load point twice. Two readings a hair apart are
  one point of coverage, and a minimum-points rule satisfied by
  duplicates has not been satisfied.
- Comparing a distance against the tolerance by bare arithmetic. A
  point placed exactly on the tolerance edge can land a few units in
  the last place outside it once the fraction has been multiplied out,
  so the comparison absorbs that while the tolerance stays untouched.

## Behavior contract (gate 3)

The policy validation, required-point construction from range
fractions and mission currents, nearest-point matching, tolerance-edge
coverage, duplicate grouping, no-load and low-end rules, minimum
distinct count and the completeness verdict are exercised by the gate 3
contract test:
scripts/test_e2020_telemetry_accuracy_verification_points.py against
scripts/e2020_telemetry_accuracy_verification_points_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_telemetry_accuracy_verification_points.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
