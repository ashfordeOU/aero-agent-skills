---
name: q7050-limit-exceedance-handling
description: "Assess a cleanliness limit exceedance and decide the disposition it owes under ECSS-Q-ST-70-50C. Use when a monitoring or verification result has come back above its action limit, the affected hardware carries a sensitivity category and a known exposure, and the exceedance has to become an impact statement, a corrective action and a re-verification rather than a note in a log. Computes the exceedance ratio and the quantity the exposure deposited, categorizes severity from ratio and sensitivity together, selects a disposition constrained by what the hardware permits, requires consecutive conforming re-verifications, and grades the closure package for what it is missing. Trigger: ecss, q-st-70-50, cleanliness-exceedance-ratio, hardware-sensitivity-category, exposure-deposition-estimate, corrective-action-disposition, consecutive-reverification-run, exceedance-closure-package."
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
  tags: [ecss, q-st-70-cleanliness-monitoring-scope, q7050-limit-exceedance-handling, cleanliness-exceedance-ratio, hardware-sensitivity-category, exposure-deposition-estimate, corrective-action-disposition, consecutive-reverification-run]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Monitoring — Limit Exceedance Handling (space-systems/ecss/q7050-limit-exceedance-handling)

Use when the task is handling a result above the ECSS-Q-ST-70-50C
cleanliness limit — establishing what the exceedance did to the hardware,
what has to be done about it, and what has to be shown before the finding
can be closed.

## Domain quick reference

- Cleanliness limits span orders of magnitude, so an exceedance is a
  ratio, not a difference. Twice the limit and fifty times the limit are
  different events, and the arithmetic difference between them says
  nothing without the limit beside it.
- The same ratio is not the same event on different hardware. A ratio
  over a bare optical surface and the same ratio over a structural
  bracket differ by the sensitivity of what was exposed, so severity is
  read from the pair and not from the ratio alone.
- An impact statement needs a quantity. The airborne concentration, the
  deposition velocity at the size of interest and the exposure duration
  give the areal density the exposure actually deposited, which is what
  a contamination budget can absorb or cannot; an adjective is not an
  impact assessment.
- The disposition is constrained by what the hardware permits, not only
  by the severity. Cleaning is a disposition only for something that can
  be cleaned, and any disposition that rests on re-verification is
  unavailable when the item cannot be re-verified once reassembled.
- Re-verification is a run, not a result. A conforming measurement after
  a non-conforming one restarts the count, because the question is
  whether the process is back under control and a single good sample
  from an unstable process is scatter.
- Closure has parts: impact assessment, root cause, corrective action,
  re-verification, approval. A package missing one of them is an open
  finding regardless of how good the others are, and a corrective action
  with no impact assessment behind it fixed something nobody sized.

## Workflow

1. Establish whether there is an exceedance at all, as a ratio; a result
   exactly on the limit is not one, and the equality is absorbed by a
   named tolerance rather than by moving the limit.
2. Weight the ratio by the sensitivity category of the exposed hardware
   and categorize the severity from the weighted ratio.
3. Estimate the deposited areal density from the exposure so the impact
   statement carries a number, and raise a finding when no exposure data
   was supplied.
4. Select the disposition from the severity, constrained by whether the
   item can be cleaned and whether it can be re-verified.
5. Set the number of consecutive conforming re-verifications the
   severity owes and grade the trailing run actually achieved.
6. Grade the closure package against its required items and name what is
   missing.
7. Report the severity, the disposition, the deposited quantity, the
   re-verification grading, the closure grading and every finding.

## Pitfalls

- Reporting the exceedance as a difference. Ten counts over a limit of
  ten and ten counts over a limit of ten thousand are the same
  difference and entirely different events.
- Grading severity on the ratio alone. Sensitivity of the exposed
  hardware is half of the input, and leaving it out grades an exposed
  optic exactly like a painted panel.
- Closing on a corrective action with no impact assessment. The action
  may be correct and still leave nobody able to say what the exposure
  cost, which is the question the programme will ask later.
- Counting re-verifications cumulatively. A conforming result after a
  non-conforming one restarts the run; totalling the conforming results
  across the campaign closes a process that never stabilised.
- Dispositioning an uncleanable item by cleaning it. The disposition has
  to be reachable for that hardware, and an exposure that can be neither
  cleaned nor re-verified is an engineering or a rejection decision, not
  a cleaning instruction.

## Behavior contract (gate 3)

The exceedance ratio, sensitivity weighting, severity categorization,
deposition estimate, disposition selection, consecutive re-verification
run and closure-package grading are exercised by the gate 3 contract
test: scripts/test_q7050_limit_exceedance_handling.py against
scripts/q7050_limit_exceedance_handling_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7050_limit_exceedance_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
