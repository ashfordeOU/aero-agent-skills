---
name: router
description: "Use when testing pack_inventory router validation: this fixture's pack field disagrees with its router folder and must exit 1."
license: Apache-2.0
compliance: none
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: cross-cutting
pack: wrongpack
metadata:
  domain: cross-cutting
  subdomain: fixture
  tags: [test, fixture]
  version: 0.0.1
  author: AeroSkills
---

# Fixture router (bad pack field)

PLANTED: pack field 'wrongpack' != router folder name. ops/automation/
test/run-tests.sh P8 asserts pack_inventory exits 1.
