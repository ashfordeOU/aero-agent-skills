# Wave-42 state notes

- 2026-09-06 WAVE-42 close. Baseline (wave-41 close): 567 leaves, 85
  packs, 12 families, 1150 router tasks, 30 standards; wave-41 close
  a9fa0d63, infra/docs commits to ba8b8906, then the wave-42 brief
  commit 58560772 == remote main (ls-remote verified at dispatch
  ~08:14 UTC). Ratings ledger 567 rows. CEO gate PASSED 9.68/10 at
  wave-41. Quiet-hours gate green at dispatch and before every batch
  (exit 0 each). API health: deepseek HTTP 401 = reachable (0.31 s);
  runtime session live on the deepseek provider throughout.
  Prep commit 7f25623f (builder kit, close runbook, merge/sim helpers,
  leaf plan, 14 specs at ops/automation/state/wave42-specs/, all
  anchor-verified by executing python anchor scripts).

## Fresh family receipts (5 parallel read-only probe agents at the
wave-42 HEAD 58560772, receipts over lists honored, deleg_85fa5536)

- GNC 42: NOT saturated (wave-41's reaffirmation was candidate-set
  specific). WHOLE-family fresh probe found clean deterministic gaps in
  navigation + optimal-control: gnss-carrier-smoothing (Hatch IIR
  between single-epoch gnss-pseudorange-positioning and raim),
  lqg-design (regulator+filter Riccati composition; lqr is full-state
  only, observer-design is deterministic Luenberger), bearing-only-
  localization (Stansfield WLS; ekf is dynamic range-bearing tracking),
  tdoa-positioning (declined for the wave: fence-adjacent to
  manufacturing-quality acoustic-emission planar hyperbolic location;
  kept in reserve). Space/control/guidance packs saturated (declines in
  receipts).
- AERO 43: 3 gaps landed: shock-tube (implicit diaphragm-match bisection
  + four-region state; normal-shock is stationary-shock-given-M1),
  thin-airfoil-section-theory (Glauert sine-series section coefficients;
  lift-curve-slope CONSUMES section data, never derives it from camber;
  the prep anchor REJECTED the probe's draft moment form and verified
  cm_c4 = (pi/4)*(A2 - A1)), compressible-couette-flow (exact
  constant-property solution, recovery factor r = Pr identity verified;
  flat-plate-skin-friction-heating is the external-plate method).
  Decline list fresh: aileron-reversal OWNED (flight-mechanics),
  van-Driest/Chapman-Rubesin dup, Fay-Riddell dup, Falkner-Skan ODE,
  law-of-the-wall fenced, Taylor-Maccoll ODE, MOC marching, etc.
- FTO 43: 13/14 saturation re-confirmed; ONE genuine gap landed:
  rotorcraft-autorotation-flight-test (measurement side of the power-off
  demo; fm rotorcraft-autorotative-descent is the analytic estimate and
  defers the flight-test reduction to FTO; wave-41 fuel-jettison
  measurement-vs-design precedent).
- PROP 43: scramjet-cycle CLOSED (not re-opened); wave-39 declines
  stood; ONE gap landed: brayton-optimum-pressure-ratio (max-work PR
  closed form x_opt = sqrt(tau*eta_c*eta_t), zero-work limit = r_opt^2;
  regenerative-cycle owns the optimum-pressure-ratio tag so the new tag
  is brayton-optimum-pressure-ratio). rocket-nozzle-divergence-loss
  flagged MARGINAL by the probe and NOT planned.
- SES 45: 2 gaps landed in arp4761a: fault-tree-quantification (the
  missing PRODUCER in the FTA->SSA chain: rare-event + Esary-Proschan
  min-cut upper bound + bounded exact IE + truncation; fta-fmea takes
  top_prob as INPUT, importance-measures is exact-IE small-n only) and
  reliability-allocation (failure-rate/MTBF budget flow-down with
  equal-split + complexity-weighted schemes + series-sum closure; PSSA
  allocate_safety_target is per-condition probability equal-split across
  channels - different quantity and schemes). reliability-prediction-
  parts-count NOW DECLINED definitively: no MIL-HDBK-217/Telcordia id in
  standards-map.yaml, a fabricated generic base-rate table violates the
  verified-anchor discipline, and the residual series-sum logic is owned
  by reliability-block-diagram + maintainability-prediction; reopen only
  if MIL-HDBK-217F is added to standards-map.yaml.
