---
name: e2008-illumination-stability-test-purpose
description: "Determine what an illumination stability test on a photovoltaic assembly has to establish under ECSS-E-ST-20-08C clause 6.4.3.12.1: group the light-driven mechanisms declared for the assembly and map each to the quantity a sustained soak must bound, project the output drift the mission accumulates over its illuminated hours, decide whether that exposure earns the test at all, then check the planned soak resolves the drift against the measurement uncertainty, samples it often enough to separate settling from trend, and is held at the reference temperature. Use when scoping or reviewing an illuminated stability characterisation. Trigger: ecss, e-st-20-08c, clause-6-4-3-12-1, illumination-stability-test-purpose, sustained-illumination-output-drift, light-induced-degradation-mechanism, reference-temperature-soak-representativeness, stability-drift-resolution-margin."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-illumination-stability-test-purpose, sustained-illumination-output-drift, light-induced-degradation-mechanism, reference-temperature-soak-representativeness, stability-drift-resolution-margin, illuminated-soak-sampling-density]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Illumination Stability Test Purpose (space-systems/ecss/e2008-illumination-stability-test-purpose)

Use when the task is to state and defend why a photovoltaic assembly is held
under sustained illumination at the reference temperature under
ECSS-E-ST-20-08C clause 6.4.3.12.1 -- which light-driven behaviours the soak
has to bound, whether the mission accumulates enough illuminated time for
any of them to act, and whether the planned soak can actually see the drift
it exists to find.

## Domain quick reference

- An assembly is characterised by a flash lasting milliseconds and then
  flown for years under continuous sun. The stability test closes that gap:
  it asks whether the number the flash measured is still the number after
  light has been on the article long enough for something to happen.
- Several distinct mechanisms move the output and each is its own reason to
  run the soak: metastable defects forming under carrier injection, adhesive
  darkening that costs transmittance rather than junction quality, contact
  resistance drifting under sustained illuminated heating, ultraviolet
  fixing volatile contamination onto the optical surface, and an output that
  has simply not reached its stabilised value yet.
- Exposure earns the test. A mechanism declared against a mission with a
  handful of illuminated hours cannot move the output far enough to matter,
  and the soak buys nothing but schedule.
- Resolution decides whether the soak answers anything. Drift the size of
  the instrument's uncertainty returns a stable reading whether or not the
  article is stable, and that outcome is indistinguishable from success.
- Two measurements, one at each end, give a difference and nothing else. A
  settling transient that has flattened and a trend still climbing produce
  the same end points; only a sampled soak tells them apart.
- Temperature is part of the purpose, not a convenience. Output moves with
  temperature far faster than with illumination history, so a soak held away
  from the reference temperature reports the two effects added together and
  nothing downstream can separate them again.

## Workflow

1. Validate the stability policy first: significance trigger, drift
   acceptance bound, resolution margin, minimum sampling and temperature
   offset allowance. A resolution margin below one is refused rather than
   used, because a drift the size of the uncertainty is not resolved.
2. Group the declared light-driven mechanisms, rejecting an unrecognised one
   rather than ignoring it, and map each to the quantity the soak must
   bound. Append the shared characterisation objective whenever any
   mechanism is present.
3. Project the drift the mission accumulates over its illuminated hours and
   compare it with the acceptance bound. This is reported whatever the
   verdict, because it is the number the soak exists to support.
4. Decide whether the test is earned at all: a mechanism declared and
   illuminated hours at or above the significance trigger. An exposure
   landing exactly on the trigger earns the test; the comparison tolerance
   absorbs representation error and the trigger does not move.
5. When it is earned and a soak is planned, project the drift over the soak
   itself, check it against the resolution margin on the measurement
   uncertainty, count the measurement points the sampling interval yields,
   and check the soak temperature stands in for the reference temperature.
6. Close on one verdict: stability test not required, measurement not
   planned, measurement inadequate, or illumination stability characterised
   -- reporting every inadequacy found, not only the first.

## Pitfalls

- Treating a declared mechanism as sufficient reason to soak. Without the
  illuminated hours behind it the mechanism has nothing to act over, and the
  test returns a stable result that proves only that the soak was short.
- Planning the soak around schedule and reading the uncertainty afterwards.
  If the expected drift sits inside the instrument's noise the result is
  fixed before the lamp is switched on.
- Measuring only before and after. The difference is real and the shape is
  gone, so a settling transient and a live trend close the same way.
- Letting the soak run at whatever temperature the chamber settles at. The
  thermal coefficient dominates, and the reported drift then contains a
  thermal term that no later analysis can subtract.
- Carrying a cell-level stability result onto the assembly. Adhesive
  darkening and photo-deposited contamination act on the optical path that
  only exists once the coverglass is bonded.

## Behavior contract (gate 3)

The policy validation, mechanism inventory and objective mapping, the
mission and soak drift projection, the acceptance bound comparison, the
resolution margin check, the measurement point count, the reference
temperature representativeness check and the purpose verdict are exercised
by the gate 3 contract test:
scripts/test_e2008_illumination_stability_test_purpose.py against
scripts/e2008_illumination_stability_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_illumination_stability_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
