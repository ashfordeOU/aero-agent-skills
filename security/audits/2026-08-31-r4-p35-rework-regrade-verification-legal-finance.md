# AeroSkills P3.5 rework re-grade — Bheem (Verification + Legal + Finance)

Date: 2026-08-31
HEAD graded: d61b61c73440c26a3476c5e98bf2e353e4d5abfc
Prior grade: Bheem 9.5/10 PASS at 822fbe1; team gate failed (Content 8.7) -> rework landed at d61b61c.
This audit: replay ALL gates FRESH at HEAD; verify the compliance-banner extension did not weaken legal posture.

## Verification (replayed FRESH at HEAD d61b61c)

| Gate | Result | Evidence |
|---|---|---|
| make validate | PASS exit 0 | 5/5 REAL gates; gate5 hit1 = **66/66 tasks Hit@1** (deterministic offline router) |
| make attest | PASS exit 0 | 3/3: number-snapshot offline 5/5 OK (K-Dense 40020 vs expected 39925, within tolerance), brief-audit 29 files resolve, content-policy-sweep **0 red-flag hits** |
| bash ops/automation/test/run-tests.sh | ALL TESTS PASS exit 0 | N1-N7 negatives (incl. N4 proves sweep flags "ITAR-compliant" = non-vacuous), S.no-license..empty-standards (8 spec-lint compliance flags), P1-P9 pack_inventory (P2: 9 packs / 27 skills), G1-G6 at-rest greens |
| make packs | PASS exit 0 | packs=9 skills=27 |
| Em dashes | 0 in prose deliverables | README.md 0, docs/harness-integration.md 0, docs/glossary.md 0, STANDARDS.md 0, NOTICE 0, CONTRIBUTING.md 0 (grep U+2014). Only U+2014 hits repo-wide are machine-generated JSON star snapshots in ops/automation/state/ — data, not prose, not the rule's target. P3.4's -0.5 em-dash finding is fully resolved. |
| Tree clean | PASS | git status --porcelain empty before and after all runs |
| Origin sync | PASS | HEAD == origin/main == d61b61c |

README rework claims verified on disk + against live gates:
- Standards map bullet names all 14 mapped standards (added DO-330, DO-160G, AS9102, MMPDS, NACA TR-824) — matches standards-map.yaml (14 entries).
- Eval-gates bullet: 66-task Hit@1 — matches eval/hit1-corpus.yaml (66 active tasks; the 67th id "t3" sits under future_pins, not in the active tasks list).
- Roadmap "All 27 gated by make validate" — matches make packs (27 leaf skills) and gate3 27/27 contract tests.
- Next: names only remaining gaps (propulsion, flight mechanics, flight test and operations) — consistent with 9-pack taxonomy.
- Contributing thin domains: aerodynamics, vehicle-design, cross-cutting (one skill each) — verified leaf counts per domain (1 each; domain SKILL.md is the router).
- docs/glossary.md Hit@1 = 66; docs/harness-integration.md nine-pack list = 9 packs — both fixed on disk.

## Legal — compliance banner extension (the rework's core legal surface)

The banner changed from listing 5 purchased standards to naming ALL 9 gated standards with per-standard publishers. Verified against standards-map.yaml:

| Banner claim | standards-map.yaml | Verdict |
|---|---|---|
| DO-330 (C) RTCA/EUROCAE | do-330, publisher RTCA (joint EUROCAE twin ED-215), proprietary-sold, gated:true | ACCURATE |
| DO-160G (C) RTCA/EUROCAE ED-14G | do-160, publisher RTCA (joint EUROCAE twin ED-14G), proprietary-sold, gated:true | ACCURATE |
| AS9102 (C) IAQG/SAE | as9102, publisher IAQG (develops)/SAE (publishes Americas), proprietary-sold, gated:true | ACCURATE |
| MMPDS (C) SAE | mmpsd, publisher SAE International (successor to MIL-HDBK-5), proprietary-sold, gated:true | ACCURATE |
| DO-178C, DO-254, ARP4754A, ARP4761A, AS9100 remain property of publishers, must be purchased | all proprietary-sold, gated:true | ACCURATE (unchanged) |
| ECSS + FAR/CS-25 freely available (public regs / free downloads) | ecss free-download, far-25 public-domain, cs-25 free-download | ACCURATE (unchanged) |
| SEP-2640 open specification from MCP working group | sep-2640 open-spec | ACCURATE (unchanged) |

Purchased/free/open split: 9 gated = 9 purchased (all proprietary-sold + gated:true). Free class: ECSS, FAR-25, CS-25. Open: SEP-2640. Split is exact against the map — no standard misclassified.

No red-flag terms: content-policy-sweep 0 hits in publishable content; N4 negative control proves the sweep detects "ITAR-compliant"-class claims (non-vacuous). Manual README scan: every ITAR/EAR/export hit is a negation ("is **not** ITAR/EAR-controlled technical data") or the hygiene disclaimer ("public availability is what keeps published information decontrolled") — the brief 06 s8.3.9 formulation, unchanged.

No ITAR-compliant claims: zero affirmative compliance/certification claims. "Verified means the gates pass on the commit you are looking at; not certification, not approval, not airworthy" — term discipline intact.

STANDARDS.md gated enumeration now lists all 9 (do-330, do-160, as9102, mmpsd added alongside the original 5) — consistent with map and README. License/NOTICE untouched by the rework (README-only diff, 20+/17-).

Verdict: the banner extension STRENGTHENED legal precision (per-standard publisher attribution, complete gated enumeration) and did NOT weaken the ITAR/EAR/export-control posture. No legal regression.

## Finance

- Rework diff (d61b61c) is README-only: zero money terms introduced (grep on added lines: no EUR/USD/price/cost/spend/budget/paid).
- finance/ = rules stub only (no ledger/, pricing/, invoices/ dirs exist); operating rules unchanged (>EUR 50 = founder VETO).
- Pricing HOLD honored (no prices anywhere; FAQ "not certified, not controlled as published").
- No new >EUR 50 commitments, no spend, no external sends implied.

## Score

**10/10 — PASS (team bar 9.0).**

All gates replayed FRESH pass with real exit codes; the Content-drift defects that failed the team gate are fixed at HEAD (66-task corpus, 9/9 gated, 14/14 standards map, thin-domain and roadmap claims verified against live packs); legal posture intact and stricter; finance clean. No defects remain in Verification/Legal/Finance lenses. Prior 9.5 stands; rework earns full marks from this lens.

Artifacts: this note committed locally at HEAD (no push — publish is founder VETO).
