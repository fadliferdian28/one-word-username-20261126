#!/usr/bin/env python3
"""Publish the account's make.fun username as the bounty entry file.

The One Word, One Username, One Reward bounty wants a single word: the
account's own handle. This script validates that word, writes it to
``entry.txt`` inside an output directory, then proves the bytes on disk
match a pinned SHA-256 before reporting success.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

# The entry is fixed: the account handle, one word, nothing else.
ENTRY_TEXT = "jackpoot"

# Filled in with the real digest of entry.txt once it has been computed.
EXPECTED_SHA256 = "5f72c35fdbfe73bac515683a08ea17a7159ccfa6bea00ed9a78e081a048b86aa"

# The script's own directory is the repository root; never write entry.txt
# there, because that file is the source of truth for this bounty.
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ENTRY = SCRIPT_DIR / "entry.txt"

MAX_CHARS = 30
MIN_CHARS = 1


def fail(message):
    """Print a clear error and terminate with a non-zero status."""
    print(f"error: {message}", file=sys.stderr)
    return 1


def validate_entry_text(text):
    """Return an error string if ``text`` is not a single valid word."""
    if not isinstance(text, str):
        return "entry text must be a string"
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        return f"entry text is not valid UTF-8: {exc}"
    length = len(text)
    if not (MIN_CHARS <= length <= MAX_CHARS):
        return f"entry text must be {MIN_CHARS}-{MAX_CHARS} characters, got {length}"
    if not text.strip():
        return "entry text must not be only whitespace"
    if any(ch.isspace() for ch in text):
        return "entry text must be a single word with no spaces or newlines"
    return None


def is_same_file(left, right):
    """True when both paths point at the same file, tolerating absent paths."""
    try:
        if left.exists() and right.exists():
            return os.path.samefile(left, right)
    except OSError:
        # If the filesystem cannot answer, fall back to resolved paths.
        pass
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def sha256_of(path):
    """Hex digest of the file at ``path``."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    problem = validate_entry_text(ENTRY_TEXT)
    if problem is not None:
        return fail(problem)

    expected = EXPECTED_SHA256.strip().lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        return fail("EXPECTED_SHA256 is not a configured SHA-256 digest")

    raw_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "./output").strip()
    if not raw_dir:
        return fail("MAKEFUN_OUTPUT_DIR is empty")
    output_dir = Path(raw_dir).expanduser()

    try:
        output_dir = output_dir.resolve()
    except OSError as exc:
        return fail(f"cannot resolve output directory {output_dir}: {exc}")

    if output_dir == SCRIPT_DIR:
        return fail("refusing to write entry.txt into the repository root")

    target = output_dir / "entry.txt"
    if is_same_file(target, REPO_ENTRY):
        return fail("refusing to overwrite the repository's own entry.txt")

    payload = (ENTRY_TEXT + "\n").encode("utf-8")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(payload)
    except shutil.SameFileError:
        return fail(f"output path {target} refers to an unexpected same file")
    except OSError as exc:
        return fail(f"cannot write {target}: {exc}")

    try:
        actual = sha256_of(target)
    except OSError as exc:
        return fail(f"cannot read back {target}: {exc}")

    if actual != expected:
        return fail(f"hash mismatch for {target}: expected {expected}, got {actual}")

    print(f"ok: wrote {len(payload)} bytes to {target} (sha256 {actual})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
