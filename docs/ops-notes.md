# Ops notes — AeroSkills

Durable operations notes for the AeroSkills repo (private, arjun-0077/aeroskills).
Ops Manager keeps incident records and runbook facts here. Supersede-not-delete:
append, never rewrite history.

## CI billing block — GitHub Actions attest runs (2026-08-31)

Status: BLOCKED. Escalated to the account owner (CEO/founder territory — Ops
does NOT spend money or change billing settings).

Evidence (verified live via `gh` on 2026-08-31):

- Every `attest` workflow run fails at JOB ALLOCATION: zero steps executed,
  runs finish in 3–5s, `gh run view <id> --log` returns "log not found"
  (no log exists because no job ever ran).
- Latest confirmed run: 33354084074 (push "Fix K-Dense star count in
  1-pager", 2026-08-31 03:30 UTC), job 99372802521, conclusion failure in 4s.
- GitHub annotation, verbatim: "The job was not started because recent
  account payments have failed or your spending limit needs to be increased.
  Please check the 'Billing & plans' section in your settings" — attest: .github#1.
- All 5 attest runs of 2026-08-31 show the same annotation: 33353159328,
  33353392069, 33353767092, 33353951693, 33354084074. Earlier runs
  (33351561882, 33352037370, 33352176933) fail the same way.
- Wiring is correct by inspection: `.github/workflows/attest.yml` triggers on
  push to main and runs the same three gates as local `make attest`
  (number-snapshot-offline, brief-audit, content-policy-sweep). No runner is
  ever allocated, so the failure is the billing block, not the workflow.

Impact: CI attest never executes. Local `make attest` (3/3) is the only
working attestation path until the block clears. Do NOT claim green CI until
a run actually passes (verify-before-credit).

Resolution: account owner (arjun-0077) must resolve payments / spending limit
in GitHub "Billing & plans". Out of Ops scope.
