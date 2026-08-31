#!/usr/bin/env python3
"""DO-178C configuration management logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-178c: gated): configuration
management keeps baselines of software lifecycle data, records problem
reports, controls changes (with independent approval at levels A/B), and
maintains archive and recovery. Release of software requires a current
baseline, closed problem reports, and an archive/recovery capability.
"""

DAL_ORDER = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


def is_baselined(item_id, baselines):
    """True when the item belongs to at least one configuration baseline."""
    for baseline in baselines:
        if item_id in baseline:
            return True
    return False


def change_review_required(dal, baselined):
    """Changes to baselined data are reviewed at every software level."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    return baselined


def change_independence_required(dal):
    """Levels A and B require independent approval of changes."""
    if dal not in DAL_ORDER:
        raise ValueError("invalid DAL: %r" % (dal,))
    return dal in ("A", "B")


def release_gate(open_prs, closed_prs, baseline_exists, archive_exists,
                 unreviewed_changes=0):
    """Return (ok, reason): release requires closed PRs, baseline, archive."""
    if open_prs > 0:
        return False, "%d open problem report(s)" % open_prs
    if not baseline_exists:
        return False, "no current baseline"
    if not archive_exists:
        return False, "no archive/recovery capability"
    if unreviewed_changes > 0:
        return False, "%d unreviewed change(s)" % unreviewed_changes
    return True, "release ready"
