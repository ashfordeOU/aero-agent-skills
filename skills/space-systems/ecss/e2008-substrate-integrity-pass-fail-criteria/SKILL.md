---
name: e2008-substrate-integrity-pass-fail-criteria
description: "Use when dispositioning a cycled coupon substrate. Determine whether a thermally cycled coupon substrate meets the integrity thresholds the assembly control drawing declares, under ECSS-E-ST-20-08C clause 5.5.3.10.2: refuse a drawing carrying no revision and a coupon graded on a revision it was not measured to, read each limit with its units and its direction of merit so a floor failure cannot pass as a ceiling, express every result as a margin fraction, report an indication landing exactly on its limit as having none left, total the kinds the drawing caps cumulatively, and leave a kind the drawing never declared undetermined rather than accepted. Trigger: ecss, e-st-20-08c, clause-5-5-3-10-2, substrate-integrity-acceptance-thresholds, assembly-control-drawing-threshold-source, cycled-substrate-indication-disposition, undeclared-criteria-refusal, substrate-integrity-margin-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-substrate-integrity-pass-fail-criteria, substrate-integrity-acceptance-thresholds, assembly-control-drawing-threshold-source, cycled-substrate-indication-disposition, undeclared-criteria-refusal, substrate-integrity-margin-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Substrate Integrity Pass/Fail Criteria (space-systems/ecss/e2008-substrate-integrity-pass-fail-criteria)

Use when the task is the acceptance decision of ECSS-E-ST-20-08C clause
5.5.3.10.2 -- turning the indications found on a cycled coupon substrate
into accept or reject against thresholds that live in the assembly
control drawing rather than in the standard.

## Domain quick reference

- The unusual property of this decision is where its numbers come from.
  The standard names the source; the assembly control drawing holds the
  values. Every threshold applied here has to be traceable to that
  drawing, and a number that cannot be traced there is not a criterion.
- An indication kind the drawing declares no threshold for is neither
  passing nor failing. It is undetermined, and the route out is a
  drawing change or a waiver -- never a limit borrowed from a similar
  kind, from a neighbouring programme or from engineering judgement
  recorded as though it were a drawing value.
- A threshold is bound to a drawing revision. Grading a coupon built
  and measured to one revision against the limits of another is a
  paperwork pass: the coupon never saw those criteria, and the limits
  may have moved in either direction.
- Direction of merit is part of the threshold, not an assumption. A
  disbond area, a crack length and a crush depth are ceilings; a
  residual bond strength and a remaining core height are floors. Code
  that assumes a ceiling everywhere passes every floor failure in
  silence, and floor failures are the ones that mean the substrate has
  lost load path.
- Units are part of the threshold too. A length compared against an
  area limit produces a confident number with no meaning, so the units
  on the measurement and the units on the drawing have to agree before
  any comparison happens.
- Margins are reported as a fraction of the limit so a millimetre, a
  square millimetre and a megapascal can be read side by side, and so a
  reviewer can see which indication is closest to its bound without
  converting anything.
- On-limit is its own result. An indication exactly on its threshold
  passes, but it passes with no margin against measurement scatter, and
  that fact belongs in the record rather than rounded away into a
  plain accept.
- The drawing can cap a kind cumulatively as well as individually.
  Indications that each clear their own limit still add up, and a
  coupon whose total disbond area crosses the drawing's ceiling
  rejects even though nothing on it failed alone.

## Workflow

1. Validate the drawing as a criteria source: a drawing identifier, a
   revision, at least one declared threshold, and for each one a
   positive limit, its units and its direction of merit. A cumulative
   cap must be a ceiling, since a total has no meaningful floor.
2. Check the revision the coupon was measured against matches the
   drawing supplied. Refuse the grading outright when they differ.
3. Look up each indication's threshold by kind. Return no threshold
   rather than a default when the drawing is silent, and carry that
   silence forward as an undetermined disposition with its reason.
4. Check the units agree, then compute the margin fraction in the
   declared direction: below a ceiling or above a floor is positive
   margin, and the sign is what decides the disposition.
5. Disposition each indication accept, accept-on-limit, reject or
   criteria-undeclared, absorbing representation error so a value
   exactly on its bound reports on-limit rather than flipping either
   way by one unit in the last place.
6. Total the kinds the drawing caps cumulatively, skipping the kinds
   whose individual threshold is a floor, and grade each total the
   same way.
7. Close with the coupon verdict. An undeclared criterion or an
   incomplete survey leaves it undetermined and outranks a rejection;
   any individual or cumulative rejection rejects it; otherwise it
   accepts, with the on-limit indications named in the findings.

## Pitfalls

- Supplying a limit the drawing does not carry. It will look exactly
  like a criterion in the record, and nobody downstream can tell the
  difference between an approved threshold and an assumed one.
- Reading an undeclared kind as a pass because nothing exceeded
  anything. Silence in the drawing is missing information, not a
  generous limit, and the verdict that reflects that is undetermined.
- Grading against whatever revision is on the desk. The coupon was
  built and measured to a specific revision, and that is the only one
  whose limits it can be held to.
- Assuming every limit is a ceiling. A residual bond strength below
  its floor is the clearest evidence of a failed substrate, and a
  ceiling comparison passes it with a large positive margin.
- Comparing a measurement against a limit in different units. The
  arithmetic succeeds, the number is meaningless, and nothing in the
  output says so unless the units are checked first.
- Accepting a coupon because every indication passed individually. The
  cumulative cap is a separate limit, and a scatter of small accepted
  disbonds is exactly the case it exists to catch.
- Flipping an on-limit value with bare arithmetic. A margin computed
  from a measured value and a drawing limit can land a few units in
  the last place either side of zero, so the equality check absorbs
  that error rather than letting the platform decide the verdict.

## Behavior contract (gate 3)

The drawing validation, revision binding, threshold lookup without a
default, margin computation in both directions of merit, per-indication
disposition, cumulative totals and the coupon verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_substrate_integrity_pass_fail_criteria.py against
scripts/e2008_substrate_integrity_pass_fail_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_substrate_integrity_pass_fail_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
