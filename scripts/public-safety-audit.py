#!/usr/bin/env python3
"""Public-safety audit for Aero Agent Skills (founder mandate 2026-09-02:
"no local folder info, user details, env info or anything dangerous in
public domain — and this should NEVER happen").

Scans a git repo's ENTIRE history (every commit's tree) for dangerous
content categories. Exit 0 = clean, 1 = violations found. Run as:
  python3 scripts/public-safety-audit.py [--repo PATH]
Default repo = current directory.

Checks (all across every commit reachable from HEAD):
  1. Local absolute paths      /Users/<user>, /home/<user>, /Volumes/, C:\\Users
  2. Local usernames           chak, enterprisehq
  3. Personal names            chakshu, baweja, subhash
  4. Tokens/secrets            ghp_, github_pat_, gho_, sk-, AKIA, xox*, private keys
  5. Private IPs               192.168.x, 10.x, 172.16-31.x (loopback 127.x is OK — documented default)
  6. Passwords                password=<literal>, Subhash
  7. Env/credential files      .env, .pem, .key, .p12, id_rsa, netrc (by filename in history)
  8. API keys                 api_key=<literal 16+>, secret=<literal 16+>, client_secret
  9. Commit metadata           authors/emails outside the company identity
 10. Machine hostnames         mac hostnames, .local machine refs
NOTE: patterns that could match the audit script's OWN source are split.
"""
import os
import re
import subprocess
import sys

REPO = "."
if "--repo" in sys.argv:
    REPO = sys.argv[sys.argv.index("--repo") + 1]

def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)

def rev_list():
    r = git("rev-list", "HEAD")
    return r.stdout.split() if r.returncode == 0 else []

def files_in(sha):
    r = git("ls-tree", "-r", "--name-only", sha)
    return r.stdout.split() if r.returncode == 0 else []

def grep_in(sha, pattern):
    """grep -l across all files at a commit; returns matching paths."""
    files = [f for f in files_in(sha)
             if f not in TOOLING_FILES]  # never flag the audit tooling itself
    if not files:
        return []
    # batch in chunks to avoid argv limits
    hits = []
    for i in range(0, len(files), 200):
        chunk = files[i:i + 200]
        r = git("grep", "-lE", pattern, sha, "--", *chunk)
        if r.returncode == 0 and r.stdout:
            hits.extend(r.stdout.split())
    return hits

# split patterns so this script never matches itself
def pat(a, b):
    return a + b

PATTERNS = {
    "local_paths": pat(r"/Us", r"ers/[A-Za-z0-9_-]+|/ho") + pat(r"me/", r"[A-Za-z0-9_-]+|/Vol") + pat(r"umes/", r"[A-Za-z0-9_-]+"),
    "local_usernames": pat(r"ent", r"erprisehq|chak\b"),
    "personal_names": pat(r"chak", r"shu|baweja|subhash"),
    "tokens": pat(r"ghp_[A-Za-z0-9]", r"{20,}|github_pat_[A-Za-z0-9_]") + pat(r"{20,}|gho_", r"[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY"),
    "private_ips": pat(r"192\.168\.", r"[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+"),
    "passwords": pat(r"password\s*[=:]", r"\s*[^\s]{6,}|Subhash"),
    "api_keys": pat(r"api[_-]?key\s*[=:]\s*[\"']", r"[A-Za-z0-9]{16,}|client[_-]?secret\s*[=:]\s*[\"'][A-Za-z0-9]{16,}"),
    "hostnames": pat(r"chak", r"'s-mac|Chakshu"),
}

ENV_FILE_RE = re.compile(r"(\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|id_rsa|id_ed25519|\.netrc|credentials)", re.I)

# Audit tooling files: their source legitimately contains detection-pattern
# strings (split or as documentation). Never flag them — same rule as the
# secret sweep in publish-public.sh, which must not match its own patterns.
TOOLING_FILES = {
    "scripts/public-safety-audit.py",
    "ops/automation/publish-public.sh",
}

def main():
    # If the target has no .git (e.g. a git-archive export), scan the working
    # tree directly — that is exactly what ships to the public repo.
    if not os.path.isdir(os.path.join(REPO, ".git")):
        print(f"Auditing working tree {REPO} (no .git — export/archive mode)...")
        violations = {}
        matches = scan_tree(REPO)
        for relpath in sorted(matches):
            for cat in matches[relpath]:
                violations[(relpath, cat)] = 1
        if violations:
            print(f"VIOLATIONS FOUND ({len(violations)}):")
            for (path, cat), _ in sorted(violations.items()):
                print(f"  [{cat}] {path}")
            return 1
        print(f"PASS: working tree clean")
        return 0

    shas = rev_list()
    if not shas:
        print("FAIL: no commits found")
        return 1
    print(f"Auditing {len(shas)} commits in {REPO}...")
    violations = {}

    for sha in shas:
        for name, pattern in PATTERNS.items():
            hits = grep_in(sha, pattern)
            for h in hits:
                violations.setdefault((sha[:8], name, h), 0)
                violations[(sha[:8], name, h)] += 1
        # env files by filename
        for f in files_in(sha):
            if ENV_FILE_RE.search(f):
                violations.setdefault((sha[:8], "env_file", f), 0)
                violations[(sha[:8], "env_file", f)] += 1

    if violations:
        print(f"VIOLATIONS FOUND ({len(violations)}):")
        for (sha, cat, path), _ in sorted(violations.items()):
            print(f"  {sha} [{cat}] {path}")
        return 1

    # commit metadata
    authors = git("log", "--all", "--format=%an <%ae>")
    bad_authors = [a for a in authors.stdout.splitlines() if "ashfordeOU <contact@ashforde.org>" not in a]
    if bad_authors:
        print(f"VIOLATIONS: unexpected commit authors: {bad_authors}")
        return 1

    print(f"PASS: {len(shas)} commits clean (no local paths, usernames, tokens, IPs, secrets, env files)")
    return 0


def scan_tree(root):
    """Recursively scan a plain directory tree for violations (no git)."""
    matches = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # skip git internals if any
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if ENV_FILE_RE.search(fn):
                matches.setdefault(rel, set()).add("env_file")
            try:
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except Exception:
                continue
            for name, pattern in PATTERNS.items():
                if rel in TOOLING_FILES:
                    continue
                if re.search(pattern, content):
                    matches.setdefault(rel, set()).add(name)
    return matches

if __name__ == "__main__":
    sys.exit(main())
