---
name: e1024-control
description: "Use when assess interface baseline control and change approval under ECSS-E-ST-10C §5.5: establish an approved baseline from candidate interface documents, categorize each change request as minor (no functional impact) or major (affecting interface definition, timing, or physical properties), verify Interface Change Board quorum before voting, evaluate vote outcome by simple majority, confirm all required stakeholders have formally agreed to the interface document, and maintain an auditable change log for every state transition. Trigger: ecss, e-st-10-system-scope, interface-control, interface-baseline, change-control, interface-change-board, icb, agreement-process."
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
  tags: [ecss, e-st-10-system-scope, interface-control, interface-baseline, change-control, interface-change-board, icb, agreement-process]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Control and Approve Interfaces (space-systems/ecss/e1024-control)

Use when the task is to assess and enforce the interface baseline control
and change approval process defined in ECSS-E-ST-10C §5.5 — covering the
establishment of a formal interface baseline, change request categorization,
Interface Change Board (ICB) governance, and stakeholder agreement tracking.

## Domain quick reference

- §5.5 establishes that interface definitions must be placed under formal
  baseline control before a project phase gate. An interface baseline is a
  versioned, approved set of interface documents; its state progresses from
  draft through proposed to approved, and may be superseded by a later
  revision when a change is incorporated.
- Change requests against a baselined interface are categorized as minor
  (editorial corrections, no change to functional, timing, or physical
  definition) or major (any change that alters the interface functional
  specification, timing constraints, or physical connector/signal
  properties). Minor changes may be incorporated by the interface owner
  without a full ICB vote; major changes require ICB deliberation.
- The Interface Change Board is the formal governance body for major
  interface changes. A valid ICB vote requires a pre-defined minimum quorum
  of board members to be present; the change is approved when yes votes
  exceed no votes among participating members, with abstentions counted
  but not decisive.
- Agreement completion is a prerequisite for transitioning an interface
  document from proposed to approved. Every required signatory (interface
  owner, affected subsystem leads, system engineer) must have formally
  agreed; a document with missing agreements cannot be baselined as
  approved.
- Every baseline state transition must be recorded in an auditable change
  log: the actor, the previous and new state, and the reason. A baseline
  with no change log entries fails the audit check.

## Workflow

1. Identify all candidate interface documents and confirm each has a unique
   interface identifier, a version string, a designated owner, and an
   initial baseline state of draft.
2. For each incoming change request, record the requester and description,
   then categorize the change: if the change affects interface functional
   definition, timing constraints, or physical properties, it is major;
   otherwise it is minor. Reject any change request that lacks a requester
   identifier.
3. For major change requests, convene the ICB: confirm the required quorum
   is met before opening the vote. If quorum is not met, the vote is
   invalid and must be rescheduled. Collect a yes/no/abstain vote from each
   ICB member and reject any vote that does not use one of those three
   values. Determine the outcome by comparing yes and no counts; abstentions
   do not count toward either side.
4. Once a change is approved (minor by owner decision, major by ICB vote),
   advance the interface document state: draft → proposed (submitted for
   review), proposed → approved (all agreements confirmed and vote passed),
   approved → superseded (replaced by a new revision). Validate that the
   requested state transition is permitted before recording it; reject any
   skip or reverse transition.
5. Before transitioning any interface from proposed to approved, check
   agreement completeness: every required signatory must have a recorded
   agreement entry. Identify any missing signatories and report them as
   open findings.
6. Record every state transition in the interface's change log with the
   actor, prior state, new state, and reason. Verify the change log is
   non-empty before reporting the interface as baselined.

## Pitfalls

- Applying a change directly to an approved baseline without creating a
  new change request — all modifications must enter the categorization and
  ICB pipeline, even corrections that appear trivial.
- Treating an ICB vote as valid when quorum is not met — the vote result
  has no standing without the required number of board members present.
- Counting abstentions as yes votes or using a plurality of all members
  (including abstentions) as the approval threshold — abstentions are
  neutral; only the yes-vs-no comparison determines the outcome.
- Allowing a skip transition (e.g., draft directly to approved) because it
  appears expedient — the proposed state carries the agreement-checking
  step and must not be bypassed.
- Treating agreement completeness as optional when a deadline is pressing —
  a missing signatory agreement is a blocking finding, not a warning.

## Behavior contract (gate 3)

The baseline state machine, change categorization, ICB quorum and voting,
and agreement completeness logic are exercised by the gate 3 contract test:
scripts/test_e1024_control.py against scripts/e1024_control_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1024_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
