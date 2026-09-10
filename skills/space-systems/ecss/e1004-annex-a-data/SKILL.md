---
name: e1004-annex-a-data
description: "Use when assembling the natural electromagnetic radiation and solar/geomagnetic index reference dataset from ECSS-E-ST-10-04C Annex A for a mission design case: determine which quantities (TSI, EUV/XUV band irradiance, Earth albedo, Earth IR emission, F10.7, F10.7A, geomagnetic index) apply, verify each quantity's solar-cycle phase tagging and that phase-dependent values ordered minimum/mean/maximum, and flag missing quantities, missing phases, or phase-tagging errors before the dataset feeds e1004-em-radiation or e1004-indices. Trigger: Annex A, natural EM radiation data, solar/geomagnetic indices, F10.7, F10.7A, Ap, Kp, TSI, solar constant, solar-cycle reference values, Earth albedo, Earth IR emission, e-st-10-04, ecss."
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
  tags: [ecss, e-st-10-04c, annex-a, em-radiation, solar-indices, reference-data, space-systems]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Annex A Natural EM Radiation & Indices Reference Data (space-systems/ecss/e1004-annex-a-data)

Use when the task is assembling or checking the natural electromagnetic
radiation and solar/geomagnetic activity index reference dataset
defined in ECSS-E-ST-10-04C Annex A (normative): the source table that
downstream clauses and leaves draw solar-cycle reference values from
instead of picking numbers ad hoc.

## Domain quick reference

- Annex A is the normative reference-data annex backing clause §6
  (electromagnetic radiation) and clause §6.2.2 (solar/geomagnetic
  activity indices): natural EM radiation quantities (total solar
  irradiance/TSI, EUV/XUV band irradiance, Earth albedo, Earth IR
  emission) and activity index reference values (F10.7, its 81-day-
  smoothed companion F10.7A, and a geomagnetic index such as Ap or Kp)
  tied to solar-cycle phase.
- Two sibling leaves consume this table rather than re-deriving it:
  `e1004-em-radiation` (§6.2, the EM radiation quantities) and
  `e1004-indices` (§6.2.2 + Annex A, the activity index values); any
  downstream analysis that needs a solar-cycle design case (thermal
  hot/cold case, power budget, drag via `e1004-atmosphere`) should
  trace its numbers back to this leaf's dataset, not to an
  independently chosen value.
- Annex A quantities split into two kinds: phase-dependent quantities
  (TSI, EUV/XUV irradiance, F10.7, F10.7A, the geomagnetic index) are
  defined separately per solar-cycle phase (minimum, mean, maximum);
  phase-independent quantities (Earth albedo, Earth IR emission) are
  design constants that vary by orbit/season rather than by solar
  cycle and carry no phase tag.
- A usable dataset entry for a quantity needs a numeric value, a
  citation back to Annex A, and — for phase-dependent quantities — the
  correct solar-cycle phase label; an entry missing any of these can't
  be checked for consistency or safely handed to a downstream leaf.
- Across the three solar-cycle phases, F10.7, F10.7A, the geomagnetic
  index, TSI, and EUV/XUV irradiance must all be monotonically
  non-decreasing from minimum to mean to maximum (higher solar
  activity drives higher radio flux, higher geomagnetic disturbance,
  and higher irradiance); a violation signals a mis-transcribed or
  swapped value.

## Workflow

1. Identify which quantities the current design case needs — the full
   EM-radiation set, the full index set, or both — and which
   solar-cycle phase(s) are required (a single phase for a nominal
   case, minimum+maximum for an envelope/hot-case-cold-case study).
2. For each required quantity, record its value, its citation to
   ECSS-E-ST-10-04C Annex A, and — if the quantity is phase-dependent
   — the minimum/mean/maximum phase label it belongs to; tag
   phase-independent quantities (Earth albedo, Earth IR emission) with
   no solar-cycle phase.
3. Check the assembled dataset against the required-quantity list;
   any quantity absent from the dataset is a missing quantity.
4. For each present quantity, check that every entry has a value and a
   citation, and that phase-dependent quantities only use the
   minimum/mean/maximum labels while phase-independent quantities only
   use the phase-independent label — a mismatch here is a
   phase-tagging error.
5. Where a phase-dependent quantity supplies two or more phases, check
   that its values are ordered minimum ≤ mean ≤ maximum; treat a
   decrease across phases as an ordering violation to be resolved
   before use.
6. Only mark the dataset complete once every required quantity is
   present, every entry passes its value/citation/phase-tagging check,
   and every multi-phase quantity passes its ordering check; otherwise
   report the specific missing quantities, missing phases, or
   violations so `e1004-em-radiation` and `e1004-indices` are not fed
   bad reference data.

## Pitfalls

- Treating an Annex A value as a single fixed constant instead of a
  solar-cycle-phase-dependent value, so a solar-minimum F10.7 or TSI
  value gets reused in a solar-maximum worst-case analysis.
- Recording a phase-dependent value without its solar-cycle phase
  label, which makes the minimum/mean/maximum ordering check
  impossible to run later.
- Tagging Earth albedo or Earth IR emission with a solar-cycle phase
  when Annex A ties them to orbit/season instead, which creates a
  spurious ordering expectation that doesn't apply to those
  quantities.
- Supplying only the mean-phase value when the actual design case
  needs an envelope (e.g. a thermal hot-case/cold-case study needs
  minimum and maximum, not just mean).
- Conflating F10.7 (instantaneous/daily) with F10.7A (81-day-smoothed)
  as if they were the same index — they are distinct quantities feeding
  different downstream models.

## Behavior contract (gate 3)

The quantity classification, entry validation, phase-tagging check,
and multi-phase ordering logic is exercised by the gate 3 contract
test: scripts/test_e1004_annex_a_data.py against
scripts/e1004_annex_a_data_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_annex_a_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
