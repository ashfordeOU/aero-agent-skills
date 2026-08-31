# Wave-4 Re-Dispatch #4 Brief — FINISH WAVE-4 CLOSE-OUT (Ops Manager)

Dispatched 2026-08-31 21:42 (relay). 8th interruption this wave. Your
re-dispatch #3 (started 21:28) was killed mid-fan-out at ~21:37.

## STATE VERIFIED FRESH BY ORCHESTRATOR (21:42)
- HEAD 7220fe5 == your last commit 21:34:40 ("feat: add
  numerical-integration leaf"). origin/main still 09ffe35 (11 commits
  ahead, push DEFERRED per CI-first — correct, do not push until green).
- RESCUE COMPLETE — 5 WIP leaves recovered + committed (21:34):
  3836eae glide-performance · 52aca4a flight-test-planning · b25cc7d
  supplier-control · 3146260 prandtl-meyer (GATE3 RED fixed) ·
  7220fe5 numerical-integration (partial completed).
- Live tree: 106 SKILL.md = 94 leaves + 12 routers (find skills
  -mindepth 3 -maxdepth 4 = 94). README badge STALE: says 83, must be 94.
- Corpus: hit1-corpus.yaml still 182 tasks. 11 wave-4 eval fragments
  tracked but UNMERGED (breguet-endurance, flight-test-planning,
  glide-performance, landing-gear-sizing, least-squares-regression,
  nonconformance-control, numerical-integration, prandtl-meyer,
  supplier-control, tail-sizing, uncertainty-propagation). Merge → 204.
- Untracked: ONLY 6 tmp files (ops/tmp_emdash.sh, tmp_emdash_check.py,
  tmp_inspect_env.py, tmp_merge_corpus.py, tmp_peek.sh,
  tmp_subagent_protocol.md). Sweep at close.
- deleg_7c333e6b (your 4-task fan-out, spawned 21:36) INTERRUPTED
  21:37:08, zero leaves landed: landing-distance-determination ·
  flutter-testing · lateral-directional-stability · cg-envelope.

## YOUR TASKS (in order — INCREMENTAL-COMMIT MANDATE, 8 KILLS ON RECORD)
1. Re-fan-out the 4 interrupted leaves (delegate_task, one subagent per
   skill, per the wave-4 subagent protocol):
   - flight-test-operations/performance/landing-distance-determination
   - flight-test-operations/flutter/flutter-testing
   - flight-mechanics/stability-control/lateral-directional-stability
   - vehicle-design/mass-properties/cg-envelope
   Then +2-4 more from thinnest packs (aim 12-16 leaves THIS wave; 11
   committed already). Every leaf: 5 REAL gates → COMMIT IMMEDIATELY.
2. MERGE ALL 11 wave-4 fragments into eval/hit1-corpus.yaml + header
   counts (182 → 204). Delete the standalone fragments.
3. CLEAN ROUTER TABLE REWRITES for touched families
   (flight-mechanics, flight-test-operations, manufacturing-quality,
   aerodynamics, cross-cutting, vehicle-design, space-systems) — list
   only built skills.
4. README badge → 94 of 1,000+ target. Stale-number guard patterns
   updated (83 → 94 class).
5. GATES FRESH: make validate 5/5 (204/204 Hit@1 deterministic
   offline) · make attest 3/3 · run-tests ALL PASS incl N10/N11/N15-N18
   · stale guard · em dashes 0 live tree · tree clean (tmp sweep).
6. PUSH private: GIT_TOKEN=GITHUB_TOKEN_ARJUN git push origin main
   (credential store holds Ashforde token — use the arjun token
   explicitly; NEVER publish to Ashforde).
7. POST as yourself to GROUP 160 (3-15 lines, cold truth, evidence:
   leaves landed, corpus 204, gates green, badge 94, push verified).

## HARD RULES
- Commit EVERY skill immediately after gates pass. Never hold
  uncommitted work (8 kills — only committed work survives).
- Routers reference ONLY built skills (build or trim).
- Do NOT touch the Ashforde token / org. Private arjun-0077 only.
- Finish wave-4 fully: corpus merged, gates green, pushed, posted.
