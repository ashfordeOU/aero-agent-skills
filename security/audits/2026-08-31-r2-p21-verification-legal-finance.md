# R2 view: P2.1 discussion gate — Verification + Legal + Finance lens (Bheem)

**Date:** 2026-08-31 · **Status:** P2.1 gate review note, PASS (all lenses >=9)
**Repo/HEAD:** ~/AeroSkills @ 3a6bc77 (main, clean, synced)
**Related:** security/audits/2026-08-31-r1-verification-legal-finance.md;
docs/harness-contract.md; standards-map.yaml; STANDARDS.md; Makefile;
ops/automation/test/run-tests.sh; eval/hit1-corpus.yaml

## Verification — STRONG (10/10)

Independently replayed all gates at HEAD (this run, 2026-08-31):

- `make validate` -> exit 0. 5/5 gates:
  - gate1 spec-lint: 12/12 SKILL.md conformant (compliance-flags-ok)
  - gate2 desc-lint: 12/12 descriptions (action+use-when+trigger)
  - gate3 pytest-contract: 12 contract test files, stdlib-only, all pass
  - gate4 no-verbatim: 0 markers + 0 objective-table blocks (skills/, docs/)
  - gate5 hit1: 25/25 tasks Hit@1 (deterministic offline router)
- `make attest` -> exit 0. 3/3:
  - number-snapshot offline: K-Dense 39111/39398, cybersecurity 31700/31729,
    aerospace 21/21, mbse 22/22, derived largest 22/22
  - brief-audit: all quoted numbers resolve (22 files)
  - content-policy-sweep: 0 red-flag hits
- `bash ops/automation/test/run-tests.sh` -> ALL TESTS PASS, exit 0.
  19/19 = N1,N2,N3,N4,N5 (negatives) + S.no-license..S.empty-standards (8
  spec-lint negatives) + G1..G6 (at-rest greens). Gates provably detect
  drift/violations (fixtures exit 1 as asserted).
- Tree clean at rest after all runs (git status empty). No network, no
  side effects. CI wired: .github/workflows/attest.yml runs validate+attest
  on push/PR.

Tautology check: contract tests exercise sibling logic modules with
independent expected values — severity->DAL table (Catastrophic->A,
Hazardous->B, Major->C, Minor->D, No safety effect->E), coverage depth
(A=MC/DC, B=decision, C=statement, D/E=none), hand-computed traceability
completeness (3/5), orphan/derived handling, package/URI/readiness rules,
plus invalid-input raises throughout. Not tautologies.

## Legal — STRONG, one standing item (9.5/10)

- Compliance flags correct: 12/12 skills `compliance: STANDARDS-REF`,
  `license: Apache-2.0`, gated standards (do-178c/do-254/arp4754a/arp4761a/
  as9100) listed `reference-only: true`, `gated: false` consistent with
  standards-map.yaml. Enforced by gate1 (spec_lint), which passed.
- No verbatim standards text: gate4 zero markers + zero objective-table
  blocks; skill bodies are paraphrase style (sampled
  do178c/planning/SKILL.md).
- No mis-marking: content-policy-sweep 0 red-flag hits; README compliance
  banner uses the allowed 06 s8.3.9 formulation ("not ITAR/EAR-controlled
  technical data", hygiene-not-mechanism).
- Enforcement stack closed vs R1: LICENSE, NOTICE, CONTRIBUTING.md,
  SECURITY.md, STANDARDS.md, standards-map.yaml, per-skill frontmatter,
  sweep, CI all present now.
- Standing (non-blocking, pre-publish): legal policy instrument
  (legal/policy/export-control-policy.md with effective date/owner/review
  cadence) still absent — required for founder legal sign-off at publish
  GO, out of P2.1 scope. Minor: buyer README Roadmap/"What's here" still
  describes only the seed skill though 12 are shipped (draft; polish item).

## Finance — STRONG (10/10)

- Zero money exposure: finance/ contains README.md only — no ledger, no
  pricing model, no invoices (pricing HOLD respected; nothing committed).
- Buyer artifacts carry no pricing/offers; README star request is not money.
- No VETO triggers: gates offline/deterministic; no git push, publish, or
  spend paths in ops/automation; no tokens found in repo; release is
  founder-gated ("Draft v0.1, in-tree only").
- Internal target numbers (EUR 10k MRR, Vecteur 200-1,200 EUR/seat/mo) live
  only in research/build reports as labeled targets/observations — not
  exposure. Any future money ask >EUR 50 enters a ledger before the gate
  (AGENTS.md VETO).

## Verdict

P2.1 discussion gate PASS. All lenses >= 9.0 (team bar 9.0).
Verification 10, Legal 9.5, Finance 10 -> Bheem 9.5/10.
