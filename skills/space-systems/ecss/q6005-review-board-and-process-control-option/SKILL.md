---
name: q6005-review-board-and-process-control-option
description: "Evaluate whether a hybrid line may keep substituting statistical monitoring and a technical review board for batch sampling under ECSS-Q-ST-60-05C clause 12.2.2: validate the per-lot yield window, draw control limits from the line's own history, find the lots outside them and the runs drifting off centre inside them, check the board's roles, quorum and review currency, and return continue, revert to per-lot testing, or suspend with every reason named. Use when auditing a monitored hybrid production line. Trigger: ecss, q-st-60-05c, hybrid-line-statistical-monitoring, hybrid-technical-review-board, hybrid-yield-control-limits, hybrid-process-drift-run-rule, hybrid-reversion-to-lot-control."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-review-board-and-process-control-option, hybrid-line-statistical-monitoring, hybrid-technical-review-board, hybrid-yield-control-limits, hybrid-process-drift-run-rule, hybrid-reversion-to-lot-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Review Board and Process Control Option (space-systems/ecss/q6005-review-board-and-process-control-option)

Use when the task is judging the acceptance option under ECSS-Q-ST-60-05C
clause 12.2.2 in which a statistically monitored production line and a
technical review board stand in for drawing a sample from every batch —
whether the substitution still holds, and what happens when it stops.

## Domain quick reference

- The substitution is conditional and continuous, not granted once. Per-lot
  sampling produces evidence about each batch; monitoring produces evidence
  about the line. The second only speaks for the batches while the line is
  demonstrably behaving as it has been behaving.
- Control limits come out of the line's own history, not out of a
  specification. The chart answers "has anything changed", which is why a
  line can sit inside its limits while performing badly, and why a very
  quiet line acquires very tight limits that a small excursion crosses.
- Stability and performance are two separate conditions with two different
  consequences. A line that has drifted or thrown a lot outside its limits
  has lost the evidence for the substitution and goes back to per-lot
  testing. A line whose central yield has fallen below the floor has a
  production problem, and per-lot testing is not the remedy.
- A run rule is not redundant with the limits. Seven lots on one side of the
  mean, every one of them inside the limits, is a process walking off its
  centre — the limits will only notice once it has arrived.
- The board is part of the evidence, not oversight of it. The substitution
  is being made in front of the customer's product assurance member, so a
  board that is quorate without that member is deciding in front of nobody,
  and a board that has not met in many lots has not decided recently.
- An absent board is a different finding from an inadequate one. No board at
  all means nothing has been authorising the substitution, which is why it
  suspends the scheme rather than reverting it.

## Workflow

1. Validate the monitoring window as per-lot yields, oldest first, each a
   fraction of the lot that came through.
2. Compute the window statistics and draw the control limits from them,
   clamping both into the range a yield can actually reach.
3. Find the lots outside the limits, absorbing representation error at the
   bound so a point landing exactly on a limit is not called an excursion.
4. Find the runs sitting on one side of the mean for the full run length,
   treating a point on the mean as breaking the run rather than continuing
   it.
5. Read the board: the required roles it holds, whether that reaches quorum,
   whether the customer product assurance member is among them, and how many
   lots have passed since it last reviewed.
6. Separate the findings into suspensions and reversions. Central yield
   below the floor and an unconvened board suspend; excursions, drifts, a
   short window, an inadequate board and an overdue review revert.
7. Return the standing with the limits, the excursion positions, the drift
   positions, the board finding and every reason, so the line's operator is
   told what to correct and the auditor can reproduce it.

## Pitfalls

- Reading the control limits as a quality requirement. They are a statement
  about the line's own spread; a line can be perfectly in control and still
  be producing at a yield nobody would accept.
- Checking only the limits and declaring the line stable. The drift run is
  the earlier signal, and a process that has walked half its spread has
  already invalidated the window the limits were drawn from.
- Re-drawing the limits on a window that contains the excursion. The
  excursion widens the spread and can move the limits out past itself; the
  detection is done on the window as it stands, and the window is retired
  once the cause is addressed.
- Treating a board that has not met in twenty lots as current because its
  membership is correct. Composition and currency are two conditions.
- Collapsing suspend and revert into one failure. They point at different
  remedies — one sends the line back to testing every batch, the other says
  testing every batch will not fix what is wrong.
- Running the chart on a handful of lots. A window shorter than the minimum
  has too little history for a mean or a spread to mean anything, and the
  limits it produces will be confidently wrong.

## Behavior contract (gate 3)

The window validation, window statistics, control limits, out-of-control
detection, drift run rule, board composition and currency check and the
three-way standing are exercised by the gate 3 contract test:
scripts/test_q6005_review_board_and_process_control_option.py against
scripts/q6005_review_board_and_process_control_option_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_review_board_and_process_control_option.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
