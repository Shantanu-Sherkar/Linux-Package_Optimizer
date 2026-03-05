"""
Scans installed packages using native package manager commands.
Primary method for pacman: parse `pacman -Qi` output directly.
"""
import re
from dataclasses import dataclass, field
from utils.command_runner import run


@dataclass
class Package:
    name: str
    version: str = ""
    description: str = ""
    size_kb: float = 0.0
    removable: bool = False

    @property
    def size_display(self) -> str:
        if self.size_kb >= 1024:
            return f"{self.size_kb / 1024:.1f} MB"
        return f"{self.size_kb:.0f} KB"


@dataclass
class ScanResult:
    packages: list[Package] = field(default_factory=list)
    orphans: list[Package] = field(default_factory=list)
    cache_size_mb: float = 0.0
    errors: list[str] = field(default_factory=list)
    manager: str = ""

    @property
    def total(self) -> int:
        return len(self.packages)

    @property
    def removable_count(self) -> int:
        return len(self.orphans)

    @property
    def reclaimable_mb(self) -> float:
        return round(sum(p.size_kb / 1024 for p in self.orphans), 1)

    @property
    def largest(self) -> list[Package]:
        return sorted(self.packages, key=lambda p: p.size_kb, reverse=True)[:20]


# ── Size parser ───────────────────────────────────────────────────────────────

def _parse_size(raw: str) -> float:
    """Convert '12.34 MiB' / '512.00 KiB' / '1.20 GiB' to kilobytes."""
    raw = raw.strip()
    m = re.match(r"([\d.,]+)\s*(B|KiB|MiB|GiB|KB|MB|GB)", raw, re.IGNORECASE)
    if not m:
        return 0.0
    value = float(m.group(1).replace(",", "."))
    unit = m.group(2).upper()
    if unit in ("B",):
        return value / 1024
    if unit in ("KIB", "KB"):
        return value
    if unit in ("MIB", "MB"):
        return value * 1024
    if unit in ("GIB", "GB"):
        return value * 1024 * 1024
    return 0.0


# ── pacman ────────────────────────────────────────────────────────────────────

def _scan_pacman() -> ScanResult:
    result = ScanResult(manager="pacman")

    # --- All installed packages via pacman -Qi ---
    qi = run("pacman -Qi")
    if not qi.success:
        result.errors.append(f"pacman -Qi failed: {qi.stderr}")
        return result

    pkg_map: dict[str, Package] = {}
    current: dict[str, str] = {}

    def _flush(d: dict):
        name = d.get("Name", "").strip()
        if not name:
            return
        size_raw = d.get("Installed Size", "0 KiB")
        pkg = Package(
            name=name,
            version=d.get("Version", "").strip(),
            description=d.get("Description", "").strip(),
            size_kb=_parse_size(size_raw),
        )
        pkg_map[name] = pkg

    for line in qi.stdout.splitlines():
        if not line.strip():
            _flush(current)
            current = {}
            continue
        if " : " in line:
            key, _, value = line.partition(" : ")
            current[key.strip()] = value.strip()

    _flush(current)  # last block
    result.packages = list(pkg_map.values())

    # --- Orphans via pacman -Qdtq ---
    orphan_cmd = run("pacman -Qdtq")
    if orphan_cmd.success and orphan_cmd.stdout:
        for name in orphan_cmd.stdout.splitlines():
            name = name.strip()
            if not name:
                continue
            pkg = pkg_map.get(name)
            if pkg:
                pkg.removable = True
                result.orphans.append(pkg)
            else:
                result.orphans.append(Package(name=name, removable=True))

    # --- Cache size ---
    cache = run("du -sm /var/cache/pacman/pkg/")
    if cache.success:
        try:
            result.cache_size_mb = float(cache.stdout.split()[0])
        except (ValueError, IndexError):
            pass

    return result


# ── apt ───────────────────────────────────────────────────────────────────────

