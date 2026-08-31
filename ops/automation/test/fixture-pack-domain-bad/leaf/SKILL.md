---
name: leaf
description: "Use when testing pack_inventory domain validation: this fixture leaf's domain is not in the taxonomy and must exit 1."
license: Apache-2.0
compliance: none
standards:
  - id: sep-2640
    reference-only: true
gated: false
domain: bogus-domain
pack: leaf
metadata:
  domain: bogus-domain
  subdomain: fixture
  tags: [test, fixture]
  version: 0.0.1
  author: AeroSkills
---

# Fixture leaf (bad domain)

PLANTED: domain 'bogus-domain' not in the 12-discipline taxonomy.
ops/automation/test/run-tests.sh P9 asserts pack_inventory exits 1.
