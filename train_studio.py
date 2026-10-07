"""Entry point for launching TrainStudio directly."""

from __future__ import annotations

import customtkinter as ctk

from src.fall_detection.studio.ui import TrainStudioApp


def main():
    root = ctk.CTk()
    root.withdraw()
    app = TrainStudioApp(root)
    app.protocol("WM_DELETE_WINDOW", lambda: (app._on_close(), root.destroy()))
    app.mainloop()


if __name__ == "__main__":
    main()
