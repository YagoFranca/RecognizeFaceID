import os
import random
import cv2
import pickle
import face_recognition
from datetime import datetime
from supabase import create_client
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk

# --- Supabase config ---
URL = "https://jtqxscwmjjaandwujsxq.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxNDM2MDUsImV4cCI6MjA2NDcxOTYwNX0.OlugtCsxjpHsU6EWjNcJsETj852TDZ0ykQVWFcS9lfo"
KEY_STORAGE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp0cXhzY3dtamphYW5kd3Vqc3hxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTE0MzYwNSwiZXhwIjoyMDY0NzE5NjA1fQ.yPXNbMP0-u3uwBTX8n-ymKIxH0S1mJV9D4TjLRC7DNk"

supabase = create_client(URL, KEY)
supabase_storage = create_client(URL, KEY_STORAGE)

# --- Funções utilitárias ---
def gerar_id_unico():
    return ''.join(random.choices('0123456789', k=6))

def obter_total_atendimentos():
    try:
        resp = supabase.table("FaceAttendenceRealTime") \
                        .select("total_attendance") \
                        .order("total_attendance", desc=True) \
                        .limit(1).execute()
        return resp.data[0]['total_attendance'] + 1 if resp.data else 1
    except Exception as e:
        print("Erro ao obter total:", e)
        return 1

# --- Classe principal da aplicação ---
class FaceRegisterApp:
    def __init__(self, master):
        self.master = master
        master.title("Cadastro Reconhecimento Facial")
        master.configure(bg="#f0f2f5")
        self.centralizar_janela(master, 600, 900)

        # Fonte padrão
        fonte_padrao = ("Segoe UI", 12)
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Título
        self.label_title = tk.Label(master, text="Cadastro Reconhecimento Facial", font=("Segoe UI", 18, "bold"), bg="#f0f2f5", fg="#333")
        self.label_title.pack(pady=(20, 10))

        # Variáveis
        self.name_var = tk.StringVar()
        self.group_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.event_var = tk.StringVar()

        # Entradas
        self.create_label_entry("Nome *", self.name_var)
        self.create_label_entry("Grupo *", self.group_var)
        self.create_label_entry("Telefone *", self.phone_var)
        self.create_label_entry("Evento *", self.event_var)

        # Botão estilizado
        self.start_button = tk.Button(master, text="Salvar & Iniciar Webcam", command=self.salvar_e_iniciar,
                                      bg="#0078D7", fg="white", font=("Segoe UI", 13, "bold"), activebackground="#005A9E")
        self.start_button.pack(pady=20, ipadx=10, ipady=5)

        # Vídeo da webcam
        self.video_label = tk.Label(master, bg="#ccc")
        self.video_label.pack(padx=20, pady=10)
        self.rosto_detectado = False

        # Status
        self.status_label = tk.Label(master, text="", font=fonte_padrao, fg="green", bg="#f0f2f5")
        self.status_label.pack(pady=(10, 0))

        # Variáveis internas
        self.id_unico = None
        self.dados = None
        self.cam = None
        self.total_attendance = 0
        self.capturou = False

    def create_label_entry(self, text, textvar):
        frame = tk.Frame(self.master, bg="#f0f2f5")
        frame.pack(padx=40, pady=6, fill="x")

        label = tk.Label(frame, text=text, font=("Segoe UI", 12), bg="#f0f2f5", anchor="w", width=12)
        label.pack(side="left")

        entry = ttk.Entry(frame, textvariable=textvar, font=("Segoe UI", 12))
        entry.pack(side="right", fill="x", expand=True)

    def centralizar_janela(self, master, largura, altura):
        largura_tela = master.winfo_screenwidth()
        altura_tela = master.winfo_screenheight()
        x = (largura_tela // 2) - (largura // 2)
        y = (altura_tela // 2) - (altura // 2)
        master.geometry(f"{largura}x{altura}+{x}+{y}")

    def salvar_e_iniciar(self):
        name = self.name_var.get().strip()
        group = self.group_var.get().strip()
        phone = self.phone_var.get().strip()
        event = self.event_var.get().strip()

        if not all([name, group, phone, event]):
            messagebox.showerror("Erro", "Preencha todos os campos!")
            return

        self.id_unico = gerar_id_unico()
        self.total_attendance = obter_total_atendimentos()

        self.dados = {
            "id": self.id_unico,
            "name": name,
            "group": group,
            "phone": phone,
            "event": event,
            "total_attendance": self.total_attendance,
            "last_attendance_time": datetime.now().isoformat()
        }

        self.status_label.config(text=f"Total de atendimentos: {self.total_attendance}")

        # Inicia webcam
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            messagebox.showerror("Erro", "Não foi possível abrir a webcam")
            return

        self.capturou = False
        self.atualizar_frame()

    def atualizar_frame(self):
        if not self.cam or not self.cam.isOpened():
            return

        ret, frame = self.cam.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        x1, y1 = w // 4, h // 4
        x2, y2 = 3 * w // 4, 3 * h // 4
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Detectar rosto
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(frame_rgb)
        self.rosto_detectado = False

        for top, right, bottom, left in faces:
            if left > x1 and right < x2 and top > y1 and bottom < y2:
                self.rosto_detectado = True
                break

        if self.rosto_detectado:
            self.status_label.config(text="Rosto detectado! Centralizado!")
        else:
            self.status_label.config(text="Centralize seu rosto no quadrado")

        if self.rosto_detectado and not self.capturou:
            self.capturou = True
            self.master.after(1000, self.capturar_e_enviar)

        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        self.master.after(30, self.atualizar_frame)


    def capturar_e_enviar(self):
        if not self.cam or not self.cam.isOpened():
            return
        ret, frame = self.cam.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        path = f"Images/{self.id_unico}.png"
        os.makedirs("Images", exist_ok=True)
        cv2.imwrite(path, frame)

        try:
            # Upload dados
            supabase.table("FaceAttendenceRealTime").upsert(self.dados).execute()

            # Upload imagem
            with open(path, "rb") as f:
                supabase_storage.storage.from_('storageforphotos') \
                    .upload(f"{self.id_unico}.png", f, file_options={"cacheControl":"3600","x-upsert":"true"})

            self.status_label.config(text="Foto enviada com sucesso!")

            # Atualizar encodings
            self.atualizar_encodings()
            self.status_label.config(text="Foto capturada e enviada com sucesso!")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar dados: {e}")

        # Para a webcam
        self.cam.release()
        self.cam = None

    def atualizar_encodings(self):
        imgs, ids = [], []
        for fn in os.listdir('Images'):
            if fn.endswith('.png'):
                img = cv2.imread(os.path.join('Images', fn))
                imgs.append(img)
                ids.append(fn[:-4])

        encs = []
        for img in imgs:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            enc = face_recognition.face_encodings(rgb_img)
            if enc:
                encs.append(enc[0])

        with open("EncodeFile.p", "wb") as f:
            pickle.dump([encs, ids], f)

# --- Rodar a aplicação ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FaceRegisterApp(root)
    root.mainloop()
