---
name: q2007-tf-risk
description: "Assess the hazards of a test facility and the residual risk left after mitigation, as ECSS-Q-ST-20-07 clause 5.6.5 asks. Use when a safety case for a facility has to be argued before a campaign rather than asserted: refuse an assessment covering fewer hazard categories than the facility owes, take a severity and a likelihood index per hazard into a risk band, credit only the mitigations actually implemented, recompute the residual band, and require a named acceptance authority for every residual risk above the acceptance line. Trigger: ecss, q-st-20-07-test-facility-clause-5-6-5, test-facility-hazard-category-coverage, test-facility-residual-risk-band, test-facility-risk-acceptance-authority, test-facility-mitigation-credit."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-tf-risk, q-st-20-07-test-facility-clause-5-6-5, test-facility-hazard-category-coverage, test-facility-residual-risk-band, test-facility-risk-acceptance-authority, test-facility-mitigation-credit, test-facility-safety-case-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres — Test Facility Risk Assessment (space-systems/ecss/q2007-tf-risk)

Use when the task is clause 5.6.5 of ECSS-Q-ST-20-07: a test facility
is to carry a campaign, its hazards have to be identified and assessed,
and the question is what risk is left after the mitigations that are
actually in place and who has to accept it.

## Domain quick reference

- Identification comes before assessment. A facility owes a declared
  set of hazard categories — pressure, energised systems, lifting,
  hazardous fluids, thermal, noise and the rest it operates — and an
  assessment that covers fewer of them is short, however careful the
  hazards it did assess are.
- Risk is a pair, not a number. A severity index and a likelihood index
  place the hazard in a band of the matrix; two hazards with the same
  index product can land in different bands when the matrix is not
  symmetric, and the band is what the decision uses.
- Only implemented mitigations may be credited. A planned interlock
  reduces nothing on the day of the run, so the residual band is
  recomputed from the implemented mitigations alone and the planned ones
  are reported as work outstanding.
- A mitigation moves likelihood or severity by a declared number of
  matrix steps, and it cannot move an index below the floor of its
  scale. Crediting an unbounded reduction turns a severe hazard into an
  acceptable one on paper.
- Above the acceptance line, a residual risk needs a named authority.
  An unacceptable residual is not made acceptable by the naming, but an
  undesirable one is carried only when somebody is recorded as carrying
  it.
- A safety case has a shelf life. A facility reassessed before its last
  modification describes a facility that no longer exists, so the
  assessment date is checked against the last modification and against
  the review interval.

## Workflow

1. Validate the risk policy first: the severity and likelihood scale
   bounds, the band thresholds over the index product, the acceptance
   line and the review interval. A band table whose thresholds are not
   ascending is refused.
2. Refuse an assessment with no hazards at all; that closes on hazards
   not identified rather than on an empty clean sheet.
3. Validate each hazard: a label, a category, a severity and a
   likelihood index inside the scale, and a list of mitigations. Refuse
   the same hazard label twice.
4. Measure category coverage against the categories the facility
   declares it operates, naming the uncovered ones.
5. Compute the initial index and band for every hazard from the
   unmitigated indices.
6. Credit the implemented mitigations only, clamping each reduced index
   at the floor of its scale, and recompute the residual index and band.
7. Check the acceptance records: every residual above the acceptance
   line needs a named authority, and a residual in the unacceptable band
   cannot be accepted at all.
8. Close on one verdict in order: hazards not identified, the safety
   case stale against the last modification or the review interval, an
   unacceptable residual risk, a residual above the line with no named
   authority, category coverage short, risk reduction outstanding on
   planned mitigations, or the residual risk accepted.

## Pitfalls

- Crediting a planned mitigation. The barrier that will be fitted next
  month does not lower the risk of a run next week, and a residual band
  computed from planned work is a statement about the future.
- Reading the index product instead of the band. The band table is what
  encodes the test centre's tolerance; two hazards at the same product
  can sit either side of the acceptance line.
- Letting a mitigation drive an index below its scale. A three step
  reduction on a likelihood of two cannot reach minus one, and an
  unclamped credit makes a severe hazard vanish arithmetically.
- Accepting an unacceptable band because an authority signed. Naming an
  authority records who carries an undesirable risk; it does not move
  the band, and a signature on an unacceptable residual is a finding.
- Reporting coverage from the hazards assessed. Coverage is against the
  categories the facility operates, so an uncovered category has to stay
  in the denominator.

## Behavior contract (gate 3)

The policy validation, hazard validation, band lookup, category
coverage, the implemented-only mitigation credit with its scale
clamping, the residual band recomputation, the acceptance authority
check, the safety case currency check and the verdict ordering are
exercised by the gate 3 contract test: scripts/test_q2007_tf_risk.py
against scripts/q2007_tf_risk_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_tf_risk.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
