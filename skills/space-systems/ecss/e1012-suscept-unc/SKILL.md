---
name: e1012-suscept-unc
description: "Use when assess radiation design margins for EEE components where susceptibility test data carries uncertainty—small sample counts, single-lot characterization, non-equivalent radiation sources, or absent test data entirely. The procedure categorizes the data quality for each radiation effect type (TID, SEE, NIEL, displacement damage), selects an uncertainty multiplication factor proportional to the data shortfall, applies that factor on top of the base radiation design margin, and checks that each component's rated threshold meets the uncertainty-scaled environment dose. Components that fail under uncertainty-adjusted margins require additional testing, design change, or formal derogation. Trigger: ecss, e-st-10-system-scope, radiation-margins, eee-components, susceptibility-uncertainty, TID, SEE, radiation-design-margin, data-quality."
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
  tags: [ecss, e-st-10-system-scope, radiation-margins, eee-components, susceptibility-uncertainty, TID, SEE, radiation-design-margin, data-quality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — EEE Component Radiation Susceptibility Uncertainty (space-systems/ecss/e1012-suscept-unc)

Use when the task is sizing radiation design margins for EEE components
under ECSS-E-ST-10-12C §5.5.1 — accounting for the uncertainty in
radiation susceptibility data by categorizing data quality, deriving an
uncertainty factor, and verifying that each component's threshold meets
the uncertainty-adjusted margin requirement.

## Domain quick reference

- §5.5.1 requires that margins applied to EEE component radiation
  susceptibility limits reflect the confidence in the underlying test
  data. Where data are sparse, the effective required margin must
  increase to cover the unknown portion of the component distribution.
- Data quality is assessed per component per effect type. The four
  recognized effect types are TID (Total Ionizing Dose), SEE (Single
  Event Effects), NIEL (Non-Ionizing Energy Loss), and DD (Displacement
  Damage). Each component/effect pair carries an independent uncertainty
  level.
- Four uncertainty levels are defined by sample count, radiation source
  equivalence, and lot coverage:
  - **high** — five or more individually tested components from two or
    more manufacturing lots, using a space-flight or ground-equivalent
    radiation source. Uncertainty factor 1.0 (no additional margin
    beyond base RDM).
  - **medium** — three or more samples from any source, or any number
    of samples from a qualified source with single-lot coverage.
    Uncertainty factor 1.5.
  - **low** — a single test point or a vendor specification with no
    independent verification. Uncertainty factor 2.0.
  - **absent** — no test data; a worst-case assumption is the only
    basis. Uncertainty factor 3.0.
- The base radiation design margin (RDM) is a project-level requirement
  (commonly 2.0 for TID in ECSS practice); the uncertainty factor
  multiplies the base RDM to yield the effective required RDM. A
  component passes when its rated threshold equals or exceeds the
  environment dose multiplied by the effective required RDM.

## Workflow

1. Inventory every EEE component in scope and, for each, list the
   radiation effect types that apply given the orbit environment
   (TID, SEE, NIEL, DD or a subset). Reject an unrecognized effect
   type before it enters the assessment.
2. For each component/effect pair, gather the available susceptibility
   data: number of tested components (sample size), radiation source
   type (space-flight, ground-equivalent, vendor-spec, or assumed), and
   the number of distinct manufacturing lots represented.
3. Call the data-quality categorization step: map (sample_size,
   source_type, lot_count) to one of the four uncertainty levels and
   read off the corresponding uncertainty factor.
4. Determine the effective required RDM = base_RDM × uncertainty_factor.
   Compute the required threshold = worst-case environment dose ×
   effective required RDM.
5. Compare the component's rated susceptibility threshold to the
   required threshold. Record pass or fail; on fail, record the
   numerical shortfall so the disposition path (more testing, design
   change, or derogation) can be quantified.
6. For each component/effect pair with an absent data level, flag the
   pair explicitly — a 3× margin assumption is a placeholder and must
   be resolved by dedicated radiation testing before final acceptance.
7. Aggregate findings: a component is margin-compliant only when all
   of its applicable effect-type checks pass.

## Pitfalls

- Applying the base RDM alone when data are sparse and reading no
  exceedance as a pass — the uncertainty factor is not optional; absent
  data demands a 3× effective RDM regardless of nominal threshold
  headroom.
- Treating a vendor specification as equivalent to independent test data
  — vendor specs are typically minimum guaranteed values that do not
  capture lot-to-lot or sample-to-sample variation; they receive a
  "low" quality level, not "high".
- Pooling test data from different effect types — a component that has
  abundant TID data may have zero SEE data; each effect type is assessed
  independently.
- Conflating the radiation environment worst-case with a design point
  that already includes shielding margin — the environment dose fed into
  this step must already be the shielded worst-case with its own
  uncertainty bounds applied; double-counting must be avoided.
- Closing an absent-data flag with a derogation alone without recording
  the residual risk — a derogation accepted without additional testing
  must carry an explicit residual-risk statement traceable to the
  project's risk register.

## Behavior contract (gate 3)

The data-quality categorization, required-threshold computation, and
margin check logic are exercised by the gate 3 contract test:
scripts/test_e1012_suscept_unc.py against
scripts/e1012_suscept_unc_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_suscept_unc.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
