from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from core.identity import (  # noqa: E402
    APP_NAME, BUILD_DIR_NAME, CREATOR, DESCRIPTION, EXE_NAME, INSTALL_DIR_NAME, SHORTCUT_NAME,
)

BUILD_ROOT = (
    Path(os.environ["LOCALAPPDATA"]) / BUILD_DIR_NAME
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA")
    else ROOT / ".build"
)
VENV = BUILD_ROOT / "venv"
DIST_DIR = BUILD_ROOT / "dist"
WORK_DIR = BUILD_ROOT / "work"
SPEC_DIR = BUILD_ROOT / "spec"


def run(*args: str) -> None:
    print("\n>", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def create_shortcut(target: Path, arguments: str = "") -> None:
    ps = (
        "$desktop=[Environment]::GetFolderPath('Desktop');"
        "if([string]::IsNullOrWhiteSpace($desktop)){"
        "$desktop=Join-Path $env:USERPROFILE 'Desktop'};"
        "New-Item -ItemType Directory -Force -Path $desktop | Out-Null;"
        "$w=New-Object -ComObject WScript.Shell;"
        "$locations=@($desktop,[Environment]::GetFolderPath('Programs'));"
        "foreach($location in $locations){"
        "if(-not [string]::IsNullOrWhiteSpace($location)){"
        "New-Item -ItemType Directory -Force -Path $location | Out-Null;"
        f"$shortcut=Join-Path $location '{SHORTCUT_NAME}';"
        "$s=$w.CreateShortcut($shortcut);"
        f"$s.TargetPath='{str(target).replace("'", "''")}';"
        f"$s.Arguments='{arguments.replace("'", "''")}';"
        f"$s.WorkingDirectory='{str(target.parent).replace("'", "''")}';"
        f"$s.Description='{DESCRIPTION} — Created by {CREATOR}';"
        f"$s.IconLocation='{str(target).replace("'", "''")},0';"
        "$s.Save()}};"
        "$startup=[Environment]::GetFolderPath('Startup');"
        "if(-not [string]::IsNullOrWhiteSpace($startup)){"
        f"$shortcut=Join-Path $startup '{SHORTCUT_NAME}';"
        "$s=$w.CreateShortcut($shortcut);"
        f"$s.TargetPath='{str(target).replace("'", "''")}';"
        "$s.Arguments='--background';"
        f"$s.WorkingDirectory='{str(target.parent).replace("'", "''")}';"
        f"$s.Description='{APP_NAME} background startup';"
        f"$s.IconLocation='{str(target).replace("'", "''")},0';"
        "$s.Save()}"
    )
    run("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps)
    print(f"\n{APP_NAME} Desktop, Start Menu and Windows startup shortcuts created.")


def installed_application() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / INSTALL_DIR_NAME
    return base / EXE_NAME


def install_built_application(built_executable: Path) -> Path:
    destination = installed_application().parent
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(built_executable.parent, destination)
    executable = destination / EXE_NAME
    if not executable.exists():
        raise RuntimeError(f"Windows application installation did not produce {EXE_NAME}.")
    return executable


def build_application(python: Path) -> Path:
    separator = ";" if sys.platform == "win32" else ":"
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    run(
        str(python), "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", INSTALL_DIR_NAME, "--icon", str(ROOT / "jarvis.ico"),
        "--version-file", str(ROOT / "version_info.txt"),
        "--distpath", str(DIST_DIR), "--workpath", str(WORK_DIR),
        "--specpath", str(SPEC_DIR),
        "--add-data", f"{ROOT / 'core' / 'prompt.txt'}{separator}core",
        "--add-data", f"{ROOT / 'core' / 'manager_prompt.txt'}{separator}core",
        "--add-data", f"{ROOT / 'jarvis.ico'}{separator}.",
        "--add-data", f"{ROOT / 'skills'}{separator}skills",
        "--hidden-import", "PyQt6.QtTextToSpeech",
        "--hidden-import", "PyQt6.QtMultimedia", "--collect-all", "edge_tts",
        "--collect-all", "speech_recognition", "--collect-all", "pocketsphinx",
        "--collect-all", "sounddevice", "--hidden-import", "numpy",
        "--hidden-import", "pyautogui", "--hidden-import", "pyperclip",
        "--collect-all", "keyring", str(ROOT / "main.py"),
    )
    executable = DIST_DIR / INSTALL_DIR_NAME / (EXE_NAME if sys.platform == "win32" else INSTALL_DIR_NAME)
    if not executable.exists():
        raise RuntimeError("Application build finished without producing the executable.")
    return executable


def main() -> None:
    if sys.platform != "win32":
        print("This installer creates a Windows desktop application shortcut.")
    existing_executable = installed_application()
    if "--shortcut-only" in sys.argv:
        if not existing_executable.exists():
            existing_executable = DIST_DIR / INSTALL_DIR_NAME / EXE_NAME
        if not existing_executable.exists():
            raise FileNotFoundError(f"{EXE_NAME} is missing. Run install.bat first.")
        create_shortcut(existing_executable)
        print(f"\nShortcut repaired. Open {APP_NAME} from your Desktop.")
        return
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"\nUsing short build directory: {BUILD_ROOT}")
    if not VENV.exists():
        run(sys.executable, "-m", "venv", str(VENV))
    python = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    run(str(python), "-m", "pip", "install", "--upgrade", "pip")
    run(str(python), "-m", "pip", "install", "-r", "requirements.txt")
    if sys.platform == "win32":
        print("\nBuilding the native Windows application. This can take several minutes…")
        executable = install_built_application(build_application(python))
        create_shortcut(executable)
    print(f"\n{APP_NAME} installation complete.")
    print(f"Double-click '{APP_NAME}' on your Desktop.")
    print(f"Created by {CREATOR}.")


if __name__ == "__main__":
    main()
