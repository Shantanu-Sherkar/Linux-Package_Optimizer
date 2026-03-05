"""
Detects the system package manager.
"""
import shutil

MANAGERS = ["pacman", "apt", "dnf", "zypper"]


def detect() -> str | None:
    """Returns the name of the first detected package manager, or None."""
    for mgr in MANAGERS:
        if shutil.which(mgr):
            return mgr
    return None
