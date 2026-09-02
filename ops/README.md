# Ops Department

**Purpose:** how it runs — infrastructure, automation, reliability.

## Workspace
- `runbooks/` — how-to for every system
- `state/` — status, health, snapshots
- `automation/` — scripts + cron jobs

## Operating rules
1. Silent-on-success: automation posts only exceptions
2. Verified over assumed: backups verify, health checks run
3. Reproducible: any machine can rebuild from docs + config
4. One branch, clean at rest, remote = backup

## Inputs
- Development builds → deploy
- Security audits → fixes

## Outputs
- Running system + health reports
