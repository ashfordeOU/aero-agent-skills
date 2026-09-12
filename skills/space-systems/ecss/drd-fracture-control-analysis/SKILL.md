---
name: drd-fracture-control-analysis
description: "Use when determine the content of a fracture control analysis report
  for a space structure per ECSS-E-ST-32 Annex E: categorize each structural item as
  fracture-critical or non-fracture-critical, compute the applied stress intensity factor
  from net-section stress and assumed flaw geometry, verify it against material fracture
  toughness with a required safety factor, derive the critical flaw size, integrate
  Paris-law crack-growth to establish damage-tolerance life, verify the leak-before-burst
  condition for pressurized components, and confirm the selected non-destructive
  inspection method can detect the assumed initial flaw. Trigger: ecss,
  e-st-32-structures-scope, fracture-control, damage-tolerance, fracture-critical,
  stress-intensity, crack-propagation, leak-before-burst, flaw-assessment."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, damage-tolerance, fracture-critical, stress-intensity, crack-propagation, leak-before-burst, flaw-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control Analysis DRD (space-systems/ecss/drd-fracture-control-analysis)

Use when the task is producing a fracture control analysis (FCA) report
whose content satisfies the data requirements of ECSS-E-ST-32 Annex E
(Fracture Control Analysis report) and the damage-tolerance verification
requirements of ECSS-E-ST-32-01. The report must demonstrate that every
fracture-critical structural item carries adequate residual strength after
the assumed initial flaw, grows that flaw slowly enough to meet a damage-tolerance
life with scatter factor, and — for pressurised items — leaks before it bursts.

## Domain quick reference

- **Fracture criticality**: each structural item is categorized as
  fracture-critical (FC) if its failure mode under the assumed flaw could
  be catastrophic (loss of mission, crew hazard, or uncontained rupture),
  or as non-fracture-critical (NFC) otherwise. Only FC items require the
  full FCA calculation chain; NFC items are documented and closed out.
- **Stress intensity factor**: the applied stress intensity factor
  K = Y × σ × √(π a), where Y is a geometry correction factor,
  σ is the net-section applied stress in MPa, and a is the assumed
  half-flaw length in metres. K is compared against the material's
  plane-strain fracture toughness K_IC (or K_c for thin sections)
  after dividing by the required safety factor to obtain the allowable.
- **Critical flaw size**: the half-flaw length a_c at which K equals K_IC
  under the design stress, derived by inverting the K equation.
  a_c = (1/π) × (K_IC / (Y × σ))². A_c must exceed the minimum
  detectable flaw of the selected NDI method; if it does not, the design
  or material choice must be revised before the report can close.
- **Crack-growth life**: Paris-law integration (da/dN = C × ΔK^m) from
  the assumed initial flaw a_i to the critical flaw a_c gives a crack-growth
  life N_g. The computed life must satisfy N_g ≥ N_req × DTF, where
  N_req is the required structural life and DTF is the damage-tolerance
  scatter factor (commonly 4 for metallic structure per ECSS-E-ST-32-01).
- **Leak-before-burst (LBB)**: for pressurised components, the critical
  flaw half-length must equal or exceed the wall thickness, confirming that
  a through-wall crack (detectable by leak) forms before the flaw reaches
  fracture instability at the design pressure. Failure of the LBB check
  requires a proof-pressure programme or design change.
- **NDI detectability**: the assumed initial flaw a_i must be at or above
  the minimum detectable flaw size of the NDI method applied during
  manufacture and in-service inspection. If the NDI method cannot reliably
  detect flaws as small as a_i, the assumed a_i is non-conservative and
  must be revised upward (or a more capable NDI method adopted).

## Workflow

1. List every load-carrying structural item in scope and categorize each one
   as FC or NFC based on failure consequence (catastrophic → FC). Items
   with an unrecognised consequence classification must be rejected before
   the analysis proceeds.
2. For each FC item, obtain (a) the design net-section stress σ, (b) the
   assumed initial half-flaw length a_i (set at the NDI detection threshold),
   (c) the material fracture toughness K_IC, (d) the Paris-law constants
   C and m for the material and environment, and (e) the geometry correction
   factor Y.
3. Compute K_applied = Y × σ × √(π × a_i / 1000) (converting a_i from mm
   to metres). Compare K_applied against K_IC / SF, where SF is the required
   safety factor; flag an exceedance as a finding.
4. Derive the critical flaw size a_c = (1/π) × (K_IC / (Y × σ))² × 1000 mm.
   Confirm a_c > a_i; if a_c ≤ a_i the item fails immediately at the initial
   flaw and the design must change.
5. Integrate Paris-law crack growth from a_i to a_c numerically to obtain
   N_g cycles. Apply the damage-tolerance scatter factor: if N_g < N_req × DTF,
   flag a damage-tolerance shortfall.
6. For every pressurised FC item, run the LBB check: confirm
   a_c ≥ wall thickness. Flag a failure.
7. Verify that the NDI method's minimum detectable flaw ≤ a_i; flag a
   mismatch as a non-conservatism finding.
8. Aggregate all findings. The FCA report is closed only when no open findings
   remain for any FC item.

## Pitfalls

- Assuming a zero initial flaw — the fracture control analysis must always
  start from a finite, NDI-capability-bounded initial flaw size. A zero
  initial flaw produces infinite computed life, which is non-physical and
  non-compliant.
- Applying a scalar safety factor to the stress σ rather than to K directly —
  the ECSS-E-ST-32 safety factor convention is applied to the allowable K,
  not to the input stress; applying it to stress double-counts the non-linearity
  in the √a term.
- Skipping the LBB check for items that are "only lightly pressurised" —
  the LBB criterion applies whenever internal pressure contributes to the
  structural load path; pressure level does not exempt the item.
- Using a geometry factor Y = 1.0 for all geometries — Y = 1.0 is only
  valid for a central through-crack in an infinite plate under uniform
  tension. Surface flaws, corner cracks, and finite-width panels all require
  appropriate Y corrections; using 1.0 for these cases unconservatively
  underestimates K.
- Treating NFC documentation as optional — every item categorized as NFC
  must appear in the FCA report with the consequence rationale recorded;
  an undocumented NFC item is an open finding, not an implicit pass.

## Behavior contract (gate 3)

The item-categorization, stress-intensity, critical-flaw, crack-growth
integration, LBB, damage-tolerance, NDI-detectability, and report-aggregation
logic is exercised by the gate 3 contract test:
scripts/test_drd_fracture_control_analysis.py against
scripts/drd_fracture_control_analysis_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_drd_fracture_control_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite source and paraphrase
  per standards-map.yaml.
- Anchor clauses: ECSS-E-ST-32 Annex E (FCA report content);
  ECSS-E-ST-32-01 (damage-tolerance and fracture control requirements).
- compliance: STANDARDS-REF, gated: false.
