
import os
import shutil
import subprocess
from pathlib import Path


# Only applications explicitly registered here can be launched.
APP_ALIASES = {
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "notepad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "file explorer": "explorer",
    "explorer": "explorer",
    "terminal": "terminal",
    "command prompt": "cmd",
    "cmd": "cmd",
    "powershell": "powershell",
    "firefox": "firefox",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "edge",
    "microsoft edge": "edge",
}


def _find_executable(name: str, candidates: list[str]) -> str | None:
    """Find an application by PATH or common Windows install paths."""
    found = shutil.which(name)
    if found:
        return found

    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path)

    return None


def _resolve_app(app_id: str) -> list[str]:
    """Resolve an allowlisted app ID to an executable and arguments."""
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get(
        "ProgramFiles(x86)", r"C:\Program Files (x86)"
    )

    candidates = {
        "vscode": [
            str(Path(local) / "Programs/Microsoft VS Code/Code.exe"),
            str(Path(program_files) / "Microsoft VS Code/Code.exe"),
        ],
        "firefox": [
            str(Path(program_files) / "Mozilla Firefox/firefox.exe"),
            str(Path(program_files_x86) / "Mozilla Firefox/firefox.exe"),
        ],
        "chrome": [
            str(Path(program_files) / "Google/Chrome/Application/chrome.exe"),
            str(Path(program_files_x86) / "Google/Chrome/Application/chrome.exe"),
            str(Path(local) / "Google/Chrome/Application/chrome.exe"),
        ],
        "edge": [
            str(Path(program_files) / "Microsoft/Edge/Application/msedge.exe"),
            str(Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe"),
        ],
    }

    if app_id == "explorer":
        return ["explorer.exe"]
    if app_id == "notepad":
        return ["notepad.exe"]
    if app_id == "calculator":
        return ["calc.exe"]
    if app_id == "terminal":
        return ["wt.exe"]
    if app_id == "cmd":
        return ["cmd.exe"]
    if app_id == "powershell":
        return ["powershell.exe"]

    executable_names = {
        "vscode": "code",
        "firefox": "firefox",
        "chrome": "chrome",
        "edge": "msedge",
    }

    executable = _find_executable(
        executable_names[app_id],
        candidates.get(app_id, []),
    )

    if not executable:
        raise FileNotFoundError(
            f"Could not find {app_id}. Check whether it is installed."
        )

    return [executable]


def launch_app(app_name: str) -> str:
    """Launch an approved Windows application."""
    normalised = " ".join(app_name.lower().strip().split())
    app_id = APP_ALIASES.get(normalised)

    if not app_id:
        raise ValueError(
            f"'{app_name}' is not an approved application."
        )

    command = _resolve_app(app_id)
    subprocess.Popen(command, shell=False)

    return f"Launched {app_id}."
