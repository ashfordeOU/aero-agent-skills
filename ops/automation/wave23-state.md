# Wave-23 state notes

- 2026-09-02 WAVE-23 close: build+close prep HEAD 9cc777a (12 leaves
  landed via 3 batches of capped fan-out, 4+4+4 concurrent subagents,
  DeepSeek API health-checked HTTP 200 before batch 1; never 429/402):
  flight-mechanics/stability-control/phugoid-mode-analysis,
  gnc-autonomy/estimation-filtering/particle-filter,
  propulsion/electric/gridded-ion-thruster,
  space-systems/orbit-mechanics/low-thrust-spiral,
  systems-engineering-safety/arp4761a/reliability-block-diagram,
  vehicle-design/mdo/design-of-experiments,
  aerodynamics/wind-tunnel/windtunnel-wall-corrections,
  avionics/fsw/fprime-component,
  cross-cutting/numerics/optimization-algorithms,
  flight-test-operations/performance/level-acceleration-test,
  manufacturing-quality/as9103/key-characteristic-management (opens the
  as9103 pack; pack count 80 -> 81),
  structures/loads/random-vibration-analysis.
  Corpus 650 -> 674 tasks (24 new, 12 fragments merged via
  state/wave23-merge-corpus.py then deleted, 0 on disk); 12 family
  routers rewritten parent-side (one row + guidance bullet each, all
  descriptions <= 1024 chars verified via
  state/wave16-router-desc-len.py PASS); README/docs visuals
  regenerated to 330 leaves / 81 packs / 674 tasks via make visuals
  (design locked, numbers only; visuals-check PASS 19 artifacts fresh);
  README statline alt reconciled by hand (330/81/25/674, wave-22
  precedent). Rate-at-creation satisfied: all 12 new leaves in
  eval/skill-ratings.md at 9.5, ledger 330 = 330 leaves on disk, rows
  319-330 sequential, written in-turn by each builder; header total
  updated 318 -> 330 at close.

- GATE FIX at close (mechanical, verified by replay): fprime-component
  description lacked the explicit 'Use when' clause (gate 2 desc-lint
  FAIL). Ops patched the description to add the when-to-use clause
  (still 831 -> ~1000 chars, <= 150 words, Trigger tail retained).
  desc-lint re-run PASS; make validate re-run 5/5. No other gate fixes
  required; all 24 wave-23 corpus tasks routed Hit@1 on the first run
  (674/674 deterministic offline).

- STALE-GUARD R26: adds the wave-22-close stale class (318 skills /
  318 leaf skills / 318 verified / 330 SKILL.md / 650/650 / 650 tasks)
  to ops/automation/stale-number-guard.sh. No R25 retirements this
  wave: DOMAINS.md per-family lines now read '4 sub-domain packs · 27
  skills' ... '10 sub-domain packs · 28 skills' (six families at 27,
  six at 28 legitimately); bare '27 skills' stays retired per R25.
  Rotation, not counts edit.

- Surviving gates FRESH at rest (run-tests.sh RETIRED by founder
  cleanup 65e93e5, NOT recreated; N55/N56 MOOT per wave-20 G7
  doctrine): make validate 5/5 (674/674 Hit@1 deterministic offline),
  make attest 3/3 (number-snapshot offline + brief-audit 14 files +
  content-policy 0), stale-number-guard G7 PASS, visuals-check PASS,
  em dashes 0 in skills/, tree clean at rest (0 untracked).

- Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN) fast-forward only
  a05c5c9..9cc777a, ls-remote verified remote main == 9cc777a == HEAD,
  no Ashforde, no visibility flip. GROUP 160 close-out post VERIFIED
  (`sent\nSEND_EXIT=0`). Prep helpers committed with close prep:
  ops/automation/state/wave23-builder-kit.md (shared leaf-builder
  rules) + ops/automation/state/wave23-merge-corpus.py. Commit
  identity ashfordeOU <contact@ashforde.org> throughout (12 leaf
  commits 2ebda54..ebb8f67 + close prep 9cc777a).

- Next: CEO P5.2 WAVE-23 gate >= 9.5 -> WAVE-24.
