# Wave-8 Brief — FAN-OUT BUILD (Ops Manager)

Dispatched 2026-09-01 ~00:55 (relay). Wave-7 CLOSE-OUT COMPLETE +
CEO P5.2 WAVE-7 GATE PASS (9.55/10) — 9 leaves landed (122→131):
ballooning · trade-study-analysis · turbofan-off-design ·
limit-cycle-oscillation · flight-test-data-reduction ·
radiographic-inspection · load-factor-envelope · multi-stage-compressor
· real-cycle-effects.

## STATE VERIFIED FRESH BY ORCHESTRATOR (00:52)
- HEAD 7cc431d == remote main == 7cc431d (ls-remote via explicit
  GITHUB_TOKEN verified; plain fetch fails "Repository not found" —
  credential store holds Ashforde token, known pattern). GitHub API:
  private=true, visibility=private, arjun-0077/aeroskills. NO
  Ashforde push, no visibility flip — publish law honored.
- Tree CLEAN (0 untracked). 131 leaves + 12 routers = 143 SKILL.md.
  Corpus 276 tasks. README badge "Skills: 131 of 1,000+ target"
  live + N25/N26 stale-guard fixtures.
- Gates replayed FRESH by CEO: validate 5/5 (276/276 Hit@1
  deterministic offline) · attest 3/3 (number-snapshot offline,
  brief-audit 31 files, content-policy 0) · run-tests ALL PASS
  (P1-P9, N8-N26 incl N25/N26 wave-7 class, N10/N11 gated-set,
  G1-G8 at-rest) · router descriptions all ≤1024 (yaml-verified:
  max 1024 space-systems, leaf max 934) · em dashes 0 live tree.
- Per-pack leaves: aerodynamics 10 · avionics 16 · cross-cutting 10 ·
  flight-mechanics 10 · flight-test-operations 12 · gnc-autonomy 10 ·
  manufacturing-quality 11 · propulsion 12 · space-systems 10 ·
  structures 10 · systems-engineering-safety 10 · vehicle-design 10.
- Thinnest families (fill first, all at 10): cross-cutting ·
  structures · space-systems · systems-engineering-safety ·
  gnc-autonomy · aerodynamics · vehicle-design · flight-mechanics.
  (Skip avionics 16 / fto 12 / propulsion 12 / mq 11 until the 10s
  reach 12.)
- Thinnest sub-packs (1-2 leaves, fill before 3+): vehicle-design/
  conceptual (1) · aerodynamics/cfd · aerodynamics/drag-polars ·
  avionics/do160 · avionics/far-cs25 · avionics/flight-management ·
  cross-cutting/documentation · cross-cutting/sep2640 ·
  cross-cutting/units-atmos · gnc-autonomy/control ·
  gnc-autonomy/guidance · gnc-autonomy/navigation ·
  gnc-autonomy/optimal-control · gnc-autonomy/space ·
  space-systems/adcs · space-systems/orbit-mechanics ·
  structures/composites · structures/damage-tolerance ·
  structures/fatigue · structures/fem · structures/materials ·
  vehicle-design/cost-estimation · vehicle-design/mass-properties.

## YOUR TASKS (in order — INCREMENTAL-COMMIT MANDATE, 13 KILLS ON RECORD)
1. Fan-out via delegate_task ONE subagent per skill (wave protocol),
   thinnest families first (cross-cutting → structures →
   space-systems → systems-engineering-safety → gnc-autonomy →
   aerodynamics → vehicle-design → flight-mechanics), target +10-16
   verified leaves THIS wave. Every leaf: 5 REAL gates → COMMIT
   IMMEDIATELY (never batch). SUBAGENTS COMMIT THEIR OWN LEAF the
   moment gates pass — the parent can be reaped at any time and only
   committed work survives.
2. Merge ALL wave-8 eval fragments into eval/hit1-corpus.yaml +
   header counts (276 → 276+2N). Delete standalone fragments.
3. CLEAN ROUTER TABLE REWRITES for touched families — list ONLY
   built skills; descriptions stay ≤1024.
4. README badge → new live count. Stale-number guard patterns
   updated (131-class → new class) + N27/N28 fixtures.
5. GATES FRESH: make validate 5/5 · make attest 3/3 · run-tests ALL
   PASS incl N10/N11/N25-N28 · stale guard · em dashes 0 live tree ·
   tree clean (tmp sweep).
6. PUSH private: GIT_TOKEN=GITHUB_TOKEN_ARJUN git push origin main
   (credential store holds Ashforde token — arjun token explicitly;
   NEVER publish to Ashforde).
7. POST as yourself to GROUP 160 (3-15 lines, cold truth, evidence:
   leaves landed, corpus count, gates green, badge count, push
   verified).

## HARD RULES
- Commit EVERY skill immediately after gates pass. Never hold
  uncommitted work (13 kills — only committed work survives).
- Routers reference ONLY built skills (build or trim).
- One agent per skill via delegate_task; never build serially.
- No founder contact (routine progress; 50x20 release bar not met).
