---
name: q7036-scc-environment-identification
description: "Determine which exposures across a part's life can promote stress-corrosion cracking under ECSS-Q-ST-70-36C. Use when humidity, coastal chlorides, cleaning fluids and propellants have to be read phase by phase rather than as one service environment: recognise the agent each phase presents and its base severity, let relative humidity set the severity of ambient and humid air because condensation is what makes an electrolyte, drop one step for an effective purge, sealed bag or conformal coat without going below inert, then take the worst phase as governing, total the promoting exposure hours and flag every severe phase left unprotected. Trigger: ecss, q-st-70-36c, scc-promoting-environment, scc-exposure-phase-profile, chloride-bearing-environment, condensing-humidity-threshold, scc-protection-severity-step."
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
  tags: [ecss, q-st-70-materials-scope, q-st-70-36c, q7036-scc-environment-identification, scc-promoting-environment, scc-exposure-phase-profile, chloride-bearing-environment, condensing-humidity-threshold, scc-protection-severity-step]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Materials — SCC Environment Identification (space-systems/ecss/q7036-scc-environment-identification)

Use when the task is the environment step of ECSS-Q-ST-70-36C --
deciding which of the atmospheres and fluids a part meets over its life
can actually promote stress-corrosion cracking, and for how long, before
an alloy or a stress level is argued about.

## Domain quick reference

- Cracking needs an electrolyte at the surface, so the question is per
  exposure phase and not per mission. Manufacture, integration, storage,
  transport, the launch site, the pad and the orbital phase each present
  a different agent, and one of them usually dominates the whole life.
- Humid air has no fixed severity. Below the condensation-prone band it
  is benign; through that band it becomes an electrolyte on any surface
  cold enough, and near saturation it is as aggressive as a standing
  film. Its severity is therefore read from the recorded relative
  humidity of the phase, and a phase declaring air without a humidity
  reading is incomplete rather than defaultable.
- Chlorides are the reference aggressive medium and they arrive by more
  routes than seawater: coastal air at a launch site, de-icing salt on a
  road transport, a chloride-bearing cleaning residue. Ammonia-bearing
  fluids are the copper-alloy agent, and chlorinated solvents are the
  halogen source that matters for titanium.
- Vacuum and a dry purge are inert, not merely mild -- no electrolyte
  can form. The long on-orbit phase that dominates the life in hours
  usually contributes nothing to this assessment, which is exactly why
  totalling hours without severity is misleading.
- Protection moves a phase one step down the ladder, never to nothing. A
  purge, a sealed bag with desiccant or a conformal coat keeps the agent
  off the surface for as long as it stays intact, and the step it buys
  is recorded against the base severity so the reviewer sees what the
  protection is carrying.

## Workflow

1. Normalize the declared agent of each phase onto a known one and read
   its base severity; refuse an unrecognised agent rather than treating
   it as mild.
2. For ambient or humid air, require the relative humidity of the phase
   and derive the severity from it, with both humidity thresholds
   inclusive and the equality resolved by a named tolerance.
3. For a chemically driven agent, validate any humidity reading that is
   offered but do not let it lower the severity the chemistry sets.
4. Apply the declared protection as a one-step reduction, floored at
   inert, and keep the base severity alongside the effective one.
5. Mark a phase promoting when its effective severity reaches the
   moderate step or above.
6. Take the governing environment as the worst phase, breaking a tie on
   the longer duration and then on the phase name so the answer is
   reproducible.
7. Total the promoting exposure hours, flag every severe phase left
   unprotected, and flag a profile whose promoting phases all carry zero
   duration as incomplete rather than clean.

## Pitfalls

- Assessing one service environment for the whole life. The launch-site
  months in coastal air routinely govern hardware whose orbital years
  are inert, and a single-environment read misses it entirely.
- Defaulting an air phase to benign when no humidity was recorded. The
  missing reading is the finding; assuming it dry clears the phase that
  most often carries the exposure.
- Totalling exposure hours without severity. The orbital phase swamps
  every other number and produces a total that describes nothing about
  the cracking risk.
- Letting a protection zero the phase out. A conformal coat on a
  chloride exposure buys one step, not immunity, and recording it as
  immunity removes the coat's own integrity from the review.
- Reading a dry-looking humidity reading as clearing a chemical agent. A
  chloride solution or an ammonia-bearing fluid is aggressive at any
  ambient humidity, so the reading is validated and then ignored for
  severity.

## Behavior contract (gate 3)

The agent normalization, the humidity-driven severity with its inclusive
thresholds, the protection step and its inert floor, the per-phase
evaluation, the governing-phase tie-breaks and the profile aggregation
are exercised by the gate 3 contract test:
scripts/test_q7036_scc_environment_identification.py against
scripts/q7036_scc_environment_identification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7036_scc_environment_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
