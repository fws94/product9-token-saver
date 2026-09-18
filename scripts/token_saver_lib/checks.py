"""Run an explicitly selected check once and retain separate byte artifacts."""
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

from .compact import compact_file
from .result import Result


def _find_executable(name: str, directory: Path) -> str | None:
    """Search PATH relative to the check directory, never the wrapper cwd."""
    names = [name]
    if os.name == "nt":
        extensions = [ext for ext in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep) if ext]
        if not any(name.lower().endswith(ext.lower()) for ext in extensions):
            names = [name + ext for ext in extensions]
    for entry in os.get_exec_path():
        folder = Path(entry.strip('"') if os.name == "nt" else entry)
        folder = folder if folder.is_absolute() else directory / folder
        for filename in names:
            candidate = folder / filename
            # An absolute path prevents shutil.which's implicit Windows cwd search.
            selected = shutil.which(str(candidate))
            if selected:
                return str(Path(selected).resolve())
    return None


def _stop_process(process: subprocess.Popen) -> tuple[bool, list[str]]:
    """Bound cleanup; report uncertainty instead of waiting indefinitely."""
    warnings = []
    try:
        if os.name == "nt":
            system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
            if not system_root:
                raise FileNotFoundError("Windows system directory is unavailable")
            taskkill = str(Path(system_root) / "System32" / "taskkill.exe")
            stop = subprocess.run([taskkill, "/PID", str(process.pid), "/T", "/F"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
            if stop.returncode:
                warnings.append("Process-tree termination was not confirmed by taskkill")
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except (OSError, subprocess.TimeoutExpired) as error:
        warnings.append(f"Process-tree termination unavailable ({type(error).__name__})")
    try:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired) as error:
        warnings.append(f"Child termination unconfirmed ({type(error).__name__}); do not retry automatically")
    return process.poll() is not None, warnings


def run_checks(command: list[str], *, cwd: str | Path, timeout: float,
               output_dir: str | Path | None = None, max_lines: int = 80) -> Result:
    """Execute an argument array once, using exit status rather than log words.

    Timeout is mandatory. Output files are unique, private local evidence.
    The caller is responsible for authorizing the selected command's effects.
    """
    if (not isinstance(command, list) or not command or not command[0]
            or any(not isinstance(arg, str) or "\0" in arg for arg in command)):
        raise ValueError("command must be a non-empty list of string arguments without NUL")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    if type(max_lines) is not int or max_lines < 1:
        raise ValueError("max_lines must be positive")
    directory = Path(cwd).resolve()
    data = {"command": list(command), "cwd": str(directory), "timeout_seconds": timeout,
            "outcome": "not-started", "timed_out": False, "termination_confirmed": None, "tree_cleanup_confirmed": None,
            "artifacts": {}}
    if not directory.is_dir():
        return Result(operation="checks", status="blocked", summary="Working directory is unavailable", data=data)
    args = list(command)
    if "/" in args[0] or "\\" in args[0]:
        executable = Path(args[0])
        args[0] = str(executable if executable.is_absolute() else directory / executable)
    else:
        selected = _find_executable(args[0], directory)
        if selected is None:
            return Result(operation="checks", status="blocked",
                          summary="Executable is unavailable on PATH", data=data)
        args[0] = selected
    if os.name == "nt" and Path(args[0]).suffix.lower() in (".bat", ".cmd"):
        return Result(operation="checks", status="blocked",
                      summary="Batch files require an explicitly authorized interpreter invocation", data=data)
    evidence = []
    try:
        base = Path(output_dir) if output_dir is not None else Path("reports/checks")
        base = (base if base.is_absolute() else directory / base).resolve()
        base.mkdir(parents=True, exist_ok=True)
        artifact_dir = Path(tempfile.mkdtemp(prefix="check-", dir=base))
        artifacts = {stream: str(artifact_dir / f"{stream}.log") for stream in ("stdout", "stderr")}
        data["artifacts"] = artifacts
        stdout = open(artifacts["stdout"], "xb")
        try:
            stderr = open(artifacts["stderr"], "xb")
        except OSError:
            stdout.close()
            raise
    except OSError as error:
        return Result(operation="checks", status="blocked",
                      summary=f"Cannot create output artifacts ({type(error).__name__})", data=data)
    evidence = list(artifacts.values())
    started = time.monotonic()
    warnings = []
    exit_code = None
    status = "blocked"
    summary = "Check was not started"
    with stdout, stderr:
        try:
            process = subprocess.Popen(args, cwd=directory, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, shell=False,
                                       start_new_session=os.name != "nt",
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except OSError as error:
            summary = f"Cannot start check ({type(error).__name__})"
        else:
            try:
                exit_code = process.wait(timeout=timeout)
                data["outcome"] = "passed" if exit_code == 0 else "failed"
                status = "completed" if exit_code == 0 else "failed"
                summary = "Check passed" if exit_code == 0 else "Check failed"
            except subprocess.TimeoutExpired:
                data["timed_out"] = True
                data["outcome"] = "timeout"
                confirmed, cleanup_warnings = _stop_process(process)
                warnings.extend(cleanup_warnings)
                data["termination_confirmed"] = confirmed
                data["tree_cleanup_confirmed"] = confirmed and not cleanup_warnings
                exit_code = process.returncode
                status = "failed" if data["tree_cleanup_confirmed"] else "uncertain"
                summary = "Check timed out" if data["tree_cleanup_confirmed"] else "Check timed out; process-tree cleanup unconfirmed"
            except BaseException:
                _stop_process(process)
                raise
    duration_ms = (time.monotonic() - started) * 1000
    for stream, artifact in artifacts.items():
        view = compact_file(artifact, format="test", max_lines=max_lines)
        data[stream] = view.to_dict()
        warnings.extend(f"{stream}: {warning}" for warning in view.warnings)
        if view.status != "completed":
            warnings.append(f"{stream}: {view.summary}; original bytes retained")
    return Result(operation="checks", status=status, summary=summary, data=data,
                  exit_code=exit_code, duration_ms=duration_ms, evidence=evidence, warnings=warnings)
