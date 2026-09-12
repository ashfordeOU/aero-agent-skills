---
name: copv-nonmetallic-liner-and-cpv
description: "Use when assess a composite overwrapped pressure vessel (COPV) with a homogeneous non-metallic liner, or an all-composite pressure vessel (CPV), under ECSS-E-ST-32C clause 4.3.4: categorize the vessel configuration, compute the sustained stress ratio (SSR) for each operating phase, accumulate composite-fiber stress rupture damage via a power-law model and verify the Miner-rule analogue damage sum against the allowable limit, check non-metallic liner hoop stress against the liner allowable, and verify damage tolerance (VDT) by confirming that the projected end-of-life flaw size remains below the critical flaw size established by fracture analysis. Trigger: ecss, e-st-32-structures-scope, copv, cpv, stress-rupture, vdt, composite-pressure-vessel, nonmetallic-liner, damage-tolerance."
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
  tags: [ecss, e-st-32-structures-scope, copv, cpv, stress-rupture, vdt, composite-pressure-vessel, nonmetallic-liner, damage-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COPV Non-Metallic Liner and All-Composite CPV (space-systems/ecss/copv-nonmetallic-liner-and-cpv)

Use when the task is the structural compliance assessment of a COPV
(composite overwrapped pressure vessel) with a homogeneous non-metallic
liner, or an all-composite CPV (composite pressure vessel), under
ECSS-E-ST-32C clause 4.3.4 -- categorizing the vessel configuration,
verifying composite-fiber stress rupture life under sustained load, checking
non-metallic liner hoop stress for a COPV, and confirming damage tolerance
(VDT) with end-of-life flaw size below the fracture-derived critical value.

## Domain quick reference

- Clause 4.3.4 covers two vessel families: COPVs with a homogeneous
  non-metallic liner (the composite overwrap carries primary load, the liner
  provides the pressure boundary) and CPVs that are all-composite with no
  distinct metallic or non-metallic liner. Each vessel is categorized into
  exactly one family before the specific checks are applied.
- Stress rupture governs composite overwrap integrity under sustained
  pressurization. The composite fibers carry a fraction of their mean
  strength (the sustained stress ratio, SSR); at any SSR below 1.0 the
  fibers still fail eventually by stress rupture following a power-law
  relationship between SSR and time-to-rupture. Operating phases with
  different SSR values contribute damage additively (Miner-rule analogue),
  and the summed damage must not exceed the allowable limit (typically 1.0).
- For a COPV, the non-metallic liner carries a thin-wall hoop stress under
  internal pressure. The liner hoop stress (pressure × radius / (2 ×
  thickness)) must remain within the liner-material allowable set by the
  material qualification; an unset allowable is itself a finding.
- Verification by Damage Tolerance (VDT) requires that any initial flaw
  present in the vessel at the start of service -- bounded from below by the
  NDT detection threshold -- does not grow to the critical flaw size
  (derived from fracture analysis) within the service life. A linear
  flaw-growth model per pressurization cycle is used to project the
  end-of-life flaw size, and the critical-size margin must be positive.

## Workflow

1. Categorize the vessel: a vessel with a homogeneous non-metallic liner is
   a COPV; a vessel with no distinct liner made entirely of composite
   material is a CPV. Reject any liner type outside these two families
   before proceeding.
2. For stress rupture, collect all operating phases (sustained-pressure hold
   periods). For each phase compute the SSR (operating fiber stress /
   mean fiber strength) and apply the power-law model to obtain the
   time-to-rupture for that SSR. Divide the phase duration by its
   time-to-rupture to obtain the phase damage fraction, then sum all
   fractions. Flag a violation when the total damage exceeds the allowable
   (default 1.0).
3. For a COPV, compute the liner hoop stress from the thin-wall formula
   (pressure × vessel inner radius / (2 × liner wall thickness)). Compare
   against the liner allowable; flag an exceedance, and separately flag when
   no allowable has been established for the liner material.
4. For VDT, confirm that the assumed initial flaw size is at least as large
   as the NDT detection threshold (a smaller value would be non-conservative).
   Project the end-of-life flaw size using the linear growth model:
   initial_flaw + growth_rate × service_cycles. Flag a violation when the
   projected size reaches or exceeds the critical flaw size from fracture
   analysis; record the margin as (critical − final) / critical.
5. Aggregate findings: the vessel is fully compliant only when stress
   rupture, liner integrity (COPV only), and VDT all report no violations.

## Pitfalls

- Applying a metallic-liner pressure-vessel workflow to a non-metallic
  liner -- the liner allowable and hoop-stress check differ materially from
  metallic liner burst and yield criteria; skipping the separate liner
  integrity step leaves the liner unverified.
- Conflating the stress rupture damage sum with a simple stress-strength
  check -- stress rupture is a time-dependent phenomenon; a fiber at 60 %
  SSR will eventually rupture, and the damage accumulation must cover every
  sustained-load phase including ground-hold and on-orbit operational dwell.
- Using an initial flaw size smaller than the NDT threshold for the VDT
  assessment -- doing so claims detectability of flaws that the inspection
  method cannot resolve, making the VDT non-conservative; the initial
  flaw must be bounded by what the chosen NDT method can actually detect.
- Omitting the VDT step for a CPV because no liner is present -- clause 4.3.4
  requires VDT for both COPVs and CPVs; the absence of a metallic or
  non-metallic liner does not remove the VDT obligation.

## Behavior contract (gate 3)

The vessel categorization, stress rupture accumulation, liner hoop stress,
liner integrity violation flagging, VDT flaw-growth projection, and full
vessel review logic are exercised by the gate 3 contract test:
scripts/test_copv_nonmetallic_liner_and_cpv.py against
scripts/copv_nonmetallic_liner_and_cpv_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_copv_nonmetallic_liner_and_cpv.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
