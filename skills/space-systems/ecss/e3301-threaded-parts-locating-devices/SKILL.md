---
name: e3301-threaded-parts-locating-devices
description: "Evaluate a threaded joint and its locating devices against ECSS-E-ST-33-01C clause 4.7.5.4.10. Use when a mechanism fastener must be shown to use a stress-corrosion-resistant material, a controlled tightening method and a positive locking feature: screening the material category against the expected one, subtracting prevailing torque before any preload is derived, widening the preload band by wrench tolerance and nut-factor spread, taking embedment and thermal relaxation off the minimum, and returning gapping, slip and fastener-yield margins. Trigger: ecss, e-st-33-01-mechanisms-scope, fastener-stress-corrosion-category, controlled-tightening-preload-band, prevailing-torque-exclusion, positive-locking-feature, joint-gapping-margin, fastener-preload-relaxation."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-threaded-parts-locating-devices, fastener-stress-corrosion-category, controlled-tightening-preload-band, prevailing-torque-exclusion, positive-locking-feature, joint-gapping-margin, fastener-preload-relaxation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Threaded Parts and Locating Devices (space-systems/ecss/e3301-threaded-parts-locating-devices)

Use when the task is the threaded-part case of ECSS-E-ST-33-01C clause
4.7.5.4.10 -- showing that the fasteners and locating devices of a
mechanism are made of a material that resists stress-corrosion
cracking, are tightened by a controlled method to a preload that is
actually known, and cannot back off in service.

## Domain quick reference

- The material screen is a category question, not a strength question.
  A high-strength martensitic steel or a peak-aged aluminium can be
  stronger than the alternative and still sit in a stress-corrosion
  category the clause does not accept. A lower category is retained only
  against a justification that is on record, and the retention is
  reported as a finding rather than silently passed.
- Prevailing torque stretches nothing. The torque a locking nut or a
  locking insert absorbs never reaches the bolt shank, so it is
  subtracted from the applied torque before any preload is derived.
  Leaving it in inflates the preload, and the inflation lands on exactly
  the margins that depend on the minimum preload.
- Preload from torque is a band, never a number. The wrench tolerance
  widens it symmetrically and the nut-factor spread widens it again --
  and the two edges pair crosswise: the minimum preload comes from the
  low torque with the high nut factor, the maximum from the high torque
  with the low nut factor.
- The two edges of that band are used for different checks. Gapping and
  slip are minimum-preload problems; fastener yield is a maximum-preload
  problem. A single nominal preload cannot answer both.
- Preload decays. Embedment of the bedding surfaces takes its share in
  the first hours and thermal relaxation takes more across the mission,
  so the residual preload -- not the installed preload -- is what the
  joint flies with.
- Gapping is governed by the joint stiffness ratio: only a fraction of
  the external tensile load reaches the bolt, and the rest unloads the
  clamped interface, so the separation load is the residual preload
  divided by one minus that ratio.
- A locking feature is either positive or it is decoration. A conical
  spring washer is a preload-maintaining device, not a locking device,
  and the distinction is the whole point of the clause.

## Workflow

1. Look up the fastener material and compare its stress-corrosion
   category with the expected one; where it falls short, accept it only
   with a recorded justification and report that acceptance.
2. Look up the locking feature, take its prevailing torque as the
   default, and confirm that it is a positive locking device.
3. Compute the tensile stress area of the thread from its nominal
   diameter and pitch.
4. Subtract the prevailing torque from both edges of the
   tolerance-widened applied torque and convert each through the
   matching edge of the nut-factor band to get the minimum and maximum
   installed preload.
5. Take embedment and thermal relaxation off the minimum preload and
   carry the residual into the gapping and slip checks.
6. Compute the gapping margin through the stiffness ratio, the slip
   margin over the declared friction interfaces, and the yield margin at
   the maximum preload plus the bolt's share of the factored external
   load; absorb representation error at zero margin with a named
   tolerance rather than by relaxing a load factor.
7. Return every margin and the finding list, so a reviewer sees which
   check governs and whether the material was retained on justification.

## Pitfalls

- Deriving preload from the full applied torque on a prevailing-torque
  fastener. The locking torque never becomes clamp force, and the error
  is largest on the small fasteners where the prevailing torque is the
  biggest fraction of the total.
- Pairing the band edges the intuitive way. Minimum preload comes from
  the low torque with the HIGH nut factor; taking low with low gives a
  minimum that is not a minimum.
- Running every margin off one nominal preload. Yield needs the maximum
  and gapping needs the minimum; a nominal value passes both checks that
  the real band fails.
- Forgetting relaxation because the joint was torqued to a measured
  preload. Measurement fixes the installed value, not the decay, and the
  residual is still what the mission sees.
- Accepting a spring washer, a nylon patch on a reused fastener, or an
  adhesive applied outside its cure window as positive locking. The
  feature has to be one the clause allows and has to still be effective
  at the point it is credited.
- Selecting on ultimate strength and assuming the corrosion category
  follows. The strongest candidate in a family is frequently the one
  with the worst stress-corrosion behaviour.

## Behavior contract (gate 3)

The material category screen and its justification path, locking-feature
lookup, thread stress area, prevailing-torque subtraction, crosswise
preload band, embedment and relaxation losses, and the gapping, slip and
yield margins are exercised by the gate 3 contract test:
scripts/test_e3301_threaded_parts_locating_devices.py against
scripts/e3301_threaded_parts_locating_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_threaded_parts_locating_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
