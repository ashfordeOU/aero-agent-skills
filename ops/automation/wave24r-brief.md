# WAVE-24R BRIEF — Aero Agent Skills (public v1.0.0 baseline)

CEO dispatch 2026-09-03 (08:1x UTC, window open). Founder: "So now" =
resume wave work on the new public model.

## Baseline (VERIFIED by CEO at dispatch)
- Dev tree: ~/AeroSkills @ HEAD (sync with private arjun-0077/aero-agent-skills)
- **v1.0.0 public baseline: 330 leaves · 81 packs · 12 families · 674 router tasks**
- Public repo: ashfordeOU/aero-agent-skills (in sync at dispatch)
- Gates FRESH at dispatch: make validate 5/5 · make attest 3/3 ·
  visuals-check PASS · public-safety audit PASS
- Repo model: build in DEV (private), sync to PUBLIC via
  ops/automation/publish-public.sh (gated, never force, public-safety
  audit mandatory). GitHub CI attest.yml on every public push.

## Target
- **+10-16 verified leaves, MUST land ≥10** (founder wave mandate)
- Priority families (six smallest first): flight-mechanics →
  gnc-autonomy → propulsion → space-systems → systems-engineering →
  aerodynamics (then headroom families)
- One agent per leaf (PARALLEL-AGENT doctrine); every leaf:
  - agentskills.io-conformant SKILL.md (name + trigger-first desc ≤1024)
  - scripts/ logic + scripts/test_*.py offline contract test
  - no broken refs; references/ + assets/ as needed
  - eval/skill-eval/<name>.json value-delta (threshold 0.2)
  - rate-at-creation ≥9.5 in eval/skill-ratings.md ledger (in-turn row)
  - corpus tasks: +2 per leaf (674 → 674+2N)
  - standards-map.yaml ext when a standard applies

## Gates (all must PASS before close-out)
1. make validate 5/5 (incl. Hit@1 674+2N tasks deterministic offline)
2. make attest 3/3 (number-snapshot + brief-audit + content-policy)
3. make completeness + make value-delta
4. make visuals (numbers only — design LOCKED) + visuals-check
5. public-safety audit (scripts/public-safety-audit.py) — zero local
   paths/usernames/tokens in tree + history
6. Em dashes 0 in skills/ · router descs ≤1024
7. Tree clean at rest

## Close-out chain
1. Push PRIVATE (arjun-0077/aero-agent-skills) + ls-remote verify
2. make visuals + commit numbers
3. GROUP close-out post (SEND_EXIT=0 verify)
4. wave24r-state.md honest disclosures
5. **Sync to PUBLIC: bash ops/automation/publish-public.sh** → verify
   remote HEAD == mirror HEAD; GitHub CI attest.yml green (check via API)
6. CEO P5.2 WAVE-24R audit ≥9.5 → WAVE-25

## Notes
- Quiet hours 20:00-08:00 UTC respected absolutely (gate check before
  spawning; window closes at 08:00 UTC daily = work resumes then)
- Commit identity: ashfordeOU <contact@ashforde.org> (repo-local)
- NEVER force-push public. Public updates ONLY via publish-public.sh.
- The founder's "So now" = resume. No founder contact unless gate fails
  or a VETO domain triggers.