- FM 46: 1 gap landed: rotorcraft-main-rotor-sizing (sizing inversion
  for the main rotor; rotorcraft-hover-performance declares geometry is
  an input, rotorcraft-tail-rotor-sizing is the anti-torque counterpart).
- STRUCT 51: 2 gaps landed: shear-center-analysis (V*Q/I transverse-
  shear shear-flow + shear-center location; torsion-shear-flow is
  Bredt-Batho torsion only, diagonal-tension stops short, divergence-
  speed consumes the offset e as input) and shrink-fit-analysis (Lame
  two-cylinder radial-interference contact pressure; solid-rivet-
  installation-quality EXCLUDES interference fits by contract).
- VD 54: 1 gap landed: landing-gear-layout (tipback / tail-strike /
  lateral-turnover / nose-gear-load-fraction band; landing-gear-sizing
  is the static load split for a GIVEN wheelbase).
- AV 46 / MQ 48 / SPACE 52 / CC 54: saturated or default-CLOSED
  reaffirmed fresh (whole-family reads); CC stayed closed (smaller
  families not exhausted).

## Leaves landed (14; one commit each unless swept; ashfordeOU)
gnc-autonomy +3 (45): gnss-carrier-smoothing (b39fe06c),
lqg-design (dc407b17), bearing-only-localization (db4ed4b0).
aerodynamics +3 (46): shock-tube (d9cdc661),
thin-airfoil-section-theory (c17578e2),
compressible-couette-flow (0aa837a2).
flight-test-operations +1 (44): rotorcraft-autorotation-flight-test
(709a01ae).
propulsion +1 (44): brayton-optimum-pressure-ratio (ee501540).
systems-engineering-safety +2 (47): fault-tree-quantification
(90ed39dc), reliability-allocation (836f05b1).
flight-mechanics +1 (47): rotorcraft-main-rotor-sizing (fb782a08).
structures +2 (53): shear-center-analysis (2a57da43),
shrink-fit-analysis (bd5bdd14).
vehicle-design +1 (55): landing-gear-layout (3e8f26f4).
Totals: 567 -> 581 leaves; 12 routers; 579 -> 593 SKILL.md;
corpus 1150 -> 1178 (28 new tasks, 2 per leaf); ledger 581 rows
(568-581 appended at creation at >= 9.5, header updated at close,
physical row order normalized to ascending; 0 duplicates, 0 gaps).

## Deviations / disclosures (honest)
- bearing-only-localization DESC-FIX at close: gate2 (desc-lint) found
  the builder's description missing the mandatory 'Trigger' keyword (the
  spec's reference description had been gate-verified with 126 words but
  the committed text ended at the Does-NOT-do sentence). Fixed by editing
  the YAML frontmatter line itself (wave-41 lesson: never a line-blob
  regex) to a 804-char / 93-word description with the Trigger tail;
  desc-lint re-run PASS, then make visuals re-run (wave-40 lesson #2:
  any leaf edit after the last make visuals must be followed by make
  visuals before push).
- Spec-engineer stalls (2 of 14, both on shear-center-analysis): the
  first hung after its reads (10:44-10:55, 11 min silent, steer queued
  but unreachable mid-generation); stopped and re-dispatched; the
  re-dispatch ALSO stalled after its reads (10:55-11:05). Ops then wrote
  the anchor + spec directly (12 min): the anchor integration initially
  returned fy ~ 0 (the V/I factor was applied to the first moment Q but
  not to the wall shear force); root-caused with a per-segment debug
  script, fixed (q = vy*Q/ixx in the force/moment integrals), verified
  equilibrium fy = -999.9 N and channel |e| = 18.750 mm matching the
  classical 3b^2/(h+6b) to 1.000002 ratio. The spec committed with REAL
  anchor outputs; the builder then built the leaf cleanly (2a57da43).
  Lesson: a spec-engineer prompt that requires reading three files then
  writing a long anchor can stall twice on this model; after one
  re-dispatch, write the anchor+spec directly (ops pattern).
