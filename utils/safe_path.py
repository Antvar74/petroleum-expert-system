"""
Safe path resolution for PETROEXPERT.

Prevents path traversal attacks by restricting file access
to the project's data/ directory with extension whitelisting.
"""
import os

# Absolute path to the project data/ directory
DATA_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "data"))

# Allowed file extensions for data files
ALLOWED_EXTENSIONS = {".pdf", ".csv", ".md", ".txt"}


def resolve_safe_data_path(filename: str) -> str:
    """
    Resolve a user-supplied filename to a safe absolute path within data/.

    Security measures:
      1. os.path.basename() strips all directory components (../../etc/passwd → passwd)
      2. Extension whitelist blocks unexpected file types
      3. os.path.realpath() resolves symlinks
      4. startswith(DATA_DIR) verifies the resolved path hasn't escaped

    Raises:
        ValueError: If filename is invalid, has disallowed extension,
                    or resolves outside the data directory.
    """
    # Strip directory components — ../../etc/passwd → passwd
    basename = os.path.basename(filename)

    if not basename:
        raise ValueError(f"Invalid filename: {filename!r}")

    # Check extension whitelist
    ext = os.path.splitext(basename)[1].lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}")
    if not ext:
        raise ValueError(f"Filename has no extension: {basename!r}")

    # Build candidate path and resolve symlinks
    candidate = os.path.realpath(os.path.join(DATA_DIR, basename))

    # Defense-in-depth: verify resolved path is within DATA_DIR
    if not candidate.startswith(DATA_DIR + os.sep) and candidate != DATA_DIR:
        raise ValueError(f"Path escapes data directory: {filename!r}")

    return candidate
