---
name: python-control-design
description: "Use when designing and validating feedback control laws with Python control-systems tooling: evaluate gain and phase margins against acceptance limits (6 dB and 45 degrees), classify closed-loop stability from the margins, and apply Ziegler-Nichols tuning to get initial PID gains. Supports controller sanity checks (positive proportional, non-negative integral and derivative gains) before simulation or root-locus and Bode iteration. Pairs with the ARP4754A development-assurance context for control law development. Trigger: control law, pid, transfer function, state space, gain margin, phase margin, root locus, bode, stability, controller tuning."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [control-law, pid, transfer-function, state-space, gain-margin, phase-margin, root-locus, bode, stability, controller-tuning]
  version: 0.1.0
  author: Aero Agent Skills
---

# Python Control Design (gnc-autonomy/control/python-control-design)

Use when the task is control law design and evaluation with Python
control-systems tooling: margin checks, stability classification,
and PID tuning.

## Domain quick reference

- Standard acceptance margins: gain margin >= 6 dB, phase margin
  >= 45 degrees.
- A loop with both margins positive is closed-loop stable; a
  non-positive margin indicates instability.
- Ziegler-Nichols continuous-cycling tuning from ultimate gain ku
  and ultimate period tu: kp = 0.6 * ku, ki = 2 * kp / tu,
  kd = kp * tu / 8.
- Structural sanity for PID gains: kp > 0, ki >= 0, kd >= 0.
- Python control tooling (control, slycot) computes margins, root
  locus, and Bode plots for iteration.

## Workflow

1. Build the plant model as a transfer function or state-space
   system.
2. Compute gain and phase margins from the open-loop response and
   check them against the acceptance minima with
   scripts/python_control_logic.py.
3. Classify closed-loop stability from the margins.
4. Tune an initial PID with Ziegler-Nichols and sanity-check the
   gains.
5. Iterate with root-locus/Bode analysis until the margins pass.

## Pitfalls

- Calling the loop stable from a single positive margin.
- Tuning PID gains without checking the ultimate gain/period
  validity.
- Mixing dB and ratio margin values in one comparison.
- Accepting negative integral or derivative gains silently.

## Behavior contract (gate 3)

The margin, stability, and tuning logic is exercised by the gate 3
contract test: scripts/test_python_control.py against
scripts/python_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_python_control.py

## Compliance

- ARP4754A is proprietary (SAE); name + paraphrase only per
  standards-map.yaml and brief 06 (revision note: ARP4754B
  supersedes; this skill keys to A, the certification-baseline
  revision).
- compliance: STANDARDS-REF, gated: false.
