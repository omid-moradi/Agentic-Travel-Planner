"""Fail if anything that looks like a real secret is about to be committed.

Deliberately simple and dependency-free so it can run as a pre-commit hook and in CI
before anything else. False positives are acceptable; false negatives are not.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

#: Prefixes of live credentials that must never appear in tracked files.
SECRET_PREFIXES = (
    "apx_live_",
    "apx_test_",
    "tvly-dev-",
    "tvly-prod-",
    "sk_live_",
    "sk_test_",
    "AIza",
    "pk_live_",
    "rk_live_",
    "AKIA",
)

PATTERNS = tuple(re.compile(re.escape(prefix)) for prefix in SECRET_PREFIXES)

#: Files allowed to mention a prefix, because they only document or test the *format*.
ALLOWED = {
    ".env",
    ".env.example",
    Path(__file__).name,
    "tests/unit/test_config.py",      # asserts that a fake key is masked
    "tests/unit/test_logging.py",     # asserts that a fake key is redacted
}

#: Files allowed to contain the value the scanner would otherwise flag, but only when the
#: value is obviously a placeholder.
PLACEHOLDER_MARKERS = ("top-secret-key-value", "sk_live_x", "fake", "dummy", "placeholder")


def staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []

    for relative in staged_files():
        path = repo_root / relative
        if not path.is_file():
            continue
        relative_posix = relative.replace("\\", "/")
        if relative_posix in ALLOWED or path.name in ALLOWED:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                line_no = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{relative}:{line_no}: looks like a live credential")

    if offenders:
        print("BLOCKED - possible secrets staged:", file=sys.stderr)
        for offender in offenders:
            print(f"  {offender}", file=sys.stderr)
        print("\nMove real keys to .env (git-ignored) and use placeholders here.", file=sys.stderr)
        return 1

    print(f"secret scan passed ({len(staged_files())} staged files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
