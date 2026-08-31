---
name: lightning-protection
description: "Use when you must evaluate DO-160 lightning protection for airborne equipment: select the section 22 induced transient susceptibility test level and waveform set, and check the section 23 direct effects pass criteria. Verdict logic classifies whether test results pass with no physical damage, no upset, and no latch-up; level and waveform checks validate inputs before the verdict is issued. Selection and verdict logic only; no standard tables reproduced. Trigger: lightning, DO-160, waveform, test level, transient susceptibility."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-160
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do160
  tags: [lightning, lightning-protection, do-160, waveform, test-level, transient-susceptibility]
  version: 0.1.0
  author: AeroSkills
---

# Lightning Protection (avionics/do160/lightning-protection)

Use when the task is DO-160 lightning protection: selecting the
section 22 induced transient susceptibility test level and waveform
set, and checking the section 23 direct effects pass criteria.

## Domain quick reference

- DO-160G (RTCA, EUROCAE twin ED-14G) section 22 covers induced
  transient susceptibility to lightning; section 23 covers lightning
  direct effects.
- Equipment is tested at a selected test level from a defined 1-5
  range with a selected waveform set; the actual level and waveform
  tables are standard data.
- Pass criteria are no physical damage, no upset, and no latch-up
  after the applied transients.
- The actual level and waveform tables must be read from the current
  revision of DO-160; this skill is selection and verdict logic only,
  no standard tables reproduced.

## Workflow

1. Confirm the applicable DO-160 revision and the equipment test
   conditions.
2. Validate the test level with test_level_in_range.
3. Validate the waveform set with waveform_supported.
4. Classify the result with pass_verdict.
5. Gate the lightning protection assessment on the verdict.

## Pitfalls

- Using a test level outside the defined 1-5 range.
- Using an unsupported waveform set (letters outside A-H).
- Counting physical damage as a pass; damage, upset, and latch-up
  all fail the verdict.

## Behavior contract (gate 3)

The selection and verdict logic is exercised by the gate 3 contract
test: scripts/test_lightning_protection.py against
scripts/lightning_protection_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_lightning_protection.py

## Compliance

- Standards referenced, not reproduced: DO-160 text is proprietary
  (RTCA); summary-only per standards-map.yaml and brief 06.
- The level and waveform tables are standard data; read them from
  the current revision before use.
- compliance: STANDARDS-REF, gated: false.
