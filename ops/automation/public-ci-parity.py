#!/usr/bin/env python3
"""Fail-closed parity: the export must pass the PUBLIC CI's own gate steps.

VEDA-0035 (founder 2026-09-10: "we never leave them broken ... no failed
commits in public repo"). An automated sync landed public commits whose CI
was red because the public workflow ran a gate the export cannot satisfy:
`make attest` -> `number-snapshot-offline` reads ops/automation/state/, a dir
the export excludes by construction, so attest died with "no snapshot
exists" on the public tree (ec9d037b67, b1f8c440e9, 0fd80ee0).

The hand-written export battery in publish-public.sh could not see that - it
runs OUR list of gates, not the WORKFLOW's. This runner closes the gap the
other way round: it reads every branch-push workflow and executes the
workflow's own `run:` steps inside the export, exactly as GitHub Actions
will. A divergence aborts the publish BEFORE anything reaches the public
repo (fail-closed), instead of landing a commit that is red on arrival.

Steps that cannot be reproduced on an export are SKIPPED and named - never
silently: a network install, a GitHub CLI call, a remote git mutation, npm,
gradle, a sleep. Two guards keep the skips honest:
  * every `make <target>` named anywhere in a workflow must appear in an
    EXECUTED step - a gate hidden inside a skipped step fails the run;
  * no workflow may be skipped entirely (a config error exits 2, not 0).

Exit codes: 0 = every workflow step ran green; 1 = a step failed or a gate
was not proven; 2 = the runner could not do its job (missing dir, bad YAML).
Both non-zero codes abort the publish.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

DEFAULT_TIMEOUT = 900

# A step containing any of these cannot be reproduced on an export: it needs
# the network, or it mutates external state (releases, tags, registries).
# Matched against the step's whole run block, so the step is skipped whole.
EXTERNAL_PATTERNS = (
    (r"(^|[^\w-])pip3?\s+install\b", "network install"),
    (r"(^|[^\w-])gh\s", "GitHub API/CLI"),
    (r"(^|[^\w-])git\s+(push|tag|remote|fetch|clone)\b", "remote git mutation"),
    (r"(^|[^\w-])npm\s", "npm (network/publish)"),
    (r"(^|[^\w-])npx\s", "npx (network)"),
    (r"(^|[^\w-])gradlew?\b", "gradle (network JVM build)"),
    (r"(^|[^\w-])sleep\s", "wait"),
)

MAKE_TOKEN = re.compile(r"\bmake\s+([A-Za-z0-9][A-Za-z0-9._-]*)")

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_CONFIG = 2


class ConfigError(Exception):
    """The runner cannot do its job - always fail-closed."""


def skip_reason(script: str) -> str | None:
    for pattern, reason in EXTERNAL_PATTERNS:
        if re.search(pattern, script):
            return reason
    return None


def triggers_on_branch_push(doc: dict) -> bool:
    """True when the workflow runs on a push to branch(es).

    Tag-only triggers (npm, jetbrains) are excluded: they build and publish
    packages, they do not gate the pushed tree.
    """
    on = doc.get("on", doc.get(True))  # YAML 1.1 parses bare `on` as True
    if on is None:
        return False
    if isinstance(on, str):
        return on == "push"
    if isinstance(on, list):
        return "push" in on
    if isinstance(on, dict):
        if "push" not in on:
            return False
        push = on["push"]
        if isinstance(push, dict) and "tags" in push and "branches" not in push:
            return False
        return True
    return False


def load_workflows(workflows_dir: str) -> list[tuple[str, dict]]:
    try:
        import yaml  # noqa: PLC0415 - named failure when PyYAML is absent
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ConfigError(f"PyYAML is required to read the workflows: {exc}") from exc

    if not os.path.isdir(workflows_dir):
        raise ConfigError(f"no workflows dir at {workflows_dir}")

    found = []
    for name in sorted(os.listdir(workflows_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        path = os.path.join(workflows_dir, name)
        try:
            with open(path, encoding="utf-8") as handle:
                doc = yaml.safe_load(handle)
        except Exception as exc:  # noqa: BLE001 - any parse error is fatal
            raise ConfigError(f"{name}: unreadable YAML: {exc}") from exc
        if not isinstance(doc, dict):
            raise ConfigError(f"{name}: not a workflow mapping")
        found.append((name, doc))
    if not found:
        raise ConfigError(f"no workflow files in {workflows_dir}")
    return found


def iter_steps(doc: dict, name: str):
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        raise ConfigError(f"{name}: no jobs mapping")
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            raise ConfigError(f"{name}: job {job_name} is not a mapping")
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                raise ConfigError(f"{name}: step in {job_name} is not a mapping")
            yield job_name, step


def run_block(script: str, repo: str, timeout: int) -> tuple[bool, str]:
    env = dict(os.environ)
    # GitHub-provided files exist in CI; point them at /dev/null so a step
    # that writes to them behaves instead of failing on an unset variable.
    for var in ("GITHUB_OUTPUT", "GITHUB_ENV", "GITHUB_STEP_SUMMARY"):
        env.setdefault(var, "/dev/null")
    env.setdefault("GITHUB_WORKSPACE", repo)
    try:
        proc = subprocess.run(
            ["bash", "-e", "-o", "pipefail", "-c", script],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
        return False, f"exit {proc.returncode}\n    " + "\n    ".join(tail)
    return True, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="tree to verify (an export)")
    parser.add_argument("--workflows-dir", default=None)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--list-steps",
        action="store_true",
        help="print the plan (RUN/SKIP per step) without executing anything",
    )
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)
    workflows_dir = args.workflows_dir or os.path.join(repo, ".github", "workflows")

    try:
        workflows = load_workflows(workflows_dir)
    except ConfigError as exc:
        print(f"public-ci-parity: CONFIG ERROR: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    selected = [(n, d) for n, d in workflows if triggers_on_branch_push(d)]
    if not selected:
        print(
            "public-ci-parity: CONFIG ERROR: no branch-push workflow found "
            f"in {workflows_dir} - refusing to report the export as proven",
            file=sys.stderr,
        )
        return EXIT_CONFIG

    print(f"public-ci-parity: verifying {repo} against {len(selected)} branch-push workflow(s)")
    executed_targets: set[str] = set()
    skipped_targets: set[str] = set()
    failures: list[str] = []
    skipped_steps: list[str] = []

    for name, doc in selected:
        print(f"  workflow {name}")
        for job_name, step in iter_steps(doc, name):
            script = step.get("run")
            label = step.get("name") or (script or "").strip().splitlines()[:1] or ["<unnamed>"]
            label = label if isinstance(label, str) else " ".join(label)
            if not isinstance(script, str) or not script.strip():
                continue  # uses:-only step (checkout, setup-node, ...)

            reason = skip_reason(script)
            if reason:
                skipped_steps.append(f"{name} :: {job_name} :: {label} ({reason})")
                skipped_targets.update(MAKE_TOKEN.findall(script))
                print(f"    SKIP  {job_name} :: {label} [{reason}]")
                continue

            if args.list_steps:
                executed_targets.update(MAKE_TOKEN.findall(script))
                print(f"    RUN   {job_name} :: {label}")
                continue

            ok, detail = run_block(script, repo, args.timeout)
            if ok:
                executed_targets.update(MAKE_TOKEN.findall(script))
                print(f"    PASS  {job_name} :: {label}")
            else:
                failures.append(f"{name} :: {job_name} :: {label} -> {detail}")
                print(f"    FAIL  {job_name} :: {label} -> {detail.splitlines()[0]}")

    if args.list_steps:
        print("public-ci-parity: plan only (--list-steps), nothing executed")
        return EXIT_PASS

    unproven = sorted(skipped_targets - executed_targets)
    if unproven:
        failures.append(
            "gate(s) named only inside skipped steps, never executed: "
            + ", ".join(f"make {t}" for t in unproven)
        )

    if skipped_steps:
        print("  skipped (not reproducible on an export):")
        for line in skipped_steps:
            print(f"    - {line}")

    if failures:
        print("public-ci-parity: FAIL - the export would not pass the public CI:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return EXIT_FAIL

    print(
        f"public-ci-parity: PASS - every public-CI gate step green on the export "
        f"({len(executed_targets)} make target(s) proven, {len(skipped_steps)} step(s) skipped by name)"
    )
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
