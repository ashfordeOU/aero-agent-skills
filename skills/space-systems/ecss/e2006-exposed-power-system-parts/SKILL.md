---
name: e2006-exposed-power-system-parts
description: "Use when determine which arcing provisions extend to the exposed elements of the power-chain beyond the solar-array under ECSS-E-ST-20-06C clause 7.3: categorize each element as drive-mechanism, rotary-transfer, conductor-run or conditioning-unit, compute the largest conductor-to-conductor differential it presents and its most negative exposed potential relative to the ambient plasma, derive the arcing regime from those two against the primary-arc-inception and sustained-arc thresholds, expand the family baseline into the provision set that regime demands, check the recorded provisions and the bonding-resistance of every element against it, and aggregate the shortfall into a per-element verdict. Trigger: ecss, e-st-20-06c, exposed-power-chain-element, solar-array-drive-mechanism, slip-ring-assembly, primary-arc-inception, sustained-arc-differential, bonding-resistance, arcing-provision-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-exposed-power-system-parts, e-st-20-06c, exposed-power-chain-element, solar-array-drive-mechanism, slip-ring-assembly, primary-arc-inception, sustained-arc-differential, bonding-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Exposed Power-Chain Elements (space-systems/ecss/e2006-exposed-power-system-parts)

Use when the task is the clause 7.3 extension of ECSS-E-ST-20-06C: the
arcing provisions written for the solar-array itself also bind every other
exposed element that carries the generated current — drive mechanisms,
rotary-transfer assemblies, exposed harness runs and the exposed faces of
conditioning units — and the question is which provisions each of those
elements has to carry and whether it does.

## Domain quick reference

- Every exposed element is categorized into exactly one of four provision
  families before anything is required of it: drive-mechanism (array drive,
  gimbal drive, deployment hinge, articulation joint), rotary-transfer
  (slip-ring assembly, twist capsule, rotary transformer), conductor-run
  (exposed harness, connector backshell, bus-bar, string interconnect) and
  conditioning-unit (unit chassis, shunt radiator, junction box). An
  element kind that matches none of them is a gap in the inventory and is
  rejected, never waved through as benign.
- Two independent figures drive the requirement. The conductor-to-conductor
  differential is the span between the most positive and most negative
  exposed conductor of that element, referred to spacecraft ground; it
  decides whether the generated current can feed a discharge once one has
  struck. The plasma-relative potential is the most negative exposed
  conductor after adding the floating potential of spacecraft ground; it
  decides whether a trigger arc can strike at all.
- The arcing regime follows from those two. An element shielded from the
  ambient plasma stays below the arcing thresholds whatever differential it
  carries. A plasma-exposed element whose most negative exposed potential
  reaches the inception magnitude is at primary-arc risk. If it also
  carries a differential at or above the sustaining value, it is at
  sustained-arc risk — the severe case, because the chain itself then feeds
  the discharge.
- Provisions accumulate with the regime on top of the family baseline.
  Every family needs bonding-to-structure and an insulation-barrier;
  rotary-transfer adds track-separation between adjacent tracks;
  primary-arc risk adds primary-arc-mitigation; sustained-arc risk adds
  secondary-arc-evidence and a gap-integrity-inspection.
- Bonding-to-structure is verified by measurement, not by declaration: the
  bonding-resistance of the element has to sit at or under the limit, and a
  reading that is simply absent is itself a finding rather than a pass.

## Workflow

1. Inventory every exposed element of the chain outside the array and
   categorize each one into its provision family. Reject an unrecognized
   element kind rather than dropping it.
2. For each element, compute the largest conductor-to-conductor
   differential from its exposed conductor potentials, and the most
   negative plasma-relative potential by adding the floating potential of
   spacecraft ground to each conductor.
3. Derive the arcing regime: below-arcing-thresholds when the element is
   shielded or its most negative potential never reaches the inception
   magnitude, primary-arc-risk when it does, sustained-arc-risk when the
   differential also reaches the sustaining value.
4. Expand the family baseline with the provisions the regime adds, and
   difference it against the provisions recorded for the element. Every
   provision still missing is a finding.
5. Check the bonding-resistance against the limit; record an absent reading
   as its own finding.
6. Aggregate per element and across the inventory: the chain conforms only
   when no element carries an open finding. Report the regime counts so the
   reviewer sees how much of the chain sits in the sustained-arc case.

## Pitfalls

- Stopping the arcing provisions at the array boundary. The drive
  mechanism and the rotary-transfer assembly sit at the same string
  potential as the array and are just as exposed; clause 7.3 exists
  precisely because that continuation is easy to forget.
- Treating a large differential as sufficient reason to require
  mitigation. Without exposure to the ambient plasma there is no trigger
  arc to sustain, so a shielded element stays on the family baseline.
- Treating exposure alone as sufficient. An exposed element whose most
  negative potential stays shallow cannot strike a trigger arc; loading it
  with sustained-arc provisions buys nothing and dilutes the findings that
  matter.
- Accepting a declared bond. A bonding-to-structure provision listed
  without a measured bonding-resistance is unverified; the absent reading
  is reported as a finding in its own right.
- Comparing an exactly-at-threshold value with a bare float comparison. The
  differential is a difference of potentials and a bond path is a sum of
  series segments, so a compliant value can land a few ULPs on the wrong
  side of the threshold; the logic absorbs that representation error
  without moving any threshold.

## Behavior contract (gate 3)

The family categorization, differential and plasma-relative potential
computation, regime derivation, provision expansion and bonding check are
exercised by the gate 3 contract test:
scripts/test_e2006_exposed_power_system_parts.py against
scripts/e2006_exposed_power_system_parts_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2006_exposed_power_system_parts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
