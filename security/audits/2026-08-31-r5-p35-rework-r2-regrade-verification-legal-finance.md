# AeroSkills P3.5 rework R2 RE-GRADE (R3) — Bheem (Verification + Legal + Finance)

Date: 2026-08-31
HEAD graded: a6367b712ba0d027b56b08eb738457821bfb8f17
Prior grade: Bheem 10/10 PASS at d61b61c (note r4); team rework R2 landed at
a6367b7 (marketing stale numbers fixed + stale-number guard + harness-contract
live counts + expansion-pipeline EXECUTED banner).
This audit: replay ALL gates FRESH independently at HEAD; verify legal surface
intact; verify stale-number guard negative/positive controls myself.

## Verification (replayed FRESH at HEAD a6367b7)

| Gate | Result | Evidence |
|---|---|---|
| make validate | PASS exit 0 | 5/5 REAL gates: spec-lint 36 SKILL.md conformant, desc-lint 36, pytest-contract 27/27, no-verbatim 0 markers in 5 roots (skills/, docs/, README.md, STANDARDS.md, NOTICE) + 0 objective-table blocks, gate5 hit1 = **66/66 tasks Hit@1** (deterministic offline router) |
| make attest | PASS exit 0 | 3/3: number-snapshot offline 5/5 OK (K-Dense 40020 vs expected 39925, within tolerance), brief-audit 29 files resolve, content-policy-sweep **0 red-flag hits** |
| bash ops/automation/test/run-tests.sh | ALL TESTS PASS exit 0 | N1-N7 negatives, S.x8 spec-lint compliance flags, P1-P9 pack_inventory (P2: 9 packs / 27 skills), G1-G7 at-rest greens, and the R2 additions: **N8** stale-number guard flags planted stale counts (exit 1), **N9** exempts dated plans/ (exit 0), **G7** guard on real repo exits 0 |
| make packs | PASS exit 0 | packs=9 skills=27 |
| Stale-number guard (run by me directly, not via run-tests) | PASS | Negative control: `bash ops/automation/stale-number-guard.sh ops/automation/test/fixture-stale-numbers` -> exit 1, flags ALL 7 patterns in marketing/stale.md AND docs/stale.md. Positive/exemption control: `... fixture-stale-plans-only` -> exit 0 (dated plans/ exempt, supersede-not-delete). Live repo: exit 0. Non-vacuous proven on both sides. |
| harness-contract.md live counts | PASS | On disk: P2.1 para "twenty-seven published skills"; P3.6 para "nine installable domain packs"; gate-5 table "66/66 corpus tasks"; gate-5 detail "sixty-six active tasks (58 domain + 8 adversarial xp1-xp8)". Diff d61b61c..HEAD rewrote every stale count (12->27, 28->66, 5->9, 17->36 SKILL.md). |
| expansion-pipeline-P3.5.md EXECUTED | PASS | EXECUTED (2026-08-31) banner: "twenty-seven verified skills live across nine installable domain packs, make validate 5/5 REAL with gate 5 Hit@1 66/66, make attest 3/3, run-tests.sh ALL PASS"; wave 3 explicitly future work; numbers updated (twelve->twenty-seven skills, twenty-eight->sixty-six tasks, nine->fourteen mapped standards). |
| Marketing stale numbers | PASS | distribution-plan-P3.md: 28->66 corpus, 12->27 skills (3 places), Hit@1 28/28->66/66 (2 places). launch-draft: 12->27 skills. positioning-1pager: rewritten to "27 skills across 9 packs, all gated by make validate on the commit you are looking at". Broader sweep of marketing/+docs/ (excl plans/): 0 remaining stale-count patterns beyond the guard's own pattern list. |
| Tree clean | PASS | git status --porcelain empty before and after all runs |
| Origin sync | PASS | HEAD == origin/main == a6367b712ba0d027b56b08eb738457821bfb8f17 |

## Legal — surface intact at HEAD

- Banner classes: README compliance notice names ALL 9 gated standards with
  publishers — DO-178C, DO-254, ARP4754A, ARP4761A, AS9100 (property of
  publishers, must be purchased), DO-330 (C) RTCA/EUROCAE, DO-160G (C)
  RTCA/EUROCAE ED-14G, AS9102 (C) IAQG/SAE, MMPDS (C) SAE. Cross-checked
  against standards-map.yaml: exactly 9 entries are proprietary-sold AND
  gated:true (arp4754a, arp4761a, do-178c, do-254, as9100, do-330, do-160,
  as9102, mmpsd) — banner matches the map entry-for-entry.
- purchased/free/open split: 9 purchased / ECSS + FAR-25 + CS-25 free
  (free-download + public-domain) / SEP-2640 open-spec — exact against the
  map (14 entries incl. NACA TR-824 public-domain, not claimed as gated).
- NOTICE: intact — Apache-2.0, export-control notice (EU dual-use public-domain
  exclusion, Reg (EU) 2021/821 Annex I GTN), non-endorsement clause. Unchanged
  by the rework (not in diff).
- LICENSE: Apache-2.0 full text present.
- no-verbatim: gate 4 PASS FRESH — 0 markers in skills/, docs/, README.md,
  STANDARDS.md, NOTICE; 0 objective-table blocks. The rework touched only
  prose/docs counts; no new verbatim risk.
- No ITAR-compliant claims: every ITAR/EAR hit repo-wide is a negation ("is
  **not** ITAR/EAR-controlled technical data") or policy reference; content-
  policy-sweep 0 red-flag hits; N4 negative control proves the sweep detects
  "ITAR-compliant"-class claims (non-vacuous).

## Finance

- Rework diff (d61b61c..HEAD) is marketing/docs prose + guard script + test
  fixtures: zero money terms introduced (no EUR/USD/price/fee/spend in added
  lines; only pre-existing competitor-context "purchase" URLs in unchanged
  table rows).
- Pricing HOLD intact (distribution-plan-P3.md lines 5, 22, 161).
- finance/ = rules stub; no >EUR 50 commitments, no external sends.

## Score

**10/10 — PASS (team bar 9.0).**

All gates replayed FRESH at HEAD a6367b7 with real exit codes: validate 5/5
(66/66 Hit@1), attest 3/3, run-tests ALL PASS (incl. N8/N9/G7), packs 9/27,
guard negative control exit 1 + positive control exit 0 verified by me
directly, harness-contract live counts (27/9/66) and expansion-pipeline
EXECUTED confirmed on disk, tree clean, origin synced. Legal surface intact:
banner classes exactly match standards-map.yaml, NOTICE/LICENSE unchanged,
no-verbatim gate 4 green, zero ITAR-compliant claims. Finance clean. No
defects in Verification/Legal/Finance lenses.

Artifacts: this note committed locally at HEAD (no push — publish is founder
VETO). Posted to telegram:-1004333545328:160 as @bhimauth_bot.
