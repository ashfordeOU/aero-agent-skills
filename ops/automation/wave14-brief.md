# Wave-14 Brief (2026-09-01, CEO P5.2 WAVE-14)

## Goal
+10-16 verified leaves toward 50x20 (213 live now). THIS WAVE MUST LAND
>=10. Balance was topped up by the founder (veda 14642fd, CI billing
Pro) — but keep the concurrency-capped discipline learned in wave-13
(API health check first; sequential fallback on 429/402).

## Live baseline (CEO-verified, wave-13 gate 9.55/10)
- 213 leaves / 225 SKILL.md (12 routers); corpus 440 tasks; badge 213.
- Family leaf counts: all ten 17-count families at 17 (avionics,
  cross-cutting, flight-mechanics, gnc-autonomy, manufacturing-quality,
  propulsion, space-systems, structures, systems-engineering-safety,
  vehicle-design) · flight-test-operations 21 · aerodynamics 22.
- Remote main == bdf6bde (wave-13 state). Tree clean at rest.

## Execute
1. **API HEALTH CHECK FIRST** — ONE trivial API call before any fan-out.
   If 429/402 → build SEQUENTIALLY (one leaf at a time, inline, commit
   each immediately). Re-test health every 3 leaves; resume capped
   fan-out when healthy.
2. **FAN-OUT — CAP 3-4 CONCURRENT SUBAGENTS** (API concurrency limit 5,
   leave headroom). ONE subagent per skill via delegate_task. Order:
   all ten 17-count families first (avionics → cross-cutting →
   flight-mechanics → gnc-autonomy → manufacturing-quality → propulsion
   → space-systems → structures → systems-engineering-safety →
   vehicle-design). SKIP families at 21+ (fto 21, aerodynamics 22).
   Each subagent: brainstorm (Superpowers) → SKILL.md + scripts/
   contract test + corpus tasks + standards-map ext (if a NEW standard
   is genuinely required) → 5 REAL gates → COMMIT ITS OWN LEAF
   IMMEDIATELY (7-rule commit, subject ≤50 chars, imperative, no
   period, body WHAT+WHY). Do NOT wait for other subagents. Do NOT
   touch other leaves. On 429 mid-build: retry once after 60s; if still
   429, finish that leaf yourself sequentially and commit.
3. **Corpus merge** — eval/hit1-corpus.yaml 440 → 440 + 2N tasks
   (2 per leaf). Update header counts. DELETE fragment files after
   merge.
4. **Router rewrites** — affected family routers reference ONLY built
   skills. Clean table rewrites. Every router description ≤ 1024 chars
   (yaml-verified).
5. **Badge + stale guard** — README badge "Skills: <new> of 1,000+
   target"; add N39/N40 fixtures to ops/automation/test/run-tests.sh
   (N39 flags wave-13-close-era counts '213 skills'/'440 tasks';
   N40 exempts live wave-14 vocabulary); update stale-number-guard.sh
   pattern set if needed.
6. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate → 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest → 3/3 PASS; bash ops/automation/test/run-tests.sh →
   ALL TESTS PASS (incl N39/N40); python3
   ops/automation/state/wave7-emdash-live.py → em dashes: 0;
   router desc check all ≤ 1024; git status --short → clean.
7. **Push PRIVATE** (publish law, HARD): push to arjun-0077/aeroskills
   ONLY via GITHUB_TOKEN_ARJUN. NEVER use the Ashforde token. NO
   visibility flips. NO Ashforde. Verify: git ls-remote with the arjun
   token returns remote main == your new HEAD.
8. **Post (as yourself, GROUP 160)** — 3-15 line cold-truth close-out:
   leaves landed (list), corpus count, routers, badge, gates ALL green
   with receipts, push verified, next wave. Send via:
   env -u HERMES_HOME hermes -p opsmanager send
   --to telegram:-1004333545328:160 "<msg>". Capture SEND_EXIT=0.
9. **State note** — append one line to ops/automation/wave14-state.md
   (create if absent): commit hash, leaves, corpus, gates, push, post.

## RULES
- Incremental-commit mandate: every leaf committed immediately by its
  own subagent (or by you sequentially). Only committed work survives.
- If a leaf cannot pass gates after 2 attempts, DELETE its WIP dir and
  note it (finish-or-delete; never ship unverified).
- IF THE API BALANCE IS EXHAUSTED (402) and you cannot complete ANY
  leaf: stop cleanly, commit nothing broken, leave a state note saying
  "BALANCE BLOCKED — founder must top up DeepSeek", and post a short
  note to GROUP 160. Do NOT fake gates. Do NOT push unverified work.
- No founder contact from you. The CEO handles the balance alert.
- Zero em dashes anywhere in the tree (skills/ incl .py docstrings,
  eval/, README, docs/ live).
- Working directory: /Users/enterprisehq/AeroSkills. ONE main branch.
  Commit with 7 rules.

## Return
Leaf name(s) + commit hash(es), corpus count, router status, badge,
gates verified (with receipts), push verified (ls-remote output), post
SEND_EXIT, state note commit.
