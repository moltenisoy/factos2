import tkinter as tk
from tkinter import ttk
import threading
import sys
from core import UnifiedProcessManager, enable_debug_privilege

class AppLauncher(tk.Tk):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.title("Optimus Prime Launcher")
        self.geometry("300x450")

        self.modules = {
            'almacenamiento': tk.BooleanVar(value=True),
            'gpu': tk.BooleanVar(value=True),
            'ram': tk.BooleanVar(value=True),
            'kernel': tk.BooleanVar(value=True),
            'cpu': tk.BooleanVar(value=True),
            'prioridades': tk.BooleanVar(value=True),
            'energia': tk.BooleanVar(value=True),
            'temperatura': tk.BooleanVar(value=True),
            'servicios': tk.BooleanVar(value=True),
            'redes': tk.BooleanVar(value=True),
            'perfiles': tk.BooleanVar(value=True),
            'ajustes_varios': tk.BooleanVar(value=True),
        }

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="Módulos de Optimización:", font=("Segoe UI", 12, "bold")).pack(pady=5, anchor='w')

        for name, var in self.modules.items():
            cb = ttk.Checkbutton(
                main_frame,
                text=name.capitalize(),
                variable=var,
                command=lambda n=name, v=var: self.toggle_module(n, v.get())
            )
            cb.pack(anchor='w', padx=10)

    def toggle_module(self, name, status):
        if hasattr(self.manager, 'toggle_module'):
            self.manager.toggle_module(name, status)

def main():
    if not enable_debug_privilege():
        sys.exit(1)
    
    manager = UnifiedProcessManager()
    
    manager_thread = threading.Thread(target=manager.run, daemon=True, name="ProcessManager")
    manager_thread.start()

    app = AppLauncher(manager)
    app.mainloop()

if __name__ == "__main__":
    main()
