---
name: e2008-sca-thermo-optical-criteria
description: "Verify the thermo optical acceptance limits of clause 6.4.3.6.3 of ECSS-E-ST-20-08C against the cell assembly control drawing that governs them: resolve whether each limit is drawing-stated, drawing-invoked or a house default nobody sanctioned, check the drawing revision the limits were read from against the revision the lot was built to, guard band every measured absorptance, emittance and ratio by its own measurement uncertainty, and separate a marginal result from a pass. Use when a thermo optical acceptance record, drawing limit sheet or lot disposition summary has to be assessed. Trigger: ecss, e-st-20-08c, sca-thermo-optical-criteria, cell-assembly-control-drawing-limit-provenance, sca-thermo-optical-acceptance-limits, sca-measurement-uncertainty-guard-band, sca-drawing-revision-alignment."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-thermo-optical-criteria, e-st-20-08c, sca-thermo-optical-criteria, cell-assembly-control-drawing-limit-provenance, sca-thermo-optical-acceptance-limits, sca-measurement-uncertainty-guard-band, sca-drawing-revision-alignment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Thermo Optical Acceptance Limits (space-systems/ecss/e2008-sca-thermo-optical-criteria)

Use when the task is clause 6.4.3.6.3 of ECSS-E-ST-20-08C: the acceptance
limits a measured solar absorptance and hemispherical emittance are held
against, and where those limits came from. This leaf asks the provenance
question before the pass-fail question, guard bands every comparison by the
uncertainty of the measurement behind it, and rolls the samples up on their
worst disposition rather than their average one.

## Domain quick reference

- The cell assembly control drawing is the authority. A limit stated on it,
  or stated in a document it invokes, governs the article. A house number,
  however sensible and however long the laboratory has used it, governs
  nothing, and a pass taken against one cannot be traced to a requirement.
- An invoked document that is never named is not a provenance, it is a
  gesture at one. The chain has to end in a document somebody can pull.
- Limits are revision-bearing. A limit read from a superseded revision can
  be tighter or looser than the one the lot was actually built against, so
  the revision the limits came from is checked against the revision the lot
  was built to before any value is compared.
- Each property is bounded in its own direction. Absorptance carries a
  ceiling because it decides how much sunlight becomes heat; emittance
  carries a floor because it decides how much heat leaves; their ratio
  carries a ceiling because that is what the thermal model consumes.
- A result inside the limit by less than its own measurement uncertainty has
  not been shown to be inside it. That is a third outcome, not a pass with a
  note: the article is marginal, and marginal is a decision for the customer.
- When the ratio carries no declared uncertainty of its own, it inherits one
  from the two properties it was derived from, propagated through the
  quotient. Treating a derived quantity as exact is how a marginal ratio
  becomes an unqualified pass.

## Workflow

1. Validate the governing drawing and compare the revision the limits were
   read from against the revision the lot was built to.
2. For every governed property, categorize the provenance of its limit into
   drawing-stated, drawing-invoked or house-default, and raise a finding on
   anything the drawing never sanctioned or any invoked document left unnamed.
3. Derive the absorptance to emittance ratio for each sample, and resolve the
   uncertainty of each of the three quantities, propagating the ratio
   uncertainty when it was not declared.
4. Guard band each comparison in the sense its property carries, absorbing
   floating-point representation error at the bound with a named tolerance
   rather than by moving the limit.
5. Roll each sample up on the heaviest disposition across its checks, so a
   single marginal or failing property carries the sample.
6. Reject a sample identifier that appears twice; two dispositions under one
   name make the lot record ambiguous.
7. Report the per-sample dispositions, the tally across the lot and a lot
   verdict, keeping the limit-provenance findings separate from the sample
   dispositions so a compliant lot measured against ungoverned limits is
   still visible as a finding.

## Pitfalls

- Answering the pass-fail question first. A lot where every sample sits well
  inside a limit nobody can trace to the drawing has no acceptance evidence
  at all, and the numbers look reassuring the whole way.
- Comparing a measured value to a limit bare. Without the guard band an
  article one part in a thousand inside the limit and one part outside are
  reported as opposite outcomes, when the measurement cannot separate them.
- Treating the derived ratio as exact. It carries the uncertainty of both
  properties it came from, and without that it is the one check that never
  goes marginal.
- Reporting the mean disposition of the lot. Averaging dispositions hides the
  single failing assembly, which is the only one the decision is about.
- Reading limits off the current drawing revision for an older lot. The
  revision is part of the limit; changing it silently re-scores hardware that
  was built and accepted against something else.

## Behavior contract (gate 3)

The limit provenance categorization, the drawing revision alignment, the
derived ratio and its propagated uncertainty, the guard-banded pass, marginal
and fail dispositions, the worst-case sample and lot rollup and the duplicate
identifier rejection are exercised by the gate 3 contract test:
scripts/test_e2008_sca_thermo_optical_criteria.py against
scripts/e2008_sca_thermo_optical_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_thermo_optical_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
