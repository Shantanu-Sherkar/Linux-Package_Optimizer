"""
Safe subprocess wrapper for running shell commands.
"""
import subprocess
import shlex


class CommandResult:
    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout.strip()
        self.stderr = stderr.strip()
        self.returncode = returncode
        self.success = returncode == 0


def run(command: str, timeout: int = 60, shell: bool = False) -> CommandResult:
    try:
        if shell:
            result = subprocess.run(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=timeout,
            )
        else:
            result = subprocess.run(
                shlex.split(command),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=timeout,
            )
        return CommandResult(result.stdout, result.stderr, result.returncode)
    except subprocess.TimeoutExpired:
        return CommandResult("", f"Timed out after {timeout}s", -1)
    except FileNotFoundError as e:
        return CommandResult("", f"Command not found: {e}", 127)
    except Exception as e:
        return CommandResult("", str(e), -1)


def run_sudo(command: str, timeout: int = 120) -> CommandResult:
    """Try pkexec first (GUI-friendly), fall back to sudo -S."""
    result = run(f"pkexec {command}", timeout=timeout)
    if result.returncode == 127:
        # pkexec not found, try sudo
        result = run(f"sudo -n {command}", timeout=timeout)
    return result
