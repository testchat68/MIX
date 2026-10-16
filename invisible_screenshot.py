#!/usr/bin/env python3
"""
Screenshot с 5 секунди закъснение – без прозорци и съобщения.
След паузата се появява селекция на целия екран.
Файлът се записва на Десктопа.
"""
import subprocess
import time
from datetime import datetime
from pathlib import Path

DELAY_SECONDS = 5


def main():
    time.sleep(DELAY_SECONDS)

    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = desktop / f"screenshot_{timestamp}.png"

    subprocess.run(
        ["gnome-screenshot", "-a", "-f", str(filename)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    main()
