"""
Package removal and cache cleaning operations.
"""
from utils.command_runner import run_sudo, CommandResult

REMOVE_CMD = {
    "pacman": "pacman -Rns --noconfirm",
    "apt":    "apt remove -y",
    "dnf":    "dnf remove -y",
    "zypper": "zypper remove -y",
}

CLEAN_CMD = {
    "pacman": "pacman -Sc --noconfirm",
    "apt":    "apt clean",
    "dnf":    "dnf clean all",
    "zypper": "zypper clean --all",
}


def remove_packages(manager: str, names: list[str]) -> CommandResult:
    if not names:
        return CommandResult("", "No packages selected.", 1)
    base = REMOVE_CMD.get(manager)
    if not base:
        return CommandResult("", f"Unsupported manager: {manager}", 1)
    return run_sudo(f"{base} {' '.join(names)}")


def clean_cache(manager: str) -> CommandResult:
    cmd = CLEAN_CMD.get(manager)
    if not cmd:
        return CommandResult("", f"Unsupported manager: {manager}", 1)
    return run_sudo(cmd)
