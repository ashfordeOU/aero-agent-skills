# Wave-25 state notes

- 2026-09-03 WAVE-25 close: 12/12 planned leaves landed (founder
  mandate >=10 MET +2), close-out at HEAD 60de138 (private
  arjun-0077/aero-agent-skills, pushed via GITHUB_TOKEN_ARJUN and
  ls-remote verified remote main == 60de138 == HEAD). Full brief:
  ops/automation/wave25-brief.md. Public sync follows via
  publish-public.sh (separate entry below once verified).

- LEAVES (341 -> 353, rate-at-creation 9.5 in-turn, rows 342-353,
  appended in-turn by each builder, no duplicates):
  vehicle-design/sizing/ice-protection-sizing (9431843),
  vehicle-design/sizing/spoiler-sizing (dba96be),
  avionics/do160/radio-frequency-emissions (72a50a6),
  avionics/flight-management/lateral-navigation (8488957 + remainder
  86edcaf), cross-cutting/numerics/quaternion-algebra (68b37ce),
  flight-mechanics/performance/windshear-analysis (fbc995d),
  flight-test-operations/planning/position-error-calibration
  (927b246), manufacturing-quality/ndt/computed-tomography (296bcd8),
  gnc-autonomy/control/control-allocation (8da55cc),
  propulsion/rocket/hybrid-rocket-motor (ba664e7),
  space-systems/adcs/control-moment-gyro (66c9b54),
  structures/materials/creep-rupture (433423e).
  Every leaf shipped the per-skill completeness standard (SKILL.md +
  stdlib logic + offline unittest + eval fragment + value-delta JSON +
  ledger row). All 12 contract tests RE-RUN by ops at HEAD: PASS.
  Family spread per brief (smallest-first): vehicle-design 27->29 (+2,
  smallest family prioritized), avionics 28->30 (+2),
  cross-cutting 28->29 (+1), flight-mechanics 28->29 (+1),
  flight-test-operations 28->29 (+1), manufacturing-quality 28->29
  (+1), gnc-autonomy 29->30 (+1), propulsion 29->30 (+1),
  space-systems 29->30 (+1), structures 29->30 (+1), aerodynamics
  30 (untouched, largest), systems-engineering-safety 28 (untouched).

- SES DELIBERATE SKIP (disclosed, not an omission): systems-
  engineering-safety (28) received no leaf this wave. Its packs are
  saturated: arp4754a 8 leaves, arp4761a 11 leaves, mbse 6,
  certification 2 (certification-basis + means-of-compliance),
  requirements 1 (requirements-elicitation). Every method slot
  (FHA/PSSA/SSA/FTA-FMEA/Markov/RBD/CCA/ZSA/PRA/OSHA/failure-rate,
  DAL/FDAL/IDAL, allocation/traceability/validation/verification-
  planning/config-mgmt, sysml/n2/state-machine/trade-study) already
  has a published leaf; no clean non-overlapping engineering gap was
  found. SES stays the smallest family at 28 and is the priority
  start point for wave-26.

- CORPUS 696 -> 720 tasks (24 new, 12 fragments merged via
  state/wave25-merge-corpus.py then deleted, 0 on disk), grep
  verified. 10 family routers updated parent-side (one table row +
  one routing-guidance bullet each; vehicle-design and avionics got
  two rows), all router descriptions <= 1024 chars verified via
  state/wave16-router-desc-len.py PASS. Ledger header updated
  341 -> 353. README/docs visuals regenerated via make visuals
  (design locked, numbers only; visuals-check PASS 19 artifacts fresh,
  353 leaves / 81 packs); manifest regenerated (365 SKILL.md);
  npm package battery PASS (manifest + router parity 720 + installer +
  MCP + CLI).

- HIT@1 ROUTING: gate 5 re-run after the merge returned 720/720
  PASS deterministic offline with ZERO pre-existing task stolen by a
  new leaf description (wave-24R lesson: means-of-compliance / desat-
  dipole). No routing fix was needed this wave. New-leaf corpus tasks
  were written to carry each leaf's distinctive hyphenated tokens, and
  descriptions were fenced against sibling claims per the specs
  (e.g. RF-emissions vs RF-susceptibility, PEC airspeed vs AoA
  calibration, hybrid vs solid rocket, CMG vs reaction wheel).

- GATES FRESH at rest HEAD 60de138: make validate 5/5 (720/720 Hit@1
  deterministic offline), make attest 3/3, make completeness PASS,
  make value-delta PASS (10/10 >= 0.2), visuals-check PASS, em dashes
  0 in skills/, router descs <= 1024, tree clean. Pre-push local gate
  battery (validate + attest + completeness + value-delta +
  visuals-check + package-test) also PASS - the push hook itself
  re-ran the full battery and verified before the private push.

- Push PRIVATE via arjun token (GITHUB_TOKEN_ARJUN) fast-forward only
  6b2551c..60de138, ls-remote verified remote main == 60de138 == HEAD,
  no Ashforde token on the private repo, no visibility flip.

- CONCURRENT-SESSION NOTE (disclosed, no conflict): three commits
  from other sessions landed in the wave window, all docs/ops only:
  d152b1a visuals refresh to 341/696, 191f9e9 visuals refresh to 344
  leaves (mid-wave), fb1b504 release machinery + maintenance doc,
  7d41b4f publish-public descriptive sync-commit helper. Explicit-path
  commits by all 12 builders kept leaf history clean; ops close-prep
  60de138 sits on top of fb1b504.

- SPEC DEVIATIONS / notes (recorded per the builder-kit rule): none
  of the 12 leaves deviated from its spec outputs; builders that hit
  ambiguity documented module constants as reference-only typicals in
  the SKILL bodies (e.g. hybrid rocket regression constants, CMG
  geometry, CT tube-energy rule of thumb). All contract tests assert
  real module outputs computed by the builders, per the wave-24R
  doctrine.

- DISPATCH LESSON (repeatable): the anti-hang protocol (write logic
  files in small pieces, compact unittests, early test runs) held for
  all 12 builders; no stalls, no TURN-ALIVE text-only deaths, no
  re-dispatches needed. Wave-25 completed in three batches of 4 from
  prep commit a66b357 in ~35 minutes of fan-out time.

- Next: CEO P5.2 WAVE-25 audit >= 9.5 -> WAVE-26.
