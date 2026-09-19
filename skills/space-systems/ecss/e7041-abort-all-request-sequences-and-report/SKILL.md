---
name: e7041-abort-all-request-sequences-and-report
description: "Execute the whole-engine abort sweep of ECSS-E-ST-70-41C clause 6.21.5.8 and assemble the report it owes the ground. Use when every executing request sequence must stop at once and the operator cannot name them: refusing an identifier list that would narrow the coverage the request exists for, attempting every executing sequence so a fault on one never stops the sweep reaching the rest, emitting one entry per sequence running when the sweep began with its step reached and outcome, and computing the totals from the assembled entries so a truncated transfer is detectable. Trigger: ecss, e-st-70-41-packet-utilization-scope, request-sequence-abort-all, request-sequence-abort-sweep-coverage, request-sequence-abort-all-report, request-sequence-abort-fault-isolation."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-abort-all-request-sequences-and-report, request-sequence-abort-all, request-sequence-abort-sweep-coverage, request-sequence-abort-all-report, request-sequence-abort-fault-isolation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Abort All Request Sequences and Report (space-systems/ecss/e7041-abort-all-request-sequences-and-report)

Use when the task is the whole-engine abort of ECSS-E-ST-70-41C clause
6.21.5.8 -- stopping every request sequence the engine is running and
reporting what the sweep found, with the four normative items that
clause places on the coverage and the report.

## Domain quick reference

- The single-sequence abort stops something the operator identified.
  This request exists for the case where they cannot identify
  anything: an anomaly of unknown origin, a safe-mode handover, a pass
  closing with sequences still running.
- Its whole value is coverage, so it takes no identifier list.
  Narrowing it to what the requester already suspects is the one
  modification that removes the reason to have it.
- Every executing sequence is attempted. An abort that fails on one
  must not stop the sweep reaching the others, because the sequences
  that would then keep running are chosen by store order rather than
  by anything operational.
- A partly-completed sweep reported as a success is worse than no
  sweep at all. The operator stops looking, and the sequences that
  survived keep releasing requests.
- The report entry set is fixed at the moment the sweep begins. A
  sequence that finished on its own during the sweep still gets an
  entry, because the ground is reconciling against what was running.
- Each entry carries the step reached, so the released requests -- the
  ones the sweep did not and cannot recall -- are countable from the
  report rather than guessed at.
- The totals are computed from the assembled entries. Computed from
  the store, they agree with the intent instead of the content, and a
  truncated transfer passes the check that was added to catch it.

## Workflow

1. Refuse an identifier list before anything else, including an empty
   one; an empty list is still a request to narrow the sweep.
2. Normalize the store and reject a duplicate identifier, a released
   count above the body length, a sequence executing while not loaded
   or an inactive one claiming released requests.
3. Select every sequence in the executing state, in store order, and
   fix that set as the scope of the report.
4. Attempt each abort independently, recording an outcome per
   sequence; a fault on one produces a failed entry and the sweep
   carries on to the next.
5. Apply only the successful aborts to the store, leaving a faulted
   sequence executing so the ground can see it is still running.
6. Compute the totals from the entries, verify the report against its
   own totals, and close with the verdict, the identifiers still
   executing, and a finding for every fault and every sequence that
   had already released requests.

## Pitfalls

- Accepting an identifier list "for convenience". The sweep then
  covers what the operator already thought of, which is precisely the
  set that did not need a whole-engine abort.
- Stopping at the first failed abort. The sequences aborted are the
  ones whose identifiers sorted first, and the operator is told the
  engine is quiet when it is not.
- Reporting a partial sweep as complete. Nobody looks again, and the
  surviving sequences keep releasing requests into an anomaly.
- Marking a faulted sequence aborted in the store. The status report
  then agrees with the abort report and both are wrong together.
- Recomputing the entry set after the aborts. Sequences that did stop
  drop out of the report, and the ground cannot reconcile the sweep
  against what was running when it was commanded.
- Taking the totals from the store rather than the entries. A
  truncated downlink then satisfies its own completeness check.
- Treating the sweep as a recall. Requests already released are
  executing in their destinations, and only the per-entry step counts
  reveal how many of them there are.

## Behavior contract (gate 3)

The selector refusal, store normalization, executing-set selection,
per-sequence abort attempt with fault isolation, entry assembly in
store order, entry-derived totals, report self-consistency check,
partial application to the store and the fault and recovery findings
are exercised by the gate 3 contract test:
scripts/test_e7041_abort_all_request_sequences_and_report.py against
scripts/e7041_abort_all_request_sequences_and_report_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_abort_all_request_sequences_and_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
