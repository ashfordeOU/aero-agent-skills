---
name: e2008-bare-cell-failure-criteria
description: "Use when subgroup bare-cell results have to become per-cell failure calls. Assess which bare solar cells a subgroup test and inspection leave failed under ECSS-E-ST-20-08C clause 7.6.1: refuse a criteria set carrying no specification reference, take each electrical parameter's loss between its before and after readings against its own allowance with a tie admissible, catch a cell that has stopped conducting, fail a measured-clean cell on any observed condition the specification lists, name every mode a cell shows rather than the first, and hold a cell whose after reading is missing as not evaluated instead of passed. Trigger: ecss, bare-cell-failure-modes, bare-cell-subgroup-test-failure, bare-cell-electrical-degradation-allowance, bare-cell-open-circuit-failure, bare-cell-disqualifying-condition, bare-cell-subgroup-failure-allowance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-failure-criteria, e-st-20-08c-clause-7-6-1, bare-cell-failure-modes, bare-cell-subgroup-test-failure, bare-cell-electrical-degradation-allowance, bare-cell-open-circuit-failure, bare-cell-disqualifying-condition, bare-cell-subgroup-failure-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Failure Criteria (space-systems/ecss/e2008-bare-cell-failure-criteria)

Use when the task is clause 7.6.1 of ECSS-E-ST-20-08C: the conditions
that mark a bare solar cell failed during a subgroup test and the
inspection that follows it. This leaf reads one declared criteria set and
the subgroup's before and after records, and returns a state per cell
with every failure mode named, plus the subgroup rollup.

## Domain quick reference

- The question is per cell, not per subgroup. A subgroup whose average
  loss looks comfortable can still contain a cell that is now a failed
  article, and averaging is exactly what hides it. The rollup comes after
  the individual states and never replaces them.
- Two independent kinds of condition fail a cell. A measured one, where
  a parameter has lost more than its declared allowance, and an observed
  one, where the inspection found a condition the specification listed as
  disqualifying. The second needs no measurement at all, so a cell that
  reads perfectly and shows a listed condition is still failed.
- Every mode is named, not the first one found. A cell that lost power,
  lost current and shows a crack has told three different stories about
  what happened to it, and the investigation that follows needs all
  three; a single first-hit verdict throws two of them away.
- Loss is taken against that cell's own before reading. Comparing an
  after reading against a lot mean, a datasheet typical or a neighbouring
  cell measures the population, not the degradation, and degradation is
  what the criteria are written about.
- A cell that has stopped conducting is its own mode. The fractional
  loss already exceeds any allowance, but naming the open circuit
  separately is what tells the investigation it is looking for a broken
  contact rather than a gradual electrical loss.
- An absent after reading is not a pass. A cell nobody finished
  measuring is not evaluated: it cannot be counted clean, it cannot be
  counted failed, and a subgroup carrying one cannot be closed either
  way until the reading exists.
- A reading that improved sharply is a setup defect. Cells do not gain
  appreciable power across a stress test, so an apparent gain past a
  small credible band says the two readings were not taken the same way
  and the record is refused rather than scored.
- The allowances live in the declared specification. A criteria set with
  no reference behind it produces verdicts nobody can audit, so an
  unreferenced set closes the assessment instead of passing it.
- How many failed cells a subgroup may carry is a separate, declared
  question. It is a subgroup allowance, not arithmetic on the cells, and
  it never changes an individual cell's state.

## Workflow

1. Validate the subgroup policy first: the largest failed share the
   subgroup may carry, the share of the before current below which a
   cell counts as open, the credible gain band and the marginal band. A
   share above one is refused rather than used.
2. Validate the declared criteria set: a specification reference, an
   allowance for each measured parameter, and the list of observed
   conditions that fail a cell on presence. A repeated or unnamed
   condition is a transcription defect and is refused.
3. Read each cell record back: a non-blank identifier, a positive before
   reading for every parameter, no negative after reading, and no
   observed condition outside the declared list. An implausible gain
   closes the record rather than scoring it.
4. Take each parameter's loss against its own allowance, admitting a
   tie, and record the mode for every allowance that was passed.
5. Compare the after current against the open-circuit floor derived from
   that cell's own before current, and record the open-circuit mode
   separately from the current loss it also produces.
6. Add a mode for every declared condition the inspection observed, then
   settle the cell state: failed if any mode is present, not evaluated
   if an after reading is missing, otherwise passed.
7. Roll the subgroup up: the failed share against the declared
   allowance, the modes seen across the subgroup, the cells nobody
   finished measuring, and advisories for passed cells that spent nearly
   all of an allowance. Close on one verdict: criteria not established,
   subgroup not evaluable, within the failure allowance, or the failure
   allowance exceeded.

## Pitfalls

- Judging the subgroup on its mean loss. The criteria decide articles,
  and a comfortable mean over a cell past its allowance passes a cell
  the specification fails.
- Stopping at the first mode. The remaining modes are the evidence the
  failure investigation works from, and they are unrecoverable from a
  one-word verdict.
- Treating the inspection as a second opinion on the measurement. A
  listed observed condition fails the cell by itself, whatever the
  readings say.
- Counting an unmeasured cell as clean. Unknown is not zero; a missing
  after reading leaves the cell and the subgroup open, not passing.
- Scoring a cell that reads better after the test than before it. That
  is two different measurement setups, not a result, and it is refused.
- Comparing a loss with its allowance by bare arithmetic. Loss is a
  ratio of two measured readings, so a loss exactly on an allowance can
  evaluate a few units in the last place above it; the comparison
  absorbs that while the allowance stays untouched.
- Applying allowances from memory. The declared specification is the
  only source of the numbers, and a criteria set with no reference
  cannot be audited afterwards.

## Behavior contract (gate 3)

The policy validation, the declared criteria validation with its
condition list, the cell record read-back with its implausible-gain and
undeclared-condition refusals, the per-parameter loss against its own
allowance with an admissible tie, the open-circuit mode, the observed
condition mode, the every-mode-named rule, the passed, failed and not
evaluated states, the subgroup failed fraction against its allowance,
the marginal advisories and the subgroup verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_bare_cell_failure_criteria.py against
scripts/e2008_bare_cell_failure_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_failure_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
