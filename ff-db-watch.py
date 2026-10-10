#!/usr/bin/env python3
"""Следи Firefox IndexedDB / sqlite WAL. Бутонът показва сбора до момента."""

import os
import time
import tkinter as tk
from tkinter import scrolledtext

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, ".mozilla", "firefox")
INTERVAL = 1.0


def profiles():
    if not os.path.isdir(ROOT):
        return []
    out = []
    for name in os.listdir(ROOT):
        storage = os.path.join(ROOT, name, "storage")
        if os.path.isdir(storage):
            out.append(storage)
        base = os.path.join(ROOT, name)
        if os.path.isdir(base) and name not in ("Crash Reports", "Pending Pings", "Profile Groups"):
            out.append(base)
    return out


def interesting(path):
    low = path.lower()
    if "/storage/" in low and low.endswith((".sqlite", ".sqlite-wal", ".sqlite-shm")):
        return True
    base = os.path.basename(low)
    return base in {
        "cookies.sqlite", "cookies.sqlite-wal",
        "places.sqlite", "places.sqlite-wal",
        "favicons.sqlite", "favicons.sqlite-wal",
        "webappsstore.sqlite", "webappsstore.sqlite-wal",
        "permissions.sqlite", "permissions.sqlite-wal",
    }


def site_of(path):
    parts = path.split(os.sep)
    if "storage" in parts and "default" in parts:
        i = parts.index("default")
        if i + 1 < len(parts):
            return parts[i + 1]
    return os.path.basename(path)


class Watch:
    def __init__(self):
        self.prev = {}
        self.events = {}
        self.bytes = {}
        self.started = time.time()
        self.last_show = self.started

    def scan(self):
        seen = set()
        for base in profiles():
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in ("cache2", "startupCache", "thumbnails")]
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    if not interesting(path):
                        continue
                    seen.add(path)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    size, mtime = st.st_size, st.st_mtime
                    old = self.prev.get(path)
                    key = site_of(path)
                    if old is None:
                        self.prev[path] = (size, mtime)
                        continue
                    old_size, old_mtime = old
                    if size != old_size or mtime != old_mtime:
                        self.events[key] = self.events.get(key, 0) + 1
                        if size > old_size:
                            self.bytes[key] = self.bytes.get(key, 0) + (size - old_size)
                        self.prev[path] = (size, mtime)
        for path in list(self.prev):
            if path not in seen:
                del self.prev[path]

    def report(self):
        now = time.time()
        lines = [
            "от старта: %d мин    от миналия бутон: %d мин" % (
                (now - self.started) / 60, (now - self.last_show) / 60),
            "записът е дописаният обем (WAL расте). свиването при checkpoint не се вади.",
            "",
            "%8s  %10s  %s" % ("пъти", "записано", "база"),
        ]
        keys = set(self.events) | set(self.bytes)
        rows = sorted(keys, key=lambda k: self.bytes.get(k, 0), reverse=True)
        if not rows:
            lines.append("(още няма мърдане)")
        for key in rows:
            n = self.events.get(key, 0)
            b = self.bytes.get(key, 0)
            if b >= 1024 * 1024:
                size = "%.1f MB" % (b / 1024 / 1024)
            else:
                size = "%.0f KB" % (b / 1024)
            lines.append("%8d  %10s  %s" % (n, size, key))
        self.last_show = now
        return "\n".join(lines)


def main():
    watch = Watch()
    root = tk.Tk()
    root.title("Firefox бази — запис")
    root.geometry("920x520")
    box = scrolledtext.ScrolledText(root, font=("DejaVu Sans Mono", 10))
    box.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh():
        text = watch.report()
        box.delete("1.0", "end")
        box.insert("end", text)
        with open(os.path.join(HOME, "ff-db-watch.txt"), "w", encoding="utf-8") as fh:
            fh.write(text + "\n")

    def copy_report():
        text = box.get("1.0", "end-1c")
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()

    bar = tk.Frame(root)
    bar.pack(pady=6)
    tk.Button(bar, text="Покажи до момента", command=refresh, height=2).pack(side="left", padx=6)
    tk.Button(bar, text="Копирай", command=copy_report, height=2).pack(side="left", padx=6)

    def tick():
        watch.scan()
        root.after(int(INTERVAL * 1000), tick)

    tick()
    root.mainloop()


if __name__ == "__main__":
    main()
