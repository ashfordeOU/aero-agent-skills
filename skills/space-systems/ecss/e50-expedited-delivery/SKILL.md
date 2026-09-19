---
name: e50-expedited-delivery
description: "Analyze the expedited delivery service of a space data transfer protocol under ECSS-E-ST-50C clause 5.6.14.3, whose single normative item asks that urgent data reach the far end ahead of the traffic already queued for the link. Compute the latency an urgent unit sees under no expedited class, a non-preemptive class that waits for the unit in service, and a preemptive class that interrupts it, compare each against the deadline, report the service rate or the policy change that would meet it, and check that the expedited load still leaves the normal traffic a share of the link. Use when specifying urgent data handling or reviewing link priority. Trigger: ecss, e-st-50-communications, expedited-data-delivery-service, expedited-queue-bypass-latency, preemptive-expedited-transmission, expedited-traffic-starvation-of-normal-traffic, urgent-data-unit-deadline."
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
  tags: [ecss, e-st-50-communications, e50-expedited-delivery, expedited-data-delivery-service, expedited-queue-bypass-latency, preemptive-expedited-transmission, expedited-traffic-starvation-of-normal-traffic, urgent-data-unit-deadline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Expedited Delivery (space-systems/ecss/e50-expedited-delivery)

Use when urgent data has to get past a queue on a space link, per
ECSS-E-ST-50C clause 5.6.14.3 — how long an urgent unit actually waits under
each queuing policy, whether that meets its deadline, and what the priority
costs the traffic behind it.

## Domain quick reference

- Expedited is a queueing property, not a rate property. A faster link
  shortens every queue including the urgent unit's, but it does not stop
  the urgent unit from sitting behind whatever is already waiting; only a
  separate class does that.
- Three policies give three very different latencies. With no expedited
  class the urgent unit waits for the whole queue; non-preemptive lets it
  jump the queue but not interrupt the unit already going out;
  preemptive interrupts that one too and pays a switch cost instead.
- The non-preemptive residual is the honest part of the calculation. The
  unit in service has some bits left to send, and that remainder is the
  irreducible wait a non-preemptive class leaves. Assuming the link is
  idle when the urgent unit arrives hides exactly the case the deadline
  was written for.
- Preemption is not free. Interrupting a unit costs a switch, and the
  interrupted unit is either resumed or resent; the resend is wasted link
  time and it belongs in the comparison.
- Priority without a cap starves the traffic behind it. An expedited load
  that consumes the whole service rate leaves nothing for the normal
  queue, which then grows without bound however healthy the urgent
  latency looks.
- The two remedies are a policy change and a rate change, and they are not
  interchangeable. Where the queue dominates, moving from no class to a
  non-preemptive class helps far more than raising the rate; where the
  unit itself is long, the rate is what moves.

## Workflow

1. State the link as the service rate, the urgent unit size, the units
   already queued with their size, and the bits left in the unit
   currently in service.
2. State the policy: no expedited class, non-preemptive, or preemptive
   with its switch cost and whether the interrupted unit is resumed or
   resent.
3. Compute the latency the urgent unit sees under that policy, and under
   the other two, so the comparison is on the table rather than asserted.
4. Compare the latency with the deadline using a relative tolerance, so a
   design landing exactly on the deadline is compliant on every build
   host.
5. Where the deadline is missed, report both remedies with their numbers:
   the policy that meets it at this rate, and the rate that meets it
   under this policy.
6. Compute the share of the link the expedited load consumes and report a
   normal queue left with nothing, whatever the urgent latency looks like.
7. Check any recommended rate or policy against the same model before
   reporting it.

## Pitfalls

- Computing the urgent latency against an idle link. The queue and the
  unit in service are the whole reason the clause exists, and an idle
  link case always meets the deadline.
- Treating non-preemptive as equivalent to preemptive. The residual of the
  unit in service is the difference, and on a link with long units it is
  most of the latency budget.
- Ignoring the cost of preemption. The switch takes time and a resent unit
  takes the whole unit time again; a policy compared without them looks
  better than it is.
- Meeting the deadline and stopping. An expedited class that consumes the
  service rate starves the normal queue, and that failure appears later
  and further away than the one being measured.
- Offering only the faster link. Where the wait is queueing rather than
  transmission, the policy is the cheaper axis and a rate increase buys
  very little of it.

## Behavior contract (gate 3)

Link and policy validation, the three policy latencies including the
in-service residual and the preemption cost, deadline comparison at the
exact bound, the rate and policy remedies checked against the same model,
and the starvation check are exercised by the gate 3 contract test:
scripts/test_e50_expedited_delivery.py against
scripts/e50_expedited_delivery_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_expedited_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
