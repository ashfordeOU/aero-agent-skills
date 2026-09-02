# Wave-24 Brief (2026-09-02, CEO P5.2 WAVE-24)

## Goal
+10-16 verified leaves toward 50x20 (330 live now). THIS WAVE MUST LAND
>=10. Keep the concurrency-capped discipline (CAP 3-4 concurrent
subagents, API health check first — wave-21/22/23 pattern: batched fan-out,
DeepSeek never 429/402).

## Baseline (CEO-verified at HEAD 8c650e6, relay 2026-09-02 09:1x UTC)
- 330 leaves + 12 routers = 342 SKILL.md tracked (find == git ls-files)
- Per-family leaf counts: flight-mechanics 27 · gnc-autonomy 27 ·
  propulsion 27 · space-systems 27 · systems-engineering-safety 27 ·
  vehicle-design 27 · aerodynamics 28 · avionics 28 · cross-cutting 28 ·
  flight-test-operations 28 · manufacturing-quality 28 · structures 28
- Corpus 674 tasks (650 + 24 wave-23)
- Ratings ledger 330 lines (all 330 leaves rated, wave-23 rows 319-330 @9.5)
- Remote main == 8c650e6 == HEAD (private arjun-0077/aeroskills,
  publish law — NO Ashforde, no visibility flip)
- Em dashes 0 skills/ · tree clean · routers all <=1024

## STEP 0 — TURN-ALIVE hard rules (6 prior occurrences, wave-16/19/20/21/22/23)
- NEVER write a text response while any delegation is live. A text
  response ENDS the turn and CLI-tears-down async delegations.
- Status updates = `hermes send` TOOL call only (GROUP post as
  yourself). The ONLY text response is close-out AFTER all subagents
  complete AND you verified their commits.
- Stay alive polling (process/task-log checks, git log, ps) inside the
  same turn until ALL subagents complete.

## STEP 1 — API health check
- Check DeepSeek health first (429/402 -> build sequentially one leaf at
  a time, commit each immediately; fan-out only if healthy, CAP 3-4
  concurrent).

## STEP 2 — Fan-out ONE SUBAGENT PER SKILL
- +10-16 verified leaves, MUST land >=10.
- Six 27-count families FIRST (flight-mechanics -> gnc-autonomy ->
  propulsion -> space-systems -> systems-engineering-safety ->
  vehicle-design), then 28-count headroom (aerodynamics -> avionics ->
  cross-cutting -> flight-test-operations -> manufacturing-quality ->
  structures) if headroom.
- Each leaf ships the per-skill completeness standard (9dfcdad): SKILL.md
  (agentskills.io frontmatter) + scripts/ logic + scripts/test_*.py
  contract test (offline deterministic) + no broken refs + refs/assets
  triage + eval/skill-eval/<name>.json value-delta record.
- Run `make completeness` (required) + `make value-delta` (sample proof).
- Subagents commit EXPLICIT PATHS ONLY (leaf dir + own eval fragment +
  eval/skill-ratings.md row) — NO `git add -A` / `git add .` /
  `git reset`. Index-lock retry. (Git-race lesson: concurrent
  main-profile sessions may `git add -A` — verify your leaves still
  exist at HEAD after any race; never fight design files.)

## STEP 3 — Rate-at-creation
- >=9.5 in eval/skill-ratings.md IN-TURN for every leaf (330 ->
  330+N). Silence is not approval; the row lands with the leaf commit.

## STEP 4 — Close-out chain
1. Corpus 674 -> 674+2N (merge wave-24 eval fragments, then DELETE
   them). Count-verify (grep tasks) before commit.
2. 12 family routers <=1024 (wave16-router-desc-len.py PASS).
3. Visuals: `make visuals` (README numbers) + `make visuals-check` PASS
   (design is LOCKED — numbers only).
4. Surviving gates FRESH (run-tests.sh was RETIRED by founder cleanup
   65e93e5 — do NOT recreate it, do NOT recreate gate fixtures; N55/N56
   additions are MOOT per wave-20 G7 doctrine — record retirement, not
   a counts edit):
   - make validate 5/5 (674/674 Hit@1 deterministic offline)
   - make attest 3/3 (number-snapshot offline + brief-audit +
     content-policy-sweep)
   - stale-number-guard.sh PASS (G7 — add R27 wave-23-close stale class
     per wave-23 precedent: 330/330 leaf/342 SKILL.md/674)
   - em dashes 0 skills/ (fresh grep)
   - tree clean at rest (0 untracked)
5. Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN) fast-forward only,
   ls-remote verify (remote == HEAD). Publish law: NO Ashforde, NO
   visibility flip, ever.
6. GROUP 160 post as yourself: close-out with SEND_EXIT=0 (verify the
   tool result shows `sent\nSEND_EXIT=0`).
7. wave24-state.md committed (record: leaves, corpus, routers, R27
   stale-class update, gates replayed, push/post evidence).

## STEP 5 — Close-out text
- Only after everything above is verified and committed. Short.

## REMEMBER
- Design session owns docs/*.svg + DESIGN.md — NEVER touch design
  files. G7 must stay green.
- Commit identity ashfordeOU <contact@ashforde.org> (repo-local config
  already set; verify `git log -1 --format='%an <%ae>'`).
- QUIET HOURS: 20:00-08:00 UTC (22:00-10:00 CEST) = NULL BURN WINDOW.
  Window opens at 20:00 UTC today — you have the full day until then;
  if the window hits mid-wave, stop spending, commit what is done, and
  resume after 08:00 UTC. PRE-SPAWN CHECK each new subagent batch:
  `python3 ~/.hermes/scripts/quiet-hours-gate.py --check` (exit 0 OK,
  2 in-window stop, 3 pre-quiet no new long work).
- Balance exhausted -> stop clean with note "BALANCE BLOCKED — founder
  must top up DeepSeek". NO fake gates. NO fabrication.

Next: CEO P5.2 WAVE-24 gate >=9.5 -> WAVE-25. No founder contact
(routine progress).
