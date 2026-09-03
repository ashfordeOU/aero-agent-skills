# Wave-28 state notes

- 2026-09-03 WAVE-28 close: 14/14 planned leaves landed (founder
  mandate >=10 MET +4), close-out at HEAD 958f453f (private
  arjun-0077/aero-agent-skills, pushed via GITHUB_TOKEN_ARJUN and
  ls-remote verified remote main == 958f453f == HEAD). Full brief:
  ops/automation/wave28-brief.md (3b315549). Prep commit 081c33fe
  (builder kit + 14 specs + merge helper). Public sync completed via
  publish-public.sh at 4020ca02 (393 skills, 84 packs, 12 families),
  leaf-count guard (393 >= 379) held, About refreshed from the mirror
  post-push; GitHub CI attest run 33783044365 and release-on-milestone
  run 33783044407 (see CI verdict at close of this note).

- LEAVES (379 -> 393, rate-at-creation 9.5 in-turn, rows 380-393,
  appended by each builder at creation, no duplicates, header updated
  379 -> 393 at close):
  cross-cutting/numerics/digital-filter-design (24bb31cf),
  flight-test-operations/performance/cruise-performance-flight-test
  (f12553bf), flight-test-operations/envelope/buffet-boundary-testing
  (512798c8), flight-test-operations/envelope/vmc-determination
  (a4ae8e4e), manufacturing-quality/special-processes/
  welding-qualification (afbe0c78),
  manufacturing-quality/assembly/fastener-installation-quality
  (1fdab0d9, NEW assembly pack - first leaf),
  manufacturing-quality/as9100/fod-control (64f318ea),
  vehicle-design/sizing/brake-energy-sizing (25e0cbcf),
  aerodynamics/high-speed/hypersonic-flow (9af45975),
  aerodynamics/wind-tunnel/wind-tunnel-model-design (f17d84b1),
  structures/fem/beam-frame-analysis (5890022d),
  structures/composites/delamination-growth (0334c563),
  avionics/flight-management/rta-time-control (3b3b9603),
  space-systems/subsystems/propellant-tank-sizing (c82675f2).
  Every leaf shipped the per-skill completeness standard (SKILL.md +
  stdlib logic + offline unittest + eval fragment + value-delta JSON +
  ledger row). All 14 contract tests re-run by ops at HEAD: PASS
  (unittest counts 32-49 per leaf). All 28 new corpus tasks Hit@1 to
  their own leaf.

- SMALLEST-FIRST honored: the five 31-count families were targeted
  first and all received genuine gaps (cross-cutting +1,
  flight-test-operations +3, manufacturing-quality +3,
  vehicle-design +1, aerodynamics +2 = 10 leaves in the 31-families),
  then four more slots went to 32-count families with provable gaps
  (avionics +1, space-systems +1, structures +2). flight-mechanics,
  gnc-autonomy, propulsion, and systems-engineering-safety received no
  leaves: gap analysis found their 32-count packs dense with claims
  and the wave-27 receipts still holding (FM: dedicated dutch-roll /
  maneuver-point / time-to-climb etc. already rejected; gnc and
  propulsion packs are full toolchains; SES is the largest family and
  is last per doctrine). Candidates rejected during prep as duplicates
  or overlaps: control-surface-reversal (flight-mechanics
  aileron-reversal already owns reversal speed), Schrenk spanload
  (aerodynamics wing-planform-design already claims the Schrenk
  approximation and washout sequencing), boundary-layer transition
  (boundary-layer-theory claims transition-location classification),
  dedicated wind-tunnel force-balance reduction and additional NDT
  leaves (siblings own them). cross-cutting has one genuine numerics
  gap (digital filter design) and is otherwise documented near-full;
  vehicle-design has one genuine sizing gap (brake energy) with its
  cost/mass/mdo trios and 15-leaf sizing pack otherwise claimed.

- FAMILY SPREAD after wave (379 -> 393): cross-cutting 31 -> 32,
  flight-test-operations 31 -> 34, manufacturing-quality 31 -> 34
  (new assembly pack), vehicle-design 31 -> 32, aerodynamics 31 -> 33,
  avionics 32 -> 33, space-systems 32 -> 33, structures 32 -> 34;
  flight-mechanics 32, gnc-autonomy 32, propulsion 32,
  systems-engineering-safety 32 unchanged. 84 packs (83 + assembly).

