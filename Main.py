import tkinter as tk
from tkinter import ttk
import subprocess
import os

class StartScreen(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Registro")
        self.geometry("400x200")

        ttk.Label(self, text="Bem-vindo ao Sistema", font=("Helvetica", 16)).pack(pady=20)
        ttk.Button(self, text="🔍 Verificar Registro", command=self.open_main).pack(pady=10)
        ttk.Button(self, text="📝 Novo Registro", command=self.open_register).pack(pady=10)

        self.process = None  # armazenar processo aberto

    def open_main(self):
        self.open_script("FaceRecognition.py")

    def open_register(self):
        self.open_script("Register.py")

    def open_script(self, script_name):
        if self.process and self.process.poll() is None:
            tk.messagebox.showinfo("Aviso", "Já existe uma janela aberta. Feche-a antes de abrir outra.")
            return
        python_cmd = "python" if os.name == "nt" else "python3"
        self.process = subprocess.Popen([python_cmd, script_name])

if __name__ == "__main__":
    app = StartScreen()
    app.mainloop()
