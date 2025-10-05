"""Cross-platform installer wizard for Bio Speak."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, Button, Entry, Frame, Label, StringVar, Tk, filedialog, messagebox

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
PAYLOAD_DIR = BASE_DIR / "payload"


class Wizard(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bio Speak Installer")
        self.geometry("560x360")
        self.configure(bg="#f8fafc")
        self.resizable(False, False)
        self.step = 0
        self.steps: list[Frame] = []
        self.install_dir = StringVar(value=self._default_install_dir())
        self.status = StringVar(value="Ready to install Bio Speak.")

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = Label(self, text="Bio Speak Setup Wizard", font=("SF Pro Display", 18, "bold"), bg="#f8fafc", fg="#0f172a")
        header.pack(pady=(24, 8))

        self.container = Frame(self, bg="#ffffff", bd=1, relief="ridge")
        self.container.pack(padx=24, pady=8, fill=BOTH, expand=True)

        self._build_steps()
        self._show_step(0)

        footer = Frame(self, bg="#f8fafc")
        footer.pack(fill="x", pady=(8, 16))

        status_label = Label(footer, textvariable=self.status, bg="#f8fafc", fg="#334155", anchor="w")
        status_label.pack(side=LEFT, padx=16)

        self.back_button = Button(footer, text="Back", state="disabled", width=10, command=self._prev_step)
        self.back_button.pack(side=RIGHT, padx=8)

        self.next_button = Button(footer, text="Next", width=10, command=self._next_step)
        self.next_button.pack(side=RIGHT, padx=8)

    def _build_steps(self) -> None:
        # Step 0: Welcome
        welcome = Frame(self.container, bg="#ffffff")
        Label(
            welcome,
            text="Welcome to Bio Speak",
            font=("SF Pro Text", 16, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        ).pack(pady=(32, 12))
        Label(
            welcome,
            text="This wizard will install the browser, desktop, and terminal editions of Bio Speak.",
            wraplength=400,
            justify="left",
            bg="#ffffff",
            fg="#475569",
        ).pack(padx=24)
        self.steps.append(welcome)

        # Step 1: Choose directory
        chooser = Frame(self.container, bg="#ffffff")
        Label(
            chooser,
            text="Choose installation folder",
            font=("SF Pro Text", 14, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        ).pack(pady=(32, 12))
        path_frame = Frame(chooser, bg="#ffffff")
        path_frame.pack(padx=32, pady=8)
        entry = Entry(path_frame, textvariable=self.install_dir, width=40)
        entry.pack(side=LEFT, padx=(0, 8))
        browse_button = Button(path_frame, text="Browse", command=self._browse_dir)
        browse_button.pack(side=LEFT)
        hint = Label(
            chooser,
            text="All Bio Speak files will be copied into the chosen folder.",
            bg="#ffffff",
            fg="#64748b",
        )
        hint.pack(pady=8)
        self.steps.append(chooser)

        # Step 2: Install progress
        progress = Frame(self.container, bg="#ffffff")
        Label(
            progress,
            text="Installing Bio Speak",
            font=("SF Pro Text", 14, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        ).pack(pady=(32, 12))
        self.progress_label = Label(progress, text="Copying files…", bg="#ffffff", fg="#475569")
        self.progress_label.pack(pady=24)
        self.steps.append(progress)

        # Step 3: Finish
        done = Frame(self.container, bg="#ffffff")
        Label(
            done,
            text="Installation complete",
            font=("SF Pro Text", 16, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        ).pack(pady=(32, 12))
        Label(
            done,
            text="Bio Speak installed successfully! Click Finish to open the welcome center.",
            wraplength=420,
            justify="left",
            bg="#ffffff",
            fg="#475569",
        ).pack(padx=24)
        self.steps.append(done)

    # ------------------------------------------------------------------
    def _show_step(self, index: int) -> None:
        for step in self.steps:
            step.pack_forget()
        self.steps[index].pack(fill=BOTH, expand=True)
        self.step = index
        self.back_button.config(state="normal" if index > 0 else "disabled")
        if index == len(self.steps) - 1:
            self.next_button.config(text="Finish")
        else:
            self.next_button.config(text="Next")

    def _next_step(self) -> None:
        if self.step == 1:
            if not self._validate_target():
                return
        if self.step == 2:
            # installation finished, go to final step
            self._show_step(3)
            self.status.set("Installation complete. Launching welcome window…")
            self.after(500, self._launch_welcome)
            return
        if self.step == 3:
            self._launch_welcome()
            self.destroy()
            return
        if self.step == 1:
            self._perform_install()
            return
        self._show_step(self.step + 1)

    def _prev_step(self) -> None:
        if self.step > 0:
            self._show_step(self.step - 1)

    def _browse_dir(self) -> None:
        current = self.install_dir.get() or str(self._default_install_dir())
        selected = filedialog.askdirectory(initialdir=current, title="Choose Bio Speak folder")
        if selected:
            self.install_dir.set(selected)

    def _default_install_dir(self) -> Path:
        base = Path.home()
        if sys.platform == "darwin":
            return base / "Applications" / "Bio Speak"
        if os.name == "nt":
            return Path(os.environ.get("ProgramFiles", str(base / "BioSpeak")))
        return base / "BioSpeak"

    def _validate_target(self) -> bool:
        path = Path(self.install_dir.get()).expanduser()
        if path.exists() and any(path.iterdir()):
            answer = messagebox.askyesno("Replace existing installation?", "The folder is not empty. Replace it?")
            if not answer:
                return False
        return True

    def _perform_install(self) -> None:
        self._show_step(2)
        self.update_idletasks()
        target = Path(self.install_dir.get()).expanduser()
        self.status.set(f"Installing to {target}")
        try:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(PAYLOAD_DIR, target)
            self._create_shortcuts(target)
        except Exception as exc:
            messagebox.showerror("Installation failed", str(exc))
            self.status.set("Installation failed.")
            return
        self.progress_label.config(text="Files copied successfully.")
        self.status.set("Bio Speak installed.")

    def _create_shortcuts(self, target: Path) -> None:
        if sys.platform == "darwin":
            apps_dir = Path.home() / "Applications"
            apps_dir.mkdir(parents=True, exist_ok=True)
            link_target = apps_dir / "Bio Speak"
            if link_target.exists() or link_target.is_symlink():
                if link_target.is_symlink() or link_target.is_dir():
                    shutil.rmtree(link_target, ignore_errors=True)
                else:
                    link_target.unlink(missing_ok=True)
            link_target.symlink_to(target, target_is_directory=True)
            bin_dir = Path.home() / "Library" / "BioSpeak" / "bin"
        elif os.name != "nt":
            bin_dir = Path.home() / ".local" / "bin"
        else:
            bin_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "BioSpeak" / "bin"
        if bin_dir:
            bin_dir.mkdir(parents=True, exist_ok=True)
            cli_source = target / "terminal"
            executable = cli_source / ("biospeak.exe" if sys.platform.startswith("win") else "biospeak")
            link = bin_dir / ("biospeak.exe" if sys.platform.startswith("win") else "biospeak")
            if link.exists() or link.is_symlink():
                link.unlink()
            try:
                link.symlink_to(executable)
            except OSError:
                shutil.copy2(executable, link)

        if os.name != "nt":
            desktop_dir = Path.home() / "Desktop"
            desktop_dir.mkdir(exist_ok=True)
            desktop_shortcut = desktop_dir / "Bio Speak.desktop"
            desktop_content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Bio Speak\n"
                f"Exec={target / 'launcher' / self._welcome_binary_name()}\n"
                "Terminal=false\n"
                "Categories=Science;Education;\n"
            )
            desktop_shortcut.write_text(desktop_content, encoding="utf-8")
            desktop_shortcut.chmod(0o755)

    def _welcome_binary_name(self) -> str:
        if sys.platform.startswith("win"):
            return "BioSpeakWelcome.exe"
        return "BioSpeakWelcome"

    def _launch_welcome(self) -> None:
        target = Path(self.install_dir.get()).expanduser()
        welcome = target / "launcher" / self._welcome_binary_name()
        if not welcome.exists():
            messagebox.showinfo("Installation complete", f"Bio Speak installed at {target}.")
            return
        if not os.access(welcome, os.X_OK):
            welcome.chmod(welcome.stat().st_mode | 0o111)
        subprocess.Popen([str(welcome)], cwd=str(welcome.parent))


def main() -> None:
    if not PAYLOAD_DIR.exists():
        root = Tk()
        root.withdraw()
        messagebox.showerror("Missing payload", f"Payload directory not found: {PAYLOAD_DIR}")
        root.destroy()
        return
    wizard = Wizard()
    wizard.mainloop()


if __name__ == "__main__":
    main()
