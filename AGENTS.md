# AGENTS.md — Aero Agent Skills project rules

Aero Agent Skills runs as a company of departments (see README.md). These
rules apply to any agent working in this repo.

## QUIET HOURS (founder mandate, PINNED)
- **20:00-08:00 UTC (22:00-10:00 CEST) = NULL BURN WINDOW.** No work, no skill builds, no
  subagent dispatch, no jobs, no token-spending activity during this
  window (DeepSeek peak pricing — the company ran out of API credits
  from night burn).
- Wave work queues and resumes at 10:00 UTC. If you are mid-task when
  the window opens, stop spending and queue the result.
- PRE-SPAWN CHECK: before spawning any subagent or long work, run
  OK: outside quiet window. (exit 0=OK,
  2=in window stop, 3=pre-quiet do not spawn long work).
- FUTURE JOBS: every new cron/job must respect the window (schedule
  outside 20:00-08:00 UTC (22:00-10:00 CEST) or attach the quiet-hours-gate.py monitor).
- Outside 20:00-08:00 UTC (22:00-10:00 CEST): normal work, full speed, agent cadence.

## Writing
- Few words, every word picked. No superlatives, no praise.
- Cold hard truth. Verify-before-credit: "done" needs artifact proof.

## Code
- ONE main branch. No feature branches. Everything lands on main.
- Every commit complete (code + docs + tests + state together).
- Clean at rest: zero uncommitted files.
- **COMMIT IDENTITY (founder mandate 2026-09-01): every commit is authored and committed as `ashfordeOU <contact@ashforde.org>` — never Hermes, never a bot name. Repo-local git config already sets this; do not override with a global identity. Verify with `git log -1 --format='%an <%ae>'` after committing.**
- Test-first: failing test → fix → passing test.
- Minimal code. No speculative abstractions. Simplicity first.

## Per-skill completeness standard (founder mandate 2026-09-01)
EVERY leaf skill (skills/<family>/<pack>/<skill>/) ships ALL of:
1. **SKILL.md** — agentskills.io conformant frontmatter (name + description) + body
2. **scripts/** — at least one logic file implementing the skill
3. **scripts/test_*.py** — behavior contract test, offline, deterministic
4. **No broken refs** — every scripts//references//assets/ path in the body exists
5. **references/** — WHEN the body inlines long external content (URLs, data tables) that belongs in a reference doc
6. **assets/** — WHEN the body names templates/checklists/forms that should be bundled
7. **eval/skill-eval/<name>.json** — value-delta record (with vs without)
Run `make completeness` (required check) + `make value-delta` (sample proof) before finishing any skill wave. `make visuals` refreshes README numbers/charts (design is locked — numbers only).

## Wave discipline — HoH doctrine (founder 2026-09-02, arXiv 2609.01481 ADAPT)
Veda's wave build IS a Harness-of-Harness loop. Sharpened rules:
1. **Evidence-bundle handoff**: each wave/leaf gate output is a structured
   record: claim → verified/gap → record path → status. The next wave's
   planner consumes that record (not vibes). Verified records become
   PRESERVATION constraints; gaps become update targets with validation
   requirements.
2. **Planner pass between waves**: CEO phase-gate carries two lists into
   the next wave: "verified, must preserve" and "gaps/reopens, candidate
   leaves" — evidence-conditioned, never frozen-spec-conditioned.
3. **Warm-start is sacred**: every wave continues from the versioned
   workspace. NEVER restart from the spec. (Ablation: no warm-start =
   −7.85 AND +32% tokens.)
4. **Freeze before eval**: the QA/Tester role evaluates the artifact AS
   COMMITTED at the gate (read-only, by a role that cannot edit mid-eval).
   No silent repair while judging.
5. **Bounded, locally-complete leaves**: one leaf = one coherent
   observable behavior with observable completion conditions. Unrelated
   refactors/feature creep = separate leaf. "Related changes across files
   OK; unrelated changes = separate leaf."
6. **Regressions are first-class work**: record "previously verified →
   now failing" transitions (status flips, not just new bugs) so the next
   planner prioritizes regression repair without re-deriving history.
7. **Role prompts constrain outputs, not workflows**: specify the output
   contract (fields, evidence schema, status vocabulary); leave tool/
   algorithm choice free.

## Departments
- Work lands in its department folder (research/development/
  marketing/finance/ops/security/legal/people/support).
- Cross-cutting work is filed where it belongs and linked.

## Delivery
- Store-first: everything learned is filed + indexed, never left in chat.
- Evidence over claims: no finding ships without receipts.
- Supersede-not-delete: history is the safety net.
- Founder VETO domains: money >€50, publish, external sends, delete/
  irreversible, security-sensitive, new commitments.
