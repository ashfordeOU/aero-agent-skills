---
name: e4008-simulator-reconfiguration
description: "Assess whether a simulator reconfiguration obeyed ECSS-E-ST-40-08C clause 5.5.3. Use when the task is deciding that a reconfiguration may only start from a quiescent simulator rather than one that is executing, storing or unwinding, confirming the rebuild walked back through build, connect and initialise to standby, and diffing the re-applied configuration so a dropped field, an undeclared new field or a service or model whose identity token changed is caught before the previous run's saved state and telemetry stop matching the new tree. Grades a run against the two normative items. Trigger: ecss, e-st-40-08c, simulator-reconfiguration-entry-state, reconfiguration-state-walk, reapplied-configuration-diff, simulator-identity-preservation, dropped-configuration-field, quiescent-model-tree."
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
  tags: [ecss, e-st-40-08-simulation-scope, e4008-simulator-reconfiguration, simulator-reconfiguration-entry-state, reconfiguration-state-walk, reapplied-configuration-diff, simulator-identity-preservation, dropped-configuration-field]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Infrastructure — Simulator Reconfiguration (space-systems/ecss/e4008-simulator-reconfiguration)

Use when the task is the reconfiguration path of ECSS-E-ST-40-08C clause
5.5.3 -- taking an already initialised simulator, giving up its
published model tree, and rebuilding it with a changed configuration.
The clause carries two normative items: where a reconfiguration may be
entered from and how it walks back, and what the re-applied
configuration owes the identities the previous one established.

## Domain quick reference

- Reconfiguration is entered from standby and nowhere else. An executing
  simulator is holding scheduled entry points that reference model
  instances; a storing or restoring one is mid-serialisation; an
  unwinding one is already tearing the tree down. None of them has a
  quiescent tree to give up, so the request is refused rather than
  queued for later.
- The rebuild is not a shortcut back to standby. It re-walks the same
  states the first start-up used, because the models expect to be built,
  connected and initialised in that order regardless of whether this is
  the first pass or the fourth.
- Ending anywhere other than standby is a reconfiguration that did not
  finish. A run that stops in the initialise state has a tree that is
  neither the old one nor a usable new one.
- The configuration diff is the substance of the second item. A changed
  value is the point of the exercise; a dropped field, an undeclared new
  field and a changed identity token are not, and they are what the
  diff is there to surface.
- Identity is what the previous run's artefacts are matched on. A
  Schedule that comes back with a new token, or a model whose path
  moved, silently orphans the saved state and the recorded telemetry
  even though every value in the new tree is individually correct.
- A reconfiguration may be declared value-preserving -- rebuild the
  tree, change nothing. That is a stricter contract, and under it a
  changed value becomes a finding rather than the expected outcome.

## Workflow

1. Resolve the entry state and refuse anything outside the quiescent
   set, naming the permitted state in the finding.
2. Validate the observed rebuild walk: every required state re-entered,
   in order, with the run ending in standby, and report a foreign state
   rather than absorbing it.
3. Diff the previous configuration against the re-applied one into four
   buckets -- retained, changed, dropped and introduced -- so each
   bucket can be graded on its own terms.
4. Compare the identity tokens of services and models before and after.
   An absent name, a changed token and an unexpected new name are three
   distinct findings.
5. Apply the value-preservation setting: with changes allowed, a changed
   value is expected; with the reconfiguration declared
   value-preserving, it is a finding.
6. Grade the two normative items separately and report the entry state,
   walk, diff buckets and identity findings alongside the verdict.

## Pitfalls

- Allowing a reconfiguration from the executing state because the
  simulator will be stopped anyway. The scheduled entry points still
  hold references into the tree that is about to be discarded.
- Treating the rebuild as a jump straight to standby. Models that
  allocate on connect never get the call, and the first run after the
  reconfiguration fails somewhere far from the cause.
- Diffing only the values. The field that vanished from the re-applied
  set produces no value difference at all, which is exactly why it
  survives a value-only comparison.
- Accepting a new identity token because the object it names is
  equivalent. Equivalent is not the same: the previous run's saved state
  and telemetry are keyed on the token, not on the behaviour.
- Reading an introduced field as a harmless addition. It was never
  declared in the configuration the models were built against, so
  whichever model reads it is reading a value the previous tree never
  had.
- Reporting one merged verdict. The entry-and-walk item and the
  identity item fail for unrelated reasons, and a merged result cannot
  say whether to look at the state machine or at the configuration set.

## Behavior contract (gate 3)

Entry-state refusal, rebuild-walk validation, the four-bucket
configuration diff, identity-token comparison, the value-preservation
setting and the two-item grading are exercised by the gate 3 contract
test: scripts/test_e4008_simulator_reconfiguration.py against
scripts/e4008_simulator_reconfiguration_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_simulator_reconfiguration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
