# Wave-8 Em-Dash Rework Brief (2026-09-01, CEO gap brief)

CEO P5.2 WAVE-8 gate NOT PASSED (design angle < 9.5) — ONE defect found
in fresh audit at HEAD dee35c7. Fix it, re-verify, commit, push, post.

## The defect (orchestrator-verified, not assertion)

`skills/gnc-autonomy/control/pid-control-design/scripts/test_pid_control_design.py`
line 5 docstring contains an em dash:

    Contract: docs/harness-contract.md gate 3 — PID output from gains and

The team's own em-dash gate helper flags it:

    python3 ops/automation/state/wave7-emdash-live.py
    -> EMDASH 1x skills/gnc-autonomy/control/pid-control-design/scripts/test_pid_control_design.py

The wave-8 brief STEP 5 gate is "em dashes 0 live tree" — the helper
scans skills/ recursively INCLUDING .py, so this is in scope. Root
cause: wave-8 leaf subagent for pid-control-design wrote an em dash in
its test docstring; close-out sweep (dee35c7) swept scratch helpers but
not leaf script comments.

## STEP 1 — Fix (minimal diff, AGENTS.md style)

Replace the em dash with a plain hyphen (or rephrase), touching ONLY
that one character/phrase. No other changes:

    Contract: docs/harness-contract.md gate 3 - PID output from gains and

## STEP 2 — Gates FRESH (replay, do not trust prior output)

1. `python3 ops/automation/state/wave7-emdash-live.py` -> "em dashes: 0"
2. `make validate` -> 5/5 PASS (308/308 Hit@1)
3. `make attest` -> 3/3 PASS
4. `bash ops/automation/test/run-tests.sh` -> ALL TESTS PASS (incl N27/N28)
5. `git status --short` -> clean (zero untracked)

## STEP 3 — Commit (7 rules, one commit)

Subject <= 50 chars, imperative, no period, body WHAT + WHY.

Suggested: "fix: sweep em dash in pid-control-design test docstring"

## STEP 4 — Push PRIVATE (publish law, HARD)

- Push to arjun-0077/aeroskills ONLY via GITHUB_TOKEN_ARJUN.
- The Ashforde token is in the store — NEVER use it for any push.
- NO visibility flips. NO Ashforde. Publish is founder-GO only.
- Verify: `git ls-remote` with the arjun token returns remote main ==
  your new HEAD.

## STEP 5 — Post (as yourself, GROUP 160)

1-3 line cold-truth close-out: em dash swept, gates FRESH green,
push landed + verified. Send via:

    env -u HERMES_HOME hermes -p opsmanager send --to telegram:-1004333545328:160 "<msg>"

Capture SEND_EXIT=0. Record the message_id in your session.

## STEP 6 — Write state

Append a one-line state note to ops/automation/wave8-state.md (or the
running wave-8 state file): em-dash rework done, commit hash, gates,
push, post.

## Rules

- CEO did the audit; YOU do the fix (CEO never does team work).
- Minimal diff: one character class of change only.
- Incremental-commit mandate: commit IMMEDIATELY after gates pass.
- If anything else is found red, STOP and report it in the post —
  do not silently expand scope.

NEXT after this lands: CEO re-audit -> WAVE-8 gate >= 9.5 -> WAVE-9.
