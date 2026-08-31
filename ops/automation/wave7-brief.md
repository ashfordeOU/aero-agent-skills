# Wave-7 Brief — FAN-OUT BUILD (Ops Manager)

Dispatched 2026-09-01 ~00:1x (relay). Wave-6 CLOSE-OUT COMPLETE +
CEO P5.2 WAVE-6 GATE PASS (9.55/10) — 10 leaves landed (112→122)
incl fuselage-sizing rescue + 9 fan-out leaves.

## STATE VERIFIED FRESH BY ORCHESTRATOR (00:1x)
- HEAD e4145e7 == remote main == e4145e7 (ls-remote via explicit
  GITHUB_TOKEN_ARJUN verified; plain fetch fails "Repository not
  found" — credential store holds Ashforde token, known pattern).
- Tree CLEAN (0 untracked). 122 leaves + 12 routers = 134 SKILL.md.
  Corpus 258 tasks. README badge "Skills: 122 of 1,000+ target"
  live + N23/N24 stale-guard fixtures.
- Gates replayed FRESH by CEO: validate 5/5 (258/258 Hit@1
  deterministic offline) · attest 3/3 (number-snapshot offline,
  brief-audit 31 files, content-policy 0) · run-tests ALL PASS
  (P1-P9, N1-N24 incl N23/N24 wave-6 class, N10/N11 gated-set,
  G1-G8 at-rest) · router descriptions all ≤1024 (yaml-verified).
- Per-pack leaves: aerodynamics 10 · avionics 16 · cross-cutting 10 ·
  flight-mechanics 10 · flight-test-operations 9 · gnc-autonomy 10 ·
  manufacturing-quality 9 · propulsion 9 · space-systems 10 ·
  structures 10 · systems-engineering-safety 9 · vehicle-design 10.
- Thinnest families (fill first): flight-test-operations 9 ·
  manufacturing-quality 9 · propulsion 9 ·
  systems-engineering-safety 9.
- Sub-packs at 2 leaves (fill before 3+): fto/envelope · fto/flutter ·
  fto/planning · mq/as9102 · mq/ndt · prop/axial-compressor ·
  prop/gas-turbine-cycle · prop/turbofan · ses/mbse.
- OPEN ITEM (carry this wave): 1 em dash in eval/skill-ratings.md
  line 3 ("CEO (Arjun) — 2026-08-31", from 4bbb89a rating ledger) —
  sweep to 0 so the live tree em-dash claim is exact again.

## YOUR TASKS (in order — INCREMENTAL-COMMIT MANDATE, 13 KILLS ON RECORD)
1. Fan-out via delegate_task ONE subagent per skill (wave protocol),
   thinnest families first (flight-test-operations →
   manufacturing-quality → propulsion → systems-engineering-safety),
   target +10-16 verified leaves THIS wave. Every leaf: 5 REAL gates
   → COMMIT IMMEDIATELY (never batch). SUBAGENTS COMMIT THEIR OWN
   LEAF the moment gates pass — the parent can be reaped at any time
   and only committed work survives.
2. Merge ALL wave-7 eval fragments into eval/hit1-corpus.yaml +
   header counts (258 → 258+2N). Delete standalone fragments.
3. CLEAN ROUTER TABLE REWRITES for touched families — list ONLY
   built skills; descriptions stay ≤1024.
4. README badge → new live count. Stale-number guard patterns
   updated (122-class → new class) + N25/N26 fixtures.
5. GATES FRESH: make validate 5/5 · make attest 3/3 · run-tests ALL
   PASS incl N10/N11/N23-N26 · stale guard · em dashes 0 live tree
   (INCL the skill-ratings.md open item) · tree clean (tmp sweep).
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
- Do NOT touch the Ashforde token / org. Private arjun-0077 only.
- One skill = one subagent. No serial building.
- Keep parent context LEAN: delegate per-skill, no large dumps into
  parent; abort completions stalled >10 min (do not sit in the 600s
  stale-kill loop).
