#!/usr/bin/env bash
# Aero Agent Skills brief-audit gate (attestation part 2).
# Scans repo docs for quoted market numbers and resolves each against
# ops/automation/numbers.yaml (canonical register). Exit 0 = every quoted
# number resolves; exit 1 = drift with a diff (file, line, expected, found).
# Usage: brief-audit.sh [path...]   (defaults: research/ marketing/ development/ docs/ README.md)
set -uo pipefail
auto_dir="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$auto_dir/number_audit.py" "$@"
