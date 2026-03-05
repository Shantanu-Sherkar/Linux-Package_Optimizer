"""
Linux Package Optimizer — Entry Point
Requires only Python 3.11+ and tkinter (ships with Python).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
