---
name: e1012-bio-quantities
description: "Use when determine dosimetric quantities for a space radiation
  environment analysis per ECSS-E-ST-10C §11.2: select a radiation weighting
  factor (wR) for each particle type from the §11.2 Table 11-1 categories
  (photons, electrons, protons, alphas, heavy ions, energy-dependent neutrons),
  select a tissue weighting factor (wT) for each organ from §11.2 Table 11-2,
  compute equivalent dose per tissue as absorbed dose multiplied by wR, compute
  effective dose as the sum of wT × HT across all tissues, and derive dose
  equivalent from absorbed dose and the LET-dependent quality factor Q(L)
  defined in §11.2. Trigger: ecss, e-st-10-system-scope, dosimetry,
  radiation-weighting-factor, tissue-weighting-factor, equivalent-dose,
  effective-dose, quality-factor, dose-equivalent."
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
  tags: [ecss, e-st-10-system-scope, dosimetry, radiation-weighting-factor, tissue-weighting-factor, equivalent-dose, effective-dose, quality-factor, dose-equivalent]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Radiation — Dosimetric Quantities (space-systems/ecss/e1012-bio-quantities)

Use when the task is to determine the dosimetric quantities for a space
radiation assessment under ECSS-E-ST-10C §11.2 — selecting radiation and
tissue weighting factors from the §11.2 tables, computing equivalent and
effective dose for human-health impact analysis, and applying the
LET-dependent quality factor to derive dose equivalent from absorbed dose.

## Domain quick reference

- §11.2 organises dosimetric quantities into three families. Basic physical
  quantities (absorbed dose D in Gy, particle fluence in cm⁻², LET in
  keV/µm) are the measured inputs. Protection quantities (equivalent dose H
  in Sv and effective dose E in Sv) weight absorbed dose by the biological
  effectiveness of each radiation type and the relative sensitivity of each
  organ. Operational quantities (dose equivalent H = D × Q in Sv) apply the
  LET-dependent quality factor Q(L) as a point-level surrogate when the
  radiation type is not resolved.
- Radiation weighting factors (wR) are tabulated in §11.2 Table 11-1 by
  radiation category: photons and electrons carry wR = 1; protons carry
  wR = 5; alpha particles and heavy ions carry wR = 20; neutrons follow a
  step-function schedule that rises from 5 at low energies (< 10 keV) to a
  peak of 20 in the 0.1–2 MeV band and returns to 5 above 20 MeV. These
  factors are applied per radiation type to the absorbed dose in that tissue
  to obtain the tissue equivalent dose HT = Σ wR × DT,R.
- Tissue weighting factors (wT) are tabulated in §11.2 Table 11-2 by organ
  or tissue, assigning fractional radiological sensitivity so that the
  effective dose E = Σ wT × HT sums to units of Sv across the whole body.
  Gonads carry the largest single factor (0.20); red bone marrow, colon,
  lung, and stomach each carry 0.12; bladder, breast, liver, oesophagus, and
  thyroid each carry 0.05; skin and bone surface each carry 0.01; remaining
  organs share 0.05 as a group. The factors sum to 1.00.
- The quality factor Q(L) converts absorbed dose to dose equivalent at a
  point without resolving radiation type: Q = 1 for L ≤ 10 keV/µm,
  Q = 0.32L − 2.2 for 10 < L ≤ 100 keV/µm, and Q = 300/√L for
  L > 100 keV/µm. This continuous function rises to a peak near
  L = 100 keV/µm and falls off at higher LET where overkill reduces
  biological damage per unit dose.

## Workflow

1. Identify the radiation field: list each radiation component (particle
   type and, for neutrons, energy range) reaching the target point or
   organ; determine or calculate the absorbed dose DT,R contributed by each
   component to each tissue of interest.
2. Assign wR: for each radiation component, look up the §11.2 Table 11-1
   radiation weighting factor. For neutrons, map the particle energy to the
   energy-dependent step in the table. Reject any radiation type that does
   not appear in Table 11-1 and flag it as requiring explicit justification.
3. Compute equivalent dose per tissue: HT = Σ_R (wR × DT,R) summed over
   all radiation components R for each tissue T.
4. Assign wT: for each tissue T with a non-zero equivalent dose, look up
   the §11.2 Table 11-2 tissue weighting factor. Organs not listed
   individually contribute to the remainder group wT = 0.05. Flag a tissue
   whose wT is not on record and cannot be placed in the remainder group.
5. Compute effective dose: E = Σ_T (wT × HT) over all tissues. The result
   is in Sv; confirm the tissue set is sufficient to capture the dominant
   dose contributors before reporting E as a whole-body estimate.
6. If the radiation field is not resolved by type (point-kernel or Monte
   Carlo output providing only absorbed dose and LET spectrum), derive dose
   equivalent H_point = D × Q(L) for each LET bin, then integrate over the
   LET spectrum to obtain the total dose equivalent at the point.
7. Report each quantity with its unit (Gy for absorbed dose, Sv for
   equivalent dose, effective dose, and dose equivalent) and the table
   reference used for each weighting factor; flag any component or tissue
   where a factor was assumed rather than looked up.

## Pitfalls

- Confusing absorbed dose (Gy) with equivalent or effective dose (Sv):
  the numerical value can differ by a factor of 20 for alpha particles or
  heavy ions; always carry the weighting factor explicitly rather than
  dropping it when wR = 1 for photons.
- Applying a single wR to the whole neutron spectrum: neutron wR is
  energy-dependent; a mixed-energy neutron field requires binning by energy
  and weighting each bin separately before summing absorbed doses.
- Stopping at equivalent dose and not computing effective dose when the
  task requires a whole-body radiological risk estimate: effective dose is
  required because organs differ in sensitivity, and the sum must be over
  all tissues, not just the most-exposed one.
- Using Q(L) where wR is required: Q is a point-level operational quantity
  for an unresolved radiation field; when particle types are known, the
  protection quantity (wR-based equivalent dose) is required by §11.2
  rather than the operational surrogate.
- Omitting the remainder group: organs not listed by name in Table 11-2
  are not excluded — they contribute through the remainder wT and must not
  simply be dropped from the effective dose sum.

## Behavior contract (gate 3)

The wR lookup, tissue wT lookup, Q(L) function, equivalent-dose
computation, and effective-dose aggregation logic are exercised by the
gate 3 contract test: scripts/test_e1012_bio_quantities.py against
scripts/e1012_bio_quantities_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bio_quantities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
