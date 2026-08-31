# Wave-6 Re-Dispatch #1 Brief — RESCUE-FIRST FAN-OUT (Ops Manager)

Dispatched 2026-08-31 ~23:00 (relay). Wave-6 first dispatch (proc 50223)
KILLED MID-FAN-OUT (10th interruption, relay runtime kill pattern) —
zero commits landed. WIP preserved on disk. Re-dispatch RESCUE-FIRST.

## STATE VERIFIED FRESH BY ORCHESTRATOR (23:00)
- AeroSkills HEAD edb38fd (wave-6 brief commit) == origin/main == remote
  (verified via explicit GITHUB_TOKEN_ARJUN ls-remote; plain fetch fails
  "Repository not found" = Ashforde store pattern, known).
- WIP on disk (untracked, from kill):
  1. skills/vehicle-design/sizing/fuselage-sizing/ — PARTIAL: SKILL.md +
     scripts/fuselage_sizing_logic.py present, NO contract test yet.
  2. count_corpus_tmp.py — tmp helper (clean at close).
- Tree otherwise clean (no other uncommitted work; incremental-commit
  mandate honored through wave-5, nothing else at risk).
- Baseline: 112 leaves + 12 routers = 124 SKILL.md, corpus 240 tasks,
  README badge "Skills: 112 of 1,000+ target", gates green at edb38fd.

## LOCKED 10-LEAF PLAN (recovered from killed session deleg_90f5b251 —
do NOT re-plan, execute exactly; all targets collision-checked by bot)
1. aerodynamics/airfoil/airfoil-geometry
2. aerodynamics/high-speed/oblique-shock
3. flight-mechanics/stability-control/dynamic-stability
4. flight-mechanics/performance/descent-performance
5. gnc-autonomy/guidance/pursuit-guidance
6. gnc-autonomy/navigation/inertial-navigation
7. structures/fatigue/load-spectrum-counting
8. structures/materials/material-selection
9. vehicle-design/sizing/fuselage-sizing   (RESCUE — WIP on disk)
10. vehicle-design/cost-estimation/life-cycle-cost

## YOUR TASKS (in order — INCREMENTAL-COMMIT MANDATE, 10 KILLS ON RECORD)
0. RESCUE FIRST: complete fuselage-sizing (SKILL.md + logic + contract
   test), run its 5 REAL gates, COMMIT IMMEDIATELY as its own commit
   (7-rule). Also sweep count_corpus_tmp.py at close.
1. Fan-out via delegate_task ONE subagent per skill (wave protocol),
   the remaining 9 leaves of the locked plan, thinnest families first
   (aerodynamics 8 → flight-mechanics 8 → gnc-autonomy 8 → structures 8
   → vehicle-design 8). Every leaf: 5 REAL gates → COMMIT IMMEDIATELY
   (never batch).
2. Merge ALL wave-6 eval fragments into eval/hit1-corpus.yaml +
   header counts (240 → 240+2N). Delete standalone fragments.
3. CLEAN ROUTER TABLE REWRITES for touched families — list ONLY
   built skills.
4. README badge → new live count. Stale-number guard patterns
   updated (112-class → new class) + N23/N24 fixtures.
5. GATES FRESH: make validate 5/5 · make attest 3/3 · run-tests ALL
   PASS incl N10/N11/N15-N24 · stale guard · em dashes 0 live tree ·
   tree clean (tmp sweep).
6. PUSH private: GIT_TOKEN=GITHUB_TOKEN_ARJUN git push origin main
   (credential store holds Ashforde token — arjun token explicitly;
   NEVER publish to Ashforde).
7. POST as yourself to GROUP 160 (3-15 lines, cold truth, evidence:
   leaves landed, corpus count, gates green, badge count, push
   verified).

## HARD RULES
- Commit EVERY skill immediately after gates pass. Never hold
  uncommitted work (10 kills — only committed work survives).
- Routers reference ONLY built skills (build or trim).
- Do NOT touch the Ashforde token / org. Private arjun-0077 only.
