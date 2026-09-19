---
name: q2007-tf-dependability
description: "Compute the achieved dependability of a test facility against its availability and reliability targets, as ECSS-Q-ST-20-07 clause 5.6.6 asks. Use when facility performance has to be monitored rather than asserted between campaigns: refuse targets that are not fractions or not positive times, take the achieved availability from the operating and downtime record, derive mean time between failures and mean time to restore, form the inherent availability those two imply, compare each against its target, and report a monitoring record older than its review interval. Trigger: ecss, q-st-20-07-test-facility-clause-5-6-6, test-facility-achieved-availability, test-facility-inherent-availability, test-facility-mean-time-between-failures, test-facility-dependability-monitoring-interval."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-tf-dependability, q-st-20-07-test-facility-clause-5-6-6, test-facility-achieved-availability, test-facility-inherent-availability, test-facility-mean-time-between-failures, test-facility-mean-time-to-restore, test-facility-dependability-monitoring-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres — Test Facility Dependability (space-systems/ecss/q2007-tf-dependability)

Use when the task is clause 5.6.6 of ECSS-Q-ST-20-07: a test facility
carries availability and reliability targets, its operating record is
what stands behind them, and the question is what the record actually
achieved and whether anyone is still monitoring it.

## Domain quick reference

- Achieved availability and inherent availability are different
  quantities and both are reported. The achieved value comes straight
  out of the record as uptime over the period; the inherent value is
  the mean time between failures over that time plus the mean time to
  restore, and it says what the facility would reach if no downtime
  were logistic.
- The gap between them is the finding. A facility with good mean times
  and poor achieved availability is waiting on parts, people or access,
  not breaking more often, and the corrective action for that is not a
  reliability programme.
- A period with no failure has no mean time between failures. Dividing
  operating time by zero failures does not give an infinite reliability;
  the quantity is simply not defined on that record, and reporting it
  as unbounded is worse than reporting it as absent.
- Downtime is not one thing. Repair time drives the mean time to
  restore; the waiting time around it does not, so a record that lumps
  them together cannot separate a reliability problem from a support
  one.
- Monitoring has a cadence. A dependability record last reviewed longer
  ago than the review interval describes an earlier facility, and the
  clause asks for monitoring, not for one historical study.
- Targets are declared, not discovered. An availability target outside
  zero to one, or a non-positive mean time target, is an input error
  rather than a stretching goal.

## Workflow

1. Validate the dependability targets first: the availability target as
   a fraction, positive mean time between failures and mean time to
   restore targets, and a positive review interval. Refuse anything
   outside those bounds rather than clamping it.
2. Validate the operating record: a positive period, non-negative
   operating, repair and waiting hours, a whole failure count, and a
   whole repair count. Refuse hours that exceed the period they sit in.
3. Take the achieved availability as operating hours over the sum of
   operating hours and total downtime hours.
4. Derive the mean time between failures as operating hours over the
   failure count, reporting it as absent when the record logged no
   failure rather than as unbounded.
5. Derive the mean time to restore from repair hours over the repair
   count, leaving the waiting hours out of it so a support delay does
   not read as a slow repair.
6. Form the inherent availability from those two mean times and carry
   the gap against the achieved value.
7. Compare achieved availability, mean time between failures and mean
   time to restore with their targets, absorbing representation error at
   each boundary with a named tolerance rather than by moving a target.
8. Close on one verdict in order: no record, monitoring stale, the
   availability target missed, the reliability target missed, the
   restore target missed, a logistic downtime gap under watch, or the
   dependability targets met.

## Pitfalls

- Reporting inherent availability as the achieved one. The inherent
  value excludes logistic delay by construction and always flatters a
  facility whose downtime is mostly waiting.
- Dividing by a zero failure count. The mean time between failures is
  not defined on a clean period, and an infinity propagated into the
  inherent availability makes every comparison pass.
- Folding waiting hours into the mean time to restore. That turns a
  spares or access problem into an apparent repair problem and sends
  the corrective action to the maintenance crew.
- Grading a facility on a record nobody has reviewed. The clause asks
  for monitoring; a study from three years ago cannot discharge it,
  however good its numbers were.
- Comparing a computed availability against a target with a strict
  inequality. Availability is a quotient, so a record that lands
  exactly on the target lands on it only to within representation
  error, and the comparison has to absorb that.

## Behavior contract (gate 3)

The target validation, record validation, achieved availability, the
mean time between failures with its undefined case, the mean time to
restore excluding waiting hours, the inherent availability, the
logistic gap, the boundary-tolerant comparisons, the monitoring
currency check and the verdict ordering are exercised by the gate 3
contract test: scripts/test_q2007_tf_dependability.py against
scripts/q2007_tf_dependability_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_tf_dependability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
