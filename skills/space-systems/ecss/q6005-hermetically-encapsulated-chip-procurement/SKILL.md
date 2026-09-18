---
name: q6005-hermetically-encapsulated-chip-procurement
description: "Assess the purchasing provisions for active chips delivered already sealed inside their own hermetic enclosure. Use when a pre-sealed chip specification and its delivery evidence have to be graded together: confirm each mandatory provision is declared rather than blank or written as a placeholder, derive the fine-leak reject limit the sealed cavity volume earns from the band schedule, hold the measured equivalent standard leak rate against it at the exact boundary, refuse a fine-leak reading behind a failed gross-leak test, hold internal moisture against its ceiling, and clear the purchase only when no finding remains. Trigger: ecss, q-st-60-05, hermetically-encapsulated-chip-procurement, sealed-cavity-volume-band, fine-leak-reject-limit, equivalent-standard-leak-rate, gross-leak-outcome, internal-moisture-ppmv, hermetic-provision-completeness."
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
  tags: [ecss, q-st-60-electronic-components-scope, q6005-hermetically-encapsulated-chip-procurement, sealed-cavity-volume-band, fine-leak-reject-limit, equivalent-standard-leak-rate, gross-leak-outcome, internal-moisture-ppmv, hermetic-provision-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Generic Procurement of Active Chips — Hermetically Encapsulated Chip Procurement (space-systems/ecss/q6005-hermetically-encapsulated-chip-procurement)

Use when the task is the procurement provision set of ECSS-Q-ST-60-05
clause 8.4 -- buying chips that arrive already sealed within their own
hermetic enclosure, where the buyer never sees the die and everything
that can still be known about it has to be bought explicitly.

## Domain quick reference

- A pre-sealed chip is bought, not inspected. Once the lid is on, the
  die is beyond visual examination, so every attribute the programme
  will later need has to appear as a purchasing provision: seal method,
  sealed cavity volume, the gross and fine leak methods, the internal
  moisture ceiling, lot and date-code traceability, screening level and
  the storage and handling regime.
- A provision left blank is unknown, not satisfied. "TBD", "n/a" and an
  empty field are absences and are reported as such; a declared value of
  zero, by contrast, is a real declaration and is treated as one.
- The fine-leak reject limit is earned by the sealed cavity volume, not
  chosen. A larger cavity dilutes the same physical leak, so its limit
  is looser, and the limit comes from a volume-banded schedule. A
  package whose cavity volume was never declared has no limit at all,
  and its leak reading cannot be graded.
- Because a reject limit and a measured rate are both floats, a reading
  that sits exactly on its limit can evaluate a few ULPs high. The
  comparison absorbs that representation error; the limit itself is
  never relaxed.
- Gross leak comes first, and it has precedence. A package with a gross
  leak equalizes with the chamber and gives back a small, healthy
  looking fine-leak number. Crediting that reading turns the worst seal
  in the batch into the best one on paper.
- Internal moisture is graded against the ceiling written into the
  specification, and an unreported moisture value is a finding rather
  than a pass -- moisture inside a sealed cavity is what drives
  corrosion once the part is powered.

## Workflow

1. Group every mandatory provision in the purchase specification as
   declared or missing, treating placeholder tokens and empty fields as
   missing and a declared zero as declared.
2. Normalize the delivered seal evidence: the gross-leak outcome as a
   boolean, the measured equivalent standard leak rate and the reported
   internal moisture. Reject a non-boolean gross-leak outcome and a
   missing or negative leak rate.
3. Derive the fine-leak reject limit from the declared sealed cavity
   volume using the band schedule. With no declared volume, record that
   the leak reading cannot be graded and stop grading it.
4. Apply the gross-leak precedence rule: where gross leak failed, the
   fine-leak reading is not credited whatever its value.
5. Otherwise hold the measured rate against the band limit under the
   boundary tolerance and report the margin.
6. Hold the reported internal moisture against the specification's
   ceiling, and raise an unreported value as its own finding.
7. Clear the procurement only when no provision is missing, the
   gross-leak test passed, the fine-leak rate is within its band limit
   and moisture is within its ceiling.

## Pitfalls

- Buying a sealed chip on a datasheet and assuming the seal attributes
  come with it -- what is not written into the purchase provisions
  cannot be demanded at delivery, and the die is no longer visible.
- Reading an empty provision field as an acceptable default -- an
  undeclared moisture ceiling or screening level is unknown, and
  rendering it as zero or as "standard" invents a requirement nobody
  agreed.
- Applying one fine-leak limit across a mixed package set -- a small
  cavity earns a much tighter limit than a large one, and a shared
  limit either passes a leaking small package or fails a sound large
  one.
- Crediting a beautiful fine-leak number behind a failed gross-leak
  test -- a grossly leaking cavity has already equalized and cannot
  hold tracer gas, so the small reading is the symptom, not the result.
- Relaxing the band limit because a reading lands exactly on it -- the
  excess is float representation error and belongs in the comparison
  tolerance, not in the limit.
- Accepting a delivery with no moisture figure because the seal tests
  passed -- leak tightness says nothing about what was sealed inside
  the cavity at lid closure.

## Behavior contract (gate 3)

The declaration testing, provision coverage, cavity-volume band
schedule, boundary tolerance, gross-leak precedence, moisture ceiling
and combined assessment logic is exercised by the gate 3 contract test:
scripts/test_q6005_hermetically_encapsulated_chip_procurement.py against
scripts/q6005_hermetically_encapsulated_chip_procurement_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6005_hermetically_encapsulated_chip_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