def _scan_apt() -> ScanResult:
    result = ScanResult(manager="apt")

    qi = run("dpkg-query -Wf ${Package}\\t${Installed-Size}\\t${Version}\\t${binary:Summary}\\n")
    pkg_map: dict[str, Package] = {}
    if qi.success:
        for line in qi.stdout.splitlines():
            parts = line.split("\t", 3)
            if len(parts) >= 2:
                try:
                    name = parts[0].strip()
                    size_kb = float(parts[1].strip()) if parts[1].strip() else 0.0
                    version = parts[2].strip() if len(parts) > 2 else ""
                    desc = parts[3].strip() if len(parts) > 3 else ""
                    pkg_map[name] = Package(name=name, version=version, description=desc, size_kb=size_kb)
                except ValueError:
                    continue
    result.packages = list(pkg_map.values())

    dry = run("apt-get -s autoremove")
    if dry.success:
        for line in dry.stdout.splitlines():
            m = re.match(r"^\s*Remv\s+(\S+)", line)
            if m:
                name = m.group(1)
                pkg = pkg_map.get(name, Package(name=name, removable=True))
                pkg.removable = True
                if pkg not in result.orphans:
                    result.orphans.append(pkg)

    cache = run("du -sm /var/cache/apt/archives/")
    if cache.success:
        try:
            result.cache_size_mb = float(cache.stdout.split()[0])
        except (ValueError, IndexError):
            pass

    return result


# ── dnf ───────────────────────────────────────────────────────────────────────

def _scan_dnf() -> ScanResult:
    result = ScanResult(manager="dnf")

    qi = run("rpm -qa --queryformat %{NAME}\\t%{SIZE}\\t%{VERSION}\\t%{SUMMARY}\\n")
    pkg_map: dict[str, Package] = {}
    if qi.success:
        for line in qi.stdout.splitlines():
            parts = line.split("\t", 3)
            if len(parts) >= 2:
                try:
                    name = parts[0].strip()
                    size_kb = float(parts[1].strip()) / 1024
                    version = parts[2].strip() if len(parts) > 2 else ""
                    desc = parts[3].strip() if len(parts) > 3 else ""
                    pkg_map[name] = Package(name=name, version=version, description=desc, size_kb=size_kb)
                except ValueError:
                    continue
    result.packages = list(pkg_map.values())

    unneeded = run("dnf repoquery --unneeded --quiet")
    if unneeded.success:
        for line in unneeded.stdout.splitlines():
            name = line.split("-")[0].strip()
            if name and name in pkg_map:
                pkg_map[name].removable = True
                result.orphans.append(pkg_map[name])

    cache = run("du -sm /var/cache/dnf/")
    if cache.success:
        try:
            result.cache_size_mb = float(cache.stdout.split()[0])
        except (ValueError, IndexError):
            pass

    return result


# ── zypper ────────────────────────────────────────────────────────────────────

def _scan_zypper() -> ScanResult:
    result = ScanResult(manager="zypper")

    qi = run("rpm -qa --queryformat %{NAME}\\t%{SIZE}\\t%{VERSION}\\t%{SUMMARY}\\n")
    pkg_map: dict[str, Package] = {}
    if qi.success:
        for line in qi.stdout.splitlines():
            parts = line.split("\t", 3)
            if len(parts) >= 2:
                try:
                    name = parts[0].strip()
                    size_kb = float(parts[1].strip()) / 1024
                    version = parts[2].strip() if len(parts) > 2 else ""
                    desc = parts[3].strip() if len(parts) > 3 else ""
                    pkg_map[name] = Package(name=name, version=version, description=desc, size_kb=size_kb)
                except ValueError:
                    continue
    result.packages = list(pkg_map.values())
    return result


# ── dispatcher ────────────────────────────────────────────────────────────────

def scan(manager: str) -> ScanResult:
    if manager == "pacman":
        return _scan_pacman()
    elif manager == "apt":
        return _scan_apt()
    elif manager == "dnf":
        return _scan_dnf()
    elif manager == "zypper":
        return _scan_zypper()
    else:
        r = ScanResult(manager=manager)
        r.errors.append(f"Unsupported package manager: {manager}")
        return r
