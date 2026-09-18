---
name: e2020-backup-dissipative-failure-protection
description: "Determine whether a dissipative switch failure still has protection once both earlier provisions have been ruled out, per clause 5.2.14.3.1 of ECSS-E-ST-20-20C. Use when the derated continuous rating cannot absorb the stuck-on case and no off-command path survives the failure: test each provision on its own terms, demand a backup only where neither holds, match the backup to the mode it genuinely covers, refuse one sharing a part with the switch it protects, and race its action time against the thermal run-up. Trigger: ecss, e-st-20-20c-clause-5-2-14-3-1, dissipative-switch-failure-protection, backup-dissipative-protection-applicability, dissipative-element-thermal-run-up, backup-protection-independence."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-14-3-1, e2020-backup-dissipative-failure-protection, dissipative-switch-failure-protection, backup-dissipative-protection-applicability, dissipative-element-thermal-run-up, backup-protection-independence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Backup Dissipative Failure Protection (space-systems/ecss/e2020-backup-dissipative-failure-protection)

Use when the task is clause 5.2.14.3.1 of ECSS-E-ST-20-20C: an additional
protection covers a dissipative switch failure in the case where neither
of the two earlier provisions can apply. The clause is conditional, so
this leaf grades an ordering rather than a checklist -- the backup is
owed only after both earlier provisions have been tested and both have
been found not to hold.

## Domain quick reference

- The first provision is the part carrying its own failure: the
  dissipative element absorbs the stuck-on case inside its derated
  continuous rating. Where it does, nothing further is owed, and a
  backup argued on top of it is answering a question nobody asked.
- The second provision is commanding the failure away: an off-command
  path reaches the switch without passing through anything the failure
  took with it. A path through the drive that just failed is not a
  second provision, it is the first one written down twice.
- Only where neither holds does the backup arrive, and it carries three
  separate burdens. It must cover the mode in question -- a fuse answers
  a stuck-on switch and says nothing about a drive that stopped
  modulating. It must stand clear of the elements that failed. And it
  must act before the element reaches its temperature limit.
- The time it has is not a preference, it is computed: the worst-case
  dissipation drives the element from where it sits to its limit across
  its own thermal capacity, and the backup has to act inside that with
  margin. A cutout that opens after the junction has passed its limit
  recorded the event rather than preventing it.
- A stuck-open dissipative switch stops dissipating. There is no thermal
  run-up to race, so only the policy ceiling bounds its backup, and the
  hazard sits with the lost dissipation function instead.
- A provision nobody tested is not a provision that failed. It leaves
  the whole ordering undecided, which is different work from a provision
  tested and found inapplicable, so it is reported ahead of everything.

## Workflow

1. Validate the policy: the derating must not exceed one and the thermal
   time margin must not sit below one, or the policy credits the element
   with capability it does not have.
2. Name the failure mode under examination and refuse an unrecognised
   one before it enters the argument.
3. Check both earlier provisions were actually tested; where either was
   not, stop and report the ordering as undecided.
4. Test provision one: worst-case dissipation against the derated
   continuous rating.
5. Test provision two: at least one off-command path sharing no element
   with the failed switch.
6. If either applies, no backup is owed -- say so and stop.
7. Otherwise resolve the backup: present, covering the mode, clear of
   the switch elements, inside the policy ceiling, and for a dissipating
   mode inside the thermal run-up with margin.

## Pitfalls

- Reaching for the backup first because it is the visible hardware. The
  clause hands it out conditionally, and a backup argued where provision
  one already applies buys nothing and costs mass.
- Counting an off-command path that runs through the failed drive. It is
  the same element twice and it goes down with the switch.
- Accepting a backup because it is in the channel rather than because it
  answers the mode. A series fuse in front of a switch that stopped
  modulating is a series fuse in front of a switch that stopped
  modulating.
- Leaving the backup on a shared thermostat, gate resistor or drive
  supply. One failure then takes the protection and the thing it
  protects, and the redundancy was only ever on the drawing.
- Comparing the backup action time against a round number instead of
  against the run-up the dissipation actually produces. The element does
  not care what the budget said.
- Racing a stuck-open switch against a thermal limit it will never
  reach, and missing that the real exposure is the dissipation function
  that is now absent.
- Reporting an untested provision inside the same list as the provisions
  that were tested and found inapplicable. One needs an analysis and the
  other needs nothing.

## Behavior contract (gate 3)

The failure mode and backup device vocabularies, the derated dissipation
capability, the two earlier provisions tested independently, the
off-command path independence check against the switch element list, the
per-mode backup coverage map, the shared-element intersection, the
thermal run-up computed from dissipation, thermal capacity and the
temperature rise, the policy action-time ceiling, the stuck-open mode
exempted from the thermal race and the untested-provision verdict that
outranks the rest are exercised by the gate 3 contract test:
scripts/test_e2020_backup_dissipative_failure_protection.py against
scripts/e2020_backup_dissipative_failure_protection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_backup_dissipative_failure_protection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
