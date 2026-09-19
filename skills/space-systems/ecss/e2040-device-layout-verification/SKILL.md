---
name: e2040-device-layout-verification
description: "Verify a device layout and its post layout netlists against the plan ECSS-E-ST-20-40C 5.6.3 asks for: fold every nominated check and every executed run onto recognised names, refuse a check answered on a netlist view that cannot carry it such as static timing taken before extraction, reconcile reported violations against the waivers covering them so none is left neither fixed nor waived, and report a rationale or approver nobody recorded. Use when a layout verification campaign is being planned, run or closed out. Trigger: ecss, e-st-20-electrical-scope, device-layout-verification, layout-check-netlist-view, post-layout-netlist-timing, layout-violation-waiver-record, planned-check-execution-coverage, layout-drc-lvs-closure."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-layout-verification, device-layout-verification, layout-check-netlist-view, post-layout-netlist-timing, layout-violation-waiver-record, planned-check-execution-coverage, layout-drc-lvs-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Layout — Verification (space-systems/ecss/e2040-device-layout-verification)

Use when the task is the checking duty of ECSS-E-ST-20-40C 5.6.3 --
saying whether the layout and the netlists taken back out of it have
actually been checked against everything the verification plan nominated,
and whether what the checks found has been closed.

## Domain quick reference

- The plan is the frame. Coverage is measured against the checks the plan
  nominated, not against the checks that happened to run, so a campaign
  cannot improve its figure by running something easy.
- A check that reported violations is the check working. The failures
  that matter are the check that never ran, the check answered on the
  wrong netlist view, and the violation closed by a waiver nobody can
  justify later.
- The netlist view decides whether a run means anything. Static timing,
  power integrity and back-annotated simulation need the extracted view;
  geometry and connectivity checks need the routed layout; formal
  equivalence is the one check that legitimately runs pre-layout.
- A check run on an unsuitable view produces real numbers about a device
  that does not exist yet, and it looks identical in a results table to
  the run that was supposed to happen.
- An aborted run is an absent result, not a clean one. It contributes
  nothing to coverage.
- A waiver needs a rationale and an approver. Without both the violation
  count reaches zero and nobody can say later why it was allowed.
- More waivers than violations is an input defect, not a finding. The
  arithmetic has gone wrong somewhere upstream and the campaign cannot be
  scored.
- A coverage figure landing exactly on its goal meets it, so the
  comparison absorbs representation error.

## Workflow

1. Fold the nominated checks onto recognised names and refuse a check
   nominated twice.
2. Fold the executed runs the same way: the check, the netlist view it
   was answered on, the outcome, the violation count and the waivers.
   Refuse a check executed twice and an outcome reporting violations with
   a count of zero.
3. Report every planned check with no execution, and every run the plan
   does not nominate.
4. Report every run answered on a view unable to carry it, naming the
   views that would have worked.
5. Reconcile violations against waivers per check, refusing more waivers
   than violations and reporting whatever is left neither fixed nor
   waived.
6. Report every waiver with no rationale and every waiver with no
   approver, separately.
7. Compute coverage over the planned checks, counting only runs that
   completed on a suitable view, and compare it with the goal absorbing
   an exact landing.

## Pitfalls

- Reading a results table as coverage. A check that never executed
  reports nothing, and nothing looks a great deal like clean.
- Accepting static timing on the pre-layout netlist. The numbers are
  real, the device they describe has no interconnect, and the run is
  indistinguishable from the correct one at a glance.
- Counting an aborted run as an answer. It has to drop out of the
  coverage numerator or the campaign scores itself for work it abandoned.
- Waiving a violation with no rationale and no approver. The count goes
  clean and the justification cannot be reconstructed at the next review.
- Failing a campaign whose coverage lands exactly on its goal. A
  three-in-four division can sit a unit in the last place below the
  figure it is compared with.

## Behavior contract (gate 3)

The check and view folding, view-suitability rule, planned-versus-
executed reconciliation, aborted-run handling, waiver reconciliation and
coverage comparison with exact goal landings are exercised by the gate 3
contract test: scripts/test_e2040_device_layout_verification.py against
scripts/e2040_device_layout_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_layout_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
