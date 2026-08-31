# Fixture tree for the content-policy sweep root regression test (N7).

A minimal repository-shaped tree used by ops/automation/test/run-tests.sh:
the sweep must resolve its repo root from ops/automation and scan nested
roots INCLUDING skills/. A red-flag term is planted in skills/dummy/SKILL.md
so the test asserts the corrected sweep finds it (exit 1). With the P2.1
pre-fix root (../../..) the sweep resolved to a directory above this tree
and never scanned skills/ - vacuous green.
