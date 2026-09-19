---
name: e2040-device-criticality-categories
description: "Allocate the criticality category a device product carries under ECSS-E-ST-20-40 clause 6.1 and derive what that category then demands. Use when a device list holds failure severities, redundancy schemes and detection routes, and each item has to be categorized before parts screening, derating and review depth can be set. Credits redundancy by a single step and only where it is independent and its loss is actually detected, refuses credit to a dormant standby nobody can switch in, flags every remaining single-point failure, and grades an applied stress against the derating limit the category imposes. Trigger: ecss, e-st-20-40-device-scope, device-criticality-category, failure-severity-to-category, redundancy-credit-one-step, dormant-standby-no-credit, device-single-point-failure, category-derating-limit."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-criticality-categories, device-criticality-category, failure-severity-to-category, redundancy-credit-one-step, dormant-standby-no-credit, device-single-point-failure, category-derating-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Device Criticality Categories (space-systems/ecss/e2040-device-criticality-categories)

Use when the task is the categorisation step of ECSS-E-ST-20-40 clause
6.1 -- placing each device product into a criticality category from the
consequence of its failure and the architecture around it, and then
reading off the parts screening, derating, review depth and
documentation the category obliges.

## Domain quick reference

- The category starts at the consequence, not at the part. A device
  whose failure is catastrophic starts in the top category however
  simple the device is; a device whose failure is a nuisance starts at
  the bottom however complex it is. Complexity drives effort, but
  consequence drives the category.
- Redundancy buys at most one step, and only when it is real. An
  independent redundant path whose loss is detected in time to be used
  moves the device one category down. Two steps are never available
  from one architecture feature, because the second step would be
  claiming the same mitigation twice.
- A redundancy that shares a cause with the path it backs up buys
  nothing. A common power feed, a common connector, a common thermal
  path or a common lot code means both branches fail together, so the
  device stays where its consequence put it.
- A dormant standby nobody can switch in buys nothing either. Credit
  depends on the failure being detected in time: a cold standby needs
  onboard detection to be switched before the function is lost, while
  a hot or cross-strapped path can be credited on ground detection
  because the alternate path is already carrying or able to carry the
  function.
- What survives the credit is the single-point-failure list. A device
  with no redundant path is a single-point failure whatever its
  category, and the top two categories do not permit one without an
  approved deviation behind it.
- The category is a budget for assurance. Parts screening level,
  derating factor, qualification route, review depth and the delivered
  documentation all descend from it, so quoting the category without
  those implications hands the reader half the answer.
- Derating is where the category becomes a number. The allowed
  operating stress is the device rating scaled by the category factor
  for that parameter, and a stress that lands exactly on the limit is
  compliant: rating times factor is a floating-point product and the
  comparison has to absorb its representation error.

## Workflow

1. Normalise each device: severity of the worst credible failure
   effect, redundancy scheme, independence of that redundancy, and the
   detection route. Reject an unrecognised value rather than
   defaulting it.
2. Take the base category straight from the severity.
3. Test the redundancy credit in order -- a scheme other than none, an
   independent path, and a detection route the scheme can actually use
   -- and record a finding for each test that fails, because each one
   is a design change that would buy the step back.
4. Apply at most one step of demotion and fix the category.
5. Mark the device a single-point failure where no independent
   redundant path exists, and raise the deviation duty where the
   category does not permit one.
6. Read off the implications the category carries, then grade any
   applied stress against the category derating limit for its
   parameter.
7. Roll the device list up: counts per category, the governing
   category for the assembly, and the single-point-failure list the
   review will ask for.

## Pitfalls

- Categorising by how expensive or how complicated the device is. The
  category follows the consequence of losing it; a cheap latching
  relay in the only power path outranks an elaborate payload
  processor whose loss degrades a secondary mode.
- Taking two steps of credit for one redundancy. Independence and
  detectability are the conditions on the single step, not two
  separate steps, and a device demoted twice ends up screened and
  derated as though its failure did not matter.
- Crediting a cold standby against a failure only the ground can see.
  By the time the pass is downlinked, analysed and a switch command is
  uplinked, the function has been lost for the whole interval; the
  credit is only real where onboard logic can switch in time.
- Calling a cross-strapped pair independent without checking what they
  share. Cross-strapping removes the interface as a single point but
  leaves a common secondary supply, a common lot code or a common
  radiator interface exactly where it was.
- Comparing an applied stress against the derated limit with bare
  arithmetic. The limit is a product of a rating and a factor, so a
  stress placed deliberately on the limit can read a few units in the
  last place over it and a compliant device is reported as
  overstressed.

## Behavior contract (gate 3)

Device normalisation, base categorisation, the redundancy credit
conditions, single-point-failure marking, the category implications,
the derating limit comparison and the device-list roll-up are exercised
by the gate 3 contract test:
scripts/test_e2040_device_criticality_categories.py against
scripts/e2040_device_criticality_categories_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_criticality_categories.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
