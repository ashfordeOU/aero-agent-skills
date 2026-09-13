---
name: e2008-sca-test-conditions-and-methods
description: "Verify that every test declared for a solar cell assembly is aligned with its cell assembly source control drawing under ECSS-E-ST-20-08C clause 6.1.2. Use when a cell assembly test matrix, acceptance procedure or laboratory report has to stand as drawing-traceable evidence: resolve whether the method is drawing-named, drawing-invoked, an approved equivalent or a house procedure; guard-band each declared condition by the uncertainty of the instrument that recorded it; rank the conditions by the window they consume; and name the drawing-required test the matrix never declared. Trigger: ecss, e-st-20-08c, sca-test-condition-alignment, cell-assembly-source-control-drawing, sca-test-method-admissibility, sca-measurement-uncertainty-guard-band, sca-test-window-margin, solar-cell-assembly-test-matrix-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-test-conditions-and-methods, sca-test-condition-alignment, cell-assembly-source-control-drawing, sca-test-method-admissibility, sca-measurement-uncertainty-guard-band, sca-test-window-margin, solar-cell-assembly-test-matrix-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Test Conditions and Methods (space-systems/ecss/e2008-sca-test-conditions-and-methods)

Use when the task is clause 6.1.2 of ECSS-E-ST-20-08C: a solar cell
assembly is procured against a cell assembly source control drawing, and
it is the drawing -- not the laboratory, not the supplier's house
practice -- that fixes which tests are run, by which method, and at
which conditions. This leaf grades a declared test matrix against that
drawing and says, test by test, what would stop a result standing as
evidence.

## Domain quick reference

- Two things decide whether a result counts: the method has to be one
  the drawing allows, and every condition has to be demonstrated inside
  the window the drawing sets. The method verdict outranks every
  condition verdict, because a run by a method the drawing never
  sanctioned is not a run against the drawing, however green its bands.
- A method is admissible when the drawing names it, when the drawing
  invokes it through a standard, or when an equivalent stands on a
  written approval. A method described as an approved equivalent that
  cites no approval is an input contradiction and is rejected rather
  than quietly downgraded -- the name asserts the approval, and without
  a reference nobody can check the assertion.
- A condition is not demonstrated by its setpoint alone. The instrument
  that recorded it has an uncertainty, and that uncertainty consumes
  the drawing window from the inside. The quantity that matters is the
  margin left after the offset from the specified value and the
  recording uncertainty are both taken out of the half window.
- Three outcomes follow, and they are not the same finding. A setpoint
  outside the window is a deviation from the drawing. A setpoint inside
  the window whose uncertainty interval crosses it is compliant on
  paper and undemonstrated in fact -- repeatable by a better instrument,
  not by a better argument. Everything else is demonstrated.
- The window each condition consumes is what ranks the conditions
  against each other. A test at nine tenths of its window is formally
  compliant and practically fragile, and that is the condition that
  governs the test.
- A zero tolerance is legitimate and means the specified value exactly
  -- a cycle count, a sample size. It is an exact match, not a
  division, and it cannot be demonstrated at all by an instrument with
  a non-zero uncertainty, because such an instrument cannot resolve the
  value the drawing asks for.
- A test the drawing calls for and the matrix never declares raises no
  deviation anywhere, so it is found by comparing the declared set
  against the drawing's set, never by grading the declared tests
  harder.

## Workflow

1. Take each declared test with its identifier, the source of its
   method, any approval reference, and its condition list. Reject a
   test that declares no conditions rather than passing it on an empty
   set.
2. Resolve the method first. Demand an approval reference from a method
   declared as an approved equivalent, record the substitution as a
   finding so it travels with the result, and return a house procedure
   as misaligned before any condition is looked at.
3. For each condition, take the signed deviation from the specified
   value, subtract both the offset and the recording uncertainty from
   the half window, and record the margin and the share of the window
   consumed. Treat a zero half window as an exact match.
4. Grade the test on the worse of the method verdict and the condition
   verdicts, and name the condition that consumes most of its window as
   the governing condition.
5. Compare the declared test identifiers with the identifiers the
   drawing calls for; name the missing tests and, separately, the tests
   the drawing never asked for.
6. Roll the matrix up: the weakest test by verdict then by margin, the
   tests that are not aligned, the aligned share, and a programme
   verdict that a missing drawing test drags off a clean sheet.

## Pitfalls

- Grading condition bands on a test whose method the drawing never
  allowed. Every band can read green on a run the customer never
  sanctioned, and reporting that as compliance is the exact failure the
  clause exists to prevent.
- Comparing a setpoint against the window and stopping there. A
  condition measured with an instrument whose uncertainty is half the
  window is a coin toss dressed as a pass, and the report that omits
  the uncertainty cannot tell the two apart.
- Treating an undemonstrated condition as a deviation from the drawing.
  It is not one; the hardware may be perfectly inside the window. What
  is missing is the evidence, and the repair is a better instrument,
  not a concession against the drawing.
- Dividing by a zero tolerance to report the window consumed. A zero
  band means the specified value exactly and is checked as a match.
- Reading an absent test as a satisfied one. A drawing test the matrix
  never declares produces no finding at all, so a check that only
  grades what was declared returns a clean sheet on the test nobody
  ran.
- Judging a margin that lands exactly on zero with bare arithmetic. The
  margin is a chain of subtractions of declared decimal values, so a
  condition sitting exactly on its guard band can evaluate a unit in
  the last place below zero on one platform and on it on another; the
  comparison absorbs that while the drawing window stays as specified.

## Behavior contract (gate 3)

The method admissibility check, the uncertainty guard-band margin, the
zero-window exact match, the window-consumed ranking, the drawing
coverage comparison and the rolled-up matrix verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_sca_test_conditions_and_methods.py against
scripts/e2008_sca_test_conditions_and_methods_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_sca_test_conditions_and_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
