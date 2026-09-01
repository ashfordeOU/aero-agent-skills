# NEGATIVE FIXTURE (N50) - real market table rows MUST still trip brief-audit.sh.
# Repo path cell (owner/repo) with a stale star value: OpenMDAO/dymos live is 296,
# the planted 2 must FAIL as drift (cell-dominant alias rule keeps this checked).
# Exit 1 expected.

| Repo | Stars |
|---|---|
| OpenMDAO/dymos | 2 |
