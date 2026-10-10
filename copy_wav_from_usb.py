#!/usr/bin/env python3
"""Копира всички .WAV/.wav файлове от USB флашка към ~/Desktop/WAV Files."""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


DESKTOP_DIR = Path.home() / "Desktop"
DEST_DIR = DESKTOP_DIR / "WAV Files"
MEDIA_ROOT = Path("/media") / os.environ.get("USER", Path.home().name)


def list_usb_candidates() -> list[Path]:
    """Типични места за USB в Linux Mint: /media/ПОТРЕБИТЕЛ/ИМЕ_НА_ФЛАШКАТА."""
    found: list[Path] = []
    if MEDIA_ROOT.is_dir():
        for child in sorted(MEDIA_ROOT.iterdir()):
            if child.is_dir() and os.path.ismount(child):
                found.append(child)
            elif child.is_dir():
                # понякога томът е подпапка, която е mountpoint
                for inner in sorted(child.iterdir()):
                    if inner.is_dir() and os.path.ismount(inner):
                        found.append(inner)
    # допълнително: /run/media/USER
    run_media = Path("/run/media") / os.environ.get("USER", Path.home().name)
    if run_media.is_dir():
        for child in sorted(run_media.iterdir()):
            if child.is_dir() and os.path.ismount(child):
                found.append(child)
    # уникални пътища
    uniq: list[Path] = []
    seen = set()
    for p in found:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def iter_wav_files(root: Path):
    root = Path(root)
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".wav"):
                yield Path(dirpath) / name


def unique_dest(dest_dir: Path, filename: str) -> Path:
    dest = dest_dir / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 1
    while True:
        candidate = dest_dir / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Копиране на WAV от USB")
        self.geometry("720x520")
        self.minsize(640, 440)

        self.source_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Избери USB флашка и натисни Старт.")
        self._busy = False

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Папка на USB флашката:").pack(anchor="w")

        row = ttk.Frame(frm)
        row.pack(fill=tk.X, pady=(4, 8))
        self.combo = ttk.Combobox(row, textvariable=self.source_var, state="readonly")
        self.combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text="Опресни", command=self.refresh_usb).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(row, text="Избери папка…", command=self.browse_folder).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(
            frm,
            text=f"Цел: {DEST_DIR}\nТърси само *.wav / *.WAV във всички подпапки.",
        ).pack(anchor="w", pady=(0, 8))

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill=tk.X, pady=(0, 8))
        self.start_btn = ttk.Button(btn_row, text="Старт", command=self.start)
        self.start_btn.pack(side=tk.LEFT)
        ttk.Button(btn_row, text="Отвори целевата папка", command=self.open_dest).pack(side=tk.LEFT, padx=6)

        self.progress = ttk.Progressbar(frm, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(frm, textvariable=self.status_var).pack(anchor="w")

        self.log = tk.Text(frm, height=18, wrap="word")
        self.log.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.refresh_usb()

    def log_line(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def refresh_usb(self) -> None:
        devices = list_usb_candidates()
        values = [str(p) for p in devices]
        self.combo["values"] = values
        if values and not self.source_var.get():
            self.source_var.set(values[0])
        if not values:
            self.status_var.set("Не е открита монтирана USB. Избери папката ръчно.")
        else:
            self.status_var.set(f"Открити устройства: {len(values)}")

    def browse_folder(self) -> None:
        start = str(MEDIA_ROOT) if MEDIA_ROOT.exists() else str(Path.home())
        chosen = filedialog.askdirectory(title="Избери папката на флашката", initialdir=start)
        if chosen:
            self.source_var.set(chosen)
            current = list(self.combo["values"])
            if chosen not in current:
                self.combo["values"] = [chosen] + current

    def open_dest(self) -> None:
        DEST_DIR.mkdir(parents=True, exist_ok=True)
        os.system(f'xdg-open "{DEST_DIR}"')

    def start(self) -> None:
        if self._busy:
            return
        src = self.source_var.get().strip()
        if not src:
            messagebox.showerror("Липсва източник", "Избери USB флашка или папка.")
            return
        src_path = Path(src)
        if not src_path.is_dir():
            messagebox.showerror("Грешка", f"Папката не съществува:\n{src_path}")
            return

        self._busy = True
        self.start_btn.config(state=tk.DISABLED)
        self.log.delete("1.0", tk.END)
        self.progress["value"] = 0
        self.status_var.set("Търсене на WAV файлове…")
        threading.Thread(target=self._work, args=(src_path,), daemon=True).start()

    def _work(self, src_path: Path) -> None:
        try:
            files = list(iter_wav_files(src_path))
            self.after(0, lambda: self.status_var.set(f"Намерени: {len(files)} файла"))
            if not files:
                self.after(0, lambda: messagebox.showinfo("Готово", "Не са намерени WAV файлове."))
                return

            DEST_DIR.mkdir(parents=True, exist_ok=True)
            copied = 0
            skipped = 0
            errors = 0
            total = len(files)

            for i, src_file in enumerate(files, start=1):
                dest_file = unique_dest(DEST_DIR, src_file.name)
                try:
                    shutil.copy2(src_file, dest_file)
                    copied += 1
                    line = f"OK  {src_file}  →  {dest_file.name}"
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    line = f"ГРЕШКА  {src_file}  ({exc})"
                self.after(0, lambda l=line, i=i, total=total: self._update_progress(l, i, total))

            summary = (
                f"Готово. Копирани: {copied}, грешки: {errors}, "
                f"пропуснати: {skipped}.\nПапка: {DEST_DIR}"
            )
            self.after(0, lambda: self.status_var.set(summary.replace("\n", " ")))
            self.after(0, lambda: messagebox.showinfo("Готово", summary))
        finally:
            self.after(0, self._done)

    def _update_progress(self, line: str, i: int, total: int) -> None:
        self.log_line(line)
        self.progress["maximum"] = total
        self.progress["value"] = i
        self.status_var.set(f"{i} / {total}")

    def _done(self) -> None:
        self._busy = False
        self.start_btn.config(state=tk.NORMAL)


if __name__ == "__main__":
    App().mainloop()
