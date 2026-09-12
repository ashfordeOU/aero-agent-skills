---
name: e20-power-protection-failure-containment
description: "Use when verify that the protection functions of a spacecraft power converter or regulator are independent enough to stop a fault spreading, under ECSS-E-ST-20C clause 5.3: categorize each protection function as current-limiting, voltage-limiting, thermal or isolating; confirm it shares no sense element, reference, control loop, housekeeping supply or return path with the function it protects; size the trip threshold above the load's steady-state and inrush draw yet below the harness and source fault rating; confirm the load-side protection trips before the source-side one with selectivity margin; and confirm the trip clears faster than the bus ride-through time. Trigger: ecss, e-st-20c-clause-5-3, power-protection-independence, fault-containment, latching-current-limiter, overcurrent-trip-threshold, protection-selectivity, converter-regulator-protection, bus-ride-through."
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
  tags: [ecss, e-st-20-electrical-scope, e20-power-protection-failure-containment, power-protection-independence, fault-containment, latching-current-limiter, overcurrent-trip-threshold, protection-selectivity, bus-ride-through]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Power Protection and Failure Containment (space-systems/ecss/e20-power-protection-failure-containment)

Use when the task is the clause 5.3 containment argument of
ECSS-E-ST-20C -- showing that the protection functions built into a
power converter or regulator are independent of what they protect, set
to a threshold that separates a real fault from normal operation, and
coordinated so a single branch fault is cleared locally instead of
propagating onto the distribution bus.

## Domain quick reference

- A protection function belongs to exactly one family before any
  independence argument is made: current-limiting (latching current
  limiter, foldback limiter, fuse, circuit breaker), voltage-limiting
  (overvoltage trip, undervoltage lockout, transient clamp), thermal
  (overtemperature trip, thermal foldback) or isolating (series
  isolation switch, blocking diode, galvanic barrier). A device that
  fits none of these is not a protection function for this assessment
  and is rejected rather than silently accepted.
- Independence is the absence of a shared failure-prone resource
  between the protection and the function it protects. Five resources
  break containment when shared: the current or voltage sense element,
  the voltage reference, the control loop, the housekeeping supply and
  the return path. Drawing the protection's own housekeeping power
  from the rail it is meant to disconnect is a separate and equally
  disqualifying dependency -- the protection dies with the fault.
- A trip threshold has a feasible window, not a single right value.
  The lower bound is the larger of the load's steady-state draw and
  its inrush peak, raised by a margin so normal transients do not
  nuisance-trip. The upper bound is the harness and source fault
  rating reduced by the same margin, so the protection always acts
  before the wiring or the source does. When the two bounds cross,
  no setting is valid and the branch needs re-sizing, not a number.
- Containment also needs ordering in two dimensions. In current, the
  load-side (downstream) protection must trip at a lower level than
  the source-side (upstream) one by a selectivity ratio, or an
  upstream device clears first and drops healthy loads with the faulty
  one. In time, the protection's total response must be shorter than
  the bus ride-through time, or the bus collapses before the fault is
  isolated.

## Workflow

1. Enumerate every protection function on the branch and categorize
   each one into its family; reject an unrecognized device type before
   it enters the containment argument.
2. For each protection function, list the resources it shares with the
   function it protects and flag every shared entry in the
   containment-breaking set; flag separately when the protection draws
   its housekeeping power from the protected rail.
3. Derive the feasible trip window from the load steady-state current,
   the inrush peak, the harness and source fault rating and the chosen
   margin fraction; flag an infeasible window as a sizing defect.
4. Compare the as-designed trip setting against that window and flag a
   setting below it (nuisance trips) or above it (the harness or
   source fails first).
5. Compute the selectivity ratio of the upstream trip level to the
   downstream one and flag any pair below the required ratio.
6. Compare the protection's total response time against the bus
   ride-through time and flag a response that is not strictly faster.
7. Aggregate the independence, threshold, selectivity and timing
   findings for the branch; the branch is contained only when every
   list is empty.

## Pitfalls

- Accepting a protection function that senses the fault through the
  same shunt or divider the regulator uses for control -- one open
  sense element then disables regulation and protection together, and
  the containment argument is void even though both functions exist
  on the schematic.
- Powering a latching current limiter's drive electronics from the
  output rail it protects, so the short that should be cleared also
  removes the energy needed to clear it.
- Setting the trip just above steady-state current and ignoring
  inrush, which turns every capacitive load turn-on into a false
  trip, or setting it just below the harness rating with no margin,
  which lets the wiring carry the fault.
- Treating a higher upstream trip level as automatic selectivity
  without a ratio -- two thresholds a few percent apart, with real
  tolerance and temperature drift, trip in an order nobody controls.
- Reporting a fast protection as sufficient without comparing it to
  the bus ride-through time; the only meaningful statement is that
  clearing completes before the bus leaves its undervoltage limit.

## Behavior contract (gate 3)

The protection-family categorization, independence, trip-window,
selectivity and response-time logic is exercised by the gate 3
contract test: scripts/test_e20_power_protection_failure_containment.py
against scripts/e20_power_protection_failure_containment_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_power_protection_failure_containment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
