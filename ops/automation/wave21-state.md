# Wave-21 state notes

- 2026-09-01 WAVE-21 close: build+close HEAD 6cc6a30. 12 leaves landed via
  3 batches of capped fan-out (4+4+4 concurrent subagents, API health-checked
  HTTP 200 before batch 1; DeepSeek never 429/402): flight-mechanics/
  stability-control/short-period-mode-analysis, gnc-autonomy/estimation-filtering/
  extended-kalman-filter, propulsion/rocket/solid-rocket-motor, space-systems/
  mission-design/entry-descent-landing, systems-engineering-safety/arp4761a/
  preliminary-system-safety-assessment, vehicle-design/sizing/nacelle-sizing,
  aerodynamics/aeroelasticity/flutter-speed-prediction, avionics/flight-management/
  performance-computation, cross-cutting/tolerancing/gdandt-basics,
  flight-test-operations/envelope/spin-testing, structures/fem/contact-analysis,
  manufacturing-quality/ndt/acoustic-emission-inspection; corpus 602 -> 626 tasks
  (24 new, 12 fragments merged via state/wave21-merge-corpus.py then deleted);
  12 family routers rewritten parent-side (one row + guidance bullet each, all
  descriptions <= 1024 chars verified via state/wave16-router-desc-len.py);
  README/docs visuals regenerated at wave-21 counts via make visuals
  (306 leaves / 74 packs / 626 tasks, visuals-check PASS 19 artifacts fresh);
  stale-number-guard R23 (294/306/602 wave-20-close stale class) added to the
  kept guard script; README statline alt reconciled (hand-authored line, not
  generated); two corpus tasks reworded for Hit@1 routing to their leaves
  (w21-flutter-speed-prediction-2, w21-gdandt-basics-2). Rate-at-creation
  mandate satisfied: all 12 new leaves in eval/skill-ratings.md at 9.5,
  ledger 306 = 306 leaves on disk, written in-turn.

- GIT-RACE (2x, wave-16 class): a concurrent founder session committed twice
  mid-build via `git add -A` (39f7cf7 AGENTS.md + swept entry-descent-landing
  and short-period-mode-analysis; 65e93e5 public-readiness cleanup + swept
  nacelle-sizing, performance-computation, and the rate-at-creation ledger
  regeneration). All swept leaves verified present at HEAD with 9.5 rows;
  no file loss.

- FOUNDER RETIREMENT (65e93e5): the public-readiness cleanup deleted
  ops/automation/test/ (run-tests.sh + fixtures), wave briefs, and research
  briefs except 3 gate-required. Per wave-20 G7 doctrine the retired files
  are NOT recreated; the surviving gates are replayed FRESH instead:
  make validate 5/5 (626/626 Hit@1), make attest 3/3, stale-number-guard.sh
  G7 PASS, visuals-check PASS, em dashes 0 in skills/, tree clean. The
  N55/N56 fixture additions and run-tests.sh replay that earlier wave briefs
  required are MOOT because the founder retired that suite; recorded here
  as the true resolution (retirement, not counts edit).

- Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN) fast-forward only,
  ls-remote verified, no Ashforde, no visibility flip. GROUP 160 post
  SEND_EXIT=0. Next: CEO P5.2 WAVE-21 gate >=9.5 -> WAVE-22.
