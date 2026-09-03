import os
import shutil
import subprocess
import sys
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "gxfr_utilA"
DISPLAY_NAME = "gxfr_utilA"
PUBLISHER = "xfr_utilA"
EXE_NAME = "gxfr_utilA.exe"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\gxfr_utilA"
CREATE_NO_WINDOW = 0x08000000


def resource_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def default_install_dir():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Programs" / APP_NAME


def special_folder(name):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"[Environment]::GetFolderPath('{name}')"],
        capture_output=True,
        text=True,
        check=True,
        creationflags=CREATE_NO_WINDOW,
    )
    return Path(result.stdout.strip())


def create_shortcut(lnk_path, target):
    lnk_path.parent.mkdir(parents=True, exist_ok=True)
    target_s = str(target).replace("'", "''")
    lnk_s = str(lnk_path).replace("'", "''")
    work_s = str(target.parent).replace("'", "''")
    script = (
        f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk_s}');"
        f"$s.TargetPath = '{target_s}';"
        f"$s.WorkingDirectory = '{work_s}';"
        f"$s.IconLocation = '{target_s},0';"
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", script],
        check=True,
        creationflags=CREATE_NO_WINDOW,
    )


def write_uninstaller(install_dir, desktop_lnk, start_lnk):
    uninstall = install_dir / "uninstall.cmd"
    desktop_s = str(desktop_lnk)
    start_s = str(start_lnk)
    start_dir = str(start_lnk.parent)
    uninstall.write_text(
        "\n".join([
            "@echo off",
            "echo Uninstalling gxfr_utilA...",
            f'if exist "{desktop_s}" del /f /q "{desktop_s}"',
            f'if exist "{start_s}" del /f /q "{start_s}"',
            f'if exist "{start_dir}" rd /q "{start_dir}"',
            f'reg delete "HKCU\\{UNINSTALL_KEY}" /f >nul 2>&1',
            f'start "" cmd /c "timeout /t 1 /nobreak >nul & rd /s /q ""{install_dir}"""',
            "echo gxfr_utilA was removed.",
        ]) + "\n",
        encoding="ascii",
        errors="replace",
    )
    return uninstall


def register_uninstall(install_dir, exe_path, uninstall_path):
    size_kb = max(1, exe_path.stat().st_size // 1024)
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    try:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, DISPLAY_NAME)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe_path))
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_path}"')
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0")
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, size_kb)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    finally:
        winreg.CloseKey(key)


def install(install_dir, desktop, start_menu):
    bundled = resource_path(EXE_NAME)
    if not bundled.is_file():
        raise FileNotFoundError(f"Could not find {EXE_NAME} inside the setup program.")
    install_dir.mkdir(parents=True, exist_ok=True)
    dest_exe = install_dir / EXE_NAME
    shutil.copy2(bundled, dest_exe)
    icon_src = resource_path("gxfr_utilA.ico")
    if icon_src.is_file():
        shutil.copy2(icon_src, install_dir / "gxfr_utilA.ico")

    desktop_lnk = special_folder("Desktop") / f"{APP_NAME}.lnk"
    start_lnk = special_folder("StartMenu") / "Programs" / APP_NAME / f"{APP_NAME}.lnk"
    if desktop:
        create_shortcut(desktop_lnk, dest_exe)
    if start_menu:
        create_shortcut(start_lnk, dest_exe)
    uninstall = write_uninstaller(install_dir, desktop_lnk, start_lnk)
    register_uninstall(install_dir, dest_exe, uninstall)
    return dest_exe


class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{DISPLAY_NAME} Setup")
        self.resizable(False, False)
        self.install_dir = tk.StringVar(value=str(default_install_dir()))
        self.desktop = tk.BooleanVar(value=True)
        self.start_menu = tk.BooleanVar(value=True)
        self.installed_exe = None
        self.build_ui()

    def build_ui(self):
        pad = {"padx": 12, "pady": 6}
        frame = ttk.Frame(self, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Install gxfr_utilA on this PC.", font=("Segoe UI", 11)).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )
        ttk.Label(frame, text="Install folder:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frame, textvariable=self.install_dir, width=48).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(frame, text="Browse...", command=self.browse).grid(row=1, column=2, **pad)
        ttk.Checkbutton(frame, text="Create a Desktop shortcut", variable=self.desktop).grid(
            row=2, column=0, columnspan=3, sticky="w", **pad
        )
        ttk.Checkbutton(frame, text="Create a Start menu shortcut", variable=self.start_menu).grid(
            row=3, column=0, columnspan=3, sticky="w", **pad
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="e", **pad)
        ttk.Button(buttons, text="Install", command=self.run_install).grid(row=0, column=0, padx=6)
        ttk.Button(buttons, text="Close", command=self.destroy).grid(row=0, column=1)

    def browse(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir.get() or str(Path.home()))
        if chosen:
            self.install_dir.set(str(Path(chosen)))

    def run_install(self):
        target = Path(self.install_dir.get().strip())
        if not target:
            messagebox.showerror(DISPLAY_NAME, "Choose an install folder.")
            return
        try:
            self.installed_exe = install(target, self.desktop.get(), self.start_menu.get())
        except Exception as exc:
            messagebox.showerror(DISPLAY_NAME, f"Install failed:\n{exc}")
            return
        launch = messagebox.askyesno(
            DISPLAY_NAME,
            "gxfr_utilA was installed.\n\nOpen it now?",
        )
        if launch and self.installed_exe:
            os.startfile(self.installed_exe)
        self.destroy()


def main():
    app = SetupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
