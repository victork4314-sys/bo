"""Welcome launcher displayed after the Bio Speak installer finishes."""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from tkinter import Button, Label, StringVar, Tk
from urllib.error import URLError
from urllib.request import urlopen

UPDATE_URL = "https://api.github.com/repos/biospeak-labs/biospeak/releases/latest"


def _candidate_paths(options: list[Path]) -> Path | None:
    for path in options:
        if path.exists():
            return path
    return None


def open_browser_version(base: Path, status: StringVar) -> None:
    index = base / "browser" / "index.html"
    if not index.exists():
        status.set("Browser version missing from installation.")
        return
    webbrowser.open(index.as_uri())
    status.set("Browser version opened in your default browser.")


def open_desktop_version(base: Path, status: StringVar) -> None:
    candidates = [
        base / "desktop" / "BioSpeak.exe",
        base / "desktop" / "BioSpeak.AppImage",
        base / "desktop" / "BioSpeak",
        base / "desktop" / "BioSpeak.app" / "Contents" / "MacOS" / "BioSpeak",
    ]
    target = _candidate_paths(candidates)
    if target is None:
        status.set("Desktop application not found.")
        return
    if target.suffix == ".AppImage":
        target.chmod(target.stat().st_mode | 0o111)
    try:
        subprocess.Popen([str(target)], cwd=str(target.parent))
    except OSError as exc:
        status.set(f"Could not launch desktop app: {exc}")
    else:
        status.set("Desktop Bio Speak Studio started.")


def open_terminal_version(base: Path, status: StringVar) -> None:
    candidates = [
        base / "terminal" / "biospeak.exe",
        base / "terminal" / "biospeak",
    ]
    target = _candidate_paths(candidates)
    if target is None:
        status.set("Terminal tool not installed.")
        return
    try:
        if sys.platform.startswith("win"):
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen([str(target)], creationflags=creationflags, cwd=str(target.parent))
        else:
            terminal = os.environ.get("TERMINAL")
            if terminal:
                subprocess.Popen([terminal, "-e", str(target)], cwd=str(target.parent))
            else:
                subprocess.Popen([str(target)], cwd=str(target.parent))
    except OSError as exc:
        status.set(f"Could not open terminal version: {exc}")
    else:
        status.set("Terminal Bio Speak opened in a new shell window.")


def check_for_updates(status: StringVar) -> None:
    status.set("Checking for updates…")
    try:
        with urlopen(UPDATE_URL, timeout=5) as response:
            data = response.read().decode("utf-8")
    except URLError:
        status.set("Unable to reach update server.")
        return
    except OSError as exc:
        status.set(f"Update check failed: {exc}")
        return
    status.set("Latest release information copied to clipboard.")
    try:
        import json
        import tkinter

        release = json.loads(data)
        message = f"Latest version: {release.get('tag_name', 'unknown')}\n{release.get('html_url', '')}"
        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(message)
        root.update()
        root.destroy()
    except Exception:
        # Clipboard may not be available in minimal environments.
        pass


def main() -> None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
    root = Tk()
    root.title("Bio Speak Installer")
    root.geometry("480x320")
    root.configure(bg="#f8fafc")

    title = Label(root, text="Bio Speak installed successfully!", font=("Segoe UI", 16, "bold"), bg="#f8fafc")
    title.pack(pady=24)

    subtitle = Label(root, text="Click one of the buttons below to begin. No setup required.", font=("Segoe UI", 11), bg="#f8fafc")
    subtitle.pack(pady=8)

    status = StringVar(value="Welcome to Bio Speak.")

    button_style = {
        "bg": "#3B82F6",
        "fg": "white",
        "activebackground": "#2563EB",
        "activeforeground": "white",
        "relief": "flat",
        "font": ("Segoe UI", 12, "bold"),
        "width": 28,
        "height": 2,
    }

    browser_btn = Button(root, text="Open Browser Version", command=lambda: open_browser_version(base, status), **button_style)
    browser_btn.pack(pady=8)

    desktop_btn = Button(root, text="Open Desktop App", command=lambda: open_desktop_version(base, status), **button_style)
    desktop_btn.pack(pady=8)

    terminal_btn = Button(root, text="Open Terminal Version", command=lambda: open_terminal_version(base, status), **button_style)
    terminal_btn.pack(pady=8)

    update_btn = Button(
        root,
        text="Check for Updates",
        command=lambda: check_for_updates(status),
        bg="#0f172a",
        fg="#e2e8f0",
        activebackground="#1e293b",
        activeforeground="#f8fafc",
        relief="flat",
        font=("Segoe UI", 11, "bold"),
        width=18,
        height=1,
    )
    update_btn.pack(pady=(16, 8))

    status_label = Label(root, textvariable=status, bg="#f8fafc", fg="#334155", font=("Segoe UI", 10))
    status_label.pack(pady=12)

    root.mainloop()


if __name__ == "__main__":
    main()
