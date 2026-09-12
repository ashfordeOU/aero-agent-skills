---
name: e1012-shield-sector
description: "Use when run detailed sector shielding calculations for a spacecraft component under ECSS-E-ST-10-12C §6.2.3: discretize the surrounding 4π steradians into directional sectors, ray-trace each direction through the spacecraft mass model to accumulate areal shielding density (g/cm²), apply dose-depth attenuation curves to derive the ionising dose contribution from each sector, and aggregate across all sectors to obtain total TID at the point of interest. Apply a radiation design margin (RDM) to the aggregated dose and compare against the part's qualified dose level to determine compliance. Suitable for shielding trade studies, shielding mass optimisation, and unit-level radiation hardness assurance verification. Trigger: ecss, e-st-10-12c, sector-shielding, ray-tracing, dose-depth, TID, radiation-design-margin, RDM, mass-model, radiation-hardness-assurance."
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
  tags: [ecss, e-st-10-12c, sector-shielding, ray-tracing, dose-depth, TID, radiation-design-margin, RDM, mass-model, radiation-hardness-assurance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Sector Shielding (space-systems/ecss/e1012-shield-sector)

Use when the task is the detailed sector shielding analysis of
ECSS-E-ST-10-12C §6.2.3 — deriving total ionising dose (TID) at a
point of interest by dividing the surrounding solid angle into
directional sectors, tracing rays through a layered mass model to
accumulate areal shielding density, applying dose-depth attenuation
per sector, and aggregating the result before applying a radiation
design margin (RDM) and comparing against the part's qualified dose.

## Domain quick reference

- §6.2.3 extends the simplified shielding approach of §6.2.2 by
  combining a geometric mass model with dose-depth response curves.
  The sector method discretises the sphere of directions around a point
  of interest into N sectors; for each sector a ray is traced through
  the spacecraft structure and the accumulated areal density (g/cm²) is
  used to look up or compute the attenuated dose contribution from that
  direction.
- **Areal shielding density** (g/cm²) is the fundamental shielding
  quantity: it equals the sum of (thickness × density) for every
  material layer a ray crosses. For a slab-modelled face, oblique rays
  at incidence angle θ from the face normal accumulate areal density
  ∑ (ρᵢ × dᵢ) / cos θ, where ρᵢ and dᵢ are the density and thickness
  of each layer i.
- **Dose-depth attenuation** converts the per-sector areal density into
  a TID contribution using a dose-depth curve — a relationship derived
  from radiation transport simulations or standard reference tables for
  the chosen shielding material (typically aluminium) in the relevant
  orbit environment (LEO, GEO, MEO). A simplified engineering
  approximation of the form D(t) = D₀ × (1 + t/λ)^(−α) captures the
  gross shielding effectiveness; λ and α are environment-specific
  scale parameters.
- **Solid-angle weighting**: each sector's dose contribution is scaled
  by its solid-angle fraction of the full sphere (ωₖ / 4π), so the
  aggregate TID equals ∑ Dₖ × (ωₖ / 4π). A complete sector set must
  integrate to 4π sr; a partial set gives an underestimate.
- **Radiation design margin (RDM)**: ECSS-E-ST-10-12C §6.2.3 requires
  the computed TID to be multiplied by an RDM (typically ×2) before
  comparing against the part's qualified dose level. The margin accounts
  for uncertainties in the environment model, mass model, dose-depth
  curve, and lot-to-lot part variability. The design meets the
  requirement only when RDM × TID ≤ qualified dose.

## Workflow

1. Define the point of interest and the surrounding material layers
   that shield it. For each distinct direction class, record the list
   of material slabs (name, thickness in mm, density in g/cm³) a ray
   must traverse. Reject any layer with non-positive density or negative
   thickness before continuing.
2. Generate the sector grid: select N_θ elevation bands and N_φ
   azimuth divisions, producing N_θ × N_φ sectors covering 4π sr with
   equal-area (approximately) bins. Confirm the solid-angle sum equals
   4π sr to within a small numerical tolerance before proceeding; a
   partial grid is invalid.
3. For each sector direction (polar angle θₖ, azimuth φₖ), compute the
   incidence angle on the representative shielding face as
   ι = min(θₖ, 180° − θₖ) for a slab model (zero at face normal,
   approaching 90° at grazing), capped at 85° to avoid numerical
   divergence. Compute the total areal density tₖ = ∑ ρᵢ dᵢ / cos ι.
4. Apply the dose-depth attenuation for the chosen environment (LEO,
   GEO, or MEO) to obtain the local dose estimate Dₖ behind shielding
   tₖ. Scale Dₖ by the sector solid-angle fraction ωₖ / 4π to obtain
   the sector dose contribution.
5. Sum the sector contributions to obtain the total estimated TID at
   the point of interest.
6. Multiply the total TID by the RDM (≥ 1.0; use ×2 unless the project
   has established and approved a different value). Compare the design
   dose (RDM × TID) against the part's qualified dose level. Compute
   the margin in dB as 10 log₁₀(qualified / design); a positive margin
   indicates the design passes.
7. Repeat steps 3–6 for alternative shielding configurations or
   environments as required for trade studies.

## Pitfalls

- Omitting the sector solid-angle normalisation and treating each
  sector's dose as an equal share of the total — sectors at high
  elevation angles subtend smaller solid angles and must be weighted by
  ωₖ / 4π, not 1/N.
- Capping the incidence angle at 90° rather than 85° — at angles very
  close to 90° cos θ approaches zero and the computed areal density
  diverges; cap at 85° (or the value the mass model's geometry
  justifies) and flag the grazing-incidence sectors rather than
  discarding them silently.
- Applying the dose-depth curve for one environment to a different
  orbit — LEO trapped-electron attenuation lengths differ substantially
  from GEO or MEO, and substituting parameters crosses environments
  introduces systematic error in either the conservative or
  non-conservative direction depending on the orbit.
- Reporting the aggregated TID directly against the qualified dose
  without applying the RDM — §6.2.3 requires the design margin factor
  to be applied before the compliance check; omitting it produces an
  optimistic comparison that is not standard-compliant.
- Confusing the sector shielding aggregate with the worst-case sector
  — the aggregate integrates over all directions and may be below the
  worst-case single sector value; the worst-case sector is the relevant
  check when a directional threat (e.g., solar energetic particle event)
  dominates from one direction.

## Behavior contract (gate 3)

The sector generation, ray-tracing, dose-depth attenuation, aggregation,
and RDM budget-check logic is exercised by the gate 3 contract test:
`scripts/test_e1012_shield_sector.py` against
`scripts/e1012_shield_sector_logic.py` (stdlib unittest, offline). Run:

python3 scripts/test_e1012_shield_sector.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
