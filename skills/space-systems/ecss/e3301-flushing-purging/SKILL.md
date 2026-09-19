---
name: e3301-flushing-purging
description: "Determine whether a mechanism needs an inert dry-gas blanket under ECSS-E-ST-33-01C clause 4.2.6, then size the one it needs. Use when operation or storage in ambient air would degrade the mechanism through lubricant oxidation, moisture uptake, corrosion or a friction rise, and the blanket has to be engineered rather than assumed: choosing a gas that is actually inert against the declared driver, computing the enclosure volume exchanges and flush duration that reach a residual target, working out the pump-and-backfill cycles a vacuum route needs instead, grading dew point and purity, and checking the blanket is unbroken across every ground phase. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-inert-gas-purge, dry-gas-flushing-plan, purge-volume-exchange, purge-dew-point-limit, pump-and-backfill-cycles, ground-phase-purge-continuity."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-flushing-purging, mechanism-inert-gas-purge, dry-gas-flushing-plan, purge-volume-exchange, purge-dew-point-limit, pump-and-backfill-cycles, ground-phase-purge-continuity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Flushing and Purging (space-systems/ecss/e3301-flushing-purging)

Use when the task is the purge provision of ECSS-E-ST-33-01C clause
4.2.6 -- establishing that ambient air degrades a mechanism, and then
specifying the inert dry-gas flush or backfill that keeps it out.

## Domain quick reference

- The clause is conditional, and the condition is the engineering
  claim: a purge is owed where air operation degrades performance. The
  drivers worth naming are a lubricant that oxidises, a surface or
  retainer that takes up moisture, a bearing or race that corrodes, a
  tribological pair whose friction rises in air, and an aperture that
  ingests particulate. With no driver declared, the clause imposes
  nothing, and saying so is a result.
- Inert is a property relative to the driver, not a label on a
  cylinder. Clean dry air answers a moisture driver and answers nothing
  else -- it still carries the oxygen that the oxidation and corrosion
  drivers are about, so those force nitrogen, argon or helium.
- A continuous flush of a well-mixed enclosure decays the contaminant
  by one factor of e per enclosure volume exchanged, so the exchanges
  needed are the natural logarithm of the concentration ratio and the
  time follows from enclosure volume over flow rate. Purging to a
  hundred parts per million from air takes roughly seven and a half
  exchanges, not one.
- A pump-and-backfill route divides the contaminant by the pressure
  ratio each cycle, so the cycle count is the same logarithm divided by
  the logarithm of that ratio. The depth of the vacuum, not the number
  of cycles, is what makes the route cheap.
- Gas quality is a separate gate from quantity. A blanket at the right
  flow with a damp or impure supply installs the contaminant it was
  meant to exclude, so dew point and purity are graded against stated
  limits and reported with the sizing.
- A blanket is only as good as its continuity. Assembly, integration,
  environmental test, transport, storage and the pad are all phases in
  which the mechanism is closed up and unattended; a purge that lapses
  through any one of them has protected nothing, and the lapse is
  invisible in the flow calculation.

## Workflow

1. Declare the degradation drivers. Reject an unrecognised driver
   rather than absorbing it, and if there are none, close the clause
   with a purge that is not required and say why.
2. Choose the gas against the drivers and check the choice: an
   oxidising driver rules out air, whatever its dew point.
3. Pick the route. A continuous flush suits an enclosure that can be
   left flowing; a pump-and-backfill suits one that can hold a vacuum
   and is only opened occasionally.
4. Size the route. For a flush, take the logarithm of the
   concentration ratio as the volume exchanges and divide the enclosure
   volume by the flow rate for the time. For a backfill, divide the
   same logarithm by the logarithm of the pressure ratio and round up
   to a whole cycle -- absorbing the last-place error so a case needing
   exactly three cycles is not billed for four.
5. Grade the gas supply on dew point and purity against the stated
   limits, and treat a value sitting exactly on a limit as meeting it.
6. Check the ground-phase coverage and report any phase the blanket
   does not span. Close as adequate only when sizing, gas, quality and
   continuity all hold.

## Pitfalls

- Reading dry as inert. A clean dry air purge fixes humidity and
  leaves the oxygen partial pressure where it was, so a lubricant
  oxidation driver is untouched by it and the report can look green
  while the failure mechanism runs.
- Sizing a flush by one enclosure volume. One exchange leaves about
  thirty-seven percent of the original charge behind; reaching a
  hundred parts per million from air takes seven or eight, and the
  difference is the whole point of the calculation.
- Quoting a flow rate without a duration or an enclosure volume. The
  quantity that matters is volumes exchanged, and a generous flow into
  a large enclosure for a short window can exchange less than a modest
  one into a small one.
- Rounding a cycle count with a bare ceiling. The count is a ratio of
  logarithms, so a case needing exactly three cycles can evaluate a
  hair above three and be billed a fourth on one platform and not on
  another.
- Grading the plan and never the cylinder. Dew point and purity are
  the other half of the clause, and a blanket delivered from a damp
  supply is a moisture source with a flow meter on it.
- Letting the blanket lapse between phases. Transport and storage are
  where mechanisms sit longest and are watched least, and a purge
  specified only for integration and the pad leaves the two longest
  exposures uncovered.

## Behavior contract (gate 3)

The driver decision, gas admissibility, dilution and pressure-cycle
sizing, gas-quality grading, ground-phase continuity and the adequacy
verdict are exercised by the gate 3 contract test:
scripts/test_e3301_flushing_purging.py against
scripts/e3301_flushing_purging_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e3301_flushing_purging.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
