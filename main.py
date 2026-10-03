import os
import sys

# Ensure the root directory is on the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from mobile_server import start_mobile_server_background

def main():
    try:
        # Start offline mobile companion server on LAN in background daemon thread
        try:
            mobile_url = start_mobile_server_background(8080)
            print(f"[MediTrack] Mobile Companion App active at {mobile_url}")
        except Exception as ex:
            print("[MediTrack] Mobile server auto-start skipped:", ex)

        app = MainWindow()
        app.mainloop()
    except Exception as e:
        print("Application failed to start:", str(e))
        import traceback
        traceback.print_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("MediTrack Startup Error", f"Application failed to start:\n\n{str(e)}")
            root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    main()
