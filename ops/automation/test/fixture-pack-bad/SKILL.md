---
name: bad-skill
description: "Use when testing the pack inventory negative path: this skill intentionally lacks top-level domain and pack frontmatter and must be rejected by the installer tooling. Trigger: pack inventory, negative fixture, untyped skill."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
metadata:
  domain: space-systems
  tags: []
  version: 0.1.0
  author: AeroSkills
---

# Bad skill fixture (no domain/pack)

Negative fixture for ops/automation/test/run-tests.sh P7:
pack_inventory.py must exit 1 because the top-level domain and pack
fields are missing, even though metadata.domain exists. An installer
must never silently install an untyped skill.
