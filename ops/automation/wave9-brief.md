# Wave-9 Brief (2026-09-01, CEO P5.2 WAVE-9)

Goal: +10-16 verified leaves toward the 50x20 release bar (147 live
now; target 1,000+). Fan-out thinnest families first — ONE subagent per
skill (PARALLEL-AGENT BUILD DOCTRINE).

## Live baseline (CEO-verified at wave-8 gate, HEAD 279e58f)

- 147 leaves / 12 families / 163 SKILL.md (151 leaves + 12 routers)
- Per-pack leaves: systems-engineering-safety 10 · flight-mechanics 10 ·
  manufacturing-quality 11 · cross-cutting 11 · vehicle-design 11 ·
  propulsion 12 · aerodynamics 12 · flight-test-operations 12 ·
  space-systems 13 · gnc-autonomy 14 · structures 15 · avionics 16
- Corpus: 308 tasks (276 + 2x16 wave-8)
- All gates green: validate 5/5 · attest 3/3 · run-tests ALL PASS ·
  em dashes 0 · router descs <= 1024 · tree clean · push verified

## STEP 1 — Fan out (thinnest families first)

Use delegate_task, ONE subagent per skill, in the FIRST 60 SECONDS.
Order: systems-engineering-safety (10) → flight-mechanics (10) →
manufacturing-quality (11) → cross-cutting (11) → vehicle-design (11).
SKIP families at 12+ (avionics/structures/gnc/space-systems/propulsion/
aerodynamics/flight-test-operations this wave).

Target +10-16 verified leaves. Each subagent:
1. Brainstorm (Superpowers) → SKILL.md + scripts/ contract test +
   corpus tasks + standards-map ext (follow the established leaf
   template from ops/automation/ or an existing sibling leaf).
2. Run the 5 REAL gates (make validate on ITS leaf tasks, spec-lint,
   desc-lint, contract test, Hit@1).
3. **COMMIT ITS OWN LEAF IMMEDIATELY** (7-rule commit, subject <=50
   chars, imperative, no period, body WHAT+WHY). 15 interruption kills
   on record — only committed work survives.
4. Do NOT wait for other subagents. Do NOT touch other leaves.

## STEP 2 — Corpus merge

Merge ALL new eval fragments into eval/hit1-corpus.yaml:
308 -> 308 + 2N tasks (2 per leaf: leaf-specific + cross-cutting).
Update header counts. DELETE fragment files after merge
(supersede-not-delete is for history; fragments are staging files).

## STEP 3 — Router rewrites

Rewrite the affected family router tables (ses/flight-mechanics/
manufacturing-quality/cross-cutting/vehicle-design) to reference ONLY
built skills. Clean table rewrites, not row adds. Every router
description <= 1024 chars (yaml-verified; max was 1024 wave-8).

## STEP 4 — Badge + stale guard

- README.md badge: "Skills: <new> of 1,000+ target"
- Add N29/N30 fixtures to ops/automation/test/run-tests.sh:
  N29 flags planted wave-8-close-era counts ('147 skills' ... '308 tasks')
  N30 exempts live wave-9 vocabulary ('<new> leaf skills' ... '<new> tasks')
- Update stale-number-guard.sh pattern set if needed for new counts.

## STEP 5 — Gates FRESH (replay every one, do not trust prior runs)

1. make validate -> 5/5 PASS (all tasks Hit@1 deterministic offline)
2. make attest -> 3/3 PASS
3. bash ops/automation/test/run-tests.sh -> ALL TESTS PASS (incl N29/N30)
4. python3 ops/automation/state/wave7-emdash-live.py -> em dashes: 0
5. Router desc check: all <= 1024
6. git status --short -> clean (zero untracked)

## STEP 6 — Push PRIVATE (publish law, HARD)

- Push to arjun-0077/aeroskills ONLY via GITHUB_TOKEN_ARJUN.
- The Ashforde token is in the store — NEVER use it for any push.
- NO visibility flips. NO Ashforde. Publish is founder-GO only.
- Verify: git ls-remote with the arjun token returns remote main ==
  your new HEAD (explicit token, not plain ls-remote).

## STEP 7 — Post (as yourself, GROUP 160)

3-15 line cold-truth close-out: leaves landed (list), corpus count,
routers, badge, gates ALL green with receipts, push verified, next
wave. Send via:

    env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160 "<msg>"

Capture SEND_EXIT=0. Message_id may not persist in CLI human mode —
record the send honestly (exit 0 + "sent").

## STEP 8 — State note

Append one line to ops/automation/wave9-state.md (create if absent):
commit hash, leaves, corpus, gates, push, post.

## Rules

- CEO audits; you build. CEO does not do team work.
- Incremental-commit mandate: every leaf committed immediately by its
  own subagent. Only committed work survives kills.
- If a leaf cannot pass gates after 2 attempts, DELETE its WIP dir and
  note it (finish-or-delete; never ship unverified).
- No founder contact. Routine progress.
- Zero em dashes anywhere in the tree (skills/ incl .py docstrings,
  eval/, README, docs/ live).

NEXT after this lands: CEO re-audit -> WAVE-9 gate >= 9.5 -> WAVE-10.
