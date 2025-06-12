"""
Sistema Integrado de Registro com Banco Local e Sincronização
Módulo: Aplicação Principal Offline-First
Autor: Yago França
"""

import os
import random
import cv2
import pickle
import face_recognition
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import time
from local_database import LocalDatabase, serialize_encoding, deserialize_encoding
from sync_manager import create_sync_manager_from_config


def gerar_id_unico():
    """Gera um ID único de 6 dígitos"""
    return ''.join(random.choices('0123456789', k=6))


class OfflineFaceRegisterApp:
    """Aplicação de registro facial com suporte offline e sincronização"""

    def __init__(self, master):
        self.master = master
        self.configurar_janela()
        self.configurar_estilos()

        # Inicializar banco local e sincronização
        self.local_db = LocalDatabase()
        self.sync_manager = create_sync_manager_from_config()

        # Variáveis internas
        self.id_unico = None
        self.dados = None
        self.cam = None
        self.capturou = False
        self.rosto_detectado = False

        # Iniciar sincronização automática em background
        self.auto_sync_enabled = True
        self.start_auto_sync()

        self.criar_interface()

    def configurar_janela(self):
        """Configura a janela principal"""
        self.master.title("272Club - Sistema de Cadastro Facial (Offline-First)")
        self.master.configure(bg="#1a1a2e")
        self.centralizar_janela(self.master, 1200, 750)
        self.master.resizable(False, False)

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
        self.criar_status_bar(main_container)

    def criar_header(self, parent):
        """Cria o cabeçalho da aplicação"""
        header_frame = tk.Frame(parent, bg="#16213e", height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)

        # Título principal
        title_label = tk.Label(
            header_frame,
            text="🎯 272 Club (Offline-First)",
            font=("Segoe UI", 24, "bold"),
            bg="#16213e",
            fg="#00d4ff"
        )
        title_label.pack(side="left", padx=20, pady=20)

        # Status de conexão
        self.connection_status = tk.Label(
            header_frame,
            text="🔄 Verificando conexão...",
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#ffaa00"
        )
        self.connection_status.pack(side="right", padx=20, pady=25)

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
        left_frame = tk.Frame(parent, bg="#16213e", width=450)
        left_frame.pack(side="left", fill="y", padx=(0, 20))
        left_frame.pack_propagate(False)

        # Título do formulário
        form_title = tk.Label(
            left_frame,
            text="📝 Dados do Usuário (Modo Offline)",
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
        #self.criar_campo_moderno(fields_container, "🎪 Evento", self.event_var)

        # Botões
        self.criar_botoes(left_frame)

        # Status
        self.status_label = tk.Label(
            left_frame,
            text="💡 Preencha todos os campos para começar",
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#00d4ff",
            wraplength=400,
            justify="center"
        )
        self.status_label.pack(pady=20)

    def criar_campo_moderno(self, parent, label_text, var):
        """Cria um campo de entrada moderno"""
        field_frame = tk.Frame(parent, bg="#16213e")
        field_frame.pack(fill="x", pady=8)

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
        entry.pack(fill="x", ipady=6)

        # Efeito de foco
        def on_focus_in(event):
            entry.config(highlightbackground="#00d4ff")

        def on_focus_out(event):
            entry.config(highlightbackground="#444")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def criar_botoes(self, parent):
        """Cria os botões da aplicação"""
        button_frame = tk.Frame(parent, bg="#16213e")
        button_frame.pack(pady=15)

        # Botão principal
        self.start_button = tk.Button(
            button_frame,
            text="Iniciar Captura Facial",
            command=self.salvar_e_iniciar,
            font=("Segoe UI", 12, "bold"),
            bg="#00d4ff",
            fg="white",
            activebackground="#0099cc",
            activeforeground="white",
            bd=0,
            cursor="hand2",
            relief="flat"
        )
        self.start_button.pack(ipadx=25, ipady=10, pady=5)

        # Botão de sincronização manual
        self.sync_button = tk.Button(
            button_frame,
            text="🔄 Sincronizar Agora",
            command=self.sincronizar_manual,
            font=("Segoe UI", 10, "bold"),
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            bd=0,
            cursor="hand2",
            relief="flat"
        )
        self.sync_button.pack(ipadx=20, ipady=8, pady=5)

        # Botão para ver registros locais
        self.view_button = tk.Button(
            button_frame,
            text="📋 Ver Registros Locais",
            command=self.mostrar_registros_locais,
            font=("Segoe UI", 10, "bold"),
            bg="#6c757d",
            fg="white",
            activebackground="#5a6268",
            activeforeground="white",
            bd=0,
            cursor="hand2",
            relief="flat"
        )
        self.view_button.pack(ipadx=20, ipady=8, pady=5)

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

    def criar_status_bar(self, parent):
        """Cria a barra de status"""
        status_frame = tk.Frame(parent, bg="#16213e", height=40)
        status_frame.pack(fill="x", pady=(20, 0))
        status_frame.pack_propagate(False)

        # Status do banco local
        self.db_status = tk.Label(
            status_frame,
            text="💾 Banco Local: Pronto",
            font=("Segoe UI", 9),
            bg="#16213e",
            fg="#00ff88"
        )
        self.db_status.pack(side="left", padx=20, pady=10)

        # Status de sincronização
        self.sync_status = tk.Label(
            status_frame,
            text="🔄 Sincronização: Aguardando",
            font=("Segoe UI", 9),
            bg="#16213e",
            fg="#ffaa00"
        )
        self.sync_status.pack(side="right", padx=20, pady=10)

    def centralizar_janela(self, master, largura, altura):
        """Centraliza a janela na tela"""
        largura_tela = master.winfo_screenwidth()
        altura_tela = master.winfo_screenheight()
        x = (largura_tela // 2) - (largura // 2)
        y = (altura_tela // 2) - (altura // 2)
        master.geometry(f"{largura}x{altura}+{x}+{y}")

    def start_auto_sync(self):
        """Inicia sincronização automática em background"""

        def auto_sync_worker():
            while self.auto_sync_enabled:
                try:
                    # Verificar conexão
                    has_internet = self.sync_manager.check_internet_connection()

                    # Atualizar status de conexão na UI
                    self.master.after(0, self.update_connection_status, has_internet)

                    if has_internet:
                        # Fazer sincronização automática a cada 30 segundos
                        result = self.sync_manager.full_sync()
                        self.master.after(0, self.update_sync_status, result)

                    # Aguardar 30 segundos antes da próxima verificação
                    time.sleep(30)

                except Exception as e:
                    print(f"Erro na sincronização automática: {e}")
                    time.sleep(30)

        # Iniciar thread de sincronização
        sync_thread = threading.Thread(target=auto_sync_worker, daemon=True)
        sync_thread.start()

    def update_connection_status(self, has_internet):
        """Atualiza o status de conexão na UI"""
        if has_internet:
            self.connection_status.config(
                text="🌐 Online",
                fg="#00ff88"
            )
        else:
            self.connection_status.config(
                text="📴 Offline",
                fg="#ff6b6b"
            )

    def update_sync_status(self, sync_result):
        """Atualiza o status de sincronização na UI"""
        if sync_result['status'] == 'success':
            uploads = sync_result['uploads_success']
            downloads = sync_result['downloads']
            self.sync_status.config(
                text=f"✅ Sync: ↑{uploads} ↓{downloads}",
                fg="#00ff88"
            )
        else:
            self.sync_status.config(
                text="❌ Sync: Erro",
                fg="#ff6b6b"
            )

    def sincronizar_manual(self):
        """Executa sincronização manual"""

        def sync_worker():
            try:
                self.sync_button.config(state="disabled", text="🔄 Sincronizando...")
                result = self.sync_manager.full_sync()

                # Atualizar UI
                self.master.after(0, self.update_sync_status, result)
                self.master.after(0, lambda: self.sync_button.config(
                    state="normal", text="🔄 Sincronizar Agora"
                ))

                # Mostrar resultado
                if result['status'] == 'success':
                    message = f"Sincronização concluída!\n\nUploads: {result['uploads_success']}\nDownloads: {result['downloads']}"
                    self.master.after(0, lambda: messagebox.showinfo("Sincronização", message))
                else:
                    self.master.after(0, lambda: messagebox.showerror("Erro", result['message']))

            except Exception as e:
                self.master.after(0, lambda: messagebox.showerror("Erro", f"Erro na sincronização: {e}"))
                self.master.after(0, lambda: self.sync_button.config(
                    state="normal", text="🔄 Sincronizar Agora"
                ))

        # Executar em thread separada
        threading.Thread(target=sync_worker, daemon=True).start()

    def mostrar_registros_locais(self):
        """Mostra uma janela com os registros locais"""
        registros = self.local_db.get_all_registrations()
        stats = self.local_db.get_database_stats()

        # Criar janela de registros
        registros_window = tk.Toplevel(self.master)
        registros_window.title("Registros Locais")
        registros_window.geometry("800x600")
        registros_window.configure(bg="#1a1a2e")

        # Header com estatísticas
        header_frame = tk.Frame(registros_window, bg="#16213e")
        header_frame.pack(fill="x", padx=10, pady=10)

        stats_text = f"Total: {stats['total_registrations']} | Pendentes: {stats['pending_sync']} | Sincronizados: {stats['synced']} | Erros: {stats['error']}"
        tk.Label(header_frame, text=stats_text, bg="#16213e", fg="white", font=("Segoe UI", 12, "bold")).pack(pady=10)

        # Lista de registros
        list_frame = tk.Frame(registros_window, bg="#1a1a2e")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        # Listbox
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, bg="#2d2d44", fg="white", font=("Segoe UI", 10))
        listbox.pack(fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        # Adicionar registros à lista
        for registro in registros:
            status_icon = {"pending": "⏳", "synced": "✅", "error": "❌"}.get(registro['sync_status'], "❓")
            item_text = f"{status_icon} {registro['name']} | {registro['group_name']} | {registro['phone']} | ID: {registro['id']}"
            listbox.insert(tk.END, item_text)

    def salvar_e_iniciar(self):
        """Valida dados e inicia captura"""
        name = self.name_var.get().strip()
        group = self.group_var.get().strip()
        phone = self.phone_var.get().strip()
        event = self.event_var.get().strip()

        if not all([name, group, phone]):
            messagebox.showerror("Erro", "Nome, Grupo e Telefone são obrigatórios!")
            return

        self.id_unico = gerar_id_unico()

        # Obter total de atendimentos do banco local
        registros = self.local_db.get_all_registrations()
        total_attendance = len(registros) + 1

        self.dados = {
            "id": self.id_unico,
            "name": name,
            "group": group,
            "phone": phone,
            "event": event if event else None,
            "total_attendance": total_attendance
        }

        self.status_label.config(
            text=f"📊 Cadastro #{total_attendance} • Iniciando webcam...",
            fg="#00d4ff"
        )

        # Inicia webcam
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            messagebox.showerror("Erro", "Não foi possível acessar a webcam")
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
            self.master.after(3000, self.capturar_e_salvar_local)

        # Atualiza imagem
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk, text="")

        self.master.after(30, self.atualizar_frame)

    def capturar_e_salvar_local(self):
        """Captura foto e salva no banco local"""
        if not self.cam or not self.cam.isOpened():
            return

        ret, frame = self.cam.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)

        # Criar diretório de imagens se não existir
        os.makedirs("Images", exist_ok=True)
        image_path = f"Images/{self.id_unico}.png"
        cv2.imwrite(image_path, frame)

        try:
            self.status_label.config(
                text="💾 Salvando no banco local...",
                fg="#00d4ff"
            )

            # Gerar encoding facial
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = face_recognition.face_locations(frame_rgb)
            encodings = face_recognition.face_encodings(frame_rgb, faces)

            encoding_data = None
            if encodings:
                encoding_data = serialize_encoding(encodings[0])

            # Adicionar dados extras
            self.dados['image_path'] = image_path
            self.dados['encoding'] = encoding_data
            self.dados['last_attendance_time'] = datetime.now().isoformat()

            # Salvar no banco local
            success = self.local_db.insert_registration(self.dados)

            if success:
                self.status_label.config(
                    text="🎉 Cadastro salvo localmente! Será sincronizado automaticamente.",
                    fg="#00ff88"
                )

                # Atualizar status do banco
                stats = self.local_db.get_database_stats()
                self.db_status.config(
                    text=f"💾 Banco Local: {stats['total_registrations']} registros",
                    fg="#00ff88"
                )
            else:
                self.status_label.config(
                    text="❌ Erro ao salvar no banco local",
                    fg="#ff6b6b"
                )

        except Exception as e:
            self.status_label.config(
                text=f"❌ Erro: {str(e)}",
                fg="#ff6b6b"
            )

        # Para a webcam
        self.cam.release()
        self.cam = None

        # Pergunta sobre novo cadastro
        self.master.after(500, self.perguntar_novo_cadastro)

    def perguntar_novo_cadastro(self):
        """Pergunta sobre novo cadastro"""
        resposta = messagebox.askyesno(
            "🎉 Cadastro Concluído!",
            "Cadastro facial salvo localmente!\n\n" +
            "Será sincronizado automaticamente quando houver conexão.\n\n" +
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
                self.auto_sync_enabled = False
                self.master.quit()
                self.master.destroy()

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


def main():
    """Função principal"""
    root = tk.Tk()
    app = OfflineFaceRegisterApp(root)

    # Configurar fechamento da aplicação
    def on_closing():
        app.auto_sync_enabled = False
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

