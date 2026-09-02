# Ops notes - Aero Agent Skills

Durable operations notes for the Aero Agent Skills repo (private, arjun-0077/aero-agent-skills).
Ops Manager keeps incident records and runbook facts here. Supersede-not-delete:
append, never rewrite history.

## CI billing block - GitHub Actions attest runs (2026-08-31)

Status: BLOCKED. Escalated to the account owner (CEO/founder territory - Ops
does NOT spend money or change billing settings).

Evidence (verified live via `gh` on 2026-08-31):

- Every `attest` workflow run fails at JOB ALLOCATION: zero steps executed,
  runs finish in 3–5s, `gh run view <id> --log` returns "log not found"
  (no log exists because no job ever ran).
- Latest confirmed run: 33354084074 (push "Fix K-Dense star count in
  1-pager", 2026-08-31 03:30 UTC), job 99372802521, conclusion failure in 4s.
- GitHub annotation, verbatim: "The job was not started because recent
  account payments have failed or your spending limit needs to be increased.
  Please check the 'Billing & plans' section in your settings" - attest: .github#1.
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

## Regression-guard hardening - P3.5 REWORK R3 (2026-08-31)

Status: DONE at e783f56 → new HEAD. Two R3 re-grade gaps closed with
test-first evidence (TDD red → green):

1. Scout 9/10: stale-number-guard missed the literal pack-count phrase and
   the literal corpus-ratio form (see guard header for exact tokens).
   - Added the literal pack-count phrase (verified 0 legit live hits;
     harness-contract now says 'nine installable domain packs').
   - The bare corpus-ratio form '3/3' was NOT added - docs/ops-notes.md:30
     legitimately says 'make attest (3/3)' (attest is 3/3 by design), so a
     bare pattern would false-positive. Added only the corpus-context form
     (verified 0 legit live hits). Skip decision documented in guard header.
2. Content Writer 8/10: enumeration drift - docs/FAQ.md + docs/glossary.md
   + marketing/positioning-1pager.md enumerate the gated set as 5 while
   standards-map.yaml has 9 gated:true of 14 total. Root cause: the guard
   greps number patterns only, so "map covers 9 standards" passes while the
   map covers 14.
   - New guard ops/automation/gated-set-check.sh (+ gated_set_check.py):
     verifies numeric gated-set/map-coverage COUNT claims (digit + word
     forms) against the LIVE standards-map.yaml (repo root - note: the
     canonical map is repo-root standards-map.yaml, NOT
     ops/automation/standards-map.yaml). Rules R1 '<N> gated standards' == 9,
     R2 'covers/maps/spans <N> standards' == 14, R3 'all <N> of the gated
     standards' == 9.
   - Scope decision (documented in guard header): guard verifies COUNT
     claims. Pure name-list drift (FAQ listing 5 names without a number) is
     the Content Writer fix track - the live docs still carry those lists at
     HEAD and the task forbids editing copy from the ops lane, so gating
     them here would fail G8. Count-claim class now fails CI; name-list fix
     is Content Writer's.
   - Wired as N10 (stale fixture exit 1), N11 (clean fixture exit 0), G8
     (real repo exit 0) in ops/automation/test/run-tests.sh. Full suite:
     35/35 ALL PASS.
   - Negative control (both guards): planted the literal pack-count phrase
     plus a 5-gated enumeration plus a stale map-coverage count claim in a
     temp tree → stale-number guard exit 1 AND gated-set check exit 1;
     removed → both exit 0.

Gates at new HEAD: make validate 5/5 (gate5 Hit@1 66/66), make attest 3/3,
run-tests.sh ALL PASS (35/35), tree clean.
