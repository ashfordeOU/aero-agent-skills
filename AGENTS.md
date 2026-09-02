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
