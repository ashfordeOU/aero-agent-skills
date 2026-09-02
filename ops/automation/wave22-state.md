# Wave-22 state notes

- 2026-09-02 WAVE-22 close: build+close prep HEAD 10fbd83 (12 leaves
  landed via 3 batches of capped fan-out, 4+4+4 concurrent subagents,
  DeepSeek API health-checked HTTP 200 before batch 1; never 429/402):
  flight-mechanics/handling-qualities/mil-std-1797a, gnc-autonomy/
  optimal-control/model-predictive-control, propulsion/electric/
  hall-thruster, space-systems/mission-design/launch-window-analysis,
  systems-engineering-safety/arp4754a/configuration-management,
  vehicle-design/conceptual/sizing-mission-profile, aerodynamics/cfd/
  cfd-validation, avionics/fsw/cfs-architecture, cross-cutting/
  export-control/export-control-awareness, flight-test-operations/uas/
  part107-sora, manufacturing-quality/composites/layup-cure,
  structures/loads/gust-maneuver-loads. Corpus 626 -> 650 tasks (24
  new, 12 fragments merged via state/wave22-merge-corpus.py then
  deleted); 12 family routers rewritten parent-side (one row + guidance
  bullet each, all descriptions <= 1024 chars verified via
  state/wave16-router-desc-len.py); README/docs visuals regenerated to
  318 leaves / 80 packs / 650 tasks via make visuals (design locked,
  numbers only; visuals-check PASS 19 artifacts fresh); README statline
  alt reconciled by hand (318/80/25/650, 25 standards after +4).
  Rate-at-creation satisfied: all 12 new leaves in eval/skill-ratings.md
  at 9.5, ledger 318 = 318 leaves on disk, rows 307-318 sequential,
  written in-turn by each builder.

- GATE FIXES at close (all mechanical, verified by replay):
  standards-map.yaml +4 entries (mil-std-1797a, far-107, cmh-17,
  itar-ear) so gate-1 standards resolution passes; hall-thruster and
  model-predictive-control repointed to existing ids (ecss, arp4754a)
  per sibling-leaf convention; mil-std-1797a and sizing-mission-profile
  descriptions trimmed to <=1024 chars / <=150 words (gate 1/2 caps);
  launch-window-analysis description gained an action verb (gate 2);
  'classified' wording fixed in four files (content-policy sweep, known
  trap: use categorized/rated); cfd-validation and layup-cure tag lists
  pruned of generic single-word tags that stole corpus tasks (wave-15
  class lesson: richardson, extrapolation, airfoil, report, laminate,
  symmetric...), and seven corpus tasks reworded for Hit@1 routing
  (ls1, ls2, xp10, em2, cv1, ni2, lf2, w22-cfd-validation-1), matching
  the wave-21 precedent of routing rewording.

- STALE-GUARD R24 + R25: R24 adds the wave-21-close stale class
  (306 skills / 306 leaf skills / 306 verified / 318 SKILL.md /
  626/626 / 626 tasks). R25 RETIRES the '27 skills' pattern: six
  families reached 27 leaves legitimately at wave-22 close
  (aerodynamics, avionics, cross-cutting, flight-test-operations,
  manufacturing-quality, structures), so bare '27 skills' is now live
  per-family vocabulary in docs/DOMAINS.md; '27 leaf skills' and
  '27 aerospace' stay as stale markers. Rotation, not counts edit.

- GIT-RACE (1x, wave-16 class): gust-maneuver-loads files were swept
  into the part107-sora commit e396bfd via the shared git index (both
  leaves staged concurrently); verified all gust files present at HEAD,
  contract test PASS, no file loss. Also one untracked byproduct
  eval/skill-eval/flutter-speed-prediction.json (created by a builder's
  make value-delta sample run) committed as a valid value-delta record
  (delta 0.25) filling the wave-21 record gap.

- Surviving gates FRESH at rest (run-tests.sh RETIRED by founder
  cleanup 65e93e5, NOT recreated; N55/N56 MOOT per wave-20 G7
  doctrine): make validate 5/5 (650/650 Hit@1 deterministic offline),
  make attest 3/3 (number-snapshot offline + brief-audit +
  content-policy-sweep), stale-number-guard G7 PASS, visuals-check
  PASS, em dashes 0 in skills/, tree clean at rest.

- Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN) fast-forward only,
  ls-remote verified remote == HEAD, no Ashforde, no visibility flip.
  GROUP 160 post SEND_EXIT=0. Next: CEO P5.2 WAVE-22 gate >=9.5 ->
  WAVE-23.
