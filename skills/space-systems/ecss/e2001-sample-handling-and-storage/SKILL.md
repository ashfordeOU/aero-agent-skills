---
name: e2001-sample-handling-and-storage
description: "Use when audit the custody of a secondary-electron-emission-yield coupon against the product-assurance rules invoked by ECSS-E-ST-20-01C clause 9.4.1.1, before its yield-measurement run: check the container type and the storage environment (purge-gas, relative-humidity, temperature band), accumulate weighted ambient-air exposure across preparation, handling and transit events, audit every handling step for glove-type, tool-material and electrostatic-discharge control, review the transport leg for seal integrity, shock monitoring and transit duration, and rule the coupon admissible, in need of re-cleaning, or withdrawn. Trigger: ecss, e-st-20-01c, emission-yield-coupon, sample-custody-record, storage-environment, ambient-air-exposure, contamination-control, coupon-handling-audit."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-sample-handling-and-storage, emission-yield-coupon, sample-custody-record, storage-environment, ambient-air-exposure, contamination-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Emission-Yield Sample Handling and Storage (space-systems/ecss/e2001-sample-handling-and-storage)

Use when the task is the clause 9.4.1.1 custody check of ECSS-E-ST-20-01C:
proving that an emission-yield coupon was contained, stored, handled and
transported to the product-assurance rules the standard invokes, so the
yield curve measured from it describes the flight surface rather than what
the coupon picked up on the way to the bench.

## Domain quick reference

- The measured yield belongs to the outermost few atomic layers. Adsorbed
  water, hydrocarbons from a bare fingertip, or a thin oxide grown in humid
  air raise the yield of a technical surface well above its cleaned value,
  and the whole multipaction assessment then rests on a surface nobody will
  ever fly. Custody control is therefore part of the measurement, not
  paperwork around it.
- Containment is graded. A vacuum-desiccator or a purge-gas container keeps
  ambient air off the surface; a sealed double-bag slows it; a vented
  transit case does not stop it at all and only ever suits a short,
  monitored leg. Each container carries its own storage-life limit, and a
  coupon held past that limit is treated as re-clean, not as compliant.
- Exposure is cumulative and weighted, not a single reading. Time in a
  vacuum-chamber or under purge-gas costs nothing; time in cleanroom air
  costs its own duration; time in uncontrolled air costs a multiple of it.
  The weighted total across preparation, handling and transit events is
  what gets compared against the allowance, so ten short uncontrolled
  exposures fail where one long cleanroom exposure passes.
- Handling and transport add their own defects: a bare-hand contact or an
  unapproved tool material contaminates the surface directly, missing
  electrostatic-discharge control risks a dielectric coupon, a broken seal
  voids the containment argument, and an over-long or unmonitored transit
  leg leaves a gap in the custody chain that cannot be closed after the
  fact.
- The verdict is three-valued. Admissible, re-cleaning-required (the
  surface can be recovered by repeating the qualified cleaning route, then
  re-entering custody), or withdrawn (the custody chain is broken or the
  contact is unrecoverable, so this coupon cannot support a yield curve).

## Workflow

1. Validate the coupon record: identifier, material, the date its surface
   was prepared, the cleanliness level it was released at, and the
   container it entered. Reject an unrecognised container type rather than
   scoring it as the safest one.
2. Check the storage environment against the container: purge-gas where the
   container needs it, relative-humidity inside the allowance, temperature
   inside the band, and storage duration inside the container's own
   storage-life limit.
3. Accumulate weighted ambient-air exposure over every custody event, using
   the per-environment weighting, and compare the total against the
   allowance. Refuse a negative duration or an unrecognised environment
   instead of scoring it as zero.
4. Audit each handling step: approved glove-type, approved tool-material,
   and electrostatic-discharge control where the coupon is a dielectric.
   Bare-hand or unapproved-tool contact is a direct-contact defect.
5. Review the transport leg: seal intact on arrival, transit duration
   inside the limit, shock monitoring present where the container relies on
   it.
6. Aggregate. Any withdraw-level defect withdraws the coupon; otherwise any
   re-clean-level defect demands re-cleaning and re-entry into custody;
   otherwise the coupon is admissible, and the report carries the weighted
   exposure and the storage age that back the verdict.

## Pitfalls

- Adding raw hours and comparing them against the allowance. Unweighted
  hours make an uncontrolled-air exposure look the same as a purge-gas one;
  the weighting is the whole point of the accumulation.
- Reading an intact seal as proof of a clean surface. The seal covers the
  transit leg only; preparation and handling exposure happened before the
  container closed and still counts.
- Withdrawing a coupon for a defect that re-cleaning recovers. Humidity
  drift or an aged-out storage period is a re-clean, and burning a limited
  coupon set on recoverable defects starves the curve set the worst-case
  envelope is built from.
- Treating a weighted exposure that lands a hair over the allowance through
  floating-point summation as an exceedance. The comparison absorbs
  representation error; the allowance itself is never widened.
- Recording the verdict without the exposure total and storage age. A later
  reviewer cannot re-derive an admissibility call from the word alone.

## Behavior contract (gate 3)

The container, storage-environment, weighted-exposure, handling-step,
transport and verdict logic is exercised by the gate 3 contract test:
scripts/test_e2001_sample_handling_and_storage.py against
scripts/e2001_sample_handling_and_storage_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_sample_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
