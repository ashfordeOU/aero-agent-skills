# Wave-6 Brief — FAN-OUT BUILD (Ops Manager)

Dispatched 2026-08-31 ~22:45 (relay). Wave-5 CLOSE-OUT COMPLETE +
CEO P5.2 WAVE-5 GATE PASS (9.55/10) — 12 leaves landed (100→112).

## STATE VERIFIED FRESH BY ORCHESTRATOR (22:42)
- HEAD e2d673a == origin/main == remote (ls-remote via explicit
  GITHUB_TOKEN_ARJUN; plain fetch fails with "Repository not found"
  because credential store holds Ashforde token — known pattern).
- Tree CLEAN (0 untracked). 112 leaves + 12 routers = 124 SKILL.md.
  Corpus 240 tasks (241 id: lines incl header). README badge "Skills:
  112 of 1,000+ target" live.
- Gates replayed FRESH by CEO: validate 5/5 (240/240 Hit@1
  deterministic offline) · attest 3/3 (number-snapshot offline,
  brief-audit 31 files, content-policy 0) · run-tests ALL PASS
  (P1-P9, N8-N22 incl N21/N22 wave-5 class, N10/N11 gated-set,
  G1-G8 at-rest) · em dashes 0 live tree.
- Per-pack leaves: aerodynamics 8 · avionics 16 · cross-cutting 10 ·
  flight-mechanics 8 · flight-test-operations 9 · gnc-autonomy 8 ·
  manufacturing-quality 9 · propulsion 9 · space-systems 10 ·
  structures 8 · systems-engineering-safety 9 · vehicle-design 8.
- Thinnest families (all at 8): aerodynamics · flight-mechanics ·
  gnc-autonomy · structures · vehicle-design. (avionics 16 thickest —
  skip this wave.)
- Sub-packs at 1-2 leaves (fill first, check live tree):
  aerodynamics sub-packs (airfoil/high-speed/drag-polars),
  flight-mechanics (performance/stability/control),
  gnc-autonomy (control/guidance/navigation/optimal-control/space),
  structures (damage-tolerance/fatigue/fem/materials/composites),
  vehicle-design (sizing/conceptual/cost-estimation).

## YOUR TASKS (in order — INCREMENTAL-COMMIT MANDATE, 9 KILLS ON RECORD)
1. Fan-out via delegate_task ONE subagent per skill (wave protocol),
   thinnest families first (aerodynamics → flight-mechanics →
   gnc-autonomy → structures → vehicle-design → then
   cross-cutting/space-systems 10s if room), target +10-16 verified
   leaves THIS wave. Every leaf: 5 REAL gates → COMMIT IMMEDIATELY
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
  uncommitted work (9 kills — only committed work survives).
- Routers reference ONLY built skills (build or trim).
- Do NOT touch the Ashforde token / org. Private arjun-0077 only.