- CORPUS 772 -> 800 tasks (28 new, 14 fragments merged via
  state/wave28-merge-corpus.py then deleted, 0 on disk), grep
  verified. 8 family routers updated parent-side (one table row + one
  routing-guidance bullet each: cross-cutting, flight-test-operations,
  manufacturing-quality, vehicle-design, aerodynamics, structures,
  avionics, space-systems), all router descriptions <= 1024 chars
  verified via wave16-router-desc-len.py PASS (all 12 families
  checked; flight-test-operations 1022 and propulsion 1024 are the
  maxes, unchanged). Router parity check PASS for all 12 families
  (rows == leaves: 33/33 aero, 33/33 avionics, 32/32 CC, 34/34 FTO,
  34/34 MQ, 32/32 VD, 34/34 structures, 33/33 space, and the
  untouched families 32/32). Ledger header updated 379 -> 393 (rows
  1-393 contiguous, no duplicates). Visuals regenerated via make
  visuals (design locked, numbers only; visuals-check PASS 19
  artifacts fresh, 393 leaves / 84 packs); manifest regenerated (405
  SKILL.md, 25 standards).

- HIT@1 NO-TASK-STEALING: gate 5 re-run after the merge returned
  800/800 PASS with ZERO pre-existing tasks stolen. Specs were written
  with distinctive hyphenated tokens per sibling fence tables (FTO
  cruise leaf deliberately avoids the flight-mechanics specific-range
  trigger phrase and tokens; vmc leaf avoids OEI/second-segment/Vref
  tokens; beam-frame leaf avoids truss/direct-stiffness tokens; space
  propellant leaf avoids aircraft fuel-volume tokens). No reword of
  any pre-existing corpus task was needed this wave.

- GATES FRESH at rest HEAD 958f453f: make validate 5/5 (800/800 Hit@1
  deterministic offline), make attest 3/3, make completeness ALL
  REQUIRED PASS, make value-delta PASS (10/10 >= 0.2), visuals-check
  PASS (19 artifacts fresh), manifest-check PASS, router descs <=
  1024, em dashes 0 in skills/, stale-number-guard PASS, tree clean.
  Pre-push hook re-ran the full gate battery and verified before the
  private push (reported all gates green).

- Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN; token identity
  verified login == arjun-0077 via the API before push) fast-forward
  only 3b315549..958f453f, ls-remote verified remote main == 958f453f
  == HEAD, no Ashforde token on the private repo, no visibility flip.
  publish-public.sh sanctioned sync: export ran the full gate battery
  inside, leaf-count guard (393 >= 379) passed, pushed 4020ca02 to
  ashfordeOU/aero-agent-skills (normal fast-forward, no force),
  verified 393 skills / 84 packs / 12 families, About refreshed from
  the mirror post-push (fix eec11e34 held). GitHub CI: attest run
  33783044365 and release-on-milestone run 33783044407 both
  SUCCESS at close-out time.

- SPEC DEVIATIONS / disclosures:
  1. buffet-boundary-testing spec fixture: the draft worked example
     used an inconsistent wing loading (1-g cruise lift coefficient
     near 1.46, unphysical for a transport); caught during prep, the
     fixture was corrected to S = 360 m2 with the derived cl_buf and
     margin numbers recomputed before dispatch. The builder's module
     reproduced the anchors (detected onset 1.8444 at M 0.80 by
     sample-grid interpolation rather than the spec's nominal 1.85;
     the spec tolerances absorbed the 0.006 difference and the fitted
     margin came out +0.551 as predicted). Recorded for the audit.
  2. delamination-growth spec: the DCB compliance cross-check
     required the correct load-line opening delta = 2*w (one-arm
     deflection double); the spec text was rewritten cleanly during
     prep with h = 0.003 m so the two forms agree to 1e-6. Builder
     smoke confirmed diff 0.0.
  3. Two sandbox interactions recurred: python3 -c / heredoc smoke
     checks are blocked in single-query mode, so builders used written
     /tmp smoke scripts (vmc-determination hit the block once and
     adapted; no re-dispatch). One compound shell for-loop with nested
     command substitution was blocked by the security scanner during
     the ops merge phase; parity was checked with a small python
     script instead.
  4. beam-frame-analysis builder went quiet mid-context-gathering
     (~8 min) and was steered once to start writing; it recovered
     without re-dispatch and delivered 35/35 tests with exact
     cantilever and simply-supported beam anchors. All other 13
     builders ran clean on the anti-hang protocol. No builder died
     this wave (14/14).

- DISPATCH LESSON: four batches (4+4+4+2) from prep commit 081c33fe
  in about 32 minutes of fan-out wall time (18:28-19:00 UTC). The
  per-spec math anchors (vmc V_auth 71.18 m/s, delamination G_I 411.52
  J/m2, hypersonic sphere Cd 0.9137, brake RTO 171.5 MJ, cruise vertex
  0.8/LRC 0.81225) matched builder smoke outputs, keeping verification
  mechanical. The one steer (beam-frame) plus the vmc smoke-block
  adaptation were the only interventions.

- Next: CEO P5.2 WAVE-28 audit >= 9.5 -> WAVE-29.
