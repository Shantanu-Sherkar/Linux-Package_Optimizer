# Linux Package Optimizer (LPO)

A lightweight desktop utility for analyzing installed packages, finding orphans, and cleaning up disk space — **no pip installs required**.

## Requirements

- Python 3.11+
- `tkinter` (ships with Python — on Arch: `sudo pacman -S tk`)

That's it. No PyQt6, no virtual environments.

## Run

```bash
python main.py
```

## How it works (pacman)

Package data is read directly from:

```bash
pacman -Qi          # all installed packages with sizes, versions, descriptions
pacman -Qdtq        # orphaned dependencies
du -sm /var/cache/pacman/pkg/   # cache size
```

## Supported Package Managers

| Manager | Distros |
|---|---|
| `pacman` | Arch, Manjaro, EndeavourOS, CachyOS |
| `apt` | Ubuntu, Debian, Linux Mint |
| `dnf` | Fedora |
| `zypper` | openSUSE |

## Project Structure

```
linux-package-optimizer/
├── main.py
├── gui/
│   └── main_window.py      # tkinter GUI
├── core/
│   ├── package_detector.py # detect package manager
│   ├── package_scanner.py  # parse pacman -Qi / dpkg-query / rpm
│   └── operations.py       # remove packages, clean cache
└── utils/
    └── command_runner.py   # subprocess wrapper
```

## Security

- Package removal and cache cleaning use `pkexec` (GUI privilege dialog) or `sudo`
- Confirmation dialog shown before any destructive action
