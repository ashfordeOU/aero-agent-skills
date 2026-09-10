#!/usr/bin/env python3
"""Gate test: release-manager.py resolves gh via shutil.which and fails loud
with a NAMED message instead of raising (VEDA-0034, durable guard).

Context: a cron no_agent job spawns with a managed PATH that omits
/opt/homebrew/bin. The cut path ran a bare "gh", raised FileNotFoundError,
and spammed the group every 30m. The fix resolves gh once at import (GH)
and returns exit 1 with a named failure when it is absent - the same
fail-loud contract the wrapper now carries.

Hermetic: stdlib only, gh forced absent via a patched shutil.which, no
network, and no release is attempted (the guard returns before any gh call).
"""
import contextlib
import importlib.util
import io
import os
import shutil
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANAGER = os.path.join(REPO_ROOT, "scripts", "release-manager.py")


def _load_manager(gh_path):
    """Import release-manager.py with shutil.which forced to resolve gh."""
    real_which = shutil.which

    def fake_which(name, *args, **kwargs):
        if name == "gh":
            return gh_path
        return real_which(name, *args, **kwargs)

    shutil.which = fake_which
    try:
        spec = importlib.util.spec_from_file_location("release_manager_test", MANAGER)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        shutil.which = real_which
    return mod


class GhGuard(unittest.TestCase):
    def test_cut_fails_named_when_gh_missing(self):
        mod = _load_manager(None)
        self.assertIsNone(mod.GH, "GH should be None when gh is not on PATH")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = mod.cut_release(False, auto=True)
        printed = out.getvalue()
        self.assertEqual(rc, 1, printed)
        self.assertIn("gh unavailable", printed)
        self.assertNotIn("Traceback", printed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
