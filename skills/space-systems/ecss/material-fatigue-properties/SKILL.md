---
name: material-fatigue-properties
description: "Use when determine fatigue properties of space-structure materials under
  ECSS-E-ST-32C clause 4.2.3: verify that the coupon test dataset spans the required
  stress-ratio range and minimum specimen count, apply a scatter factor to convert
  the mean test life to a design fatigue allowable, correct for mean stress using
  the Goodman or Gerber relation, evaluate fatigue life from a log-log S-N curve,
  and confirm that every material record is fully documented with ultimate strength,
  endurance limit, S-N data, and an assigned scatter factor before the data package
  is accepted. Trigger: ecss, e-st-32-structures-scope, material-fatigue,
  fatigue-properties, s-n-curve, scatter-factor, mean-stress-correction,
  endurance-limit, goodman, gerber."
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
  tags: [ecss, e-st-32-structures-scope, material-fatigue, fatigue-properties, s-n-curve, scatter-factor, mean-stress-correction, endurance-limit, goodman, gerber]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Material Fatigue Properties (space-systems/ecss/material-fatigue-properties)

Use when the task is to determine fatigue properties for materials
intended for space-structure use under ECSS-E-ST-32C clause 4.2.3 —
collecting and qualifying coupon S-N data, applying scatter factors,
correcting for mean stress, and confirming every material data record
is complete before the fatigue pack is submitted for design allowables
derivation.

## Domain quick reference

- An S-N dataset maps cyclic stress amplitude to mean cycles to failure.
  For structural metals in space applications the relationship is
  evaluated in log-log space; a minimum number of test coupons is
  required to draw a statistically valid curve. Too few points yield a
  dataset that is provisional rather than qualified.
- A scatter factor is applied to the mean test life to obtain the
  design fatigue allowable: N_design = N_mean / scatter_factor. Typical
  values range from 2 to 4 depending on material pedigree, coupon count,
  and consequence of failure (ECSS-E-ST-32C §4.2.3 guidance). A higher
  scatter factor corresponds to less data or higher consequence.
- Mean stress shifts the fatigue life at a given amplitude. Two common
  correction methods: Goodman (linear) gives
  sigma_a_eq = sigma_a / (1 - sigma_m / sigma_ult) and is conservative;
  Gerber (parabolic) gives
  sigma_a_eq = sigma_a / (1 - (sigma_m / sigma_ult)^2) and is less
  conservative in the mid-range. Both reduce to sigma_a when sigma_m = 0
  (fully reversed cycling).
- Stress ratio R = sigma_min / sigma_max characterises the cycle. The
  dataset must cover the R-ratio range relevant to the component; a
  dataset with only one R-ratio is provisional and may not bound the
  design loading.
- The fatigue ratio f = endurance_limit / sigma_ult is a quick
  plausibility check: values typically fall in 0.35–0.55 for metallic
  alloys used in space structures. A ratio outside this band flags a
  potential data entry error.

## Workflow

1. Inventory every material in the fatigue pack and confirm each record
   carries the mandatory fields: material identifier, ultimate strength
   (sigma_ult), endurance limit, assigned scatter factor, S-N data
   (list of stress-amplitude/cycles pairs), and the number of distinct
   R-ratio variants tested. Flag any record with a missing field before
   proceeding; do not carry incomplete records forward.
2. For each complete record, categorize the dataset quality using the
   point count, R-ratio coverage, and presence of run-out data. A
   dataset with fewer than 3 points is insufficient and must be
   supplemented before use. A dataset with 3 or more points but below
   the recommended minimum of 6 points, fewer than 2 R-ratio variants,
   or no run-out data is provisional and requires an explicit engineering
   acceptance justification.
3. For each design stress cycle (sigma_max, sigma_min), compute the
   stress amplitude and mean stress, then apply the selected mean-stress
   correction (Goodman for conservative margin, Gerber where justified)
   to obtain the equivalent fully-reversed amplitude sigma_a_eq.
4. Evaluate the design fatigue life from the S-N curve at sigma_a_eq
   using log-log interpolation. If sigma_a_eq falls outside the tested
   range, note that extrapolation is being used and flag it; extrapolated
   lives carry higher uncertainty and the scatter factor should be
   reviewed.
5. Apply the scatter factor to the mean life from step 4 to obtain the
   design fatigue allowable. Compare against the required mission
   fatigue life; flag any exceedance.
6. Compute the fatigue ratio for each material and flag any value outside
   the expected 0.35–0.55 band for additional review.
7. Aggregate findings per material: a record is fatigue-pack-ready only
   if it is complete, the dataset is qualified (or provisionally accepted
   with documented justification), no endurance or allowable life
   exceedance exists, and the fatigue ratio is in range.

## Pitfalls

- Applying a scatter factor of 1 (no reduction) because the test data
  looks clean — the scatter factor accounts for population variability
  and surface finish effects beyond what coupon scatter alone shows; it
  is never 1 unless the standard explicitly permits it for that material
  and application class.
- Ignoring mean stress correction for components under significant
  sustained load — mean stress markedly reduces fatigue life; omitting
  the correction unconservatively overstates the allowable amplitude.
- Treating an incomplete dataset as equivalent to a provisional one —
  a missing sigma_ult or scatter_factor makes the allowable life
  undefined, not merely uncertain; the record must be rejected, not
  downgraded.
- Using the Gerber correction for all cases without justification —
  Gerber is less conservative than Goodman in the tensile mean-stress
  region; its use requires explicit approval unless the material's
  mean-stress behaviour has been experimentally characterised.
- Failing to flag extrapolated lives — log-log extrapolation beyond
  the tested stress range can substantially overstate or understate
  life; extrapolated results must be identified and the scatter factor
  reconsidered.

## Behavior contract (gate 3)

The stress-parameter computation, Goodman and Gerber corrections,
log-log S-N interpolation/extrapolation, scatter-factor application,
dataset categorization, record-completeness check, fatigue-ratio
computation, and full material assessment are exercised by the gate 3
contract test:
scripts/test_material_fatigue_properties.py against
scripts/material_fatigue_properties_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_material_fatigue_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
