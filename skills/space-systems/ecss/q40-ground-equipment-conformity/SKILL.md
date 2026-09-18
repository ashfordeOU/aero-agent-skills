---
name: q40-ground-equipment-conformity
description: "Produce the declaration of conformity for a piece of ground equipment under ECSS-Q-ST-40C: screen the item against the EU instruments its own properties pull in — a powered moving assembly, a vessel above the pressure-volume product, a supply inside the low-voltage band, emitting electronics, an explosive-atmosphere zone, a lifting accessory — then settle the assessment route, say whether the conformity mark is carried at all, and list what is still missing before anyone signs. Use when ground support equipment is being released. Trigger: ecss, q-st-40c, ground-equipment-declaration-of-conformity, ce-marking-applicability, pressure-volume-product-screening, notified-body-route, ground-equipment-technical-file."
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
  tags: [ecss, q-st-40c-safety, q-st-40c, q40-ground-equipment-conformity, ground-equipment-declaration-of-conformity, ce-marking-applicability, pressure-volume-product-screening, notified-body-route, ground-equipment-technical-file]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety — Ground Equipment Conformity (space-systems/ecss/q40-ground-equipment-conformity)

Use when the task is the ground-equipment clause of ECSS-Q-ST-40C and its annex
on EU legislation: a trolley, bench, lifting frame or pressurised rig is about
to be released for use and somebody has to say what it falls under, how it is
assessed, and whether a declaration can actually be signed.

## Domain quick reference

- The instruments attach to what the item does, not to what it is called. A
  "test bench" is not a category; a power-driven moving assembly, a vessel over
  the pressure-volume product and a mains-fed enclosure each are, and one item
  is commonly all three at once.
- The pressure route turns on pressure times volume, not on pressure. A small
  high-pressure bottle and a large low-pressure tank sit on opposite sides of
  the same bound, which is why the product is the thing to compute.
- Below the product bound the item is not exempt, it falls to sound
  engineering practice. That is a real route with real duties and no mark under
  that instrument, so marking it anyway is as wrong as leaving it unassessed.
- Below the minimum gauge pressure the pressure screen does not run at all,
  which is different again from falling to sound engineering practice.
- The low-voltage bands are different for alternating and direct supply, and an
  item can be inside one and outside the other. Screen both.
- The assessment route is a schedule fact. A notified body has a queue, and
  discovering the route at the release review is discovering it too late.
- A declaration asserts things. Each one has to exist before the signature: an
  identified item, a named responsible entity, a technical file, the list of
  instruments, and either the standards applied or the third-party certificate.

## Workflow

1. Validate the item: identity, the physical and electrical properties, the
   explosive-atmosphere zone from the known set, and the declaration inputs.
2. Screen for machinery from the powered moving assembly and the annex flag.
3. Run the pressure screen in two steps: the minimum gauge pressure first,
   then the pressure-volume product against its bound with a tolerance, so an
   item sitting exactly on the bound grades the same everywhere.
4. Screen both supply bands, the electronics flag and the zone.
5. Decide the route: a notified body for the annex machinery, for pressure
   equipment above the product bound, and for the tighter explosive zones;
   otherwise self-assessment.
6. Decide whether the mark is carried, remembering that the sound-engineering
   route contributes no mark on its own.
7. List the blockers: unnamed responsible entity, no technical file, a
   third-party route with no certificate, a self-declared route with no
   standards listed, or an item under no instrument at all.
8. Close: issuable when nothing blocks, otherwise blocked with the reasons, and
   roll a set of items up with the third-party ones called out.

## Pitfalls

- Screening by the item's name. Nothing in the instruments keys off what the
  drawing calls it.
- Comparing pressure alone against the pressure bound. The bound is on the
  product, and a five-litre bottle and a five-hundred-litre tank land on
  different sides of it at the same pressure.
- Treating the sound-engineering route as an exemption and marking the item
  anyway, or as a mark and skipping the duties.
- Screening the alternating band only and missing a direct-supply item inside
  its own, different band.
- Comparing a computed product with a bare inequality. The product is a float
  multiplication and an item that should sit on the bound can land under it.
- Leaving the route to the release review, when the third-party queue is the
  long pole.
- Signing a declaration whose technical file is "in preparation". The
  declaration asserts the file exists on the day it is signed.

## Behavior contract (gate 3)

The item validation, the machinery, pressure, voltage, electronics, zone and
lifting screens, the pressure-volume product with its tolerance, the
notified-body route rules, the marking decision including the sound-engineering
case, the declaration blockers and the issuable / blocked disposition plus the
set rollup are exercised by the gate 3 contract test:
scripts/test_q40_ground_equipment_conformity.py against
scripts/q40_ground_equipment_conformity_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q40_ground_equipment_conformity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml. EU instrument bounds are restated for
  screening only and are not legal advice.
- compliance: STANDARDS-REF, gated: false.
