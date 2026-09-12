---
name: e20-solar-array-drive-current-capability
description: "Use when verify that every conductor carrying solar array section output meets ECSS-E-ST-20C clause 5.5.4: take the applied current as the hot, near-sun short-circuit current of the section rather than its maximum-power current, categorize each element of the path as harness wire, connector pin or slip-ring contact, derate the catalogue rating of that element for conductor temperature against insulation rating, for bundle size and for vacuum operation, reduce a paralleled slip-ring set for imperfect current sharing and for the loss of one contact where redundancy is demanded, then report the current margin of every element and name the weakest link. Trigger: ecss, e-st-20-electrical-scope, solar-array-drive, slip-ring-contact-rating, connector-pin-current-rating, harness-wire-derating, short-circuit-current-sizing, current-sharing-imbalance, power-path-current-capability."
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
  tags: [ecss, e-st-20-electrical-scope, e20-solar-array-drive-current-capability, solar-array-drive, slip-ring-contact-rating, connector-pin-current-rating, harness-wire-derating, short-circuit-current-sizing, current-sharing-imbalance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Solar Array Drive Current Capability (space-systems/ecss/e20-solar-array-drive-current-capability)

Use when the task is the current-capability check of ECSS-E-ST-20C
clause 5.5.4 -- showing that the wires, connector pins and slip-ring
contacts between a solar array section and the power bus are each
rated above what that section can actually push through them.

## Domain quick reference

- The applied current is not the maximum-power current. A section held
  off its maximum-power point, or shorted by a regulator that is
  shunting, delivers its short-circuit current, and that current rises
  with cell temperature and with incident intensity. The worst case is
  therefore the hot, minimum-solar-distance, normal-incidence
  short-circuit current of the section, multiplied by the number of
  parallel strings feeding the element. Using the maximum-power
  current understates the applied load by roughly the fill-factor
  current ratio for the whole check.
- Three element families sit in the path and derate differently.
  A harness wire starts from a gauge-based catalogue rating.
  A connector pin starts from a per-contact rating in its qualification
  data. A slip-ring contact starts from a per-contact rating that is
  then multiplied by the number of parallel contacts allocated to that
  circuit -- and paralleling is where the sharing assumption bites.
- Wire and pin derating has three multiplicative terms: bundle
  derating, because conductors in a loom heat each other and only the
  outer ones see free convection-free radiation; temperature derating
  against the insulation rating, which collapses as the conductor
  temperature approaches that rating; and a vacuum derating, because
  the only heat path left is conduction and radiation.
- Parallel slip-ring contacts do not share current equally.
  Contact-resistance spread, brush wear and track eccentricity push
  more current into some contacts than others, so the set capability
  is the per-contact rating times the contact count times a sharing
  factor below one. Where the circuit is required to survive a lost
  contact, the count used is one less than the installed count.
- The verdict on each element is a current margin: derated capability
  divided by applied current, minus one, compared against the project
  current-margin requirement. The path is only compliant when every
  element clears it; the weakest element is reported by name so the
  redesign has a target.

## Workflow

1. Compute the applied current: section short-circuit current at the
   reference condition, scaled by the intensity ratio (inverse square
   of minimum solar distance times cosine of incidence) and by the
   positive short-circuit temperature coefficient at the maximum
   operating temperature, times the parallel string count.
2. Categorize each element of the path as harness wire, connector pin
   or slip-ring contact. Reject an element whose family is not one of
   those three rather than guessing a derating rule.
3. Resolve the base rating: gauge lookup for a wire, declared
   per-contact rating for a pin, declared per-contact rating times the
   usable contact count for a slip-ring set.
4. Apply the derating terms. Bundle derating from the conductor count
   in the loom; temperature derating from conductor temperature
   against insulation rating, rejecting a conductor already at or
   above its insulation rating; vacuum derating where the element
   operates outside atmosphere.
5. For a slip-ring set apply the sharing factor and, where redundancy
   is required, drop one contact from the count. Reject a set that
   falls below one usable contact.
6. Compute each element's margin against the applied current, grade it
   against the required margin, then report the full table, the
   weakest element and whether the path is compliant.

## Pitfalls

- Rating the path on the maximum-power current. The element has to
  survive the shunted or short-circuit condition, which is the larger
  current, and a regulator that shunts routinely puts the array there.
- Taking the cold case as the current worst case. Cold is the worst
  case for string voltage; short-circuit current rises with
  temperature, so the hot case drives the conductor sizing.
- Multiplying the per-contact slip-ring rating straight by the contact
  count. Perfect sharing is never achieved, and the margin computed
  that way evaporates on the first contact that takes more than its
  share.
- Applying bundle derating to the slip ring. Its limit is contact
  resistance and heat removal at the interface, not loom self-heating;
  mixing the two derating chains double-counts on one element and
  under-counts on another.
- Reporting a pass because the path total looks generous. The check is
  per element and the weakest one governs; an average across the path
  hides a single undersized pin.

## Behavior contract (gate 3)

The applied-current, element-categorization, wire-gauge lookup,
bundle/temperature/vacuum derating, slip-ring sharing and per-element
margin logic is exercised by the gate 3 contract test:
scripts/test_e20_solar_array_drive_current_capability.py against
scripts/e20_solar_array_drive_current_capability_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_solar_array_drive_current_capability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
