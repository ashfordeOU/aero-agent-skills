# GREEN FIXTURE (N49) - skill-inventory table rows must NOT trip brief-audit.sh.
# docs/DOMAINS.md shape: second cell is a comma-separated list of backtick-quoted
# skill names; alias 'dymos' (OpenMDAO/dymos, 296) appears INSIDE 'dymos-trajectory'
# and the trailing numeric cell is the pack skill count, not a star claim.
# Exit 0 expected (cell-dominant alias rule: a comma list is not a repo cell).

| Pack | Skills | Count |
|---|---|---|
| `control` | `frequency-response-design`, `gain-scheduling`, `pid-control-design`, `state-space-analysis` | 8 |
| `guidance` | `command-to-line-of-sight`, `midcourse-guidance`, `proportional-navigation`, `pursuit-guidance` | 5 |
| `navigation` | `dilution-of-precision`, `inertial-navigation`, `kalman-filter-design`, `navigation-frames` | 4 |
| `optimal-control` | `dymos-trajectory`, `lqr-design` | 2 |
| `space` | `attitude-dynamics`, `orbit-dynamics`, `rendezvous-phasing` | 3 |
