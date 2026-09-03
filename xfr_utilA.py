import json
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_TITLE = "xfr_utilA"


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_file(name):
    bases = []
    if getattr(sys, "frozen", False):
        bases.append(Path(getattr(sys, "_MEIPASS", "")))
        bases.append(Path(sys.executable).resolve().parent)
    bases.append(Path(__file__).resolve().parent)
    for base in bases:
        path = base / name
        if path.is_file():
            return path
    return None


def app_icon():
    icon_path = bundled_file("gxfr_utilA.ico")
    if icon_path:
        return QIcon(str(icon_path))
    return QIcon()


def config_path():
    if getattr(sys, "frozen", False):
        folder = Path(os.environ.get("APPDATA", str(Path.home()))) / "gxfr_utilA"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            return folder / "xfr_utilA_config.json"
        except OSError:
            return app_dir() / "xfr_utilA_config.json"
    return Path(__file__).resolve().parent / "xfr_utilA_config.json"


DEFAULT_SOURCE = r"D:\USB321FD"
DEFAULT_DEST = r"C:\Users\oscar\OneDrive\Desktop"


def load_config():
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data):
    try:
        config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def folder_date(path):
    return datetime.fromtimestamp(os.path.getmtime(path)).date()


def format_size(num_bytes):
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


class CopyWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int, int)

    def __init__(self, jobs, skip_newer_dest):
        super().__init__()
        self.jobs = jobs
        self.skip_newer_dest = skip_newer_dest

    def run(self):
        copied = 0
        skipped = 0
        errors = 0
        for job in self.jobs:
            src = Path(job["src"])
            dest = Path(job["dest"])
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and self.skip_newer_dest:
                    dest_mtime = dest.stat().st_mtime
                    src_mtime = src.stat().st_mtime
                    if dest_mtime >= src_mtime:
                        self.log_signal.emit(f"  skipped (destination not older): {job['label']}")
                        skipped += 1
                        continue
                shutil.copy2(src, dest)
                self.log_signal.emit(f"  copied: {job['label']}")
                copied += 1
            except OSError as exc:
                self.log_signal.emit(f"  error: {job['label']} ({exc})")
                errors += 1
        self.finished_signal.emit(copied, skipped, errors)


