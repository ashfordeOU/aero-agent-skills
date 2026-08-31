# R3 view: Publish-readiness audit — Verification + Legal (Bheem)

**Date:** 2026-08-31 · **Status:** APPROVE (7/7 PASS), founder-gated publish
**Repo/HEAD:** ~/AeroSkills @ 82a362d17585801e05ae6baa80abd602a58cb0bd (main, private, tree clean)
**Related:** security/audits/2026-08-31-r1-verification-legal-finance.md;
security/audits/2026-08-31-r2-p21-verification-legal-finance.md;
docs/harness-contract.md; standards-map.yaml; STANDARDS.md; NOTICE;
README.md; ops/automation/content-policy-sweep.sh

Independent publish-readiness audit per founder instruction. Every check
re-run FRESH with real commands at HEAD; no report trusted.

## Check results (evidence, not assertion)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Secrets | PASS | `git ls-files \| grep -iE '\.env\|credential\|secret\|token\|api.?key'` -> exit 1 (0 hits); `grep -rniE 'sk-[a-z0-9]{20,}\|BEGIN (RSA\|EC\|OPENSSH) PRIVATE\|ghp_[a-zA-Z0-9]{20,}'` excluding .git -> exit 1 (0 hits) |
| 2 | Personal data | PASS | repo-wide email/phone/name greps hit only official government contacts in research/briefs (docs) and the `you@example.com` placeholder in CONTRIBUTING.md; zero hits in code/config |
| 3 | Legal stack | PASS | LICENSE = Apache-2.0 full text; NOTICE = Ashforde OU + export-control statement citing EU 2021/821 GTN public-domain exclusion; CITATION.cff (Ashforde OU, Apache-2.0, v0.1.0); SECURITY.md (private reporting, disclosure policy); CONTRIBUTING.md (workflow, DCO, ITAR/EAR/USML contributor certification); STANDARDS.md; README compliance banner standard classes match standards-map.yaml exactly (5 gated proprietary-sold RTCA/SAE/IAQG, ECSS/FAR/CS-25 free, SEP-2640 open spec) |
| 4 | Policy enforcement | PASS | `bash ops/automation/content-policy-sweep.sh` -> exit 0, "0 red-flag hits in publishable content" |
| 5 | Gates green | PASS | `make validate` -> exit 0, 5/5 (gate1 spec-lint 12/12, gate2 desc-lint 12/12, gate3 contract tests 12/12, gate4 no-verbatim 0 markers + 0 objective-table blocks, gate5 Hit@1 28/28); `make attest` -> exit 0, 3/3 (number-snapshot offline 5 OK, brief-audit 26 files, content-policy-sweep 0 hits); `bash ops/automation/test/run-tests.sh` -> ALL TESTS PASS, exit 0 (21/21: 7 negatives N1-N5/N7, 8 spec-lint negatives, 6 at-rest greens) |
| 6 | Tag v0.1.0 | PASS | annotated tag local id d47a8141 == remote id d47a8141, peels to HEAD 82a362d (ls-remote `^{}`); `git status --porcelain` = 0 post-gate; one main branch (local + origin/HEAD -> origin/main) |
| 7 | Visibility | PASS | `gh repo view arjun-0077/aeroskills --json visibility` -> {"isPrivate":true,"visibility":"PRIVATE"} |

## Verification verdict

APPROVE, 7/7 PASS. Gates replayed fresh at HEAD: validate 5/5 exit 0
(Hit@1 now 28/28 incl. 3 cross-domain probes), attest 3/3 exit 0,
run-tests.sh ALL PASS 21/21 exit 0. Negative fixtures exit 1 as asserted,
so the gates provably detect drift/violations. Tree clean at rest after
all runs. No network or side effects from gate runs.

## Legal verdict

APPROVE. Compliance flags enforced (gate1): 12/12 STANDARDS-REF,
license Apache-2.0, gated standards reference-only. No verbatim gated
text (gate4 0 markers, 0 objective-table blocks). README banner and
NOTICE are hygiene-not-mechanism with the EU 2021/821 GTN public-domain
exclusion cited; disclaimers cover non-affiliation and user
responsibility. CONTRIBUTING carries ITAR/EAR/USML contributor
certification and DCO.

## Conditions / residuals (non-blocking for this checklist)

1. Standing R2 item: legal policy instrument (legal/policy/
   export-control-policy.md with owner, effective date, review cadence)
   still absent. NOTICE + banner carry the substantive statement with
   rule cited, so this is a founder legal-sign-off polish item, not a
   publish blocker on these 7 checks.
2. Publish itself is founder-gated (README: "release is founder-gated";
   AGENTS.md VETO domain). Audit evidence lives here; flip-to-public is
   the founder's call.
