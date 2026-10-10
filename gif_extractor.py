#!/usr/bin/env python3
"""
GIF Frame Extractor & Viewer
Програма за преглед на GIF файлове и извличане на кадри.
За Linux Mint 22.2 (и други Linux дистрибуции с Python 3).

Зависимости:
    sudo apt update
    sudo apt install python3-tk python3-pil
    # или: pip3 install pillow

Стартиране:
    python3 gif_extractor.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageSequence
import os
import math


class GIFViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GIF Frame Extractor")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # Данни
        self.current_path = None
        self.frames = []          # списък от PIL.Image
        self.thumb_refs = []      # за да не се изтриват PhotoImage

        self._build_ui()

    def _build_ui(self):
        # ===== Горна лента с бутони =====
        top = ttk.Frame(self.root, padding=6)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top, text="Избери папка", command=self.select_folder).pack(side=tk.LEFT, padx=4)
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(top, text="Auto (всички кадри)", command=self.extract_auto).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="10 кадъра", command=lambda: self.extract_n(10)).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="20 кадъра", command=lambda: self.extract_n(20)).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="30 кадъра", command=lambda: self.extract_n(30)).pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="Изберете папка с GIF файлове")
        ttk.Label(top, textvariable=self.status_var).pack(side=tk.RIGHT, padx=10)

        # ===== Основен панел =====
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # --- Лява част: тумбнейли ---
        left = ttk.Frame(paned, width=180)
        paned.add(left, weight=0)

        ttk.Label(left, text="GIF файлове", font=("Segoe UI", 10, "bold")).pack(pady=(4, 2))

        self.thumb_canvas = tk.Canvas(left, bg="#f0f0f0", highlightthickness=0)
        vscroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=vscroll.set)

        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.thumb_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.thumb_inner = ttk.Frame(self.thumb_canvas)
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor="nw")

        self.thumb_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(
            scrollregion=self.thumb_canvas.bbox("all")))
        self.thumb_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.thumb_canvas.bind("<Button-4>", self._on_mousewheel)
        self.thumb_canvas.bind("<Button-5>", self._on_mousewheel)

        # --- Дясна част: голям изглед + плъзгач ---
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self.display_label = ttk.Label(right, text="Изберете GIF отляво", anchor="center")
        self.display_label.pack(fill=tk.BOTH, expand=True, pady=10)

        # Плъзгач и информация
        slider_frame = ttk.Frame(right)
        slider_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.frame_info = ttk.Label(slider_frame, text="Кадър: — / —")
        self.frame_info.pack(side=tk.LEFT, padx=(0, 10))

        self.slider = ttk.Scale(
            slider_frame,
            from_=0, to=0,
            orient=tk.HORIZONTAL,
            command=self.on_slider_move
        )
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.thumb_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.thumb_canvas.yview_scroll(1, "units")

    def select_folder(self):
        folder = filedialog.askdirectory(title="Изберете папка с GIF файлове")
        if not folder:
            return
        self.load_gifs_from_folder(folder)

    def load_gifs_from_folder(self, folder):
        # Изчистваме старите тумбнейли
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self.thumb_refs.clear()

        gifs = sorted(
            [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(".gif")],
            key=lambda p: os.path.basename(p).lower()
        )

        if not gifs:
            self.status_var.set("Няма GIF файлове в папката")
            messagebox.showinfo("Инфо", "В избраната папка няма GIF файлове.")
            return

        self.status_var.set(f"Заредени {len(gifs)} GIF файла")

        for path in gifs:
            self._add_thumbnail(path)

        self.thumb_inner.update_idletasks()
        self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))

    def _add_thumbnail(self, path):
        try:
            with Image.open(path) as img:
                img.seek(0)
                thumb = img.copy()
                thumb.thumbnail((120, 120), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(thumb)
                self.thumb_refs.append(photo)

                frame = ttk.Frame(self.thumb_inner)
                frame.pack(pady=4, padx=6, fill=tk.X)

                btn = tk.Button(
                    frame,
                    image=photo,
                    command=lambda p=path: self.load_gif(p),
                    relief="flat",
                    bd=1,
                    highlightthickness=1
                )
                btn.pack()

                name = os.path.basename(path)
                if len(name) > 18:
                    name = name[:15] + "..."
                ttk.Label(frame, text=name, font=("Segoe UI", 8)).pack()

        except Exception as e:
            print(f"Грешка при тумбнейл {path}: {e}")

    def load_gif(self, path):
        self.current_path = path
        self.frames.clear()

        try:
            with Image.open(path) as img:
                for frame in ImageSequence.Iterator(img):
                    # Копираме и конвертираме, за да избегнем проблеми с паметта и режима
                    self.frames.append(frame.copy().convert("RGBA"))

            total = len(self.frames)
            if total == 0:
                raise ValueError("GIF-ът няма кадри")

            self.slider.config(from_=0, to=max(0, total - 1))
            self.slider.set(0)
            self.show_frame(0)
            self.status_var.set(f"{os.path.basename(path)}  •  {total} кадъра")

        except Exception as e:
            messagebox.showerror("Грешка", f"Не мога да отворя GIF:\n{e}")
            self.frames.clear()
            self.display_label.config(image="", text="Грешка при зареждане")

    def show_frame(self, index):
        if not self.frames:
            return
        index = int(round(float(index)))
        index = max(0, min(index, len(self.frames) - 1))

        frame = self.frames[index]
        display = frame.copy()
        # Ограничаваме размера за удобен преглед
        display.thumbnail((700, 550), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display)

        self.display_label.config(image=photo, text="")
        self.display_label.image = photo  # задължително задържане на референция

        self.frame_info.config(text=f"Кадър: {index + 1} / {len(self.frames)}")

    def on_slider_move(self, value):
        self.show_frame(value)

    def extract_auto(self):
        self._extract(None)

    def extract_n(self, n):
        self._extract(n)

    def _extract(self, n):
        if not self.current_path or not self.frames:
            messagebox.showwarning("Няма GIF", "Първо изберете GIF файл от тумбнейлите.")
            return

        total = len(self.frames)

        if n is None or n >= total:
            indices = list(range(total))
            suffix = "all_frames"
        else:
            if n <= 1:
                indices = [0]
            else:
                # Равномерно разпределени кадри
                indices = [int(round(i * (total - 1) / (n - 1))) for i in range(n)]
            suffix = f"{n}_frames"

        base = os.path.splitext(os.path.basename(self.current_path))[0]
        out_dir = os.path.join(os.path.dirname(self.current_path), f"{base}_{suffix}")
        os.makedirs(out_dir, exist_ok=True)

        for i, idx in enumerate(indices):
            frame = self.frames[idx]
            # Записваме като PNG (без загуба)
            frame.save(os.path.join(out_dir, f"frame_{i + 1:04d}.png"))

        messagebox.showinfo(
            "Готово",
            f"Записани {len(indices)} кадъра в:\n{out_dir}"
        )
        self.status_var.set(f"Извлечени {len(indices)} кадъра → {os.path.basename(out_dir)}")


def main():
    root = tk.Tk()
    # По-модерен вид
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    app = GIFViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
