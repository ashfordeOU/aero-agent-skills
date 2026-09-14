---
name: e2008-power-burn-in-purpose
description: "Assess whether a blocking diode power burn stage actually simulates device operation under accelerated conditions, which is the only reason the stage exists: take the applied forward current and duty against the in-service operating point, raise them to the declared power-law exponent to size the acceleration the stage buys, convert the burn duration into simulated field hours, refuse a stress that sits under the operating point or past the regime ceiling where a new mechanism takes over, and report whether the screening purpose was met. Use when justifying, sizing or auditing a power burn stage. Trigger: ecss, e-st-20-08c-clause-12-6-7-2-1, blocking-diode-power-burn-purpose, power-burn-operation-simulation, power-burn-duty-acceleration, power-burn-simulated-field-hours, power-burn-regime-ceiling."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-power-burn-in-purpose, blocking-diode-power-burn-purpose, power-burn-operation-simulation, power-burn-duty-acceleration, power-burn-simulated-field-hours, power-burn-regime-ceiling, power-burn-stress-representativeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Power Burn Purpose (space-systems/ecss/e2008-power-burn-in-purpose)

Use when the question is why the power burn stage of ECSS-E-ST-20-08C
clause 12.6.7.2.1 is in the flow at all, and whether a particular stage
earns its place. The clause gives the purpose: device operation is
simulated under accelerated conditions. A stage either satisfies that
sentence on every axis or it is an oven bill with a certificate
attached.

## Domain quick reference

- Operation means this device's operation. A blocking diode has two
  duty points, forward conduction and reverse blocking, and a stage that
  drives only one of them has simulated half a part.
- Simulated means at least the in-service point on every axis. Below it,
  the stage runs a gentler life than the mission and screens out nothing
  the mission would have found.
- Accelerated means meaningfully above it. Acceleration is the entire
  justification for days standing in for years, so a stage that merely
  reproduces the operating point has not earned the word and is reported
  as unaccelerated rather than as a pass.
- The acceleration has a ceiling. Past a declared ratio the part leaves
  the regime the mission puts it in, and a different mechanism takes
  over: the stage then precipitates failures the flight article would
  never have had, rejecting good devices while missing the population it
  was meant to remove. The ceiling is a limit, never a target.
- Duty is part of the stress. A part biased for a fifth of the soak has
  spent most of the stage simulating an idle device, and the elapsed
  hours in the log say nothing about that on their own.
- What the stage buys is stated in simulated field hours: time actually
  under bias, multiplied by what the applied point earns on each axis
  under the declared power law. That number, not the wall-clock
  duration, is what the screen is sized against.
- A stage shorter than the floor is not judged at all. There is no
  reading to argue about, so it closes as not evaluated rather than as a
  failure of the parts.

## Workflow

1. Validate the purpose policy first: stage duration floor, duty floor,
   regime ceiling, acceleration floor, simulated field hour floor and
   the per-axis exponents. A regime ceiling at or below the operating
   point leaves no room to accelerate and is refused rather than used.
2. Check the stage ran past its duration floor. Anything shorter closes
   as not evaluated, whatever the applied point was.
3. Take the ratio of the applied point to the in-service point on each
   axis, and group the axis as operation simulated, below operation or
   beyond the regime. A ratio landing exactly on the ceiling passes; the
   comparison tolerance absorbs representation error and the ceiling
   itself does not move.
4. Raise each ratio to its declared exponent and multiply the axes into
   one acceleration, then check it against the acceleration floor. A
   stage at unity reproduces operation without accelerating it.
5. Check the duty the part was actually held at against the duty floor,
   then turn duration, duty and acceleration into simulated field hours.
6. Close on one verdict: purpose not evaluated, stress not
   representative, purpose unmet, or purpose met. Report every finding,
   not the first, and keep the per-axis ratios beside the verdict so a
   reviewer can see which axis carried the claim.

## Pitfalls

- Reading the purpose as a licence to stress harder. The clause asks for
  the device's own operation, faster; it does not ask for the hardest
  condition the bench can produce.
- Driving one axis and calling it operation. A diode held in forward
  conduction for a week has had nothing said about its blocking
  behaviour, which is the function it is fitted for.
- Running at the in-service point and calling it a burn. The part is
  then living its normal life in an oven, and a week of that stands in
  for a week.
- Chasing the acceleration by climbing past the regime ceiling. The
  failures that arrive are the ceiling's, not the mission's, and the
  population the stage existed to remove is still in the lot.
- Quoting elapsed hours as the result. A part biased for a fifth of the
  soak has a fifth of the exposure, and the two numbers look identical
  in a report.
- Treating the exponents as physics. They are a declared model of a
  mechanism; a project that substitutes its own gets a different
  acceleration from the same bench settings, and the model belongs in
  the record beside the number.
- Reporting a stage that never ran as a failure of the parts. Nothing
  was screened, so nothing was learned about them.
- Comparing an acceleration or a field-hour total against its floor by
  bare arithmetic. Both come out of a power law that lands a few units
  in the last place either side of a limit on different hosts, so the
  comparison absorbs that error while the floor is never relaxed.

## Behavior contract (gate 3)

The policy validation, the duration floor, the per-axis stress ratios
and their grouping against the operating point and the regime ceiling,
the power-law acceleration per axis and combined, the duty floor, the
simulated field hour conversion and the stage verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_power_burn_in_purpose.py against
scripts/e2008_power_burn_in_purpose_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_power_burn_in_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
