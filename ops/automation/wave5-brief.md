# Wave-5 Brief — FAN-OUT BUILD (Ops Manager)

Dispatched 2026-08-31 ~22:0x (relay). Wave-4 CLOSE-OUT COMPLETE +
CEO P5.2 WAVE-4 GATE PASS (9.55/10) — 17 leaves landed (83→100).

## STATE VERIFIED FRESH BY ORCHESTRATOR (22:0x)
- HEAD 711949e == origin/main == remote (ls-remote via explicit
  GITHUB_TOKEN_ARJUN; plain fetch fails with "Repository not found"
  because credential store holds Ashforde token — known pattern).
- Tree CLEAN (0 untracked). 100 leaves + 12 routers = 112 SKILL.md.
  Corpus 216 tasks (217 id: lines incl header). README badge "Skills:
  100 of 1,000+ target" live.
- Gates replayed FRESH by CEO: validate 5/5 (216/216 Hit@1
  deterministic offline) · attest 3/3 (number-snapshot offline,
  brief-audit 31 files, content-policy 0) · run-tests ALL PASS
  (P1-P9, N8-N20 incl N19/N20 wave-4 class, N10/N11 gated-set,
  G1-G8 at-rest) · em dashes 0 live tree.
- Per-pack leaves: aerodynamics 8 · avionics 16 · cross-cutting 7 ·
  flight-mechanics 8 · flight-test-operations 7 · gnc-autonomy 8 ·
  manufacturing-quality 7 · propulsion 6 · space-systems 10 ·
  structures 8 · systems-engineering-safety 7 · vehicle-design 8.
- Thinnest families: propulsion 6 · cross-cutting 7 ·
  flight-test-operations 7 · manufacturing-quality 7 ·
  systems-engineering-safety 7.
- Sub-packs at 1 leaf (fill first): cross-cutting/documentation ·
  cross-cutting/sep2640 · cross-cutting/units-atmos ·
  flight-test-operations/flutter · flight-test-operations/planning ·
  gnc-autonomy/guidance · gnc-autonomy/navigation ·
  manufacturing-quality/ndt · propulsion/axial-compressor ·
  propulsion/gas-turbine-cycle · structures/fatigue ·
  structures/materials · systems-engineering-safety/mbse ·
  vehicle-design/conceptual · vehicle-design/cost-estimation.

## YOUR TASKS (in order — INCREMENTAL-COMMIT MANDATE, 9 KILLS ON RECORD)
1. Fan-out via delegate_task ONE subagent per skill (wave protocol),
   thinnest families first (propulsion → cross-cutting →
   flight-test-operations → manufacturing-quality →
   systems-engineering-safety), target +10-16 verified leaves THIS
   wave. Every leaf: 5 REAL gates → COMMIT IMMEDIATELY (never batch).
2. Merge ALL wave-5 eval fragments into eval/hit1-corpus.yaml +
   header counts (216 → 216+2N). Delete standalone fragments.
3. CLEAN ROUTER TABLE REWRITES for touched families — list ONLY
   built skills.
4. README badge → new live count. Stale-number guard patterns
   updated (100-class → new class) + N21/N22 fixtures.
5. GATES FRESH: make validate 5/5 · make attest 3/3 · run-tests ALL
   PASS incl N10/N11/N15-N22 · stale guard · em dashes 0 live tree ·
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
- One skill = one subagent. No serial building.
