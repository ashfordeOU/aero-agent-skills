---
name: e2020-lcl-repetitive-overload-endurance
description: "Evaluate whether a latching current limiter rides out repeated overload cycles inside its rating and derating limits, for ECSS-E-ST-20-20C clause 5.2.10.1.1: confirm the faulted load really drives the limiter into current limitation, resolve the pass-element dissipation and per-trip energy at the regulated output voltage, propagate a single-pole junction model through the commanded re-closure train to its settled peak, then grade settled junction temperature, limiting-current derating, average dissipation and applied trip count against the rated repetitive-trip capability. Use when a distribution outlet has to survive a repeated short or a stalled load. Trigger: ecss, e-st-20-20c, latching-current-limiter, lcl-repetitive-overload, lcl-trip-energy, pass-element-junction-temperature, lcl-reclosure-train, limiter-derating-policy, repetitive-trip-capability."
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
  tags: [ecss, e-st-20-20c, e2020-lcl-repetitive-overload-endurance, latching-current-limiter, lcl-repetitive-overload, lcl-trip-energy, pass-element-junction-temperature, lcl-reclosure-train, limiter-derating-policy, repetitive-trip-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution — LCL Repetitive-Overload Endurance (space-systems/ecss/e2020-lcl-repetitive-overload-endurance)

Use when the task is the repetitive-overload endurance of a latching current
limiter under ECSS-E-ST-20-20C clause 5.2.10.1.1 -- showing that an outlet
which is driven into limitation again and again, by a short that keeps coming
back or a load that keeps stalling, still sits inside every rating and derating
limit it was designed against once the last re-closure has been made.

## Domain quick reference

- An LCL does not interrupt an overload instantly. It regulates the output at
  its limiting current for a trip delay, and only then latches off. The pass
  element therefore carries the full limiting current across whatever bus
  voltage the load does not take, which is the largest dissipation the part
  ever sees and the reason a repeated trip is a thermal question first.
- While the limiter regulates, the output voltage is not zero unless the load
  is a dead short; it settles at the limiting current times the load
  resistance. A stalled motor or a partly carbonised harness leaves several
  volts on the output, and using zero instead overstates the dissipation.
- The converse case matters more: a load whose resistance is high enough that
  the limiting current would need more than the bus voltage never enters
  limitation at all. That case is not an endurance cycle, and running it
  through a thermal model produces a number with no event behind it.
- The limiting current is a band, not a value. A load can draw more than the
  low end of the band and less than the nominal setting, and then whether the
  outlet limits at all depends on where in the band the delivered unit sits.
  The honest answer there is to re-declare the case against the band edge being
  demonstrated, not to pick the convenient one.
- A train of trips is not a sequence of independent single pulses. The junction
  heats with a time constant during the delay and cools with the same constant
  during the recovery interval, so a short re-closure interval leaves the
  junction above the case when the next overload arrives and the train settles
  on a peak higher than the first pulse. Where the recovery is long against the
  time constant the settled peak collapses back onto the single-pulse value.
- Endurance is a set of limits, not one: the settled junction temperature, the
  limiting current against the pass element's derated rating, the dissipation
  averaged over the cycle against its derated power, and the applied trip count
  against the rated repetitive-trip capability. The derating fractions are
  declared project policy rather than physical constants, so they travel with
  the result.

## Workflow

1. Validate the bus voltage, the limiting current and its band tolerance, the
   faulted load, the trip delay, the recovery interval, the applied and rated
   trip counts and the pass-element thermal and rating data. Refuse a missing
   or non-physical value instead of defaulting it.
2. Decide whether the case is an overload cycle at all. Compare the prospective
   load current at full bus with the low end of the limiting band; report a
   load below it as no cycle, and a load inside the band but under the nominal
   setting as indeterminate until the demonstrated band edge is declared.
3. Resolve the regulated output voltage and the pass-element dissipation of one
   limitation interval, and the energy that interval deposits.
4. Propagate the single-pole junction model through the re-closure train and
   take the settled peak rise, the settled valley and the first-pulse rise;
   add the case temperature to get the junction temperatures.
5. Grade the four checks -- settled junction temperature, limiting-current
   derating, average-dissipation derating and repetitive-trip capability --
   each against its declared limit, absorbing representation error at the bound
   with a named tolerance rather than by moving the limit.
6. Report the verdict with every check, its value and its limit, plus a finding
   wherever the settled peak stands materially above the first pulse, because
   that is the case a single-pulse check would have passed wrongly.

## Pitfalls

- Analysing one trip and declaring the train. The settled peak is the first
  pulse divided by one minus the product of the two exponentials, so a
  re-closure interval short against the thermal time constant multiplies the
  rise many times over while the single-pulse number stays reassuring.
- Assuming the output collapses to zero during limitation. The regulated output
  is the limiting current across the load resistance, and treating a stalled
  load as a dead short inflates the pass-element dissipation and the junction
  temperature with it.
- Taking the nominal limiting current as the entry threshold. The band's low
  end is what a marginal overload has to clear, and a case that sits between
  the two is indeterminate rather than passing.
- Judging endurance on peak dissipation alone. The average over the overload
  and recovery cycle is what the derated power rating is written against, and
  a long recovery makes a frightening peak an unremarkable average.
- Letting the applied trip count go unchecked because the thermal result looks
  comfortable. The rated repetitive-trip capability is a separate life limit on
  the latch and the pass element, and temperature margin does not buy cycles.
- Relaxing a derated limit so an exactly-on-the-bound case passes. An equality
  at a limit is a representation question, handled by the tolerance inside the
  comparison; the derated value stays as the policy declared it.

## Behavior contract (gate 3)

The input validation, limitation-entry decision, regulated-output and
dissipation resolution, settled junction-temperature train, derating checks and
endurance verdict are exercised by the gate 3 contract test:
scripts/test_e2020_lcl_repetitive_overload_endurance.py against
scripts/e2020_lcl_repetitive_overload_endurance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_lcl_repetitive_overload_endurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
