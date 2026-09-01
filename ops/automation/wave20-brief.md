# Wave-20 Brief (2026-09-01, CEO P5.2 WAVE-20)

## Goal
+10-16 verified leaves toward 50x20 (282 live now). THIS WAVE MUST LAND
>=10. Keep the concurrency-capped discipline (API health check first;
sequential fallback on 429/402; cap 3-4 concurrent subagents).

## Live baseline (CEO-verified, wave-19 gate 9.55/10 + design gate-fix 6716069)
- 282 leaves / 294 SKILL.md (12 routers); corpus 578 tasks; badge 282.
- Family leaf counts: six 23-count families (flight-mechanics,
  gnc-autonomy, propulsion, space-systems, systems-engineering-safety,
  vehicle-design) · aerodynamics 24 · avionics 24 · cross-cutting 24 ·
  flight-test-operations 24 · manufacturing-quality 24 · structures 24.
- Remote main == 6716069 (wave-19 close + design gate-fix; ls-remote-verified).
- Tree clean at rest (2 kept helpers: ops/automation/state/wave16-merge-corpus.py +
  wave16-router-desc-len.py — do not delete, may reuse pattern).

## Execute
1. **API HEALTH CHECK FIRST** — ONE trivial API call before any fan-out.
   If 429/402 → build SEQUENTIALLY (one leaf at a time, inline, commit
   each immediately). Re-test health every 3 leaves; resume capped
   fan-out when healthy.
2. **FAN-OUT — CAP 3-4 CONCURRENT SUBAGENTS** (API concurrency limit 5,
   leave headroom). ONE subagent per skill via delegate_task. Order:
   the six 23-count families first (flight-mechanics → gnc-autonomy →
   propulsion → space-systems → systems-engineering-safety →
   vehicle-design), then the 24-count families (aerodynamics → avionics
   → cross-cutting → flight-test-operations → structures →
   manufacturing-quality) if headroom. Each subagent: brainstorm
   (Superpowers) → SKILL.md + scripts/ contract test + corpus tasks +
   standards-map ext (if a NEW standard is genuinely required) → 5 REAL
   gates → **RATE THE LEAF AT CREATION (founder mandate): run `python3
   ops/automation/update-skill-ratings.py` so this leaf appears in
   eval/skill-ratings.md with CEO rating >= 9.5 in the SAME flow. If
   the leaf does NOT achieve >= 9.5 (or its gates fail), REBUILD IT IN
   THE SAME TURN — fix, re-gate, re-rate; after 2 attempts delete the
   WIP dir and note it. A leaf is not done until it is rated in the
   ledger.** → COMMIT ITS OWN LEAF IMMEDIATELY (7-rule commit, subject
   ≤50 chars, imperative, no period, body WHAT+WHY) INCLUDING its
   ratings-ledger row. Do NOT wait for other subagents. Do NOT touch
   other leaves. On 429 mid-build: retry once after 60s; if still 429,
   finish that leaf yourself sequentially and commit.
3. **Corpus merge** — eval/hit1-corpus.yaml 578 → 578 + 2N tasks
   (2 per leaf). Update header counts. DELETE fragment files after
   merge.
4. **Router rewrites** — affected family routers reference ONLY built
   skills. Clean table rewrites. Every router description ≤ 1024 chars
   (yaml-verified via ops/automation/state/wave16-router-desc-len.py
   pattern or equivalent).
5. **Badge + stale guard** — README badge "Skills: <new> of 1,000+
   target"; add N53/N54 fixtures to ops/automation/test/run-tests.sh
   (N53 flags wave-19-close-era counts '282 skills'/'578 tasks';
   N54 exempts live wave-20 vocabulary); update stale-number-guard.sh
   pattern set if needed.
6. **Gates FRESH** (replay every one, do not trust prior runs):
   make validate → 5/5 PASS (all tasks Hit@1 deterministic offline);
   make attest → 3/3 PASS; bash ops/automation/test/run-tests.sh →
   ALL TESTS PASS (incl N53/N54, and the full N1-N52 + G1-G8 set);
   em dashes: 0 (scan skills/ incl .py); router desc check all ≤ 1024;
   git status --short → clean.
