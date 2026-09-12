---
name: e20-payload-bus-interaction-verification
description: "Use when verify how a payload interacts with the spacecraft primary power bus under ECSS-E-ST-20C clause 5.7.6: categorize each campaign case as an inrush case, an undervoltage case or an agreed failure case, confirm it carries the mandatory case fields, compute the peak inrush current and the time it spends above the protection threshold against the trip delay, derive the transient bus sag from the load step, the bus capacitance and the control bandwidth and check it against the bus lower limit and the payload undervoltage lockout, size the fault current and the protection clearing time against the containment requirement, and report coverage of the three families. Trigger: ecss, e-st-20c-clause-5-7-6, payload-bus-interaction-verification, inrush-current-limiting, undervoltage-transient-sag, agreed-failure-case, protection-trip-delay, payload-undervoltage-lockout, primary-bus-load-step."
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
  tags: [ecss, e-st-20-electrical-scope, e20-payload-bus-interaction-verification, payload-bus-interaction-verification, inrush-current-limiting, undervoltage-transient-sag, agreed-failure-case, protection-trip-delay, payload-undervoltage-lockout]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Payload Bus Interaction Verification (space-systems/ecss/e20-payload-bus-interaction-verification)

Use when the task is the clause 5.7.6 verification campaign of
ECSS-E-ST-20C -- showing by test that a payload switched onto the
primary power bus does not disturb it beyond what the bus is specified
to tolerate, across inrush, undervoltage and the failure cases agreed
with the customer.

## Domain quick reference

- A campaign case is categorized once as inrush (cold start, hot
  switchover, capacitive load, heater switch-on), undervoltage (load
  step, ride-through, eclipse entry, battery discharge) or agreed
  failure (payload short circuit, overcurrent, reverse energy,
  internal latch-up, protection switch failure). The category sets the
  mandatory field list, and a field that is absent or left empty is a
  finding on its own -- the case cannot be evaluated from an
  incomplete sheet.
- Inrush is the charging current of the payload input capacitance
  through its limiting element. The peak is the bus voltage over the
  limiting resistance and the decay follows the product of that
  resistance and the capacitance, so the time the current spends above
  the upstream protection threshold is that time constant scaled by
  the natural logarithm of the peak over the threshold. The case fails
  if the peak exceeds what the bus interface allows, or if the time
  above the threshold outlasts the protection trip delay -- the
  payload then nuisance-trips its own feeder.
- The undervoltage case is a load step landing on a finite bus. The
  sag is the step current divided by the product of the bus
  capacitance and the angular control bandwidth of the regulator, and
  the resistive drop of the harness adds to it. The remaining voltage
  is checked twice: against the lower limit the bus specification
  holds, and against the payload undervoltage lockout, because a
  payload that drops out and re-enters inrush turns one transient into
  a cycle.
- An agreed failure case is only agreed if it appears on the list
  negotiated with the customer. Its fault current is the bus voltage
  over the sum of the fault and harness resistance; the protection
  clears it in the inverse-square time its energy constant allows,
  floored by its own minimum response time, and a fault current at or
  below the protection rating never clears at all. The clearing time
  is checked against the containment requirement and the let-through
  energy against what the interface allows, and the case must state
  what containment outcome was observed.

## Workflow

1. Categorize every case in the campaign; reject a case kind that is
   not a clause 5.7.6 interaction case.
2. List the mandatory fields the category requires and report each one
   the case sheet does not carry or leaves empty.
3. For an inrush case, compute the peak current, the decay time
   constant and the time above the protection threshold; flag a peak
   above the allowed value, a time above the threshold that outlasts
   the trip delay, and a settling time beyond any declared limit.
4. For an undervoltage case, compute the transient sag and the harness
   drop, subtract both from the bus voltage, and flag a result below
   the bus lower limit or below the payload undervoltage lockout;
   where a recovery current and a ride-through time are declared,
   flag a recharge that outlasts the ride-through.
5. For a failure case, confirm the kind is on the agreed list, compute
   the fault current, the clearing time and the let-through energy,
   and flag a fault the protection never clears, a clearing time past
   the containment requirement, energy above the allowance, or an
   outcome that is not one of the recognised containment results.
6. Check coverage: the campaign is incomplete until at least one case
   of each of the three families has been run.
7. Aggregate the coverage findings and the per-case findings; the
   interaction is verified only when both lists are empty.

## Pitfalls

- Running the inrush case at nominal bus voltage only. The peak scales
  with the bus voltage, so the high end of the regulation band is the
  case that trips the feeder, not the nominal point.
- Comparing the inrush peak against the protection rating and stopping
  there. A protection device rides through a current well above its
  rating for a short time; what decides the case is how long the
  current stays above the threshold against the trip delay.
- Deriving the undervoltage sag from the bus capacitance alone and
  ignoring the harness resistance, which adds a step of drop that does
  not recover with the loop and pushes a marginal payload under its
  lockout.
- Checking the sag against the bus lower limit only. The payload
  lockout usually sits above that limit for a reason, and a payload
  that drops out restarts into inrush, converting a single load step
  into a repeating disturbance.
- Testing a failure case that was never agreed, or agreeing a list and
  then reporting a different fault; the clause anchors the failure
  campaign to the agreed set, so an unagreed case is evidence of
  nothing and a missing agreed case is an open verification.
- Reading a long clearing time as conservative. A fault current at or
  below the protection rating is not cleared at all, and reporting a
  very large number instead of a non-clearing result hides a
  containment failure.

## Behavior contract (gate 3)

The case categorization, mandatory-field, inrush, undervoltage,
failure-clearing and campaign-coverage logic is exercised by the gate 3
contract test:
scripts/test_e20_payload_bus_interaction_verification.py against
scripts/e20_payload_bus_interaction_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_payload_bus_interaction_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