- No pre-merge rewording was needed: the routing simulation PASSed
  1178/1178 with zero pre-existing task thefts (14 fragments, 28 tasks).
- value-delta sampler rewrite: at close, make value-delta recomputed and
  persisted thin-airfoil-section-theory's eval record (passed 33 ->
  1, without_estimate 0.5 -> 0.667, delta 0.5 -> 0.333) from TEST FILE
  term presence per the wave-38 lesson #3 sampler rule; delta 0.333 is
  still >= 0.2 (PASS), so the gate-sanctioned record was committed as-is.

## Close-out gates FRESH at rest (re-run, not claimed; commit c96c9507)
make validate 5/5 (1178/1178 Hit@1 deterministic offline) PASS
make attest 3/3 (number-snapshot offline + brief-audit + content
policy 0 red flags) PASS
make completeness ALL REQUIRED PASS
make value-delta 10/10 >= 0.2 PASS
make visuals-check PASS (19 artifacts fresh; manifest zero diff;
re-run after the desc fix)
router parity rows == leaves on all 12 families (aero 46, av 46,
cc 54, fm 47, fto 44, gnc 45, mq 48, prop 44, space 52, struct 53,
ses 47, vd 55)
router descriptions <= 1024 chars (wave16 checker PASS)
stale-number-guard PASS
REAL em-dash count in skills/ = 0 (git grep U+2014; zero at prep and
zero at close)
git status --short clean (tree clean at rest)

## Push / publish receipts
- PRIVATE push: 58560772..dcff3923 (17 commits: prep, 14 leaf builds,
  close, exact-float test fix) fast-forward via the arjun origin token,
  background process. FIRST TWO push attempts were blocked by the
  pre-push hook at gate3 (pytest-contract) with the SAME latent defect
  class as wave-41's event-tree-analysis, this time in the new
  reliability-allocation test: test_equal_split_closure_relative_error_
  at_float_noise asserted the EXACT float-noise relative error
  (1.3552527156068805e-16, delta=1e-18) of a series-sum closure.
  Root-caused with a hash-seed gate loop (6 seeds PASS), a 10-seed
  stress of all 14 new leaves (PASS), a full hook log capture, and a
  two-interpreter check: the pre-push hook env resolves python3 to
  pyenv 3.13.12 (login shell sources .zshrc -> pyenv shims first;
  Neumaier-accurate sum() since 3.12 -> relative_error 0.0) while
  foreground shells use /usr/bin/python3 3.9.6 (naive sum() ->
  1.3552527e-16). Fixed structurally: exact-noise asserts replaced
  with algorithm-safe bounds (abs < 1e-15), docstrings updated,
  verified 33 tests PASS on BOTH interpreters, __pycache__ purged
  (581 dirs), committed dcff3923. Then ALL GATES GREEN and the push
  succeeded; ls-remote verified remote main == local HEAD dcff3923.
  No Ashforde token, no visibility flip.
- PUBLIC sync: publish-public.sh PASS at 10:25-10:28 UTC (log
  /tmp/w42_pub.log; ~12:25 CEST): full gate battery inside the
  export green, leaf-count guard 581 >= 567 (no regression), public
  repo fast-forward to f017adc8 (581 skills, 85 packs, 12 families),
  GitHub About refreshed. Public mirror HEAD == public remote main ==
  f017adc8 at the wave sync (10:28 UTC). GitHub CI for f017adc8:
  attest run 34027538618 SUCCESS (completed ~10:33 UTC; re-verified
  by the close-out rescue at 10:43 UTC) and release-on-milestone run
  34027538616 SUCCESS. NOTE: the publish-public AUTOMATION later
  synced the local dev tree (f42208e9 + 4819dc97, then still
  unpushed privately) to public as 358c5824 at 10:41 UTC - gates
  verified in-export; CI attest run 34028106082 SUCCESS +
  release-on-milestone run 34028106088 SUCCESS for 358c5824 (the
  wave-41 race-ahead pattern; further automation syncs may follow
  the rescue commits).
  publish-public.sh fixes kept: 2da34f0e (leaf-count guard),
  eec11e34 (About refreshed from the mirror post-push), 4819dc97
  (refresh BOTH Abouts public+private + no-op falls through;
  committed 12:41 +0200 by the build proc seconds before the kill).
