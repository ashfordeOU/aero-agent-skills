---
name: e2007-power-lead-transient-setup
description: "Verify the differential-mode injection arrangement a power-lead transient test is built on under ECSS-E-ST-20-07C clause 5.4.9.3: confirm the standard bench underneath it still holds its bond and its supply isolation, then grade each injected lead for its injection device, the offset of the injection point from the unit connector, the separation between injector and monitoring probe, the harness height above the plane and the series isolation that keeps the bus supply from swallowing the pulse, and compute the amplitude the generator truly delivers into the loaded lead. Use when building or auditing a power-lead transient bench before any pulse is applied. Trigger: ecss, e-st-20-07c, power-lead-transient-setup, differential-mode-pulse-injection, transient-injection-offset-window, injection-monitor-probe-separation, transient-source-isolation-inductance, pulse-generator-delivered-amplitude."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-power-lead-transient-setup, differential-mode-pulse-injection, transient-injection-offset-window, injection-monitor-probe-separation, transient-source-isolation-inductance, pulse-generator-delivered-amplitude]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Power-Lead Transient Setup (space-systems/ecss/e2007-power-lead-transient-setup)

Use when the task is the injection arrangement of ECSS-E-ST-20-07C clause
5.4.9.3 -- the differential-mode pulse path the transient susceptibility
method adds on top of the standard bench, and the conformance decision on
every injected lead before the first pulse is fired.

## Domain quick reference

- The arrangement is an addition, not a replacement. The standard
  configuration already fixes the ground plane, the support equipment and
  the bonding; this clause adds where the pulse enters the harness, what
  drives it in, what watches it and what stops the facility supply from
  taking it away.
- Differential mode means the pulse is driven between a supply lead and
  its own return, not between a lead and the structure. A pulse injected
  on the primary positive lead and returned through the secondary return
  is a common-mode arrangement wearing a differential label, and the
  susceptibility level it reports belongs to a different clause.
- The injection device is part of the arrangement. A series transformer,
  a series coupling capacitor and a clamp probe present different source
  impedances to the lead, so the device is recorded rather than chosen on
  the day from whatever is on the shelf.
- The injection point is a dimension with a window, not a preference.
  Moving the injector down the harness changes the length of lead between
  the injection point and the unit, and with it the stray capacitance the
  pulse edge sees. Two runs at different offsets are not comparable.
- The monitoring probe must sit clear of the injector. Clamped close, it
  reads the injector's own near field rather than the current reaching
  the unit, and the run then records the generator rather than the lead.
- The bus supply needs a series isolation in the feed. Without it the
  supply and its decoupling present a low impedance across the injection
  point, the pulse is absorbed before the unit sees it, and a unit that
  would have failed passes because the bench never delivered the level.
- A generator dial is an open-circuit amplitude. What the unit sees is
  that amplitude divided down by the generator impedance against the lead
  it is driving, so the delivered value is computed, not read off.
- A dimension inside its window but close to the edge is a limitation to
  carry, not a deviation to raise. Keeping the two apart stops a bench
  being rebuilt over a millimetre and stops a real deviation being lost
  among rounding matters.

## Workflow

1. Validate the bench: differential mode declared, unit bonded to the
   plane inside the milliohm ceiling, support equipment powered, and a
   positive series isolation in the supply feed.
2. Normalize each injected lead, confirm the declared return is the one
   that actually closes the differential loop for that supply lead, and
   reject a supply lead appearing twice -- a duplicate means two runs were
   merged into one arrangement.
3. Confirm a monitoring probe is fitted on every injected lead.
4. Grade the injection offset and the harness height against their
   windows, and the probe separation and the series isolation against
   their floors, grouping each result as conforming, marginal or
   deviation.
5. Compute the delivered pulse amplitude from the open-circuit amplitude,
   the generator impedance and the lead impedance whenever a generator is
   on record.
6. Aggregate: per-path deviations as findings, edge-of-window dimensions
   as limitations, and the governing path. The bench conforms only when no
   finding stands.

## Pitfalls

- Returning the pulse through the structure or through another lead's
  return and still calling the arrangement differential. The level that
  comes out characterizes a common-mode path.
- Recording the injection device as an afterthought. The source impedance
  it presents is part of what reaches the unit, so two benches with the
  same dial setting deliver different pulses.
- Clamping the injector wherever the harness is easiest to reach, then
  comparing that run against one taken at the nominal offset.
- Placing the monitoring probe against the injector because the bench is
  crowded, and recording the injector's near field as lead current.
- Leaving the bus supply unisolated. The pulse then dies into the supply
  decoupling and the unit is graded against a level it never received.
- Reporting the generator dial as the applied amplitude. It is the
  open-circuit value, and the loaded lead always sees less.
- Filing every millimetre at the window edge as a deviation, so the real
  deviations stop being read.

## Behavior contract (gate 3)

The bench validation, differential pairing, windowed and floored dimension
grading, delivered-amplitude computation, governing-path reduction and
conformance aggregation logic is exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_transient_setup.py against
scripts/e2007_power_lead_transient_setup_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_power_lead_transient_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