7. **Push PRIVATE** (publish law, HARD): push to arjun-0077/aeroskills
   ONLY via GITHUB_TOKEN_ARJUN. NEVER use the Ashforde token. NO
   visibility flips. NO Ashforde. Verify: git ls-remote with the arjun
   token returns remote main == your new HEAD.
8. **Post (as yourself, GROUP 160)** — 3-15 line cold-truth close-out:
   leaves landed (list), corpus count, routers, badge, gates ALL green
   with receipts, push verified, next wave. Send via:
   env -u HERMES_HOME hermes -p opsmanager send
   --to telegram:-1004333545328:160 "<msg>". Capture SEND_EXIT=0.
9. **State note** — append one line to ops/automation/wave20-state.md
   (create if absent): commit hash, leaves, corpus, gates, push, post.

## RULES
- Incremental-commit mandate: every leaf committed immediately by its
  own subagent (or by you sequentially). Only committed work survives.
- **RATE-AT-CREATION mandate (founder, verbatim): "they should be rated
  exactly at the time of creation and if they didnt achieve the score
  they get rebuilt in the same flow or same turn." A leaf is not done
  until it is in eval/skill-ratings.md with CEO rating >= 9.5, written
  in the same build turn. Below-score leaves are rebuilt in-turn, not
  shipped and backfilled later.**
- **WAVE-19 DESIGN GATE-FIX LESSON (apply, do not repeat):** a parallel
  docs/design stream pushed docs/domain-map.svg + banners with
  wave-18-era counts after running ONLY `make validate` — G7
  (stale-number guard) lives in run-tests.sh, so the push went out with
  RED CI (same class as wave-18 5ed9e43). ANY commit that touches
  count-bearing docs (domain-map.svg, banners, README, DOMAINS.md,
  positioning) MUST run the FULL gate set (make validate + make attest
  + run-tests.sh incl G7) BEFORE pushing. The CEO FRESH replay catches
  red CI at the gate — do not make him find it.
- **WAVE-18 GATE-FIX LESSON (apply, do not repeat):** number_audit.py
  table-row star logic requires CELL-DOMINANT aliases (alias == cell
  after markdown stripping, or owner/repo path). When you add tables
  to docs/ (DOMAINS.md style skill inventories), keep star columns
  unambiguous — a backtick-quoted skill-name list is never a repo cell.
  N49/N50 fixtures guard both directions; do not regress.
- **WAVE-15 LESSON (apply, do not repeat): subagents must NEVER touch
  scripts/ or ops/automation briefs, and must NEVER run shared merge
  helpers or /tmp scratch that can collide with another subagent.**
  Parent-side close prep only.
- **WAVE-16 LESSONS (apply, do not repeat):**
  (1) TURN-ALIVE — never end your turn while ANY fan-out subagent is
  live; final text response = close-out only. A wave is not complete
  until every leaf is committed. (2) TEMPLATE CHECK — validate every
  delegate_task goal for unexpanded '<...>' markers before dispatch.
  (3) GIT-RACE — if two builders touch shared files, git reset can
  sweep a peer's staged files; stop both builders, recommit cleanly,
  parent-commit any swept leaf. (4) FRAGMENT FORMAT — eval fragments
  must be in the wave fragment format the merge helper parses; verify
  before merge. (5) CONTENT POLICY — avoid trigger words ('classified'
  → 'categorized') in leaf prose; sweep before commit.
- **CONCURRENCY-CAPPED doctrine (balance incident 2026-09-01):** DeepSeek
  concurrency limit is balance-derived (5 at low balance). Never exceed
  3-4 concurrent subagents. If 429/402 appears: STOP fan-out, build
  sequentially, state note "BALANCE BLOCKED — founder must top up
  DeepSeek" if exhausted, NO fake gates.
- **TURN-CLOSE rule (20 kills):** do not emit a final text response
  while delegations are live. Poll/verify inside the same turn.

## Definition of done (CEO verifies FRESH at completion)
>=10 leaves landed (each: SKILL.md + logic + test + ratings-ledger row
>= 9.5 written in-turn) · corpus 578+2N · routers ≤1024 · badge + N53/N54
· gates FRESH (validate 5/5, attest 3/3, run-tests ALL PASS incl
N49/N50 + N51/N52, em dashes 0, tree clean) · pushed PRIVATE + ls-remote
verified · GROUP 160 post (SEND_EXIT=0) · state note committed.
