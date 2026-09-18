---
name: e2020-failure-propagation-containment
description: "Verify that a failed current limiter puts no fault effect onto the distribution bus or a neighbouring output line, per clause 5.2.7.3.1 of ECSS-E-ST-20-20C. Use when a containment argument has to hold for every way a limiter fails and not just the convenient one: trace failing conducting, failing open, losing the limiting function and oscillating apart, keep a barrier to the modes it genuinely covers, turn the uncontained fault current into a bus droop across the source impedance, and refuse a backup device that clears after the bus has gone. Trigger: ecss, e-st-20-20c-clause-5-2-7-3-1, limiter-failure-containment, limiter-fault-propagation-to-bus, limiter-barrier-mode-coverage, limiter-fault-bus-droop, limiter-backup-clearing-time."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-7-3-1, e2020-failure-propagation-containment, limiter-failure-containment, limiter-fault-propagation-to-bus, limiter-barrier-mode-coverage, limiter-fault-bus-droop, limiter-backup-clearing-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Limiter Failure Propagation Containment (space-systems/ecss/e2020-failure-propagation-containment)

Use when the task is clause 5.2.7.3.1 of ECSS-E-ST-20-20C: a limiter
failure is contained, so no fault effect from it reaches the
distribution bus or a neighbouring output line. Containment is not a
property of the limiter -- it is a property of what stands between the
limiter and everything else -- so this leaf grades the argument one
failure mode at a time instead of one device at a time.

## Domain quick reference

- A limiter fails in several ways and they do not behave alike. Failing
  conducting hands the line whatever the source can deliver. Failing
  open loses the load on that line and nothing beyond it. Losing the
  limiting function leaves a plain switch where a limiter used to be.
  Failing oscillating puts energy onto the bus at a rate no steady-state
  current sum will ever show. An argument that says "the limiter is
  protected" without saying against which of these has argued nothing.
- A barrier only contains the modes it actually covers. A blocking diode
  does nothing about an oscillation. An output filter does nothing about
  a hard short. A backup fuse and an upstream limiter both answer an
  overcurrent and neither answers a ringing loop. Coverage is read from
  the barrier type, not from its presence on the schematic.
- Where no barrier covers the mode, the fault current is still bounded
  by something: it lands on the source impedance, and the product is the
  droop everybody else on that bus sees. Two thresholds sit on that one
  number -- the droop a neighbouring line tolerates, and the larger one
  at which the bus itself is out of limits -- so the same fault reaches
  a neighbour before it reaches the bus.
- A covering barrier still has to act in time. A backup device that
  clears after the bus has already collapsed contained nothing; it
  tidied up afterwards. Clearing is therefore compared against a budget
  that itself sits inside the bus ride-through.
- A mode nobody traced is not a mode that passed. It is the part of the
  argument where no one looked, and it outranks a mode traced and found
  to propagate, because the two need different work.

## Workflow

1. Validate the policy: the neighbour droop limit must sit at or below
   the bus limit, and the clearing budget must sit inside the bus
   ride-through, or the policy permits the collapse it is meant to
   prevent.
2. Name every declared failure mode and refuse an unrecognised one
   before it enters the argument.
3. For each mode, resolve which declared barriers genuinely cover it;
   refuse a barrier declared twice and a barrier type nobody recognises.
4. Compute the droop the mode's fault current produces across the source
   impedance at the bus voltage.
5. Decide the reach: a covered mode clearing inside the budget is
   contained; otherwise the droop places it against the neighbour limit
   and then the bus limit.
6. Collect the modes covered by a barrier that acts outside the budget
   separately -- they are a timing finding, not a coverage one.
7. List the modes never traced at all, then rank the channel at its
   worst standing: untraced, reaching the bus, reaching a neighbour,
   cleared too late, contained.

## Pitfalls

- Arguing containment for the short-circuit case and stopping. The hard
  short is the mode everyone designs for; the oscillation and the
  silently lost limiting function are the ones that arrive at review
  unanswered.
- Counting a barrier because it is in the line rather than because it
  covers the mode. A diode in series with an oscillating limiter is a
  diode in series with an oscillating limiter.
- Reading a failed-open limiter as a containment failure. It takes its
  own load down and puts nothing anywhere else; the finding belongs to
  availability, not to containment.
- Comparing the fault current against a rating and never turning it into
  a bus droop. The neighbours do not feel amps, they feel volts, and the
  source impedance is what converts one into the other.
- Accepting a backup fuse as containment without its clearing time. A
  fuse that opens after the bus undervoltage has tripped everything else
  has cleared a fault on a bus that was already gone.
- Reporting a mode nobody analysed inside the same list as the modes
  that passed. The first needs an analysis and the second needs nothing,
  and merging them buries the one that matters.

## Behavior contract (gate 3)

The failure mode and barrier vocabularies, the per-mode coverage map
that keeps a diode away from an oscillation, the bus droop built from
fault current, source impedance and bus voltage, the neighbour and bus
thresholds on that one droop, the failed-open mode treated as contained,
the clearing budget inside the bus ride-through, the untraced modes kept
apart from the traced ones and the worst-reach channel verdict are
exercised by the gate 3 contract test:
scripts/test_e2020_failure_propagation_containment.py against
scripts/e2020_failure_propagation_containment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_failure_propagation_containment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
