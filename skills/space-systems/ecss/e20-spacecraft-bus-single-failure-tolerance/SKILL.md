---
name: e20-spacecraft-bus-single-failure-tolerance
description: "Use when verify that a spacecraft electrical power chain survives any single fault without dropping below the power its minimum mission objectives need, under ECSS-E-ST-20C clause 5.7.2: categorize each unit failure mode and its redundancy scheme, sum the essential minimum-mission load demand, recompute the surviving bus capability with each branch failed in turn, report every non-redundant essential function, and check the stored energy carries the essential load across a cold-standby switchover outage. Trigger: ecss, e-st-20-electrical-scope, single-failure-tolerance, single-point-failure, power-chain-redundancy, cold-standby-reconfiguration, minimum-mission-power-demand, surviving-bus-capability, cross-strapped-power-branch."
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
  tags: [ecss, e-st-20-electrical-scope, e20-spacecraft-bus-single-failure-tolerance, single-failure-tolerance, single-point-failure, power-chain-redundancy, cold-standby-reconfiguration, minimum-mission-power-demand, surviving-bus-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Spacecraft Bus Single-Failure Tolerance (space-systems/ecss/e20-spacecraft-bus-single-failure-tolerance)

Use when the task is the clause 5.7.2 robustness demonstration of
ECSS-E-ST-20C -- showing that no single fault anywhere in the
spacecraft electrical power chain takes the bus below the power the
minimum mission objectives require, neither in the steady state that
follows the fault nor during the switchover that recovers from it.

## Domain quick reference

- The chain is treated as a set of parallel contributing branches --
  solar array sections, regulator branches, battery branches,
  distribution paths -- each carrying the power it delivers to the
  bus. Chain capability is the sum over branches, and the single-fault
  case is that sum recomputed with one branch faulted.
- Each branch failure mode is categorized once into its effect on the
  chain: loss of output (short circuit, open circuit, a switch stuck
  open), degraded output (the branch still delivers a reduced
  fraction), or loss of the control path (a switch stuck closed, a
  lost command route). An unrecognized mode is rejected before it
  reaches the arithmetic rather than being silently treated as benign.
- Each branch redundancy scheme is categorized into how it recovers:
  single string recovers not at all and the fault is permanent; cold
  standby recovers fully but only after a switchover outage; hot
  standby and cross strapping recover with no interruption because the
  alternate element is already powered and carrying the function.
- Two capability figures follow from that. The steady-state figure --
  what the chain delivers once any redundancy has taken over -- is the
  one compared against the minimum-mission demand. The transient
  figure, which excludes a cold-standby branch for the length of its
  outage, is what the battery has to make up while the spare is
  switched in.
- Demand is the summed power of the loads flagged essential for the
  minimum mission objectives, not the full load list. A payload left
  unflagged is outside the minimum objectives and is excluded by
  design; the flag, not the power number, is what decides.
- A non-redundant branch whose function the chain cannot do without --
  a single battery, a single main regulator -- is a finding on its own
  terms whatever the power arithmetic says, because losing the
  function loses the bus regardless of the margin that remains.
- Capability meets demand when it equals or exceeds it. Both sides are
  sums of floating-point numbers, so an equal case can land a few
  units in the last place short; the comparison absorbs that
  representation error rather than widening the engineering limit.

## Workflow

1. Categorize every branch failure mode into its chain effect and
   every redundancy scheme into its recovery category; reject an
   unrecognized mode or scheme, a duplicated branch identifier and an
   empty chain before any capability is computed.
2. Sum the power of the loads flagged essential for the minimum
   mission objectives to get the demand the clause protects.
3. Fail each branch in turn and recompute the steady-state chain
   capability: a single-string branch contributes only its degraded
   residual, a standby or continuously redundant branch contributes
   its full capability again.
4. Flag every single fault whose surviving capability falls below the
   demand, recording the branch, the capability and the redundancy
   category that produced it.
5. Report every branch that is both essential by function and carries
   no redundancy, independently of step 4.
6. For each cold-standby branch with a non-zero switchover time,
   recompute the capability available during the outage, take the
   deficit against the demand, convert it to watt-hours over the
   outage, and flag a deficit the usable battery energy cannot cover.
7. Aggregate the capability, single-point and reconfiguration
   findings; the chain is single-fault tolerant only when all three
   lists are empty.

## Pitfalls

- Checking only the steady state after the fault and declaring
  tolerance -- a cold-standby branch is absent for its whole switchover
  time, and an essential load that outlives the stored energy during
  that window has already failed the clause.
- Summing the whole load list as the demand instead of the loads
  flagged essential -- the clause protects the minimum mission
  objectives, and a full-service demand turns every ordinary
  degradation into a false finding.
- Reading a healthy margin as proof that there is no single point of
  failure -- a single battery branch with generous margin still takes
  the bus down when it fails, and that is a design finding the
  arithmetic never surfaces.
- Treating a degraded-output fault as a total loss -- a branch still
  delivering a known fraction is worst-cased away, which hides the
  branches that genuinely go to zero behind a wall of false positives.
- Treating cold standby as equivalent to hot standby because both end
  up restoring capability; the difference is the outage, and it is
  precisely the part clause 5.7.2 makes you size the battery for.
- Comparing a summed capability against a summed demand with a bare
  greater-or-equal test -- an exactly compliant case can report a
  shortfall of a few units in the last place, so the comparison must
  absorb representation error without loosening the limit itself.

## Behavior contract (gate 3)

The failure-mode and redundancy categorization, minimum-mission
demand, post-fault and transient capability, single-point-failure and
reconfiguration-energy logic is exercised by the gate 3 contract test:
scripts/test_e20_spacecraft_bus_single_failure_tolerance.py against
scripts/e20_spacecraft_bus_single_failure_tolerance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_spacecraft_bus_single_failure_tolerance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
