---
name: e1002-pre-launch
description: "Use when a flight item needs a pre-launch readiness go/no-go before launch under ECSS-E-ST-10-02C: transport-induced damage check, storage/shelf-life and environmental-excursion check, launch-site health/functional checks, and as-built launch configuration vs qualified/accepted baseline. Trigger: pre-launch readiness, launch readiness review, LRR, transport check, shelf life, storage excursion, launch-site checkout, launch configuration, as-built vs baseline, verification stage, E-ST-10-02, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, e-st-10-02, pre-launch, verification-stage, launch-readiness, configuration-baseline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Pre-Launch Readiness Verification (space-systems/ecss/e1002-pre-launch)

Use when the task is confirming pre-launch readiness of a flight item
under ECSS-E-ST-10-02C, the verification stage that runs after
qualification and acceptance and immediately ahead of launch.

## Domain quick reference

- ECSS-E-ST-10-02C clause 5.2.4.4 defines the pre-launch verification
  stage: confirm, ahead of launch, that transport did not degrade the
  flight hardware, that storage conditions and life-limited items
  remain within qualified limits, that the launch-site health and
  functional checks required before launch have all been completed and
  passed, and that the as-built launch configuration matches the
  qualified/accepted baseline (clauses 5.2.4.2, 5.2.4.3).
- Four readiness areas, each independently blocking: transport (no
  environmental excursion beyond the qualified transport envelope),
  storage (no expired life-limited item, no out-of-limit storage
  environment), launch-site activities (every required health/
  functional check completed and passed), launch configuration
  (as-built matches baseline, no open critical non-conformance).
- Pre-launch readiness is a gate, not a re-qualification: it checks
  that nothing has changed or degraded since acceptance, it does not
  replace qualification or acceptance testing.
- A single failing area is enough to withhold a go — readiness is not
  scored by counting how many areas passed.

## Workflow

1. Collect the transport record: every transport event (shipment leg,
   handling operation) with whether its measured environment stayed
   inside the qualified transport envelope.
2. Collect the storage record: every life-limited or environmentally
   sensitive item, its shelf-life expiry (if life-limited) and whether
   its storage environment log stayed within qualified limits, as of
   the readiness-review date.
3. Collect the launch-site activity record: the full list of required
   pre-launch health/functional checks for this item, and which of them
   have been completed and passed.
4. Collect the launch-configuration record: the as-built configuration
   values, the qualified/accepted baseline values to compare them
   against, and any open non-conformance with its severity and
   disposition status.
5. Run the four category checks independently, then combine them: the
   item is go only if transport, storage, launch-site activities, and
   launch configuration are all ready. Any one blocking reason is
   enough for a no-go.
6. For a no-go, report every blocking reason per category (not just the
   first) so the review board can disposition transport anomalies,
   life-limit extensions, outstanding launch-site checks, and
   configuration non-conformances in parallel rather than one at a
   time.
7. Hand a go result to the launch campaign; hand a no-go result, with
   its blocking reasons, back to the Verification Control Board
   (clause 5.4.2) for disposition before the readiness check is rerun.

## Pitfalls

- Treating pre-launch readiness as a formality once qualification and
  acceptance passed — degradation during transport or storage is
  exactly what this stage exists to catch.
- Stopping at the first failing category instead of collecting every
  blocking reason, which forces the review board through repeated
  reruns instead of one consolidated disposition pass.
- Accepting a launch-configuration mismatch or an un-dispositioned
  critical non-conformance because "it's probably fine" — the baseline
  comparison exists precisely so this is not a judgment call at this
  stage.
- Ignoring a minor, non-critical non-conformance's severity field and
  blocking on it anyway, which stalls a readiness review that clause
  5.2.4.4 does not require to stop for.

## Behavior contract (gate 3)

The transport, storage, launch-site, launch-configuration, and combined
go/no-go logic is exercised by the gate 3 contract test:
scripts/test_e1002_pre_launch.py against
scripts/e1002_pre_launch_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_pre_launch.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