class TransferApp(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
        self.restore_config()
        self.update_direction_label()

    def init_ui(self):
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(app_icon())
        self.resize(720, 620)

        layout = QVBoxLayout()

        self.direction_label = QLabel()
        layout.addWidget(self.direction_label)

        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Source folder, any drive")
        layout.addLayout(self.path_row("Source:", self.source_input, self.browse_source))

        swap_row = QHBoxLayout()
        self.swap_btn = QPushButton("Swap source and destination")
        self.swap_btn.clicked.connect(self.swap_paths)
        swap_row.addWidget(self.swap_btn)
        swap_row.addStretch()
        layout.addLayout(swap_row)

        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Destination folder, any drive")
        layout.addLayout(self.path_row("Destination:", self.dest_input, self.browse_dest))

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Subfolders:"))
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("optional, space-separated: U chj S SGK LDESK ibkr")
        folder_layout.addWidget(self.folder_input)
        self.scan_btn = QPushButton("Scan common")
        self.scan_btn.setToolTip("Fill with subfolder names that exist in both source and destination")
        self.scan_btn.clicked.connect(self.scan_common_subfolders)
        folder_layout.addWidget(self.scan_btn)
        layout.addLayout(folder_layout)
        layout.addWidget(QLabel("Leave subfolders empty to copy files from the source folder itself."))

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Target date:"))
        self.date_combo = QComboBox()
        self.date_combo.addItem(f"Today ({datetime.now().date()})", 0)
        for i in range(1, 5):
            day = datetime.now().date() - timedelta(days=i)
            self.date_combo.addItem(f"{i} day(s) ago ({day})", i)
        date_layout.addWidget(self.date_combo)
        self.or_newer_check = QCheckBox("This date or newer")
        date_layout.addWidget(self.or_newer_check)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        self.skip_newer_check = QCheckBox("Do not overwrite a newer file already at the destination")
        self.skip_newer_check.setChecked(True)
        layout.addWidget(self.skip_newer_check)

        button_row = QHBoxLayout()
        self.preview_btn = QPushButton("Preview matching files")
        self.preview_btn.clicked.connect(self.preview_files)
        self.run_btn = QPushButton("Copy selected files")
        self.run_btn.clicked.connect(self.run_transfer)
        button_row.addWidget(self.preview_btn)
        button_row.addWidget(self.run_btn)
        layout.addLayout(button_row)

        layout.addWidget(QLabel("Matching files:"))
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        select_row = QHBoxLayout()
        select_all_btn = QPushButton("Select all")
        select_all_btn.clicked.connect(lambda: self.set_all_checked(True))
        select_none_btn = QPushButton("Select none")
        select_none_btn.clicked.connect(lambda: self.set_all_checked(False))
        select_row.addWidget(select_all_btn)
        select_row.addWidget(select_none_btn)
        select_row.addStretch()
        layout.addLayout(select_row)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)
        self.source_input.textChanged.connect(self.update_direction_label)
        self.dest_input.textChanged.connect(self.update_direction_label)

    def path_row(self, label, line_edit, browse_fn):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(line_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(browse_fn)
        row.addWidget(browse_btn)
        return row

    def restore_config(self):
        cfg = load_config()
        self.source_input.setText(cfg.get("source", DEFAULT_SOURCE))
        self.dest_input.setText(cfg.get("dest", DEFAULT_DEST))
        self.folder_input.setText(cfg.get("folders", ""))
        self.or_newer_check.setChecked(bool(cfg.get("or_newer", False)))
        self.skip_newer_check.setChecked(bool(cfg.get("skip_newer_dest", True)))

    def persist_config(self):
        save_config({
            "source": self.source_input.text().strip(),
            "dest": self.dest_input.text().strip(),
            "folders": self.folder_input.text().strip(),
            "or_newer": self.or_newer_check.isChecked(),
            "skip_newer_dest": self.skip_newer_check.isChecked(),
        })

    def browse_source(self):
        self.browse_into(self.source_input, "Select source folder")

    def browse_dest(self):
        self.browse_into(self.dest_input, "Select destination folder")

    def browse_into(self, line_edit, title):
        start = line_edit.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, title, start)
        if chosen:
            line_edit.setText(os.path.normpath(chosen))

    def swap_paths(self):
        source = self.source_input.text()
        dest = self.dest_input.text()
        self.source_input.setText(dest)
        self.dest_input.setText(source)
        self.log("Swapped source and destination.")
        self.update_direction_label()

    def update_direction_label(self):
        source = self.source_input.text().strip()
        dest = self.dest_input.text().strip()
        src_drive = Path(source).drive or "?"
        dest_drive = Path(dest).drive or "?"
        self.direction_label.setText(f"Direction: {src_drive}  ->  {dest_drive}")

    def log(self, message):
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()

    def set_busy(self, busy):
        for widget in (
            self.preview_btn,
            self.run_btn,
            self.swap_btn,
            self.scan_btn,
            self.source_input,
            self.dest_input,
            self.folder_input,
            self.date_combo,
        ):
            widget.setEnabled(not busy)

    def set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(state)

    def parsed_roots(self):
        source = self.source_input.text().strip()
        dest = self.dest_input.text().strip()
        if not source or not dest:
            QMessageBox.warning(self, APP_TITLE, "Choose both a source folder and a destination folder.")
            return None
        source_path = Path(source)
        dest_path = Path(dest)
        if not source_path.is_dir():
            QMessageBox.warning(self, APP_TITLE, f"Source folder not found:\n{source}")
            return None
        if not dest_path.is_dir():
            QMessageBox.warning(self, APP_TITLE, f"Destination folder not found:\n{dest}")
            return None
        if source_path.resolve() == dest_path.resolve():
            QMessageBox.warning(self, APP_TITLE, "Source and destination must be different folders.")
            return None
        return source_path, dest_path

    def folder_pairs(self, source_path, dest_path):
        names = self.folder_input.text().split()
        if not names:
            return [(source_path, dest_path, source_path.name or str(source_path))]
        pairs = []
        for name in names:
            pairs.append((source_path / name, dest_path / name, name))
        return pairs

    def target_date(self):
        days_ago = self.date_combo.currentData()
        return datetime.now().date() - timedelta(days=days_ago)

    def matches_date(self, file_date, target):
        if self.or_newer_check.isChecked():
            return file_date >= target
        return file_date == target

    def collect_jobs(self, source_path, dest_path):
        target = self.target_date()
        jobs = []
        for src_dir, dest_dir, label in self.folder_pairs(source_path, dest_path):
            if not src_dir.is_dir():
                self.log(f"Skipping '{label}': source folder not found.")
                continue
            try:
                entries = sorted(src_dir.iterdir(), key=lambda p: p.name.lower())
            except OSError as exc:
                self.log(f"Skipping '{label}': {exc}")
                continue
            for item in entries:
                if not item.is_file():
                    continue
                try:
                    file_date = folder_date(item)
                except OSError:
                    continue
                if not self.matches_date(file_date, target):
                    continue
                jobs.append({
                    "src": str(item),
                    "dest": str(dest_dir / item.name),
                    "label": f"{label}\\{item.name}",
                    "date": str(file_date),
                    "size": item.stat().st_size,
                })
        return jobs, target

    def scan_common_subfolders(self):
        roots = self.parsed_roots()
        if not roots:
            return
        source_path, dest_path = roots
        try:
            src_names = {p.name for p in source_path.iterdir() if p.is_dir()}
            dest_names = {p.name for p in dest_path.iterdir() if p.is_dir()}
        except OSError as exc:
            QMessageBox.warning(self, APP_TITLE, f"Could not scan folders:\n{exc}")
            return
        common = sorted(src_names & dest_names, key=str.lower)
        if not common:
            self.log("No common subfolder names found.")
            return
        self.folder_input.setText(" ".join(common))
        self.log(f"Found {len(common)} common subfolder(s).")

    def preview_files(self):
        roots = self.parsed_roots()
        if not roots:
            return
        self.persist_config()
        self.log_output.clear()
        self.file_list.clear()
        jobs, target = self.collect_jobs(*roots)
        date_note = "or newer" if self.or_newer_check.isChecked() else "exact date"
        self.log(f"Preview for {target} ({date_note}). {len(jobs)} file(s) matched.\n")
        for job in jobs:
            text = f"{job['label']}  ({job['date']}, {format_size(job['size'])})"
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, job)
            self.file_list.addItem(item)
        if not jobs:
            self.log("No matching files. Check the folders and date.")

    def selected_jobs(self):
        jobs = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                jobs.append(item.data(Qt.UserRole))
        return jobs

    def run_transfer(self):
        if self.worker and self.worker.isRunning():
            return
        jobs = self.selected_jobs()
        if not jobs:
            self.preview_files()
            jobs = self.selected_jobs()
        if not jobs:
            return
        self.persist_config()
        self.log(f"Copying {len(jobs)} file(s)...\n")
        self.set_busy(True)
        self.worker = CopyWorker(jobs, self.skip_newer_check.isChecked())
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.transfer_done)
        self.worker.start()

    def transfer_done(self, copied, skipped, errors):
        self.log(
            f"\nTask complete. {copied} copied, {skipped} skipped, {errors} error(s)."
        )
        self.set_busy(False)
        self.worker = None

    def closeEvent(self, event):
        self.persist_config()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    window = TransferApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
