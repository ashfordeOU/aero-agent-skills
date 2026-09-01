# AGENTS.md — AeroSkills project rules

AeroSkills runs as a company of departments (see README.md). These
rules apply to any agent working in this repo.

## QUIET HOURS (founder mandate, PINNED)
- **00:00-10:00 UTC = NULL BURN WINDOW.** No work, no skill builds, no
  subagent dispatch, no jobs, no token-spending activity during this
  window (DeepSeek peak pricing — the company ran out of API credits
  from night burn).
- Wave work queues and resumes at 10:00 UTC. If you are mid-task when
  the window opens, stop spending and queue the result.
- PRE-SPAWN CHECK: before spawning any subagent or long work, run
  OK: outside quiet window. (exit 0=OK,
  2=in window stop, 3=pre-quiet do not spawn long work).
- FUTURE JOBS: every new cron/job must respect the window (schedule
  outside 00:00-10:00 UTC or attach the quiet-hours-gate.py monitor).
- Outside 00:00-10:00 UTC: normal work, full speed, agent cadence.

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
