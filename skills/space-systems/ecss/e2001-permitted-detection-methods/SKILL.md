---
name: e2001-permitted-detection-methods
description: "Use when determine which of the global and local multipactor-detection techniques catalogued by ECSS-E-ST-20-01C clause 7.2 may actually be used on a given RF-item: resolve each declared technique-name onto its catalogue entry and coverage-scope, check the facility-capabilities each technique needs, rule out a technique whose enabling condition the hardware denies (an isolator masking the reflected-wave, an output-filter suppressing harmonic-rise, a sealed region blocking probe-access or gas-pressure-rise, a windowless region blocking optical-emission), reject an intermodulation-technique under single-carrier-drive, and assemble a permitted suite that pairs global-coverage with local-coverage inside the latency-budget. Trigger: ecss, e-st-20-01c, multipactor-detection-technique, global-detection-technique, local-detection-technique, nulling-detection, harmonic-rise-detection, electron-probe-detection, optical-emission-detection, gas-pressure-rise-detection."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-permitted-detection-methods, multipactor-detection-technique, global-detection-technique, local-detection-technique, nulling-detection, harmonic-rise-detection, electron-probe-detection, optical-emission-detection, gas-pressure-rise-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Permitted Detection Methods (space-systems/ecss/e2001-permitted-detection-methods)

Use when the task is the technique-selection step of
ECSS-E-ST-20-01C clause 7.2 -- taking the catalogue of global and
local multipactor-detection techniques, filtering it down to the ones
the facility can run and the RF-item under discussion does not
physically forbid, and assembling a permitted suite that pairs
global-coverage with local-coverage.

## Domain quick reference

- Clause 7.2 enumerates techniques, it does not authorize all of them
  everywhere. Each catalogue entry carries a coverage-scope, an
  observable-family, the facility-capabilities it needs, the hardware
  conditions that block it and a nominal detection-latency.
- Global-coverage techniques observe the whole RF-chain through a
  transmitted, reflected or spectral quantity: forward-reflected
  nulling (a discharge unbalances the nulling-bridge),
  harmonic-rise (the non-linear discharge current generates harmonics
  of the drive), third-order-intermodulation-rise (usable only with
  two or more carriers present) and close-to-carrier-noise-rise (the
  electron-cloud modulates the carrier). They notice an event anywhere
  and localize nothing.
- Local-coverage techniques observe one suspect region: electron-probe
  current (a biased probe collects the escaping electrons),
  optical-emission (the discharge and the gas it releases emit light
  through a window or dielectric) and gas-pressure-rise (desorbed gas
  raises the chamber-pressure near the region). They localize the
  event but see nothing outside their region.
- A technique is permitted only when every facility-capability it
  needs is available AND no blocking condition on the item is present.
  The blocking conditions are physical, not procedural: an isolator in
  the output path hides the reflected-wave from the nulling-bridge; an
  output-filter attenuates the harmonic-rise the detector is looking
  for; a sealed region admits neither a probe nor the desorbed gas; a
  windowless region admits no optical view; a single-carrier-drive
  produces no intermodulation-product to watch.
- Calorimetric thermal-rise is catalogued as corroborating-only: its
  latency is orders of magnitude above a discharge-duration, so it may
  support a finding but may never be the primary channel of a
  coverage-scope.
- A suite carries a latency-budget. Because the budget is compared
  against a sum of per-technique latencies, an exactly-on-budget suite
  can land a few ULPs over: the comparison absorbs that representation
  error rather than inflating the budget.

## Workflow

1. Resolve every declared technique-name onto its canonical catalogue
   entry; reject an unrecognized name instead of passing it through as
   an unknown-coverage channel.
2. For each candidate, subtract the facility-capabilities on record
   from the capabilities the technique needs; a non-empty remainder is
   an unmet-prerequisite rejection with the missing capability named.
3. Intersect the item's conditions with the technique's blocking
   conditions; a non-empty intersection is a blocked rejection with
   the blocking condition named.
4. Apply the drive-mode rule: under single-carrier-drive the
   intermodulation-rise technique has no product to observe and is
   rejected; under multi-carrier-drive it is admitted.
5. Partition the permitted candidates by coverage-scope and order them
   by detection-latency, then by name, so selection is deterministic.
6. Select a suite: the fastest permitted primary technique of each
   coverage-scope. A coverage-scope with only corroborating-only
   candidates is reported as uncovered, not filled.
7. Sum the selected latencies and compare against the suite's
   latency-budget under the boundary tolerance. Report the suite as
   permitted only when both coverage-scopes are filled, the budget
   holds, and no rejection is left unexplained.

## Pitfalls

- Reading clause 7.2 as a menu where any listed technique is always
  available -- most entries carry a physical enabling condition, and a
  technique the hardware forbids is not a detection channel however
  standard it looks on paper.
- Selecting harmonic-rise behind an output-filter -- the filter
  attenuates exactly the observable the technique depends on, so the
  channel reads quiet through a discharge it should have caught.
- Planning an intermodulation-rise channel for a single-carrier
  campaign -- with one carrier there is no intermodulation-product,
  and the channel is dead before the item is even mounted.
- Filling the local-coverage slot with calorimetric thermal-rise
  because it is the only region-bound instrument available -- its
  latency cannot resolve a discharge, so it corroborates and never
  registers.
- Raising the latency-budget because a suite lands exactly on it --
  the overshoot is float summation error, and it belongs in the
  comparison tolerance, not in the budget.

## Behavior contract (gate 3)

The catalogue resolution, prerequisite, blocking-condition,
drive-mode, suite-selection and latency-budget logic is exercised by
the gate 3 contract test:
scripts/test_e2001_permitted_detection_methods.py against
scripts/e2001_permitted_detection_methods_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_permitted_detection_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
