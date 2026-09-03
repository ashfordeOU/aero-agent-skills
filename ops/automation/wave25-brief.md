# WAVE-25 BRIEF — Aero Agent Skills (public v1.0.1 baseline)

CEO dispatch 2026-09-03 (~10:20 UTC, window open). Continuation of the
founder-mandated wave cadence after CEO P5.2 WAVE-24R audit PASSED
9.66/10 (relay 2026-09-03 ~12:18 CEST).

## Baseline (VERIFIED by CEO at dispatch)
- Dev tree: ~/AeroSkills @ HEAD 85c2f59 (== private arjun-0077/aero-agent-skills main, verified)
- **Current: 341 leaves · 81 packs · 12 families · 696 router tasks**
- Per-family leaf counts (341 leaves; router excluded per family):
  vehicle-design 27 · avionics 28 · cross-cutting 28 · flight-mechanics 28 ·
  flight-test-operations 28 · manufacturing-quality 28 ·
  systems-engineering-safety 28 · gnc-autonomy 29 · propulsion 29 ·
  space-systems 29 · structures 29 · aerodynamics 30
- Public repo: ashfordeOU/aero-agent-skills main == 7ba2507149 (sync:
  341 skills, 81 packs, 12 families; GitHub CI attest SUCCESS on that commit)
- Repo model: build in DEV (private), sync to PUBLIC via
  ops/automation/publish-public.sh (gated, never force, public-safety
  audit mandatory). GitHub CI attest.yml on every public push.
- Gates FRESH at dispatch: make validate 5/5 (696/696) · make attest 3/3 ·
  completeness PASS · router descs ≤1024 · em dashes 0 · tree clean.

## Target
- **+10-16 verified leaves, MUST land ≥10** (founder wave mandate)
- Priority families (smallest first): vehicle-design (27) → the six
  28-count families (avionics · cross-cutting · flight-mechanics ·
  flight-test-operations · manufacturing-quality ·
  systems-engineering-safety) → then 29-count headroom (gnc-autonomy ·
  propulsion · space-systems · structures) → then aerodynamics (30).
  ONE agent per leaf (PARALLEL-AGENT doctrine).
- Every leaf (per-skill completeness standard, wave-24R kit at
  ops/automation/state/wave24r-builder-kit.md is the reference):
  - agentskills.io-conformant SKILL.md (name + trigger-first desc ≤1024)
  - scripts/ logic + scripts/test_*.py offline contract test
  - no broken refs; references/ + assets/ as needed
  - eval/skill-eval/<name>.json value-delta (threshold 0.2)
  - rate-at-creation ≥9.5 in eval/skill-ratings.md ledger (in-turn row,
    341 → 341+N; do NOT disturb rows ≤341)
  - corpus tasks: +2 per leaf (696 → 696+2N via the merge-corpus
    pattern; delete eval/hit1-wave25-*.yaml fragments after merge)
  - standards-map.yaml ext when a standard applies
  - Hit@1: verify no existing task is stolen by a new leaf's description
    (wave-24R gate-fix lesson: means-of-compliance stole p1; reaction
    wheel stole the desat-dipole task — re-run gate 5 and fix routing
    BEFORE close-out, never after)

## Gates (all must PASS before close-out)
1. make validate 5/5 (incl. Hit@1 696+2N tasks deterministic offline)
2. make attest 3/3 (number-snapshot + brief-audit + content-policy)
3. make completeness + make value-delta
4. make visuals (numbers only — design LOCKED) + visuals-check
5. public-safety audit (scripts/public-safety-audit.py) — zero local
   paths/usernames/tokens in tree + history
6. Em dashes 0 in skills/ · router descs ≤1024
7. Tree clean at rest

## Close-out chain
1. Push PRIVATE (arjun-0077/aero-agent-skills) + ls-remote verify
   (GITHUB_TOKEN_ARJUN; NO Ashforde token on the private repo, NO
   visibility flip)
2. make visuals + commit numbers
3. GROUP 160 close-out post as self (SEND_EXIT=0 verify)
4. wave25-state.md honest disclosures (spec deviations documented in
   SKILL bodies; no silent changes)
5. **Sync to PUBLIC: bash ops/automation/publish-public.sh** → verify
   remote HEAD == mirror HEAD; GitHub CI attest.yml green (check via API)
6. CEO P5.2 WAVE-25 audit ≥9.5 → WAVE-26

## Notes
- TURN-ALIVE (HARD, wave-24R re-dispatch lesson): NEVER end a turn with
  a text-only response while any delegation is live — the CLI exits and
  tears down all children (4 prior occurrences). Status updates are
  tool calls (hermes send / polls), never bare text. The ONLY permitted
  text-only response is the final close-out report AFTER all subagents
  completed and all gates are green.
- API health first: if 429/402/balance → build SEQUENTIALLY, commit each
  leaf immediately, re-test every 3 leaves; if balance exhausted → stop
  clean "BALANCE BLOCKED — founder must top up DeepSeek", NO fake gates.
- Anti-hang protocol (wave-24R lesson): write large logic files in 2-3
  small pieces (write_file + patch); compact unittests; run tests early.
- Subagents commit EXPLICIT PATHS ONLY (no git add -A — wave-21 git-race
  lesson; no sweeping files into the wrong commit).
- Quiet hours 20:00-08:00 UTC respected absolutely (gate check before
  spawning; ~/hermes/scripts/quiet-hours-gate.py --check exit 0 = OK).
  Dispatched ~10:20 UTC — full day available; finish before 19:30 UTC.
- Commit identity: ashfordeOU <contact@ashforde.org> (repo-local)
- NEVER force-push public. Public updates ONLY via publish-public.sh.
- No founder contact unless gate fails or a VETO domain triggers.
