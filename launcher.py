import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
from core import UnifiedProcessManager, enable_debug_privilege

class AppLauncher(tk.Tk):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.title("Optimus Prime - Control de Módulos")
        self.geometry("450x600")
        self.resizable(False, False)
        
        # Configure style
        self.configure(bg='#f0f0f0')
        
        # Module information with descriptions
        self.module_info = {
            'almacenamiento': ('Almacenamiento', 'Optimización de disco y cache'),
            'gpu': ('GPU', 'Optimización de tarjeta gráfica'),
            'ram': ('RAM', 'Gestión de memoria RAM'),
            'kernel': ('Kernel', 'Optimización del núcleo del sistema'),
            'cpu': ('CPU', 'Gestión de procesador y núcleos'),
            'prioridades': ('Prioridades', 'Control de prioridades de procesos'),
            'energia': ('Energía', 'Administración de energía'),
            'temperatura': ('Temperatura', 'Monitoreo térmico'),
            'servicios': ('Servicios', 'Gestión de servicios de Windows'),
            'redes': ('Redes', 'Optimización de red y TCP/IP'),
            'perfiles': ('Perfiles', 'Perfiles automáticos de optimización'),
            'ajustes_varios': ('Ajustes Varios', 'Optimizaciones generales del sistema'),
        }

        self.modules = {}
        for name in self.module_info.keys():
            self.modules[name] = tk.BooleanVar(value=True)
        
        self.status_labels = {}
        self.create_widgets()

    def create_widgets(self):
        # Header
        header_frame = tk.Frame(self, bg='#2c3e50', height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="⚙️ OPTIMUS PRIME", 
            font=("Segoe UI", 18, "bold"),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(
            header_frame,
            text="Control de Módulos de Optimización",
            font=("Segoe UI", 10),
            bg='#2c3e50',
            fg='#ecf0f1'
        )
        subtitle_label.pack()
        
        # Main content area with scrollbar
        content_frame = tk.Frame(self, bg='#f0f0f0')
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Canvas and scrollbar for modules
        canvas = tk.Canvas(content_frame, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Module checkboxes
        for name, (display_name, description) in self.module_info.items():
            self._create_module_row(scrollable_frame, name, display_name, description)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Button frame
        button_frame = tk.Frame(self, bg='#f0f0f0')
        button_frame.pack(fill='x', padx=10, pady=10)
        
        # Control buttons
        btn_enable_all = tk.Button(
            button_frame,
            text="✓ Activar Todos",
            command=self.enable_all_modules,
            bg='#27ae60',
            fg='white',
            font=("Segoe UI", 10, "bold"),
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        btn_enable_all.pack(side='left', expand=True, fill='x', padx=5)
        
        btn_disable_all = tk.Button(
            button_frame,
            text="✗ Desactivar Todos",
            command=self.disable_all_modules,
            bg='#e74c3c',
            fg='white',
            font=("Segoe UI", 10, "bold"),
            relief='flat',
            padx=15,
            pady=8,
            cursor='hand2'
        )
        btn_disable_all.pack(side='left', expand=True, fill='x', padx=5)
        
        # Status bar
        self.status_bar = tk.Label(
            self,
            text="Sistema funcionando correctamente",
            bg='#34495e',
            fg='white',
            font=("Segoe UI", 9),
            anchor='w',
            padx=10,
            pady=5
        )
        self.status_bar.pack(side='bottom', fill='x')
    
    def _create_module_row(self, parent, name, display_name, description):
        """Create a row for each module with checkbox and status"""
        row_frame = tk.Frame(parent, bg='white', relief='solid', borderwidth=1)
        row_frame.pack(fill='x', pady=3, padx=5)
        
        # Left side: checkbox and info
        left_frame = tk.Frame(row_frame, bg='white')
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=8)
        
        var = self.modules[name]
        cb = tk.Checkbutton(
            left_frame,
            text=f"📦 {display_name}",
            variable=var,
            command=lambda: self.toggle_module(name, var.get()),
            bg='white',
            font=("Segoe UI", 10, "bold"),
            activebackground='white',
            selectcolor='#3498db',
            cursor='hand2'
        )
        cb.pack(anchor='w')
        
        desc_label = tk.Label(
            left_frame,
            text=description,
            bg='white',
            fg='#7f8c8d',
            font=("Segoe UI", 8),
            anchor='w'
        )
        desc_label.pack(anchor='w', padx=20)
        
        # Right side: status indicator
        status_label = tk.Label(
            row_frame,
            text="●",
            bg='white',
            fg='#27ae60',
            font=("Segoe UI", 16),
            padx=10
        )
        status_label.pack(side='right')
        self.status_labels[name] = status_label
    
    def toggle_module(self, name, status):
        """Toggle a specific module on or off"""
        if hasattr(self.manager, 'toggle_module'):
            self.manager.toggle_module(name, status)
            
            # Update status indicator
            if name in self.status_labels:
                color = '#27ae60' if status else '#e74c3c'
                self.status_labels[name].config(fg=color)
            
            # Update status bar
            enabled_count = sum(1 for v in self.modules.values() if v.get())
            total_count = len(self.modules)
            self.status_bar.config(
                text=f"Módulos activos: {enabled_count}/{total_count}"
            )
    
    def enable_all_modules(self):
        """Enable all modules"""
        for name, var in self.modules.items():
            var.set(True)
            self.toggle_module(name, True)
        messagebox.showinfo("Éxito", "Todos los módulos han sido activados")
    
    def disable_all_modules(self):
        """Disable all modules"""
        response = messagebox.askyesno(
            "Confirmar",
            "¿Está seguro de que desea desactivar todos los módulos?"
        )
        if response:
            for name, var in self.modules.items():
                var.set(False)
                self.toggle_module(name, False)
            messagebox.showinfo("Éxito", "Todos los módulos han sido desactivados")

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