- GROUP 160 close-out post sent as Ops Manager at 12:36:55 CEST
  (10:36:55 UTC): SEND_EXIT=0, hermes send output "sent" (the CLI
  emits no numeric message_id; platform_message_id NULL in the
  session DB). Landed verified: opsmanager session DB row 73130 in
  telegram session 20260830_210110_3522b7ea (session_key
  agent:opsmanager:telegram:group:-1004333545328:160, "Project
  Veda"). The close-out rescue did NOT re-post: the message landed
  before the build proc was killed, so a second post would duplicate
  (dedup; relay task 3 satisfied by verification, not re-send).
- Close-out rescue (relay dispatch ~12:35 CEST): the relay snapshot
  was stale - the build proc actually survived to 12:41 +0200,
  completing the GROUP post (above), the state-note commit f42208e9,
  and the publish fix 4819dc97 before the kill; its final push
  (origin target dcff3923..f42208e9) was killed mid-pre-push-hook
  and never landed (origin stayed at dcff3923). Rescue tail: attest
  re-verified SUCCESS (run 34027538618), receipts completed here,
  GROUP post deduped (not re-sent), and f42208e9 + 4819dc97 + relay
  brief 4498e568 + the receipts commit were pushed together to the
  private origin (arjun token, CI-first). Push verification: the
  rescue's pre-push battery ran ALL GATES GREEN on c9e81c46; the ref
  update was rejected only because a concurrent pusher (a respawned
  push chain from the dead session's still-alive gateway-supervised
  process - since terminated) landed the SAME sha c9e81c46 first.
  Final state: origin/main == c9e81c46, ls-remote verified by the
  rescue at ~10:57 UTC; no Ashforde token, no force, fast-forward
  only. The gateway-supervised build-proc husk (started 10:13 UTC)
  was NOT dead at relay dispatch - it respawned push retries until
  terminated by the rescue; the relay snapshot that declared it
  killed at 12:29 CEST was stale by ~12 minutes.

## Lessons (this wave, for the next brief)
1. INTERPRETER-DEPENDENT SUM (wave-42, extends the wave-41 exact-float
   lesson): the pre-push hook runs under a login-shell environment where
   python3 resolves to pyenv 3.13.12 (Neumaier-accurate sum() since
   3.12) while foreground shells use /usr/bin/python3 3.9.6 (naive
   sum()). Any test asserting an exact float-noise value of a computed
   aggregate with a sub-1e-15 delta can pass standalone and fail under
   the hook. VERIFY new contract tests under BOTH interpreters before
   pushing (python3 vs ~/.pyenv/versions/3.13.12/bin/python3), and keep
   every computed-aggregate assert at a >= 1e-15 tolerance band.
2. A spec-engineer prompt that requires reading three files then
   writing a long anchor script can stall twice on this model (2 of 14
   stalls this wave, both shear-center-analysis, 8-11 min silent each;
   the steer could not reach the hung child). After one re-dispatch,
   write the anchor + spec directly (ops pattern) - 12 min including a
   numerical bug root-cause (V/I factor missing in the wall-shear force
   integral; fixed with a per-segment debug script; channel |e| matched
   the classical 3b^2/(h+6b) to 1.000002).
3. Builder descriptions drafted within limits held all wave: 0 desc
   trims needed at close (wave-41's desc-trim lesson internalized by the
   kit); the one close fix was a missing mandatory Trigger keyword in
   bearing-only-localization's description (spec reference desc had been
   gate-checked, the committed text ended early) - fixed via the YAML
   frontmatter line, desc-lint re-run, visuals re-run.
4. Wave-38 lesson #3 value-delta sampler confirmed at close: the gate
   recomputes AND persists the sampled eval record from test-file term
   presence (thin-airfoil-section-theory record rewritten by the gate to
   delta 0.333; still >= 0.2 so committed as the gate-sanctioned value).
