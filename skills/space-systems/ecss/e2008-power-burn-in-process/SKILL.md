---
name: e2008-power-burn-in-process
description: "Evaluate whether a power burn-in under ECSS-E-ST-20-08C clause 12.6.7.2.2 held the specified forward current for the ninety-six hour minimum or merely logged oven time: group each logged segment as soak, interruption or overdrive against the current tolerance band, count only continuous in-band hours, restart the clock when an interruption runs past its allowance, derive the junction temperature the forward loading produces, confirm every declared build defect has a parameter watching it, and separate a completed soak from one short, overdriven, overheated or blind. Use when planning or reviewing a device power burn-in before the qualification lot is released. Trigger: ecss, e-st-20-08c-clause-12-6-7-2-2, power-burn-in-forward-current-band, power-burn-in-ninety-six-hour-floor, power-burn-in-interruption-restart, power-burn-in-junction-temperature-limit, power-burn-in-monitored-parameters."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-power-burn-in-process, power-burn-in-forward-current-band, power-burn-in-ninety-six-hour-floor, power-burn-in-interruption-restart, power-burn-in-junction-temperature-limit, power-burn-in-monitored-parameters]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Power Burn-in Process (space-systems/ecss/e2008-power-burn-in-process)

Use when the task is to plan or defend the power burn-in actually run on a
device lot under ECSS-E-ST-20-08C clause 12.6.7.2.2 -- what current was
held, how closely, for how many hours that count, and watched through what.

## Domain quick reference

- The clause is written about the process, not the outcome. It fixes the
  drive -- the specified forward current -- and the floor -- ninety-six
  hours -- and a soak log either meets both or it does not.
- The current has to sit inside a tolerance band around the specified
  value. Below the band the devices are not being driven and the hours are
  not soak hours. Above it they are being overdriven, and a run that
  overdrives introduces the defects it exists to remove.
- Only continuous in-band time counts. A log that totals well past the
  floor can still fail it, because total hours and continuous hours are
  different numbers and the requirement is written against the second.
- An interruption short enough that the devices do not cool is tolerated
  and the clock keeps running across it. One past that allowance restarts
  the clock: the accumulated time no longer describes one run.
- The acceleration runs on the junction, not the oven. Case temperature
  plus the dissipated power across the thermal path is where the device
  actually sits, and a soak sized on the oven set point is sized on the
  wrong temperature.
- The same thermal path makes the ceiling real. A junction driven past its
  limit damages the lot the soak was meant to screen, so more drive is not
  monotonically more screening.
- Every declared build defect surfaces in one measurable parameter. A
  defect with nothing watching it survives the whole soak untouched
  however many hours were logged, and the lot certificate will not say so.

## Workflow

1. Validate the process policy first: soak-hours floor, current tolerance
   band, interruption allowance and junction ceiling. A tolerance band as
   wide as the set point is refused rather than used.
2. Group the declared build defects, rejecting an unrecognised one rather
   than ignoring it, and map each to the parameter it is read through.
3. Group every logged segment against the band as soak time, an
   interruption or an overdrive. Report the three totals separately; they
   answer three different questions.
4. Accumulate the longest continuous in-band run, carrying the clock
   across a tolerated interruption and restarting it after one that is
   not. That run, not the log total, is the duration evidence.
5. Derive the dissipated power from the specified loading, then the
   junction temperature from the case temperature and the thermal
   resistance, and compare it against the ceiling.
6. Check monitoring coverage separately from loading: a soak can be long
   enough, hot enough and blind at the same time.
7. Close on one verdict -- burn-in not performed, junction over limit,
   current out of band, duration short, monitoring blind, or burn-in
   complete -- reporting every inadequacy found, not only the first. A
   run landing exactly on the hours floor or exactly on a band edge is
   accepted; the comparison tolerance absorbs representation error and
   the limit does not move.

## Pitfalls

- Reading the log total as the soak duration. Hours separated by a cold
  gap are not ninety-six continuous hours, and the floor is written
  against the continuous figure.
- Treating any deviation as a stoppage. A brief dip the devices ride
  through is not the same event as an overdrive, and grouping them
  together loses the finding that matters.
- Turning the current up to buy margin. Past the upper band edge the run
  introduces the defects it was meant to remove, and the lot arrives
  damaged with a certificate saying it was screened.
- Sizing the run on the oven set point. The junction sits above the case
  by the dissipated power across the thermal path, and on a device under
  forward load that difference is tens of degrees.
- Declaring a defect and not measuring its parameter. The soak is then
  long, hot and blind to exactly the defect it was justified by.
- Stopping at the first finding. A soak can be short, overdriven and
  blind at once, and a report naming one of the three understates the
  repair.

## Behavior contract (gate 3)

The policy validation, the current band and segment grouping, the total,
overdrive and interruption hours, the continuous qualifying hours with
their interruption restart, the dissipated power and junction
temperature, the defect inventory and parameter coverage, and the
burn-in verdict are exercised by the gate 3 contract test:
scripts/test_e2008_power_burn_in_process.py against
scripts/e2008_power_burn_in_process_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_power_burn_in_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
