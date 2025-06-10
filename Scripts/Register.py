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
        self.configurar_janela()
        self.configurar_estilos()
        self.criar_interface()

        # Variáveis internas
        self.id_unico = None
        self.dados = None
        self.cam = None
        self.total_attendance = 0
        self.capturou = False
        self.rosto_detectado = False

    def configurar_janela(self):
        """Configura a janela principal"""
        self.master.title("272Club - Sistema de Cadastro Facial")
        self.master.configure(bg="#1a1a2e")
        self.centralizar_janela(self.master, 1100, 700)
        self.master.resizable(False, False)

        # Ícone da janela (se disponível)
        try:
            self.master.iconbitmap("icon.ico")
        except:
            pass

    def configurar_estilos(self):
        """Configura os estilos modernos do ttk"""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Configurar estilo dos Entry
        self.style.configure("Modern.TEntry",
                             fieldbackground="#2d2d44",
                             borderwidth=2,
                             focuscolor="#00d4ff",
                             insertcolor="white")

        # Configurar estilo dos Labels
        self.style.configure("Modern.TLabel",
                             background="#1a1a2e",
                             foreground="white",
                             font=("Segoe UI", 11))

    def criar_interface(self):
        """Cria toda a interface da aplicação"""
        # Container principal
        main_container = tk.Frame(self.master, bg="#1a1a2e")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        self.criar_header(main_container)
        self.criar_corpo_principal(main_container)

    def criar_header(self, parent):
        """Cria o cabeçalho da aplicação"""
        header_frame = tk.Frame(parent, bg="#16213e", height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)

        # Título principal
        title_label = tk.Label(
            header_frame,
            text="🎯 272 Club",
            font=("Segoe UI", 24, "bold"),
            bg="#16213e",
            fg="#00d4ff"
        )
        title_label.pack(side="left", padx=20, pady=20)

        # Subtítulo
        subtitle_label = tk.Label(
            header_frame,
            text="Sistema Avançado de Reconhecimento Facial",
            font=("Segoe UI", 12),
            bg="#16213e",
            fg="#a0a0a0"
        )
        subtitle_label.pack(side="left", padx=(0, 20), pady=25)

    def criar_corpo_principal(self, parent):
        """Cria o corpo principal com formulário e webcam"""
        body_frame = tk.Frame(parent, bg="#1a1a2e")
        body_frame.pack(fill="both", expand=True)

        # Frame esquerdo - Formulário
        self.criar_formulario(body_frame)

        # Frame direito - Webcam
        self.criar_area_webcam(body_frame)

    def criar_formulario(self, parent):
        """Cria o formulário de cadastro"""
        left_frame = tk.Frame(parent, bg="#16213e", width=400)
        left_frame.pack(side="left", fill="y", padx=(0, 20))
        left_frame.pack_propagate(False)

        # Título do formulário
        form_title = tk.Label(
            left_frame,
            text="📝 Dados do Usuário",
            font=("Segoe UI", 18, "bold"),
            bg="#16213e",
            fg="white"
        )
        form_title.pack(pady=(30, 20))

        # Container dos campos
        fields_container = tk.Frame(left_frame, bg="#16213e")
        fields_container.pack(fill="x", padx=30)

        # Variáveis
        self.name_var = tk.StringVar()
        self.group_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.event_var = tk.StringVar()

        # Criar campos
        self.criar_campo_moderno(fields_container, "👤 Nome Completo", self.name_var)
        self.criar_campo_moderno(fields_container, "👥 Grupo", self.group_var)
        self.criar_campo_moderno(fields_container, "📱 Telefone", self.phone_var)
        self.criar_campo_moderno(fields_container, "🎪 Evento", self.event_var)

        # Botão principal
        self.criar_botao_principal(left_frame)

        # Status
        self.status_label = tk.Label(
            left_frame,
            text="💡 Preencha todos os campos para começar",
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#00d4ff",
            wraplength=350,
            justify="center"
        )
        self.status_label.pack(pady=20)

    def criar_campo_moderno(self, parent, label_text, var):
        """Cria um campo de entrada moderno"""
        field_frame = tk.Frame(parent, bg="#16213e")
        field_frame.pack(fill="x", pady=12)

        # Label
        label = tk.Label(
            field_frame,
            text=label_text,
            font=("Segoe UI", 11, "bold"),
            bg="#16213e",
            fg="white",
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 5))

        # Entry moderno
        entry = tk.Entry(
            field_frame,
            textvariable=var,
            font=("Segoe UI", 12),
            bg="#2d2d44",
            fg="white",
            insertbackground="white",
            bd=0,
            highlightthickness=2,
            highlightcolor="#00d4ff",
            highlightbackground="#444"
        )
        entry.pack(fill="x", ipady=8)

        # Efeito de foco
        def on_focus_in(event):
            entry.config(highlightbackground="#00d4ff")

        def on_focus_out(event):
            entry.config(highlightbackground="#444")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def criar_botao_principal(self, parent):
        """Cria o botão principal estilizado"""
        button_frame = tk.Frame(parent, bg="#16213e")
        button_frame.pack(pady=20)

        self.start_button = tk.Button(
            button_frame,
            text="Iniciar Captura Facial",
            command=self.salvar_e_iniciar,
            font=("Segoe UI", 14, "bold"),
            bg="#00d4ff",
            fg="white",
            activebackground="#0099cc",
            activeforeground="white",
            bd=0,
            cursor="hand2",
            relief="flat"
        )
        self.start_button.pack(ipadx=30, ipady=12)

        # Efeito hover
        def on_enter(event):
            self.start_button.config(bg="#0099cc")

        def on_leave(event):
            self.start_button.config(bg="#00d4ff")

        self.start_button.bind("<Enter>", on_enter)
        self.start_button.bind("<Leave>", on_leave)

    def criar_area_webcam(self, parent):
        """Cria a área da webcam"""
        right_frame = tk.Frame(parent, bg="#16213e")
        right_frame.pack(side="right", fill="both", expand=True)

        # Título da webcam
        webcam_title = tk.Label(
            right_frame,
            text="📷 Captura Facial",
            font=("Segoe UI", 18, "bold"),
            bg="#16213e",
            fg="white"
        )
        webcam_title.pack(pady=(30, 20))

        # Container da webcam com borda
        webcam_container = tk.Frame(right_frame, bg="#00d4ff", relief="flat", bd=3)
        webcam_container.pack(padx=30, pady=20, fill="both", expand=True)

        # Label da webcam
        self.video_label = tk.Label(
            webcam_container,
            bg="#2d2d44",
            text="🎥\n\nWebcam será ativada\napós preencher os dados",
            font=("Segoe UI", 14),
            fg="#888",
            justify="center"
        )
        self.video_label.pack(fill="both", expand=True, padx=3, pady=3)

        # Instruções
        instructions = tk.Label(
            right_frame,
            text="💡 Posicione seu rosto no centro da tela quando a webcam ativar",
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#a0a0a0",
            wraplength=400,
            justify="center"
        )
        instructions.pack(pady=20)

    def centralizar_janela(self, master, largura, altura):
        """Centraliza a janela na tela"""
        largura_tela = master.winfo_screenwidth()
        altura_tela = master.winfo_screenheight()
        x = (largura_tela // 2) - (largura // 2)
        y = (altura_tela // 2) - (altura // 2)
        master.geometry(f"{largura}x{altura}+{x}+{y}")

    def limpar_campos(self):
        """Limpa todos os campos do formulário"""
        self.name_var.set("")
        self.group_var.set("")
        self.phone_var.set("")
        self.event_var.set("")
        self.status_label.config(
            text="✨ Campos limpos! Pronto para novo cadastro",
            fg="#00ff88"
        )

    def resetar_webcam(self):
        """Reseta o estado da webcam"""
        self.video_label.config(
            image="",
            text="🎥\n\nWebcam será ativada\napós preencher os dados",
            fg="#888"
        )
        self.video_label.imgtk = None
        self.rosto_detectado = False
        self.capturou = False
        self.id_unico = None
        self.dados = None
        self.total_attendance = 0

    def salvar_e_iniciar(self):
        """Valida dados e inicia captura"""
        name = self.name_var.get().strip()
        group = self.group_var.get().strip()
        phone = self.phone_var.get().strip()
        event = self.event_var.get().strip()

        if not all([name, group, phone, event]):
            self.mostrar_erro("❌ Todos os campos são obrigatórios!")
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

        self.status_label.config(
            text=f"📊 Cadastro #{self.total_attendance} • Iniciando webcam...",
            fg="#00d4ff"
        )

        # Inicia webcam
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            self.mostrar_erro("❌ Não foi possível acessar a webcam")
            return

        self.capturou = False
        self.atualizar_frame()

    def atualizar_frame(self):
        """Atualiza o frame da webcam"""
        if not self.cam or not self.cam.isOpened():
            return

        ret, frame = self.cam.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        x1, y1 = w // 4, h // 4
        x2, y2 = 3 * w // 4, 3 * h // 4

        # Desenha retângulo moderno
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 212, 255), 3)
        cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (255, 255, 255), 1)

        # Detectar rosto
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_locations(frame_rgb)
        self.rosto_detectado = False

        for top, right, bottom, left in faces:
            if left > x1 and right < x2 and top > y1 and bottom < y2:
                self.rosto_detectado = True
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                break

        # Atualiza status
        if self.rosto_detectado:
            self.status_label.config(
                text="✅ Rosto detectado! Capturando em 3 segundos...",
                fg="#00ff88"
            )
        else:
            self.status_label.config(
                text="🎯 Posicione seu rosto no quadrado azul",
                fg="#ffaa00"
            )

        if self.rosto_detectado and not self.capturou:
            self.capturou = True
            self.master.after(3000, self.capturar_e_enviar)

        # Atualiza imagem
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk, text="")

        self.master.after(30, self.atualizar_frame)

    def capturar_e_enviar(self):
        """Captura foto e envia dados"""
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
            self.status_label.config(
                text="☁️ Enviando dados para o servidor...",
                fg="#00d4ff"
            )

            # Upload dados
            supabase.table("FaceAttendenceRealTime").upsert(self.dados).execute()

            # Upload imagem
            with open(path, "rb") as f:
                supabase_storage.storage.from_('storageforphotos') \
                    .upload(f"{self.id_unico}.png", f, file_options={"cacheControl": "3600", "x-upsert": "true"})

            # Atualizar encodings
            self.atualizar_encodings()

            self.status_label.config(
                text="🎉 Cadastro realizado com sucesso!",
                fg="#00ff88"
            )

        except Exception as e:
            self.mostrar_erro(f"❌ Erro ao enviar dados: {str(e)}")
            self.cam.release()
            self.cam = None
            return

        # Para a webcam
        self.cam.release()
        self.cam = None

        # Pergunta sobre novo cadastro
        self.master.after(500, self.perguntar_novo_cadastro)

    def perguntar_novo_cadastro(self):
        """Pergunta sobre novo cadastro com diálogo moderno"""
        resposta = messagebox.askyesno(
            "🎉 Cadastro Concluído!",
            "Cadastro facial realizado com sucesso!\n\n" +
            "Deseja realizar um novo cadastro?",
            icon="question"
        )

        if resposta:
            self.limpar_campos()
            self.resetar_webcam()
        else:
            fechar = messagebox.askyesno(
                "👋 Finalizar Sessão",
                "Deseja fechar o aplicativo?",
                icon="question"
            )
            if fechar:
                self.master.quit()
                self.master.destroy()

    def atualizar_encodings(self):
        """Atualiza arquivo de encodings"""
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

    def mostrar_erro(self, mensagem):
        """Mostra mensagem de erro estilizada"""
        self.status_label.config(text=mensagem, fg="#ff4444")
        messagebox.showerror("Erro", mensagem.replace("❌ ", ""))


# --- Rodar a aplicação ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FaceRegisterApp(root)
    root.mainloop()