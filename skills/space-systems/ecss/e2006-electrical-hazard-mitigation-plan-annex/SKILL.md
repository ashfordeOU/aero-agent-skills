---
name: e2006-electrical-hazard-mitigation-plan-annex
description: "Use when structure and check the electrical-hazard mitigation-plan annex of ECSS-E-ST-20-06C Annex A: confirm the document carries every required section, categorize each declared hazard into an electrostatic, propulsion-interaction, power-distribution or grounding-and-bonding family, score its assessment outcome on the severity-by-likelihood grid, credit only the mitigations whose verification-status has actually progressed, recompute the residual-risk band per hazard, and decide release readiness from the exposure-weighted residual score measured against the acceptance threshold. Trigger: ecss, e-st-20-electrical-scope, e2006-electrical-hazard-mitigation-plan-annex, electrical-hazard-inventory, mitigation-plan-annex, verification-status-tracking, residual-risk-band, severity-likelihood-grid, hazard-mitigation-credit, annex-content-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-electrical-hazard-mitigation-plan-annex, electrical-hazard-inventory, mitigation-plan-annex, verification-status-tracking, residual-risk-band, severity-likelihood-grid, annex-content-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Scope — Hazard Mitigation Plan Annex (space-systems/ecss/e2006-electrical-hazard-mitigation-plan-annex)

Use when the task is the electrical-hazard mitigation-plan annex defined by
ECSS-E-ST-20-06C Annex A -- assembling or auditing the plan document that
carries the hazard inventory, the assessment outcome of each hazard, the
mitigations adopted against it, and the verification-status of every one of
those mitigations.

## Domain quick reference

- Annex A is a document content definition, not a calculation. Its
  completeness is graded against a fixed section list: scope and
  applicability, applicable and reference documents, hazard inventory,
  assessment outcomes, mitigation measures, verification-status and the
  residual-risk statement. Projects may add optional sections such as a
  configuration baseline or an open-work list without changing that
  grading.
- Each declared hazard belongs to exactly one family: electrostatic
  (differential surface-charging, deep-dielectric internal-charging,
  discharge arcs), propulsion-interaction (plume-induced-erosion,
  loss of beam-neutralization, induced-plasma-coupling),
  power-distribution (arc-tracking in a harness, low-pressure insulation
  breakdown) or grounding-and-bonding (bonding discontinuity, a
  structure return-current loop). An unrecognized hazard type is
  rejected rather than filed under a default.
- The assessment outcome is a position on a four-by-four grid: a
  severity rank from negligible to catastrophic against a likelihood
  rank from improbable to probable, multiplied into an index between one
  and sixteen, which bands as acceptable, tolerable-with-review or
  unacceptable.
- A mitigation earns rank credit only in proportion to how far its
  verification has actually gone. A closed verification earns the full
  credit of its class; a running one earns a capped provisional credit;
  an open one earns nothing and is itself a finding. Each class acts on
  one axis of the grid -- a conductive-surface-treatment or a
  grounding-bond lowers likelihood, a filter-network or a
  redundant-return-path lowers severity -- and neither rank falls below
  one however much credit accumulates.
- Release readiness combines three things: no missing section, no open
  finding on any hazard, and an exposure-weighted mean of the residual
  indices at or below the acceptance threshold agreed for the project.

## Workflow

1. Read the section list the annex actually contains and compare it with
   the required list, keeping the missing entries in reading order.
   Reject a section name that belongs to neither the required nor the
   optional list, because an unrecognized heading means the document was
   built against a different template.
2. Validate each hazard entry: resolve its type to a family, resolve its
   severity and likelihood to ranks, compute the initial grid index and
   band, and read the exposure weight that says how much of the mission
   the hazard applies to.
3. Validate each mitigation entry: it names the hazard it acts on, a
   recognized mitigation class, a recognized verification method and one
   of the three verification states.
4. For each hazard, gather the mitigations pointing at it and convert
   each into rank credit on its own axis according to
   verification-status. Subtract the accumulated credit from the
   severity and likelihood ranks, floor both at one, and recompute the
   residual index and band.
5. Raise a finding for a hazard with no mitigation at all, for a
   mitigation still carrying an open verification, and for a residual
   band that stays unacceptable after every credit is applied.
6. Cross-check the other direction: a mitigation pointing at a hazard
   the inventory does not declare is an integrity defect in the
   document, not a silent no-op.
7. Compute the exposure-weighted mean of the residual indices, compare
   it with the acceptance threshold, and declare the annex ready only
   when it is within threshold and no finding remains open.

## Pitfalls

- Crediting a mitigation the moment it is written down. The rank
  reduction belongs to the verification, not the intention; an annex
  that books full credit against open verifications reports a residual
  risk the programme has not actually bought.
- Applying every mitigation to the likelihood axis. A filter-network or
  a redundant-return-path limits how bad the consequence is rather than
  how often it happens, and collapsing both axes into one hides which
  half of the risk was actually addressed.
- Letting a rank fall below one because credits accumulated. No
  mitigation removes a hazard from the inventory; the floor at rank one
  is what keeps a mitigated hazard visible in the residual statement.
- Grading section completeness by counting headings. The required list
  is a named set -- seven present headings are not the seven required
  ones, and an unrecognized heading is evidence the document followed a
  different template.
- Treating a mitigation that names an undeclared hazard as harmless. It
  means either the inventory lost an entry or the mitigation is
  mis-referenced, and both defects survive into the next revision unless
  the cross-check is run in that direction too.
- Reading an acceptable weighted score as release readiness. The score
  is a mean, so one unacceptable residual hazard can sit under a
  comfortable average; readiness requires the findings list to be empty
  as well.

## Behavior contract (gate 3)

The section-completeness, hazard-categorization, risk-grid,
mitigation-credit, residual-risk and readiness logic is exercised by the
gate 3 contract test:
scripts/test_e2006_electrical_hazard_mitigation_plan_annex.py against
scripts/e2006_electrical_hazard_mitigation_plan_annex_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_electrical_hazard_mitigation_plan_annex.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
