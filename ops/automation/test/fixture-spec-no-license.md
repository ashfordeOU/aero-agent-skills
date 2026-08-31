---
name: test
description: "Use when fixture testing spec lint compliance enforcement: verify the gate fails on a frontmatter violation while the file remains otherwise conformant. Trigger: spec lint, frontmatter, compliance flags, license enforcement, gate 1."
compliance: STANDARDS-REF
standards:
  - id: DO-178C
    reference-only: true
gated: false
metadata:
  version: 0.1.0
  author: AeroSkills Fixtures
---
# fixture

Fixture body for spec-lint compliance tests.
