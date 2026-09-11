---
name: e1002-closeout-docs
description: "Use when consolidate verification close-out documentation under ECSS-E-ST-10C §5.4.4.2: gather all verification reports at the applicable review milestone, merge per-requirement verification statuses into a consolidated register, identify requirements that failed or were not verified and determine whether each needs a waiver or a deviation, draft register entries with technical justification and risk-level tag, and confirm every requirement carries a final disposition (Pass, Fail, Waived, or Deferred) before the review board gate. Trigger: ecss, e-st-10-system-scope, closeout-documents, verification-consolidation, waiver-register, deviation-register, review-gate, close-out."
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
  tags: [ecss, e-st-10-system-scope, closeout-documents, verification-consolidation, waiver-register, deviation-register, review-gate, close-out]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification Close-Out Documents — §5.4.4.2 (space-systems/ecss/e1002-closeout-docs)

Use when the task is to consolidate verification reports and issue close-out
documentation at a review milestone under ECSS-E-ST-10C §5.4.4.2 — gathering
per-requirement statuses, populating a waiver/deviation register for non-
compliant items, and confirming the consolidated register is gate-ready before
the review board.

## Domain quick reference

- §5.4.4.2 requires two complementary outputs at each applicable review gate:
  a consolidated verification register (one row per requirement, carrying
  the verification method, measured result, and final disposition) and a
  waiver/deviation register for every requirement that cannot carry a Pass
  disposition at the gate.
- Final dispositions are constrained to four values: **Pass** (requirement
  fully met by the reported evidence), **Fail** (requirement not met and no
  approved relief in place — blocks the gate), **Waived** (requirement
  permanently relaxed via an approved waiver or deviation entry), or
  **Deferred** (verification not yet performed — open item, allowed at the
  gate but must be tracked to closure).
- A waiver applies when a requirement is permanently relaxed for all units.
  A deviation applies when a specific unit or build does not meet the
  requirement for a bounded scope and time. Both require a written technical
  justification and a risk-level tag (LOW, MEDIUM, HIGH, or CRITICAL).
- Verification methods that may appear in the consolidated register are:
  Test, Analysis, Inspection, and Review — matching the four methods defined
  in ECSS-E-ST-10C §5.3.
- The gate is blocked only by Fail dispositions. Deferred and Waived items
  are allowed at the gate and must be tracked as open items in the project's
  risk and action-item log.

## Workflow

1. Collect the individual verification reports for every requirement in scope
   at the milestone. Each report provides: requirement identifier, verification
   method used, measured or observed result, pass/fail status, and any
   relevant notes. Reject a report with an unknown method or an empty
   requirement identifier before it enters the register.
2. Consolidate the reports into a single register, one row per requirement.
   Where the status is Pass the disposition is set to Pass. Where the status
   is Fail the disposition is set to Fail. Where the requirement has not yet
   been verified the status is recorded as Not_Verified and the disposition
   is set to Deferred.
3. Identify every requirement with a Fail or Deferred disposition and decide
   whether a waiver (permanent relaxation) or a deviation (bounded, unit-
   specific) is appropriate. For each such requirement that will receive
   relief, draft a waiver/deviation register entry containing: the requirement
   identifier, the entry type (WAIVER or DEVIATION), a technical justification
   describing why the requirement cannot be met and why the risk is acceptable,
   and a risk-level tag.
4. Apply the approved waiver/deviation entries to the consolidated register:
   update any Fail or Deferred disposition to Waived where an approved entry
   exists. Fail dispositions with no approved entry remain as Fail and block
   the gate.
5. Run the gate-readiness check: the gate is ready if no requirement carries
   a Fail disposition. Collect all remaining Fail items as blocking
   requirements. Collect all Deferred and Waived items as open items for
   the tracking log.
6. Produce the two close-out documents: the finalised consolidated
   verification register (all requirements, final dispositions) and the
   waiver/deviation register (all entries with justification and risk level).
   Both are issued to the review board as part of the §5.4.4.2 close-out
   package.

## Pitfalls

- Treating Not_Verified as a pass because no failure was observed — a
  requirement that was never verified carries a Deferred disposition and must
  remain in the open-items tracking log; it cannot be silently dropped.
- Mixing waivers and deviations: a waiver permanently changes the requirement
  for all units; a deviation is time- and unit-bounded. Using the wrong type
  causes the wrong obligation to flow to the customer and the review board.
- Leaving a Fail disposition in the register without a corresponding waiver
  or deviation entry — a Fail with no approved relief blocks the review gate
  and cannot be papered over by marking the row as Deferred.
- Omitting the risk-level tag from a waiver/deviation entry — the tag drives
  the approval authority level (programme manager vs. customer sign-off) and
  is mandatory for the entry to be actionable.
- Issuing the consolidated register without cross-checking it against the
  requirements baseline — requirements added or removed since the last
  milestone may be missing from or spuriously present in the register.

## Behavior contract (gate 3)

The consolidation, waiver/deviation entry construction, disposition update,
gate-readiness check, and register summary logic are exercised by the gate 3
contract test: scripts/test_e1002_closeout_docs.py against
scripts/e1002_closeout_docs_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_closeout_docs.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
